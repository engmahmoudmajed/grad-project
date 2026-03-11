"""
monitor/server.py – Live MJPEG dual-camera stream.

Streams both cameras as live video in your browser — no page reload.

Run ALONGSIDE main.py in a separate terminal:
    python monitor/server.py
    Open:  http://<pi-ip>:8080

How it works
------------
• If a camera is FREE  → opens it directly and streams live frames (~15 fps)
• If a camera is BUSY  → streams the last saved image from disk repeatedly
  This means even while main.py is running you still see the last captured frame.

Press Ctrl+C to stop.
"""

import os, io, time, socket, threading
from http.server import HTTPServer, BaseHTTPRequestHandler

try:
    from picamera2 import Picamera2
    import cv2
    HAS_CAM = True
except ImportError:
    HAS_CAM = False

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
    <h2>Camera 0 &mdash; ov5647</h2>
    <img src="/stream/0" alt="cam0">
  </div>
  <div class="card">
    <h2>Camera 1 &mdash; imx219</h2>
    <img src="/stream/1" alt="cam1">
  </div>
  <div class="card best">
    <h2>&#10003; Best result (last detection by main.py)</h2>
    <img src="/stream/best" alt="best">
  </div>
</div>
</body>
</html>
"""


# ─── Per-camera MJPEG frame buffer ─────────────────────────────────────────

class FrameBuffer:
    """Thread-safe buffer holding the latest JPEG bytes for one camera."""
    def __init__(self):
        self._lock  = threading.Lock()
        self._frame = None
        self._event = threading.Event()

    def put(self, jpeg_bytes: bytes):
        with self._lock:
            self._frame = jpeg_bytes
        self._event.set()
        self._event.clear()

    def get(self) -> bytes | None:
        with self._lock:
            return self._frame

    def wait(self, timeout=1.0):
        self._event.wait(timeout)


# Global buffers
_buffers = {
    "0":    FrameBuffer(),
    "1":    FrameBuffer(),
    "best": FrameBuffer(),
}


def _open_camera(index: int):
    """Try video then still config; return (cam, mode) or None."""
    for mode in ("video", "still"):
        try:
            cam = Picamera2(index)
            if mode == "video":
                cfg = cam.create_video_configuration(
                    main={"size": (640, 480), "format": "RGB888"}
                )
            else:
                cfg = cam.create_still_configuration(
                    main={"size": (640, 480), "format": "RGB888"}
                )
            cam.configure(cfg)
            cam.start()
            print(f"  [cam{index}] Opened in {mode} mode ✓")
            return cam, mode
        except Exception as e:
            print(f"  [cam{index}] {mode} mode failed: {e}")
            try: cam.close()
            except Exception: pass
    print(f"  [cam{index}] Both modes failed – using saved images")
    return None, None


def _cam_thread(index: int, save_path: str):
    """Background thread: captures frames and pushes to FrameBuffer."""
    key = str(index)
    buf = _buffers[key]

    cam, mode = _open_camera(index) if HAS_CAM else (None, None)

    while True:
        try:
            if cam is not None:
                # Live capture
                if mode == "video":
                    frame_rgb = cam.capture_array()
                else:
                    cam.start()  # still mode needs start each capture
                    frame_rgb = cam.capture_array()
                    cam.stop()
                import numpy as np, cv2
                frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                ok, enc = cv2.imencode(".jpg", frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 70])
                if ok:
                    buf.put(enc.tobytes())
            else:
                # Fallback: read last saved file from main.py
                if os.path.exists(save_path):
                    with open(save_path, "rb") as f:
                        buf.put(f.read())
                time.sleep(0.2)   # 5 fps from file
        except Exception as e:
            print(f"  [cam{index}] frame error: {e}")
            time.sleep(0.5)


def _file_thread(key: str, path: str):
    """Streams a saved file continuously (for 'best' result panel)."""
    buf = _buffers[key]
    last_mtime = 0
    while True:
        try:
            if os.path.exists(path):
                mt = os.path.getmtime(path)
                if mt != last_mtime:
                    with open(path, "rb") as f:
                        buf.put(f.read())
                    last_mtime = mt
        except Exception:
            pass
        time.sleep(0.25)


def _mjpeg_chunks(key: str):
    """Yields raw bytes for an MJPEG multipart stream."""
    buf = _buffers[key]
    while True:
        buf.wait(timeout=1.0)
        frame = buf.get()
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

        elif path.startswith("/stream/"):
            key = path[len("/stream/"):]
            if key not in _buffers:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header(
                "Content-Type",
                f"multipart/x-mixed-replace; boundary=frame"
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


# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        ip = "localhost"

    # Start camera capture threads with a 1s delay between them
    # (prevents libcamera race when both cameras initialise simultaneously)
    for idx, save in ((0, CAM0_SAVE), (1, CAM1_SAVE)):
        t = threading.Thread(target=_cam_thread, args=(idx, save), daemon=True)
        t.start()
        time.sleep(1.2)   # give cam(idx) time to fully init before opening next

    # Start best-result file watcher
    t = threading.Thread(
        target=_file_thread, args=("best", "/tmp/fruit_capture.jpg"), daemon=True
    )
    t.start()

    print("=" * 50)
    print("  Live Camera Monitor (MJPEG)")
    print("=" * 50)
    print(f"  http://{ip}:{PORT}")
    print(f"  http://localhost:{PORT}")
    print()
    print("  If cameras are busy (main.py running),")
    print("  shows last saved frames from disk.")
    print("  Ctrl+C to stop.")
    print("=" * 50)

    try:
        server = HTTPServer(("0.0.0.0", PORT), Handler)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
