"""Quick diagnostic for the 2 remaining test failures."""
import httpx
import asyncio
import traceback

BASE = "http://localhost:8000/api/v1"
LPR_SECRET = "lpr_secret"
SECRET = {"X-Secret": LPR_SECRET}

async def main():
    async with httpx.AsyncClient(timeout=15) as c:
        # Login
        r = await c.post(f"{BASE}/auth/login", json={"username": "admin", "password": "acuseek"})
        token = r.json()["access_token"]
        AUTH = {"Authorization": f"Bearer {token}"}

        # 1. Test search
        print("=== SEARCH TEST ===")
        try:
            r = await c.get(f"{BASE}/search/images", headers=AUTH, params={"q": "test", "limit": 5})
            print(f"Status: {r.status_code}")
            print(f"Body: {r.text[:500]}")
        except Exception as e:
            print(f"Error: {e}")
            traceback.print_exc()

        # 2. Test exit event with requires_exit_permission
        print("\n=== EXIT EVENT TEST ===")
        # First create a vehicle with requires_exit_permission
        import time
        plate = f"EX-{int(time.time()) % 100000:05d}"
        r = await c.post(f"{BASE}/vehicles", headers=AUTH, json={
            "plate_number": plate, "owner_name": "Exit Test",
            "vehicle_type": "truck", "department": "QA",
            "is_whitelisted": True, "requires_exit_permission": True,
        })
        print(f"Vehicle created: {r.status_code}")

        # Do entry first
        r = await c.post(f"{BASE}/gates/lpr-event", headers=SECRET, json={
            "plate_number": plate, "direction": "in",
        })
        entry = r.json()
        print(f"Entry: {entry}")

        # Now do exit
        r = await c.post(f"{BASE}/gates/lpr-event", headers=SECRET, json={
            "plate_number": plate, "direction": "out",
        })
        exit_resp = r.json()
        print(f"Exit: {exit_resp}")

        evt_id = exit_resp.get("event_id", "")
        print(f"event_id: '{evt_id}'")

        if evt_id:
            r = await c.post(f"{BASE}/gates/exit-approval", headers=AUTH, json={
                "event_id": evt_id, "approved": True, "manager": "test-mgr",
            })
            print(f"Approval: {r.status_code} {r.json()}")
        else:
            print("No event_id returned — exit may have been auto-granted or denied")

        # Cleanup
        vid_resp = await c.get(f"{BASE}/vehicles", headers=AUTH)
        for v in vid_resp.json():
            if v["plate_number"] == plate:
                await c.delete(f"{BASE}/vehicles/{v['id']}", headers=AUTH)
                print(f"Cleaned up vehicle {plate}")

asyncio.run(main())
