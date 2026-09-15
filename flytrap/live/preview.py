"""Explicit CLI preview: private loopback reads, expires without model work."""
import base64
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import secrets
import socket
import threading
import time
import uuid

from .capture import Capture
from .encoding import preview_pair


PAGE = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Flyjam source preview</title><style>
body{background:#101b28;color:#edf3fa;font:18px system-ui;max-width:850px;margin:32px auto;padding:16px}
.pair{display:flex;gap:24px;flex-wrap:wrap}canvas{max-width:100%;background:#000;image-rendering:pixelated}
pre{white-space:pre-wrap;overflow-wrap:anywhere}h2{font-size:18px}</style>
<h1>Explicit source preview</h1><p>Expires automatically. No neural inference. Recording is off.</p>
<p id="state">Waiting for source</p><div class="pair"><section><h2>Latest source (thumbnail)</h2>
<canvas id="source"></canvas></section><section><h2>Exact 16 × 16 observation</h2>
<canvas id="encoded" width="16" height="16" style="width:160px;height:160px"></canvas></section></div>
<pre id="identity"></pre><script>
function draw(id,w,h,bytes,gray=false){const c=document.getElementById(id);c.width=w;c.height=h;
 const ctx=c.getContext('2d'), im=ctx.createImageData(w,h);
 for(let i=0;i<w*h;i++){for(let j=0;j<3;j++)im.data[i*4+j]=gray?bytes[i]:bytes[i*3+j];im.data[i*4+3]=255;}
 ctx.putImageData(im,0,0);}
async function update(){try{const r=await fetch(location.pathname+'/frame',{cache:'no-store'});
 if(!r.ok)throw Error();const p=await r.json();document.getElementById('state').textContent=
 p.label+' · '+p.status.state+' · producer: '+p.status.producer+' · '+(p.status.reason||'');
 if(p.frame){draw('source',p.preview_width,p.preview_height,Uint8Array.from(atob(p.preview_rgb),c=>c.charCodeAt(0)));
 draw('encoded',16,16,p.observation_u8,true);document.getElementById('identity').textContent=
 'Both previews: '+p.frame.source_id+' / '+p.frame.session_id+' / generation '+p.frame.generation+
 ' / frame '+p.frame.sequence+'\\nObservation SHA256: '+p.observation_sha256;}
 if(p.status.state==='previewing'||p.status.state==='starting')setTimeout(update,150);
 }catch{document.getElementById('state').textContent='Preview ended or connection lost. Capture expires automatically.';}}
update();</script></html>"""


def preview_payload(capture):
    status = capture.status()
    frame = capture.slot.latest()
    payload = {"status": asdict(status), "frame": None,
               "label": "SYNTHETIC FIXTURE" if capture.slot.identity[0] == "fixture-pattern"
               else ("OBS producer active; source-app freshness unknown" if status.verified_live
                     else "UNVERIFIED OBS PREVIEW"), "neural_calls": 0, "recording": False}
    if frame is not None and status.state == "previewing":
        pair = preview_pair(frame)
        payload.update(frame=frame.identity.model_dump(mode="json"), preview_width=pair.source.width,
                       preview_height=pair.source.height, preview_rgb=base64.b64encode(pair.source.rgb).decode("ascii"),
                       observation_u8=list(pair.encoded.u8), observation_sha256=pair.encoded.sha256)
    return payload


def run_preview(*, source_id: str, duration_s: float = 15, port: int = 8768, monitor=None, verified=False):
    if not 0 < duration_s <= 30 or type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError("Preview requires an unprivileged port and duration of at most 30 seconds.")
    token = secrets.token_urlsafe(24)
    route = f"/preview/{token}"
    capture = Capture(source_id=source_id, session_id=uuid.uuid4().hex, generation=1,
                      duration_s=duration_s, monitor=monitor, verified=verified)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Never log private frame endpoints or request data.

        def setup(self):
            super().setup()
            self.connection.settimeout(.25)

        def handle(self):
            # Socket inactivity alone permits a slow sender to extend parsing
            # forever. Enforce an absolute deadline for each accepted request.
            def expire():
                try:
                    self.connection.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
            timer = threading.Timer(.25, expire)
            timer.daemon = True
            timer.start()
            try:
                super().handle()
            except OSError:
                pass
            finally:
                timer.cancel()

        def do_GET(self):
            origin = f"http://127.0.0.1:{port}"
            if (self.headers.get("Host") != f"127.0.0.1:{port}"
                    or self.headers.get("Origin", origin) != origin):
                self.send_error(403)
                return
            if self.path == route:
                payload, content_type = PAGE.encode(), "text/html; charset=utf-8"
            elif self.path == route + "/frame":
                payload = json.dumps(preview_payload(capture)).encode()
                content_type = "application/json"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'unsafe-inline'; "
                             "style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            try:
                self.wfile.write(payload)
            except (OSError, TimeoutError):
                pass

    # Acquire the port before opening the selected source. Never kill a listener.
    with HTTPServer(("127.0.0.1", port), Handler) as server:
        server.timeout = .1
        try:
            capture.start()
            print(f"Preview: http://127.0.0.1:{port}{route} (expires after {duration_s:g}s)", flush=True)
            deadline = time.monotonic() + duration_s
            while time.monotonic() < deadline and capture.status().state == "previewing":
                server.handle_request()
        except KeyboardInterrupt:
            pass
        finally:
            status = capture.stop()
            print(json.dumps({"capture": asdict(status), "neural_calls": 0, "recording": False}), flush=True)
    return 2 if status.state in ("failed", "source_lost") else 0
