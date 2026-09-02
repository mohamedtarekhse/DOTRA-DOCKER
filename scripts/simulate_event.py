"""Simulate LPR events & intrusion alerts for testing without real cameras.

Usage:
    python simulate_event.py --plate ABC-1234 --in
    python simulate_event.py --plate DEF-5678 --out
    python simulate_event.py --intrusion
"""
import argparse
import os
import httpx

API_URL = os.environ.get("API_URL", "http://localhost:8001/api/v1")
LPR_SECRET = os.environ.get("LPR_EVENT_SECRET", "")
SECRET_HEADERS = {"X-Secret": LPR_SECRET} if LPR_SECRET else {}


def lpr(plate: str, direction: str):
    resp = httpx.post(
        f"{API_URL}/gates/lpr-event",
        json={"plate_number": plate, "direction": direction},
        headers=SECRET_HEADERS,
        timeout=10,
    )
    print(f"LPR event -> {resp.status_code}: {resp.text}")


def intrusion():
    resp = httpx.post(
        f"{API_URL}/alerts/intrusion",
        json={"zone": "Restricted Zone 1", "camera": "Cam-010",
              "detections": [{"label": "person", "confidence": 0.95}]},
        timeout=10,
    )
    print(f"Intrusion -> {resp.status_code}: {resp.text}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--plate", help="plate number")
    parser.add_argument("--in", dest="direction_in", action="store_true")
    parser.add_argument("--out", dest="direction_out", action="store_true")
    parser.add_argument("--intrusion", action="store_true")
    args = parser.parse_args()

    if args.intrusion:
        intrusion()
    elif args.plate:
        direction = "in" if args.direction_in else "out"
        lpr(args.plate, direction)
    else:
        parser.print_help()
