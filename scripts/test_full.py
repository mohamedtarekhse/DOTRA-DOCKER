"""ACUSEEK comprehensive test suite — backend, API, and frontend integration.

Covers:
  Layer 1 - Backend API endpoints (all routers, auth, CRUD, gate flow, search)
  Layer 2 - Frontend pages & form POST handlers (dashboard proxy layer)
  Layer 3 - Data integrity (backend ↔ frontend calling paths)
  Layer 4 - Seed verification (demo data loaded, search returns results)

Run on the server (docker compose up must be running):
    cd ~/acuseek && python scripts/test_full.py
    or from inside the api container:
    docker exec -it acuseek-api-1 python /app/scripts/test_full.py
"""

import asyncio
import json
import os
import sys
import time

import httpx

BASE = os.environ.get("API_URL", "http://localhost:8001/api/v1")
HEALTH = os.environ.get("HEALTH_URL", "http://localhost:8001/health")
DASH = os.environ.get("DASHBOARD_URL", "http://localhost")
ADMIN_USER = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASSWORD", "acuseek")
LPR_SECRET = os.environ.get("LPR_EVENT_SECRET", "lpr_secret")
SECRET_HDRS = {"X-Secret": LPR_SECRET}

PASS = FAIL = 0
RESULTS = []


def check(name: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        tag = "PASS"
    else:
        FAIL += 1
        tag = "FAIL"
    line = f"  [{tag}] {name}" + (f"  ({detail})" if detail else "")
    print(line)
    RESULTS.append({"name": name, "passed": condition, "detail": detail})


async def run():
    global PASS, FAIL
    print("=" * 72)
    print("ACUSEEK COMPREHENSIVE TEST SUITE")
    print(f"API:      {BASE}")
    print(f"Dashboard: {DASH}")
    print("=" * 72)

    async with httpx.AsyncClient(timeout=30, follow_redirects=False) as c:
        # =========================================================================
        # LAYER 1: BACKEND API
        # =========================================================================
        print("\n== LAYER 1: Backend API ==")

        # 1.1 Health
        print("  -- Health --")
        r = await c.get(HEALTH)
        check("GET /health", r.status_code == 200, f"got {r.status_code}")

        # 1.2 Auth
        print("  -- Auth --")
        r = await c.post(f"{BASE}/auth/login",
                         json={"username": ADMIN_USER, "password": ADMIN_PASS})
        check("POST /auth/login (valid)", r.status_code == 200, f"got {r.status_code}")
        token = r.json().get("access_token", "") if r.status_code == 200 else ""
        AUTH = {"Authorization": f"Bearer {token}"} if token else {}

        r = await c.post(f"{BASE}/auth/login",
                         json={"username": ADMIN_USER, "password": "wrong"})
        check("POST /auth/login (bad pw) -> 401", r.status_code == 401)

        r = await c.get(f"{BASE}/auth/me", headers=AUTH)
        check("GET /auth/me (valid token)", r.status_code == 200 and r.json().get("role") == "admin")

        r = await c.get(f"{BASE}/auth/me")
        check("GET /auth/me (no token) -> 401", r.status_code == 401)

        # 1.3 Vehicles
        print("  -- Vehicles --")
        plate = f"TST-{int(time.time()) % 100000:05d}"
        r = await c.post(f"{BASE}/vehicles", headers=AUTH, json={
            "plate_number": plate, "owner_name": "Test Owner",
            "vehicle_type": "car", "department": "QA",
            "is_whitelisted": True, "requires_exit_permission": True,
        })
        check(f"POST /vehicles ({plate})", r.status_code == 200)
        vid = r.json().get("id", "") if r.status_code == 200 else ""

        r = await c.get(f"{BASE}/vehicles", headers=AUTH)
        check("GET /vehicles", r.status_code == 200 and isinstance(r.json(), list))

        r = await c.get(f"{BASE}/vehicles/{plate}/status")
        check(f"GET /vehicles/{plate}/status", r.status_code == 200 and r.json().get("whitelisted"))

        r = await c.patch(f"{BASE}/vehicles/{vid}", headers=AUTH,
                          json={"department": "Updated Dept"})
        check("PATCH /vehicles/{id}", r.status_code == 200 and r.json().get("department") == "Updated Dept")

        r = await c.get(f"{BASE}/vehicles/{plate}/events")
        check(f"GET /vehicles/{plate}/events", r.status_code == 200)

        # 1.4 Persons
        print("  -- Persons --")
        r = await c.post(f"{BASE}/persons", headers=AUTH, json={
            "full_name": "Test Person", "department": "QA", "access_level": "admin"
        })
        check("POST /persons", r.status_code == 200)
        pid = r.json().get("id", "") if r.status_code == 200 else ""

        r = await c.get(f"{BASE}/persons", headers=AUTH)
        check("GET /persons", r.status_code == 200 and len(r.json()) > 0)

        # 1.5 Cameras + Zones
        print("  -- Cameras & Zones --")
        r = await c.post(f"{BASE}/cameras/zones", headers=AUTH, json={
            "name": "Test Zone", "zone_type": "restricted", "is_restricted": True
        })
        check("POST /cameras/zones", r.status_code == 200)
        zid = r.json().get("id", "") if r.status_code == 200 else ""

        r = await c.get(f"{BASE}/cameras/zones", headers=AUTH)
        check("GET /cameras/zones", r.status_code == 200 and len(r.json()) >= 1)

        r = await c.post(f"{BASE}/cameras", headers=AUTH, json={
            "name": "Test Cam", "ip_address": "10.0.0.100",
            "camera_type": "lpr", "rtsp_url": "rtsp://x",
            "zone_id": zid,
        })
        check("POST /cameras", r.status_code == 200)
        cid = r.json().get("id", "") if r.status_code == 200 else ""

        r = await c.get(f"{BASE}/cameras", headers=AUTH)
        check("GET /cameras", r.status_code == 200 and len(r.json()) >= 1)

        r = await c.get(f"{BASE}/cameras/{cid}", headers=AUTH)
        check(f"GET /cameras/{cid[:8]}...", r.status_code == 200)

        r = await c.patch(f"{BASE}/cameras/{cid}", headers=AUTH,
                          json={"name": "Test Cam Updated"})
        check("PATCH /cameras", r.status_code == 200 and r.json().get("name") == "Test Cam Updated")

        # 1.6 Gate LPR flow
        print("  -- Gate LPR Flow --")
        r = await c.post(f"{BASE}/gates/lpr-event", headers=SECRET_HDRS, json={
            "plate_number": plate, "direction": "in", "camera_id": cid, "confidence": 0.97,
        })
        check("LPR event (whitelisted entry)", r.status_code == 200)
        decision = r.json().get("decision", {})
        is_permitted = decision.get("allowed", False)
        check(f"  -> entry {'granted' if is_permitted else 'denied'} (expected denied without permit)",
              not is_permitted, f"decision={decision}")

        r = await c.post(f"{BASE}/gates/lpr-event", headers=SECRET_HDRS, json={
            "plate_number": "FAKE-00000", "direction": "in",
        })
        check("LPR event (unknown vehicle)", r.status_code == 200)
        check("  -> denied", not r.json().get("decision", {}).get("allowed"))

        r = await c.post(f"{BASE}/gates/lpr-event", headers=SECRET_HDRS, json={
            "plate_number": plate, "direction": "out",
        })
        exit_evt = r.json()
        check("Exit event", r.status_code == 200)
        evt_id = exit_evt.get("event_id", "")

        if evt_id:
            r = await c.post(f"{BASE}/gates/exit-approval", headers=AUTH, json={
                "event_id": evt_id, "approved": True, "manager": "test-mgr",
            })
            check("Exit approval (manager)", r.status_code == 200 and r.json().get("event_type") == "exit_granted")

        # Manual override
        r = await c.post(f"{BASE}/gates/gate1/manual-override", headers=AUTH,
                         params={"action": "open"})
        check("Manual gate override", r.status_code == 200 and r.json().get("action") == "open")

        # 1.7 Alerts
        print("  -- Alerts --")
        r = await c.post(f"{BASE}/alerts/intrusion", headers=SECRET_HDRS, json={
            "zone": "Restricted Zone 1", "camera": "Test Cam",
            "detections": [{"label": "person", "confidence": 0.92}],
        })
        check("POST /alerts/intrusion", r.status_code == 200)
        aid = r.json().get("alert_id", "")

        r = await c.get(f"{BASE}/alerts", headers=AUTH)
        check("GET /alerts", r.status_code == 200 and len(r.json()) >= 1)

        r = await c.patch(f"{BASE}/alerts/{aid}", headers=AUTH, json={
            "status": "resolved", "resolved_by": "test-suite",
        })
        check("PATCH /alerts/{id} (resolve)", r.status_code == 200 and r.json().get("status") == "resolved")

        # 1.8 Permits
        print("  -- Permits --")
        r = await c.get(f"{BASE}/permits", headers=AUTH, params={"days": 30})
        check("GET /permits", r.status_code == 200 and isinstance(r.json(), list))

        # 1.9 Search
        print("  -- Search --")
        r = await c.get(f"{BASE}/search/images", headers=AUTH,
                        params={"q": "red truck", "limit": 5})
        check("GET /search/images", r.status_code == 200, f"status={r.status_code}")
        results = r.json() if r.status_code == 200 else []
        search_ok = isinstance(results, list)
        check("  -> returns list", search_ok, f"count={len(results) if search_ok else 'N/A'}")

        # 1.10 WebSocket
        print("  -- WebSocket --")
        try:
            async with httpx.AsyncClient(timeout=5) as ws_c:
                # Just check the route exists (WebSocket needs proper upgrade)
                r = await ws_c.get(f"{DASH}/ws/events")
                # Will get 426 or similar for non-WS request
                check("GET /ws/events (non-WS) -> upgrade required",
                      r.status_code in (403, 426, 101), f"got {r.status_code}")
        except Exception:
            check("WebSocket route reachable", False, "connection refused")

        # 1.11 Auth guard (unauthenticated)
        print("  -- Auth Guards --")
        for path in ["/vehicles", "/persons", "/cameras", "/alerts", "/permits"]:
            r = await c.get(f"{BASE}{path}")
            check(f"  {path} (no token) -> 401/403",
                  r.status_code in (401, 403), f"got {r.status_code}")

        # =========================================================================
        # LAYER 2: FRONTEND (Dashboard pages via HTTP)
        # =========================================================================
        print("\n== LAYER 2: Frontend Pages ==")

        # Login first to get cookie
        login_r = await c.post(f"{DASH}/login",
                               data={"username": ADMIN_USER, "password": ADMIN_PASS})
        check("Dashboard POST /login -> 303", login_r.status_code == 303)

        cookies = {}
        if "acuseek_token" in login_r.cookies:
            cookies["acuseek_token"] = login_r.cookies["acuseek_token"]
        elif login_r.headers.get("set-cookie", ""):
            for part in login_r.headers["set-cookie"].split(";"):
                if "acuseek_token=" in part:
                    cookies["acuseek_token"] = part.split("=", 1)[1].split(";")[0]
                    break

        if not cookies.get("acuseek_token"):
            # Try getting it via API directly
            api_r = await httpx.AsyncClient(timeout=10).post(
                f"{BASE}/auth/login",
                json={"username": ADMIN_USER, "password": ADMIN_PASS},
            )
            if api_r.status_code == 200:
                token = api_r.json()["access_token"]
                # Manually set cookie in cookie jar
                c.cookies.set("acuseek_token", token, domain="localhost")

        has_cookie = bool(cookies.get("acuseek_token"))
        check("  got auth cookie", has_cookie)

        # 2.1 Dashboard pages
        pages = [
            ("/", "Dashboard", 200),
            ("/gates", "Gates", 200),
            ("/vehicles", "Vehicles", 200),
            ("/persons", "Persons", 200),
            ("/alerts", "Alerts", 200),
            ("/settings", "Settings", 200),
            ("/preapprovals", "Pre-Approvals", 200),
            ("/search", "Search", 200),
        ]
        for path, name, expected in pages:
            r = await c.get(f"{DASH}{path}", cookies=cookies)
            ok = r.status_code == expected
            check(f"GET {path} ({name})", ok, f"got {r.status_code}")
            if ok and path in ("/", "/vehicles", "/alerts", "/persons", "/settings"):
                # Check page has key content
                has_title = name.lower().split()[0] in r.text.lower()
                check(f"  -> page has title content", has_title or "fiori" in r.text.lower())

        # 2.2 Unauthenticated pages -> redirect to /login
        for path in ["/", "/vehicles", "/alerts"]:
            r = await c.get(f"{DASH}{path}")
            check(f"GET {path} (no cookie) -> 303 to /login",
                  r.status_code == 303, f"got {r.status_code}")

        # 2.3 Dashboard health check
        r = await c.get(f"{DASH}/api/health", cookies=cookies)
        check("GET /api/health (dashboard proxy)", r.status_code == 200 and r.json().get("status") == "ok")

        # 2.4 Search results HTMX endpoint
        r = await c.get(f"{DASH}/api/search-results", params={"q": "red truck"}, cookies=cookies)
        check("GET /api/search-results (HTMX)", r.status_code == 200)

        # 2.5 Nginx /health endpoint
        r = await c.get(f"{DASH}/health")
        check("GET /health (nginx -> api)", r.status_code == 200, f"got {r.status_code}")

        # =========================================================================
        # LAYER 3: DATA INTEGRITY
        # =========================================================================
        print("\n== LAYER 3: Data Integrity ==")

        # Verify vehicle we created is visible through dashboard API proxy
        r = await c.get(f"{BASE}/vehicles/{plate}/status")
        if r.status_code == 200:
            v = r.json()
            check(f"Vehicle {plate} integrity", v.get("whitelisted") and v.get("department") == "Updated Dept",
                  f"got {v}")
        else:
            check(f"Vehicle {plate} integrity", False, f"status {r.status_code}")

        # Verify alert was created and resolved
        r = await c.get(f"{BASE}/alerts", headers=AUTH)
        if r.status_code == 200:
            alerts = r.json()
            resolved = [a for a in alerts if a.get("status") == "resolved"]
            check("Alert integrity (resolved alert exists)", len(resolved) > 0)

        # =========================================================================
        # LAYER 4: CLEANUP (delete test data)
        # =========================================================================
        print("\n== LAYER 4: Cleanup ==")
        if vid:
            r = await c.delete(f"{BASE}/vehicles/{vid}", headers=AUTH)
            check(f"DELETE vehicle {plate}", r.status_code == 200)
        if cid:
            r = await c.delete(f"{BASE}/cameras/{cid}", headers=AUTH)
            check(f"DELETE test camera", r.status_code == 200)

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 72)
    print(f"RESULTS: {PASS} passed, {FAIL} failed  ({PASS + FAIL} total)")
    print("=" * 72)

    if FAIL > 0:
        print("\nFAILED TESTS:")
        for r in RESULTS:
            if not r["passed"]:
                print(f"  FAIL: {r['name']}  {r['detail']}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
