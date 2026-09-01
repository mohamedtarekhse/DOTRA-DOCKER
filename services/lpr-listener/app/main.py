import logging
import os
import time

import httpx
import xmltodict

from .isapi_client import ISAPIClient
from .event_processor import normalize_plate, arabic_plate_to_latin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("lpr-listener")

API_URL = os.environ.get("API_URL", "http://api:8000/api/v1")
LPR_EVENT_SECRET = os.environ.get("LPR_EVENT_SECRET", "lpr_secret")

# Configure your LPR cameras here (Gate 1 & Gate 2)
LPR_CAMERAS = [
    # {"name": "Gate1-LPR1", "ip": "192.168.20.11", "user": "admin", "pass": "password"},
    # {"name": "Gate1-LPR2", "ip": "192.168.20.12", "user": "admin", "pass": "password"},
    # {"name": "Gate2-LPR1", "ip": "192.168.20.21", "user": "admin", "pass": "password"},
    # {"name": "Gate2-LPR2", "ip": "192.168.20.22", "user": "admin", "pass": "password"},
]


def process_event(plate: str, direction: str, gate: str):
    """Send a recognized plate to the API gate service."""
    plate = arabic_plate_to_latin(plate)
    plate = normalize_plate(plate)
    if not plate:
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
    """Poll Hikvision LPR camera for recent plate events (HTTP mode).
    Real deployments use Hikvision's HTTP alarm push to this server instead.
    """
    client = ISAPIClient(cam["ip"], cam["user"], cam["pass"])
    if not client.test_connection():
        logger.warning(f"[{cam['name']}] offline")
        return
    try:
        resp = httpx.get(
            f"http://{cam['ip']}:80/ISAPI/Traffic/channels/1/vehicleDetect/plates",
            headers={"Authorization": "Basic placeholder"}, timeout=5,
        )
        # Note: real implementation polls or receives HTTP push; simplified here.
        logger.info(f"[{cam['name']}] poll HTTP {resp.status_code}")
    except Exception as exc:
        logger.error(f"[{cam['name']}] poll error {exc}")


def main():
    logger.info("Starting LPR Listener...")
    logger.info(f"API_URL={API_URL}")
    while True:
        for cam in LPR_CAMERAS:
            try:
                poll_camera(cam)
            except Exception as exc:
                logger.error(f"[{cam['name']}] {exc}")
        time.sleep(5)


if __name__ == "__main__":
    main()
