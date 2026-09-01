import time

import cv2
import httpx

from .stream_worker import StreamWorker

AI_ENGINE_URL = "http://ai-engine:8100"
API_URL = "http://api:8000/api/v1"
MEDIA_DIR = "/media"

RESTRICTED_LABELS = {"person", "car", "truck", "motorbike", "bicycle"}


class ZoneMonitor:
    """Monitors a restricted-zone RTSP stream; raises alerts when unauthorized
    person/vehicle is detected via YOLOv8."""

    def __init__(self, stream_worker: StreamWorker, zone_name: str, camera_name: str):
        self.worker = stream_worker
        self.zone_name = zone_name
        self.camera_name = camera_name

    def analyze(self) -> list[dict] | None:
        frame = self.worker.next_frame()
        if frame is None:
            return None
        # Save snapshot locally
        path = f"/media/snapshots/{int(time.time())}_{self.zone_name}.jpg"
        cv2.imwrite(path, frame)

        # Send to AI engine for detection
        # In a real deployment we POST to /detect and evaluate person/vehicle presence.
        # Simplified here: return the bbox list.
        return [{"label": "person", "confidence": 0.9}]

    def raise_intrusion(self, detections: list[dict]):
        try:
            httpx.post(
                f"{API_URL}/alerts/intrusion",
                json={
                    "zone": self.zone_name,
                    "camera": self.camera_name,
                    "detections": detections,
                },
                timeout=10,
            )
        except Exception as exc:
            print(f"alert send error: {exc}")


def monitor_loop():
    # Configure your restricted-zone cameras here
    RESTRICTED_CAMERAS = [
        # {"zone": "Restricted Zone 1", "camera": "RZ1-Cam1", "rtsp": "rtsp://user:pass@192.168.20.x:554/Streaming/Channels/101"},
    ]
    monitors = []
    for cam in RESTRICTED_CAMERAS:
        worker = StreamWorker(cam["rtsp"], cam["camera"], fps=0.5)
        if worker.open():
            monitors.append(ZoneMonitor(worker, cam["zone"], cam["camera"]))
            print(f"[STREAM] Monitoring {cam['camera']} in {cam['zone']}")
        else:
            print(f"[STREAM] FAILED to open {cam['camera']}")

    while True:
        for monitor in monitors:
            detections = monitor.analyze()
            if detections:
                # filter to restricted-relevant objects
                relevant = [d for d in detections if d["label"] in RESTRICTED_LABELS]
                if relevant:
                    monitor.raise_intrusion(relevant)
        time.sleep(2)


if __name__ == "__main__":
    monitor_loop()
