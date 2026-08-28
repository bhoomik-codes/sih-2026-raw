import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import cv2

logger = logging.getLogger(__name__)


class MJPEGStreamer:
    """
    A lightweight, background HTTP server that serves the latest annotated
    video frame as an MJPEG stream over HTTP (multipart/x-mixed-replace).
    """

    def __init__(self, port: int = 8081):
        self.port = port
        self.frame_jpeg = b""
        self.server = None
        self.thread = None

    def update_frame(self, frame_bgr):
        """Encode the latest frame and update the stream buffer."""
        ret, jpeg = cv2.imencode(".jpg", frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 70])
        if ret:
            self.frame_jpeg = jpeg.tobytes()

    def start(self):
        class StreamingHandler(BaseHTTPRequestHandler):
            streamer = self

            def log_message(self, format, *args):
                # Suppress basic HTTP server logs to avoid console spam
                pass

            def do_GET(self):
                if self.path == "/stream":
                    self.send_response(200)
                    self.send_header("Age", "0")
                    self.send_header("Cache-Control", "no-cache, private")
                    self.send_header("Pragma", "no-cache")
                    self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=FRAME")
                    self.end_headers()
                    try:
                        while True:
                            frame = self.streamer.frame_jpeg
                            if frame:
                                self.wfile.write(b"--FRAME\r\n")
                                self.send_header("Content-Type", "image/jpeg")
                                self.send_header("Content-Length", str(len(frame)))
                                self.end_headers()
                                self.wfile.write(frame)
                                self.wfile.write(b"\r\n")
                            time.sleep(0.04)  # ~25 FPS max serving rate to prevent busy looping
                    except Exception:
                        # Client disconnected
                        pass
                else:
                    self.send_response(404)
                    self.end_headers()

        try:
            self.server = HTTPServer(("0.0.0.0", self.port), StreamingHandler)
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            logger.info(f"MJPEG Streamer started on port {self.port}")
        except Exception as e:
            logger.error(f"Failed to start MJPEG Streamer on port {self.port}: {e}")

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            logger.info("MJPEG Streamer stopped")
