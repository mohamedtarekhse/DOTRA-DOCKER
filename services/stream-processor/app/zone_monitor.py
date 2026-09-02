import logging
import os
import time

import cv2
import httpx

from .stream_worker import StreamWorker

logger = logging.getLogger("zone-monitor")

AI_ENGINE_URL = os.environ.get("AI_ENGINE_URL", "http://ai-engine:8100")
API_URL = os.environ.get("API_URL", "http://api:8000/api/v1")
LPR_EVENT_SECRET = os.environ.get("LPR_EVENT_SECRET", "lpr_secret")
MEDIA_DIR = os.environ.get("MEDIA_DIR", "/media")
INTRUSION_COOLDOWN = float(os.environ.get("INTRUSION_COOLDOWN", "60"))

RESTRICTED_LABELS = {"person", "car", "truck", "motorbike", "bicycle"}


class ZoneMonitor:
    """Monitors a restricted-zone RTSP stream; raises alerts when unauthorized
    person/vehicle is detected via YOLOv8 (/detect)."""

    def __init__(self, stream_worker: StreamWorker, zone_name: str, camera_name: str):
        self.worker = stream_worker
        self.zone_name = zone_name
        self.camera_name = camera_name
        self._last_alert = 0.0

    def _snapshot_path(self) -> str:
        os.makedirs(f"{MEDIA_DIR}/snapshots", exist_ok=True)
        return f"{MEDIA_DIR}/snapshots/{int(time.time())}_{self.zone_name}.jpg"

    def analyze(self) -> list[dict]:
        """Grab a frame and ask the AI engine for detections.

        Returns the raw YOLO detections (empty list when no frame/detect error).
        The frame is saved to the shared /media volume and passed to /detect as a
        local path (ai-engine mounts the same volume).
        """
        frame = self.worker.next_frame()
        if frame is None:
            return []
        path = self._snapshot_path()
        if not cv2.imwrite(path, frame):
            logger.warning(f"[{self.camera_name}] failed to save snapshot {path}")
            return []

        try:
            resp = httpx.post(
                f"{AI_ENGINE_URL}/detect",
                json={"image_url": path},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json().get("detections", [])
        except Exception as exc:
            logger.error(f"[{self.camera_name}] /detect failed: {exc}")
            return []

    def raise_intrusion(self, detections: list[dict]):
        now = time.time()
        if now - self._last_alert < INTRUSION_COOLDOWN:
            return
        try:
            resp = httpx.post(
                f"{API_URL}/alerts/intrusion",
                headers={"X-Secret": LPR_EVENT_SECRET},
                json={
                    "zone": self.zone_name,
                    "camera": self.camera_name,
                    "detections": detections,
                },
                timeout=10,
            )
            logger.info(f"[{self.camera_name}] intrusion alert -> {resp.status_code}")
            if resp.status_code == 200:
                self._last_alert = now
        except Exception as exc:
            logger.error(f"[{self.camera_name}] alert send error: {exc}")


def monitor_loop():
    # Configure restricted-zone cameras here OR via the RESTRICTED_CAMERAS JSON
    # env var (Coolify-friendly). Each entry:
    # {"zone": ..., "camera": ..., "rtsp": "rtsp://user:pass@ip:554/Streaming/Channels/101"}
    import json as _json
    _cams = os.environ.get("RESTRICTED_CAMERAS", "[]")
    RESTRICTED_CAMERAS = _json.loads(_cams)

    monitors = []
    for cam in RESTRICTED_CAMERAS:
        worker = StreamWorker(cam["rtsp"], cam["camera"], fps=0.5)
        if worker.open():
            monitors.append(ZoneMonitor(worker, cam["zone"], cam["camera"]))
            logger.info(f"[STREAM] Monitoring {cam['camera']} in {cam['zone']}")
        else:
            logger.warning(f"[STREAM] FAILED to open {cam['camera']}")

    while True:
        for monitor in monitors:
            detections = monitor.analyze()
            relevant = [d for d in detections if d.get("label") in RESTRICTED_LABELS]
            if relevant:
                monitor.raise_intrusion(relevant)
        time.sleep(2)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    monitor_loop()