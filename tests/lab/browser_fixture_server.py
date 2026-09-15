"""Actual lab HTTP/UI with an explicitly unavailable synthetic model boundary.

The P00 result schema permits only real results. This fixture therefore tests
editing, submission and recoverable failure without inventing a real result or
touching the protected P00 model, budget, locks or artifacts.
"""
import argparse

import uvicorn

from flytrap.lab.api import Unavailable, create_lab_app
from flytrap.lab.contracts import CALL_CAP, SEEDS


class SyntheticUnavailableService:
    def __init__(self):
        self.requests = []

    def status(self):
        return dict(state="ready", message="SYNTHETIC browser fixture; model unavailable",
                    attempted_calls=0, call_cap=CALL_CAP, seeds=list(SEEDS),
                    calls_per_comparison=9)

    def compare(self, request):
        self.requests.append(request.model_dump())
        raise Unavailable("SYNTHETIC browser fixture: no model calls or result")


def create_fixture_app():
    service = SyntheticUnavailableService()
    app = create_lab_app(service)

    @app.get("/fixture/requests")
    def requests():
        return {"fixture": True, "model_calls": 0, "requests": service.requests}

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8898)
    args = parser.parse_args()
    uvicorn.run(create_fixture_app(), host="127.0.0.1", port=args.port)
