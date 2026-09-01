import argparse

import cv2


class StreamWorker:
    """Threaded RTSP frame grabber using OpenCV. Samples at low FPS for AI."""

    def __init__(self, rtsp_url: str, name: str, fps: float = 0.5):
        self.rtsp_url = rtsp_url
        self.name = name
        self.interval = 1.0 / fps if fps > 0 else 2.0
        self.cap = None
        self.running = False

    def open(self) -> bool:
        self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
        if not self.cap.isOpened():
            self.cap = None
            return False
        self.running = True
        return True

    def next_frame(self):
        """Blocking grab of a single decoded frame. Returns BGR numpy array or None."""
        if self.cap is None:
            return None
        ok, frame = self.cap.read()
        return frame if ok else None

    def close(self):
        self.running = False
        if self.cap:
            self.cap.release()
            self.cap = None


def build_rtsp_url(ip: str, user: str, password: str, port: int = 554, channel: int = 1, subtype: int = 1) -> str:
    """Build a Hikvision RTSP URL for the sub-stream (lower resolution, for AI)."""
    return f"rtsp://{user}:{password}@{ip}:{port}/Streaming/Channels/{channel}{subtype}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test RTSP stream grab")
    parser.add_argument("--url", required=True, help="RTSP URL")
    parser.add_argument("--fps", type=float, default=0.5)
    args = parser.parse_args()
    worker = StreamWorker(args.url, "test", args.fps)
    if worker.open():
        print("Stream connected. Grabbing sample frames...")
        for _ in range(int(args.fps * 5)):
            frame = worker.next_frame()
            if frame is not None:
                print(f"frame shape={frame.shape}")
    else:
        print("Failed to open stream")
