"""P00 HTTP unit integration with an explicit fake service; no real-model evidence."""

import asyncio
import json
import threading
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from fastapi.testclient import TestClient

from flytrap.lab import api
from flytrap.lab.contracts import CALL_CAP, SEEDS

pytestmark = [pytest.mark.unit, pytest.mark.api]
BASE = "http://127.0.0.1"
REQUEST = dict(schema_version="flytrap-lab-request-1", a=[0] * 256, b=[255] * 256)


class FakeService:
    """Exercises HTTP transport and errors only, never invokes the model."""
    def __init__(self, error=None):
        self.error = error
        self.requests = []

    def status(self):
        return dict(state="ready", message="synthetic unit service", attempted_calls=0,
                    call_cap=CALL_CAP, seeds=list(SEEDS), calls_per_comparison=9)

    def compare(self, request):
        self.requests.append(request)
        raise self.error or api.Unavailable("synthetic unit service has no model")


def client(service=None):
    return TestClient(api.create_lab_app(service or FakeService()), base_url=BASE)


def test_health_and_state_are_local_nonproduction_and_not_cacheable():
    with client() as http:
        response = http.get("/health/live")
        assert response.json() == {"status": "ok", "prototype": "P00", "production": False}
        assert response.headers["cache-control"] == "no-store"
        assert http.get("/api/lab/status").json()["seeds"] == [17, 29, 43]
        assert http.get("/health/live", headers={"host": "example.com"}).status_code == 400


@pytest.mark.parametrize("error,status", [(api.Busy("occupied"), 409), (api.Unavailable("data missing"), 503),
                                         (ValueError("bad model result"), 503), (OSError("read failed"), 503)])
def test_model_failures_are_explicit_http_states(error, status):
    fake = FakeService(error)
    with client(fake) as http:
        response = http.post("/api/lab/compare", json=REQUEST)
    assert response.status_code == status
    assert response.json() == {"detail": str(error)}
    assert fake.requests[0].model_dump() == REQUEST


@pytest.mark.parametrize("payload", [{**REQUEST, "a": [0] * 255}, {**REQUEST, "a": [True] * 256},
                                     {**REQUEST, "b": [256] * 256}, {**REQUEST, "seed": 1}])
def test_invalid_payload_never_reaches_service(payload):
    fake = FakeService()
    with client(fake) as http:
        assert http.post("/api/lab/compare", json=payload).status_code == 422
    assert fake.requests == []


def test_body_limit_origin_and_json_boundary_prevent_inference():
    fake = FakeService()
    with client(fake) as http:
        assert http.post("/api/lab/compare", content=b" " * (api.MAX_BODY + 1),
                         headers={"content-type": "application/json"}).status_code == 413
        assert http.post("/api/lab/compare", json=REQUEST,
                         headers={"origin": "https://foreign.example"}).status_code == 403
        assert http.post("/api/lab/compare", content=json.dumps(REQUEST),
                         headers={"content-type": "text/plain"}).status_code == 415
        assert http.post("/api/lab/compare", content="{broken",
                         headers={"content-type": "application/json"}).status_code == 422
    assert fake.requests == []


def test_same_origin_and_json_charset_are_accepted():
    fake = FakeService()
    with client(fake) as http:
        response = http.post("/api/lab/compare", content=json.dumps(REQUEST),
                             headers={"origin": BASE, "content-type": "application/json; charset=utf-8"})
    assert response.status_code == 503
    assert len(fake.requests) == 1


def test_chunked_payload_bound_is_enforced_without_content_length():
    async def scenario():
        fake = FakeService()
        transport = httpx.ASGITransport(app=api.create_lab_app(fake))

        async def chunks():
            yield b" " * 4096
            yield b" " * 4096
            yield b" "

        async with httpx.AsyncClient(transport=transport, base_url=BASE) as http:
            response = await http.post("/api/lab/compare", content=chunks(),
                                       headers={"content-type": "application/json"})
        assert response.status_code == 413
        assert fake.requests == []

    asyncio.run(scenario())


def test_model_slot_is_exclusive_across_instances_and_released_after_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "ARTIFACTS", tmp_path)
    first, second = api.LabService(), api.LabService()
    with pytest.raises(RuntimeError, match="synthetic work failed"):
        with first.slot():
            with pytest.raises(api.Busy):
                with second.slot():
                    pytest.fail("second model job admitted")
            raise RuntimeError("synthetic work failed")
    with second.slot():
        pass


def test_busy_state_and_budget_admission_without_model(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "ARTIFACTS", tmp_path)
    service = api.LabService()
    monkeypatch.setattr(service, "prerequisites", lambda: None)
    with service.slot():
        assert service.status()["state"] == "busy"
    assert service.status()["state"] == "ready"
    monkeypatch.undo()
    monkeypatch.setattr(api, "ARTIFACTS", tmp_path)
    service = api.LabService()
    # Stub only existence checks: budget admission is exercised without loading data.
    monkeypatch.setattr(api.Path, "is_file", lambda _: True)
    service.budget.path.write_text("".join(json.dumps({"attempt": i}) + "\n" for i in range(1, 249)))
    state = service.status()
    assert state["state"] == "unavailable"
    assert state["attempted_calls"] == 248
    assert "9-call" in state["message"]


def test_corrupt_ledger_is_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "ARTIFACTS", tmp_path)
    service = api.LabService()
    monkeypatch.setattr(api.Path, "is_file", lambda _: True)
    service.budget.path.write_text('{}\n')
    state = service.status()
    assert state["state"] == "unavailable"
    assert state["attempted_calls"] == CALL_CAP


def test_health_remains_responsive_while_fake_inference_thread_waits():
    started, release = threading.Event(), threading.Event()

    class SlowFake(FakeService):
        def compare(self, request):
            started.set()
            if not release.wait(timeout=5):
                raise AssertionError("test did not release fake inference")
            raise api.Unavailable("synthetic work finished")

    with client(SlowFake()) as http, ThreadPoolExecutor(max_workers=2) as pool:
        comparison = pool.submit(http.post, "/api/lab/compare", json=REQUEST)
        try:
            assert started.wait(timeout=5)
            health = pool.submit(http.get, "/health/live")
            assert health.result(timeout=2).status_code == 200
            assert not comparison.done()
        finally:
            release.set()
        assert comparison.result(timeout=5).status_code == 503


def test_local_root_routes_to_lab_screen():
    with TestClient(api.create_lab_app(), base_url="http://127.0.0.1") as client:
        response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/lab"
