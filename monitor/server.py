"""
monitor/server.py – Live MJPEG dual-camera stream.

Streams both cameras as live video in your browser — no page reload.

Can be run in two ways:
  1. Automatically as part of main.py (imported and started in background)
  2. Standalone:  python monitor/server.py

How it works
------------
• main.py's camera module continuously saves frames to /tmp/ (~10 fps)
• This server reads those files and streams them as MJPEG to the browser

Press Ctrl+C to stop (if running standalone).
"""

import os, time, socket, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

CAM0_SAVE = "/tmp/fruit_capture_cam0.jpg"
CAM1_SAVE = "/tmp/fruit_capture_cam1.jpg"
PORT      = 8080
BOUNDARY  = b"--frame"

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Live Camera Monitor</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0f0f1a;color:#eee;font-family:sans-serif;padding:20px}
h1{text-align:center;color:#e94560;margin-bottom:16px;font-size:1.5em}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;max-width:1400px;margin:0 auto}
.card{background:#16213e;border-radius:10px;padding:12px;border:1px solid #1a3060}
.card h2{color:#57c5f7;font-size:.95em;margin-bottom:8px}
.card img{width:100%;border-radius:6px;display:block}
.best{grid-column:1/-1}
@media(max-width:700px){.grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<h1>&#127909; Live Camera Monitor</h1>
<div class="grid">
  <div class="card">
    <h2>Camera 0 &mdash; imx219</h2>
    <img id="cam0" alt="cam0">
  </div>
  <div class="card">
    <h2>Camera 1 &mdash; ov5647</h2>
    <img id="cam1" alt="cam1">
  </div>
  <div class="card best">
    <h2>&#10003; Best result (last detection by main.py)</h2>
    <img id="best" alt="best">
  </div>
</div>
<script>
// Use JS-based image refresh instead of native MJPEG <img> streams.
// Native MJPEG can cause browsers to only render one stream at a time.
function startStream(imgId, url) {
  var img = document.getElementById(imgId);
  function refresh() {
    var newImg = new Image();
    newImg.onload = function() {
      img.src = newImg.src;
      setTimeout(refresh, 100);
    };
    newImg.onerror = function() {
      setTimeout(refresh, 500);
    };
    newImg.src = url + '?t=' + Date.now();
  }
  refresh();
}
startStream('cam0', '/snapshot/0');
startStream('cam1', '/snapshot/1');
startStream('best', '/snapshot/best');
</script>
</body>
</html>
"""


# ─── Per-camera frame buffer ──────────────────────────────────────────────

class FrameBuffer:
    """Thread-safe buffer holding the latest JPEG bytes for one camera."""
    def __init__(self):
        self._cond  = threading.Condition()
        self._frame = None
        self._seq   = 0          # sequence counter

    def put(self, jpeg_bytes: bytes):
        with self._cond:
            self._frame = jpeg_bytes
            self._seq += 1
            self._cond.notify_all()      # wake ALL waiting consumers

    def get(self) -> bytes | None:
        with self._cond:
            return self._frame

    def wait_for_new(self, last_seq: int, timeout=1.0) -> tuple:
        """Wait until a new frame is available (seq > last_seq)."""
        with self._cond:
            self._cond.wait_for(lambda: self._seq > last_seq, timeout=timeout)
            return self._frame, self._seq


# Global buffers
_buffers = {
    "0":    FrameBuffer(),
    "1":    FrameBuffer(),
    "best": FrameBuffer(),
}


def _file_stream_thread(key: str, path: str):
    """
    Reads a saved JPEG file continuously and pushes to buffer.
    camera.py's background threads update these files at ~10 fps.
    """
    buf = _buffers[key]
    last_data = None
    while True:
        try:
            if os.path.exists(path):
                with open(path, "rb") as f:
                    data = f.read()
                # Only push if we got valid data that is different from last
                if data and len(data) > 100 and data != last_data:
                    buf.put(data)
                    last_data = data
        except Exception:
            pass
        time.sleep(0.08)  # ~12 fps polling


def _mjpeg_chunks(key: str):
    """Yields raw bytes for an MJPEG multipart stream."""
    buf = _buffers[key]
    last_seq = 0
    while True:
        frame, last_seq = buf.wait_for_new(last_seq, timeout=1.0)
        if frame is None:
            continue
        yield (
            BOUNDARY + b"\r\n"
            b"Content-Type: image/jpeg\r\n"
            b"Content-Length: " + str(len(frame)).encode() + b"\r\n\r\n"
            + frame + b"\r\n"
        )


# ─── HTTP handler ────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]

        if path in ("/", ""):
            data = HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(data)

        elif path.startswith("/snapshot/"):
            # Single JPEG snapshot – used by the JS-based refresh loop
            key = path[len("/snapshot/"):]
            if key not in _buffers:
                self.send_error(404)
                return
            frame = _buffers[key].get()
            if frame is None:
                self.send_error(503, "No frame available yet")
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(frame)))
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            try:
                self.wfile.write(frame)
            except (BrokenPipeError, ConnectionResetError):
                pass

        elif path.startswith("/stream/"):
            key = path[len("/stream/"):]
            if key not in _buffers:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header(
                "Content-Type",
                "multipart/x-mixed-replace; boundary=frame"
            )
            self.end_headers()
            try:
                for chunk in _mjpeg_chunks(key):
                    self.wfile.write(chunk)
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass   # client disconnected

        else:
            self.send_error(404)

    def log_message(self, *a):
        pass


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle each request in a separate thread so both MJPEG streams run."""
    daemon_threads = True
    allow_reuse_address = True
    allow_reuse_port = True


# ─── Public API (used by main.py) ────────────────────────────────────────────

def start_monitor(port: int = PORT):
    """
    Start the monitor server in background threads.

    Call this from main.py to integrate the monitor automatically.
    The server runs entirely in daemon threads and stops when main.py exits.
    """
    try:
        ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        ip = "localhost"

    # Start file-streaming threads for each camera
    for key, path in [("0", CAM0_SAVE), ("1", CAM1_SAVE)]:
        t = threading.Thread(target=_file_stream_thread, args=(key, path), daemon=True)
        t.start()

    # Start best-result file watcher
    t = threading.Thread(
        target=_file_stream_thread, args=("best", "/tmp/fruit_capture.jpg"), daemon=True
    )
    t.start()

    # Start HTTP server in a daemon thread
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    print("=" * 50)
    print("  Live Camera Monitor (MJPEG)")
    print("=" * 50)
    print(f"  http://{ip}:{port}")
    print(f"  http://localhost:{port}")
    print("=" * 50)

    return server


# ─── Standalone entry point ──────────────────────────────────────────────────

if __name__ == "__main__":
    server = start_monitor()
    print()
    print("  Running standalone. Ctrl+C to stop.")
    print("  Streams saved images from /tmp/ if available.")
    print()
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopped.")
