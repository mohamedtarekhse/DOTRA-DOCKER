"""Pre-register 90 factory cameras + zones via the API.

Run inside the api container:
    docker compose exec api python ./seed_cameras.py
"""
import os

import httpx

API_URL = os.environ.get("API_URL", "http://localhost:8001/api/v1")

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "acuseek")

ZONES = [
    ("Gate 1", "gate", False),
    ("Gate 2", "gate", False),
    ("Loading Dock A", "loading_dock", True),
    ("Loading Dock B", "loading_dock", True),
    ("Warehouse", "warehouse", False),
    ("Production Hall", "production", False),
    ("Restricted Zone 1", "restricted", True),
    ("Restricted Zone 2", "restricted", True),
]

CAMERA_PLAN = [
    # (name, ip, camera_type, zone_idx, rtsp_user, rtsp_pass)
    ("Gate1-LPR-1", "192.168.20.11", "lpr", 0, "admin", "camera_pass"),
    ("Gate1-LPR-2", "192.168.20.12", "lpr", 0, "admin", "camera_pass"),
    ("Gate1-Overview", "192.168.20.13", "overview_ptz", 0, "admin", "camera_pass"),
    ("Gate1-Face", "192.168.20.14", "face", 0, "admin", "camera_pass"),
    ("Gate2-LPR-1", "192.168.20.21", "lpr", 1, "admin", "camera_pass"),
    ("Gate2-LPR-2", "192.168.20.22", "lpr", 1, "admin", "camera_pass"),
    ("Gate2-Overview", "192.168.20.23", "overview_ptz", 1, "admin", "camera_pass"),
    ("Gate2-Face", "192.168.20.24", "face", 1, "admin", "camera_pass"),
]

# Expand to 90 cameras across production/warehouse/loading zones
count = len(CAMERA_PLAN)
for i in range(count + 1, 91):
    zone_idx = 2 + ((i - count - 1) % 6)  # distribute among zones 2..7
    CAMERA_PLAN.append(
        (f"Cam-{i:03d}", f"192.168.20.{i}", "fixed_bullet", zone_idx, "admin", "camera_pass")
    )


def seed():
    client = httpx.Client(timeout=10)
    login = client.post(f"{API_URL}/auth/login",
                        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD})
    if login.status_code != 200:
        raise SystemExit(f"Login failed ({login.status_code}) — check ADMIN_USERNAME/ADMIN_PASSWORD")
    client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"

    zone_ids = []
    zones = client.get(f"{API_URL}/cameras/zones").json()
    if not zones:
        for name, ztype, restricted in ZONES:
            r = client.post(f"{API_URL}/cameras/zones",
                            json={"name": name, "zone_type": ztype, "is_restricted": restricted})
            if r.status_code == 200:
                zone_ids.append(r.json()["id"])
                print(f"  + zone {name}")
            else:
                print(f"  ! zone {name} failed: {r.text}")
    else:
        zone_ids = [z["id"] for z in zones][:8]

    created = 0
    for name, ip, ctype, zidx, user, pwd in CAMERA_PLAN:
        rtsp = f"rtsp://{user}:{pwd}@{ip}:554/Streaming/Channels/101"
        payload = {
            "name": name,
            "ip_address": ip,
            "camera_type": ctype,
            "rtsp_url": rtsp,
            "zone_id": zone_ids[zidx] if zidx < len(zone_ids) else None,
            "config": {"rtsp_user": user, "rtsp_pass": pwd},
        }
        r = client.post(f"{API_URL}/cameras", json=payload)
        if r.status_code == 200:
            created += 1
        else:
            print(f"  ! {name} failed: {r.text}")
    print(f"Seeded {created} cameras into {len(zone_ids)} zones.")


if __name__ == "__main__":
    seed()
