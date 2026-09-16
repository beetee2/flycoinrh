"""GPU01 headed Screen Gremlin comparison using only generated safe imagery.

Consumes exactly 32 attempts per backend when successful. Never retries a
session, records video, selects a desktop device, or uses human accounting.
"""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

import numpy as np
from playwright.async_api import async_playwright, expect

from flytrap.live.accounting import LiveLedger

ROOT = Path(__file__).resolve().parents[1]
BASELINE_ATTEMPTS = 219
TASK_ATTEMPT_CAP = 384
CALLS = 32

INSTRUMENT = """(() => {
  const evidence = window.gpu01 = {requests: [], snapshots: [], draws: [], start: null};
  const record = (value, transport) => {
    if (value && value.schema_version === 'obs-api-snapshot-1')
      evidence.snapshots.push({browser_ms: performance.now(), transport, value});
  };
  const originalFetch = window.fetch;
  window.fetch = async (...args) => {
    const path = new URL(typeof args[0] === 'string' ? args[0] : args[0].url, location.href).pathname;
    const begin = performance.now();
    if (path === '/api/live/sessions') evidence.start = begin;
    const response = await originalFetch(...args);
    const end = performance.now();
    evidence.requests.push({path, begin_ms: begin, headers_ms: end, status: response.status});
    if (/^\\/api\\/live\\/sessions(?:\\/[^/]+(?:\\/renew|\\/stop)?)?$/.test(path)) {
      const value = await response.clone().json(); record(value, 'fetch');
    }
    return response;
  };
  const NativeEventSource = window.EventSource;
  window.EventSource = class extends NativeEventSource {
    constructor(...args) { super(...args); this.addEventListener('snapshot', event => record(JSON.parse(event.data), 'sse')); }
  };
})();"""


def stats(values):
    values = list(values)
    return {"samples": len(values), "median": float(np.median(values)) if values else None,
            "p95": float(np.percentile(values, 95)) if values else None}


def allowance(required):
    ledger = LiveLedger.automated(ROOT)
    count = ledger.attempted
    if count + required > BASELINE_ATTEMPTS + TASK_ATTEMPT_CAP or ledger.remaining < required:
        raise RuntimeError(f"GPU01 browser requires {required} attempts; current global count is {count}")
    return count


def free_port():
    with socket.socket() as channel:
        channel.bind(("127.0.0.1", 0))
        return channel.getsockname()[1]


def resource_sample(server_pid, browser_pids):
    processes = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            data = (entry / "stat").read_text().split(") ", 1)[1].split()
            processes[int(entry.name)] = {"ppid": int(data[1]),
                "cpu_seconds": (int(data[11]) + int(data[12])) / os.sysconf("SC_CLK_TCK"),
                "rss_bytes": int(data[21]) * os.sysconf("SC_PAGE_SIZE")}
        except (OSError, ValueError, IndexError):
            continue
    owned = {server_pid}
    while True:
        children = {pid for pid, info in processes.items() if info["ppid"] in owned}
        if children <= owned:
            break
        owned |= children
    selected = {str(pid): {**info, "kind": "service_worker" if pid in owned else "browser"}
                for pid, info in processes.items() if pid in owned or pid in browser_pids}
    gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.used,memory.free,utilization.gpu",
                          "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5)
    return {"python_monotonic_ms": time.monotonic() * 1000, "processes": selected,
            "gpu_csv": gpu.stdout.strip(), "gpu_exit": gpu.returncode}


async def wait_ready(server, base):
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        if server.poll() is not None:
            raise RuntimeError(f"Owned service exited during startup: {server.returncode}")
        try:
            with urllib.request.urlopen(base + "/health/live", timeout=.4) as reply:
                if reply.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            pass
        await asyncio.sleep(.1)
    raise RuntimeError("Owned service startup timed out")


def summarize(data):
    snapshots = data["snapshots"]
    samples = {}
    for event in snapshots:
        sample = event["value"].get("last_inferred")
        if sample is not None:
            samples.setdefault(sample["step_index"], event)
    ordered = [samples[key] for key in sorted(samples)]
    if not ordered:
        return {"completed_samples_observed": 0}
    start, end = ordered[0]["browser_ms"], ordered[-1]["browser_ms"]
    draws = [entry for entry in data["draws"] if start <= entry["browser_ms"] <= end]
    intervals = [b["browser_ms"]-a["browser_ms"] for a, b in zip(draws, draws[1:])]
    receipts = [entry["browser_ms"] for entry in ordered]
    completions = [entry["value"]["last_inferred"]["completed_monotonic_ms"] for entry in ordered]
    accepted_age = [entry["value"]["last_inferred"]["completed_monotonic_ms"]
                    - entry["value"]["last_inferred"]["frame"]["receipt_monotonic_ms"] for entry in ordered]
    rtts = [entry["headers_ms"]-entry["begin_ms"] for entry in data["requests"]
            if start <= entry["begin_ms"] <= end and entry["path"].endswith("/display")]
    return {"completed_samples_observed": len(ordered), "active_browser_window_ms": end-start,
        "render_draw_interval_ms": stats(intervals), "completed_draw_samples": len(draws),
        "observed_draw_hz": (len(draws)-1)*1000/(draws[-1]["browser_ms"]-draws[0]["browser_ms"]) if len(draws)>1 else None,
        "browser_neural_receipt_interval_ms": stats(b-a for a, b in zip(receipts, receipts[1:])),
        "server_neural_completion_interval_ms": stats(b-a for a, b in zip(completions, completions[1:])),
        "accepted_frame_receipt_to_completion_ms": stats(accepted_age),
        "server_reported_response_age_ms": stats(entry["value"]["response_age_ms"] for entry in ordered
                                                  if entry["value"]["response_age_ms"] is not None),
        "server_completion_to_publication_ms": stats(entry["value"]["sent_monotonic_ms"]
            - entry["value"]["last_inferred"]["completed_monotonic_ms"] for entry in ordered),
        "last_step_wall_ms": stats(entry["value"]["last_step_wall_ms"] for entry in ordered
                                   if entry["value"]["last_step_wall_ms"] is not None),
        "display_fetch_headers_rtt_ms": stats(rtts),
        "start_to_first_neural_receipt_browser_ms": start-data["start"],
        "source_sequences": [entry["value"]["last_inferred"]["frame"]["sequence"] for entry in ordered],
        "source_clock_sequences": [entry["value"]["last_inferred"]["frame"]["source_sequence"] for entry in ordered],
        "observation_sha256": [hashlib.sha256(bytes(entry["value"]["last_inferred"]["observation_u8"])).hexdigest()
                               for entry in ordered],
        "model_ids": sorted({entry["value"]["last_inferred"]["model_id"] for entry in ordered}),
        "clock_note": "Intervals use one clock each; browser and Python monotonic values are never subtracted.",
        "render_note": "DOM-observed completed Screen Gremlin draws/DOM commits between first and last neural receipt, including interpolation; not GPU-present/vblank timing or display FPS."}


def active_resources(result):
    """Derive active resources from stored evidence using the host's common CLOCK_MONOTONIC."""
    snapshots = result["browser"]["snapshots"]
    completed = [entry["value"]["last_inferred"]["completed_monotonic_ms"] for entry in snapshots
                 if entry["value"].get("last_inferred") is not None]
    first, last = min(completed), max(completed)
    resources = [entry for entry in result["resources"] if first <= entry["python_monotonic_ms"] <= last]
    output = {"samples": len(resources), "server_window_ms": last-first,
              "clock_note": "All host processes use the same Linux CLOCK_MONOTONIC; browser clocks are excluded."}
    for kind in ("service_worker", "browser"):
        totals = [(entry["python_monotonic_ms"], sum(process["rss_bytes"] for process in entry["processes"].values()
                   if process["kind"] == kind), {pid: process["cpu_seconds"] for pid, process in entry["processes"].items()
                   if process["kind"] == kind}) for entry in resources]
        cpu_percent = [100000 * sum(max(0, b[2][pid]-a[2][pid]) for pid in b[2].keys() & a[2].keys()) / (b[0]-a[0])
                       for a, b in zip(totals, totals[1:]) if b[0] > a[0]]
        output[kind+"_rss_bytes"] = stats(entry[1] for entry in totals)
        output[kind+"_cpu_percent_one_core"] = stats(cpu_percent)
    values = [[float(part.strip()) for part in entry["gpu_csv"].split(",")[1:]] for entry in resources
              if entry["gpu_exit"] == 0 and len(entry["gpu_csv"].split(",")) == 4]
    output["whole_card_used_mib"] = stats(entry[0] for entry in values)
    output["whole_card_free_mib"] = stats(entry[1] for entry in values)
    output["whole_card_utilization_percent"] = stats(entry[2] for entry in values)
    output["limitations"] = "Whole-card readings include the user's existing desktop; RSS includes shared pages. CPU 100% is one core; only sampled surviving owned processes are included."
    ready = next((entry for entry in snapshots if entry["value"]["status"]["state"] == "running"), None)
    output["start_to_worker_ready_snapshot_browser_ms"] = None if ready is None else ready["browser_ms"]-result["browser"]["start"]
    return output


async def run_backend(playwright, backend, output, executable):
    initial_count = allowance(CALLS)
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    command = [sys.executable, "-m", "flytrap.live", "serve", "--safe-source", "--execution-purpose",
               "automated", "--backend", backend, "--port", str(port)]
    result = {"backend": backend, "source": "fixture-pattern; deterministic generated imagery only",
        "recording": "off; no video capture", "calls_requested": CALLS, "initial_ledger_count": initial_count,
        "command": command, "resources": [], "status": "FAIL"}
    browser = page = server = None
    log = (output / f"{backend}-server.log").open("x")
    try:
        began = time.perf_counter()
        server = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        await wait_ready(server, base)
        result["service_startup_ms"] = (time.perf_counter()-began)*1000
        browser = await playwright.chromium.launch(executable_path=executable, headless=False,
            chromium_sandbox=True, ignore_default_args=["--enable-unsafe-swiftshader"])
        result["browser_version"] = browser.version
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        await context.add_init_script(INSTRUMENT)
        page = await context.new_page()
        await page.goto(base + "/live")
        await page.bring_to_front()
        await expect(page.get_by_test_id("graphics-state")).to_have_text("Ready")
        await expect(page.get_by_label("Presentation", exact=True)).to_have_value("screen-gremlin")
        result["renderer"] = await page.locator(".flight-canvas canvas").evaluate("""canvas => {
          const gl = canvas.getContext('webgl2'), extension = gl.getExtension('WEBGL_debug_renderer_info');
          return {renderer: gl.getParameter(extension ? extension.UNMASKED_RENDERER_WEBGL : gl.RENDERER),
                  vendor: gl.getParameter(extension ? extension.UNMASKED_VENDOR_WEBGL : gl.VENDOR)};
        }""")
        if any(word in result["renderer"]["renderer"].lower() for word in ("swiftshader", "llvmpipe", "software")):
            raise RuntimeError("A hardware-accelerated visible browser is required")
        capabilities = await (await context.request.get(base + "/api/live/capabilities")).json()
        if capabilities["neural_backend"] != backend or not capabilities["inference"]:
            raise RuntimeError("Service backend/capability mismatch")
        result["ui_backend_label"] = await page.get_by_test_id("neural-backend").text_content()
        await expect(page.get_by_test_id("neural-backend")).to_contain_text("CUDA" if backend == "cuda" else "CPU")
        await page.get_by_role("button", name="Live source", exact=True).click()
        await page.get_by_role("combobox", name="Source", exact=True).select_option("fixture-pattern")
        await page.get_by_label("Maximum model calls", exact=True).fill(str(CALLS))
        await page.get_by_label("Session duration (seconds)", exact=True).fill("120")
        await page.get_by_label("Seed", exact=True).fill("17")
        await expect(page.get_by_label("Record this session locally", exact=True)).not_to_be_checked()
        await page.evaluate("""() => {
          new MutationObserver(() => {
            const pose = JSON.parse(document.querySelector('[data-testid="rendered-pose"]').textContent);
            if (pose) window.gpu01.draws.push({browser_ms: performance.now(), tick: pose.tick, position: pose.position});
          }).observe(document.querySelector('[data-testid="rendered-pose"]'), {childList: true, subtree: true, characterData: true});
        }""")
        cdp = await browser.new_browser_cdp_session()
        browser_pids = {int(entry["id"]) for entry in (await cdp.send("SystemInfo.getProcessInfo"))["processInfo"]}
        allowance(CALLS)
        await page.get_by_role("button", name="Start live flight", exact=True).click()
        # Keep the actual character canvas visible while inference and capture run.
        await page.locator(".flight-viewport").scroll_into_view_if_needed()
        if await page.evaluate("document.visibilityState") != "visible":
            raise RuntimeError("Screen Gremlin browser must remain visible")
        screenshot_taken = False
        deadline = time.monotonic()+145
        while time.monotonic() < deadline:
            result["resources"].append(await asyncio.to_thread(resource_sample, server.pid, browser_pids))
            latest = await page.evaluate("window.gpu01.snapshots.at(-1)?.value ?? null")
            if latest:
                state = latest["status"]["state"]
                if not screenshot_taken and latest["completed_calls"] >= 2:
                    await page.locator(".flight-viewport").screenshot(path=str(output / f"{backend}-safe-generated.png"))
                    screenshot_taken = True
                if state in {"failed", "source_lost", "stopped", "limit_reached"}:
                    result["terminal"] = latest
                    break
            await asyncio.sleep(.25)
        else:
            raise RuntimeError("Session did not reach its terminal call cap")
        result["browser"] = await page.evaluate("window.gpu01")
        result["summary"] = summarize(result["browser"])
        result["active_resources"] = active_resources(result)
        for kind in ("service_worker", "browser"):
            totals = [(entry["python_monotonic_ms"], sum(process["rss_bytes"] for process in entry["processes"].values()
                       if process["kind"] == kind), {pid: process["cpu_seconds"] for pid, process in entry["processes"].items()
                       if process["kind"] == kind}) for entry in result["resources"]]
            cpu_percent = [100000 * sum(max(0, b[2][pid]-a[2][pid]) for pid in b[2].keys() & a[2].keys()) / (b[0]-a[0])
                           for a, b in zip(totals, totals[1:]) if b[0] > a[0]]
            result["summary"][kind+"_rss_bytes"] = stats(entry[1] for entry in totals)
            result["summary"][kind+"_cpu_percent_one_core"] = stats(cpu_percent)
        result["summary"]["resource_note"] = "RSS sums include shared pages; CPU is summed owned process time, 100% equals one CPU core. Exited process tails may be absent."
        result["summary"]["instrumentation_note"] = "Browser observers, duplicate telemetry JSON parsing, resource polling and one safe screenshot are included in measured wall time."
        terminal = result["terminal"]
        if terminal["status"]["state"] != "limit_reached" or terminal["completed_calls"] != CALLS:
            raise RuntimeError(f"Incomplete {backend} run: {terminal['status']['state']}, {terminal['completed_calls']} completed")
        if terminal["recording_state"] != "off":
            raise RuntimeError("Recording unexpectedly enabled")
        result["status"] = "PASS"
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        if page is not None:
            try:
                result["browser"] = await page.evaluate("window.gpu01")
            except Exception:
                pass
        raise
    finally:
        if page is not None:
            try:
                button = page.get_by_role("button", name="Stop session", exact=True).first
                if await button.is_enabled():
                    await button.click(timeout=3000)
            except Exception:
                pass
        if browser is not None:
            await browser.close()
        if server is not None and server.poll() is None:
            server.terminate()
            try:
                await asyncio.to_thread(server.wait, 10)
            except subprocess.TimeoutExpired:
                server.kill()
                await asyncio.to_thread(server.wait, 5)
        log.close()
        result["final_ledger_count"] = LiveLedger.automated(ROOT).attempted
        result["attempts_consumed"] = result["final_ledger_count"]-initial_count
        (output / f"{backend}.json").write_text(json.dumps(result, indent=2)+"\n")
    if result["attempts_consumed"] != CALLS:
        raise RuntimeError("Durable attempt count disagrees with requested browser cap")
    return result


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/milestones/GPU01/browser")
    parser.add_argument("--browser", default="/opt/google/chrome/chrome")
    args = parser.parse_args()
    # Fail before either CPU or CUDA session if the qualification is not ready.
    from flytrap.live.gpu import require_qualified_gpu
    require_qualified_gpu()
    allowance(2*CALLS)
    if not os.environ.get("DISPLAY"):
        raise RuntimeError("Headed browser requires the existing local display")
    args.output.mkdir(parents=True, exist_ok=True)
    if any((args.output / f"{backend}.json").exists() for backend in ("cpu", "cuda")):
        raise RuntimeError("Preserve previous browser evidence; select a new output directory")
    async with async_playwright() as playwright:
        results = [await run_backend(playwright, backend, args.output, args.browser) for backend in ("cpu", "cuda")]
    comparison = {"status": "PASS", "source": "generated fixture-pattern, recording off",
        "calls_per_backend": CALLS, "runs": {result["backend"]: result["summary"] for result in results},
        "limitation": "Higher inference cadence samples different source frames; this is live responsiveness, not fixed-input equivalence."}
    (args.output / "comparison.json").write_text(json.dumps(comparison, indent=2)+"\n")
    print(json.dumps(comparison, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
