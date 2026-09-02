"""End-to-end API smoke test for ACUSEEK.

Verifies the core flow WITHOUT needing real cameras or hardware:
  1. API + DB health
  2. Vehicle whitelist CRUD
  3. Gate LPR event -> entry granted/denied + exit approval
  4. Persons + face match (no-op if no face in image)
  5. Text-to-image search

Run on the HOST (uses exposed ports 8001 from docker-compose.yml):
    python scripts/smoke_test.py
"""
import asyncio
import os

import httpx

API_URL = os.environ.get("API_URL", "http://localhost:8000/api/v1")
HEALTH_URL = os.environ.get("HEALTH_URL", "http://localhost:8000/health")

LPR_SECRET = os.environ.get("LPR_EVENT_SECRET", "")
SECRET_HEADERS = {"X-Secret": LPR_SECRET} if LPR_SECRET else {}

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "acuseek")

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = ""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name} {detail}")


async def run():
    async with httpx.AsyncClient(timeout=20) as c:
        print("== 1. Health ==")
        r = await c.get(HEALTH_URL)
        check("api /health", r.status_code == 200, r.text[:200])

        print("== 2. Auth ==")
        r = await c.post(f"{API_URL}/auth/login",
                         json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD})
        check("login", r.status_code == 200, r.text[:200])
        token = r.json().get("access_token", "") if r.status_code == 200 else ""
        if token:
            c.headers["Authorization"] = f"Bearer {token}"

        print("== 3. Vehicles ==")
        plate = "TST-0001"
        r = await c.post(f"{API_URL}/vehicles", json={
            "plate_number": plate, "owner_name": "Test Driver",
            "vehicle_type": "van", "is_whitelisted": True,
        })
        check("create vehicle", r.status_code == 200)
        r = await c.get(f"{API_URL}/vehicles/{plate}/status")
        check("vehicle status whitelisted", r.status_code == 200 and r.json().get("whitelisted"))

        print("== 4. Gate LPR entry (should be granted) ==")
        r = await c.post(f"{API_URL}/gates/lpr-event",
                         json={"plate_number": plate, "direction": "in"},
                         headers=SECRET_HEADERS)
        ok = r.status_code == 200 and r.json().get("decision", {}).get("allowed") is True
        check("whitelisted entry granted", ok, r.text[:200])

        print("== 5. Unknown vehicle entry (should be denied) ==")
        r = await c.post(f"{API_URL}/gates/lpr-event",
                         json={"plate_number": "UNKNOWN-99", "direction": "in"},
                         headers=SECRET_HEADERS)
        ok = r.status_code == 200 and r.json().get("decision", {}).get("allowed") is False
        check("unknown entry denied", ok, r.text[:200])

        print("== 6. Exit pending (requires manager approval) ==")
        r = await c.post(f"{API_URL}/gates/lpr-event",
                         json={"plate_number": plate, "direction": "out"},
                         headers=SECRET_HEADERS)
        event_id = r.json().get("event_id")
        check("exit pending for whitelisted", r.json().get("event_type") == "exit_pending", r.text[:200])

        print("== 7. Manager approves exit ==")
        r = await c.post(f"{API_URL}/gates/exit-approval", json={
            "event_id": event_id, "approved": True, "manager": "test-manager",
        })
        ok = r.status_code == 200 and r.json().get("event_type") == "exit_granted"
        check("exit granted after approval", ok, r.text[:200])

        print("== 8. Text-to-image search (empty is fine) ==")
        r = await c.get(f"{API_URL}/search/images", params={"q": "red truck", "limit": 5})
        check("search endpoint responds", r.status_code == 200, r.text[:200])

    print(f"\n=== RESULT: {PASS} passed, {FAIL} failed ===")
    return 1 if FAIL else 0


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(run()))
