import json
import logging
import os
import time

import httpx

from .event_processor import normalize_plate, arabic_plate_to_latin, parse_plates
from .isapi_client import ISAPIClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("lpr-listener")

API_URL = os.environ.get("API_URL", "http://api:8000/api/v1")
LPR_EVENT_SECRET = os.environ.get("LPR_EVENT_SECRET", "lpr_secret")
POLL_INTERVAL = float(os.environ.get("LPR_POLL_INTERVAL", "5"))

# Configure LPR cameras here OR via the LPR_CAMERAS JSON env var (Coolify-friendly).
# Each entry: {"name": ..., "ip": ..., "user": ..., "pass": ...}
# Example: LPR_CAMERAS='[{"name":"Gate1-LPR1","ip":"192.168.20.11","user":"admin","pass":"pw"}]'
LPR_CAMERAS = json.loads(os.environ.get("LPR_CAMERAS") or "[]")

# Dedup cache so a plate that stays in the camera's result list isn't re-sent.
RECENT_LIMIT = 200
_recent_sent: dict[str, float] = {}


def _is_recent(key: str) -> bool:
    now = time.time()
    sent_at = _recent_sent.get(key)
    if sent_at is not None and now - sent_at < 60:
        return True
    if len(_recent_sent) >= RECENT_LIMIT:
        _recent_sent.clear()
    _recent_sent[key] = now
    return False


def process_event(plate: str, direction: str, gate: str):
    """Send a recognized plate to the API gate service."""
    plate = arabic_plate_to_latin(plate)
    plate = normalize_plate(plate)
    if not plate:
        return
    key = f"{plate}|{direction}"
    if _is_recent(key):
        return
    try:
        resp = httpx.post(
            f"{API_URL}/gates/lpr-event",
            headers={"X-Secret": LPR_EVENT_SECRET},
            json={"plate_number": plate, "direction": direction},
            timeout=10,
        )
        logger.info(f"[{gate}] plate={plate} dir={direction} -> {resp.status_code} {resp.text[:200]}")
    except Exception as exc:
        logger.error(f"[{gate}] send failed: {exc}")


def poll_camera(cam: dict):
    """Poll a Hikvision LPR camera's plate channel (ISAPI Digest auth)."""
    client = ISAPIClient(cam["ip"], cam.get("user", "admin"), cam.get("pass", ""))
    if not client.test_connection():
        logger.warning(f"[{cam['name']}] offline")
        return
    try:
        xml_text = client.get_plates()
    except Exception as exc:
        logger.error(f"[{cam['name']}] plate channel error {exc}")
        return

    plates = parse_plates(xml_text)
    if not plates:
        return
    logger.info(f"[{cam['name']}] {len(plates)} plate(s) seen")
    for p in plates:
        process_event(p["plate_number"], p["direction"], cam["name"])


def main():
    logger.info("Starting LPR Listener...")
    logger.info(f"API_URL={API_URL}  cameras_configured={len(LPR_CAMERAS)}")
    while True:
        for cam in LPR_CAMERAS:
            try:
                poll_camera(cam)
            except Exception as exc:
                logger.error(f"[{cam['name']}] {exc}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()