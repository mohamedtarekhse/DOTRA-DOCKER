"""Verify dashboard has seeded data and search works."""
import asyncio
import httpx

API = "http://localhost:8000/api/v1"
DASH = "http://acuseek-nginx-1"

async def main():
    async with httpx.AsyncClient(timeout=15) as c:
        # Login
        r = await c.post(f"{API}/auth/login", json={"username": "admin", "password": "acuseek"})
        token = r.json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}

        # Cameras
        r = await c.get(f"{API}/cameras", headers=h)
        cams = r.json()
        print(f"Cameras: {len(cams)}")
        for cam in cams:
            print(f"  {cam['name']} ({cam['type']}) - {cam['ip_address']}")

        # Image search (all)
        r = await c.get(f"{API}/search/images", headers=h, params={"q": "", "limit": 20})
        imgs = r.json()
        print(f"\nImages in DB: {len(imgs)}")

        # Text search
        for q in ["red truck", "person walking", "loading dock", "license plate"]:
            r = await c.get(f"{API}/search/images", headers=h, params={"q": q, "limit": 3})
            results = r.json()
            scores = [f"{s['score']:.4f}" for s in results]
            print(f"  Search '{q}': {len(results)} results scores={scores}")

        # Dashboard page check
        r = await c.get(f"{DASH}/login")
        print(f"\nDashboard login page: {r.status_code}")

        # Vehicles count
        r = await c.get(f"{API}/vehicles", headers=h)
        vehs = r.json()
        print(f"Vehicles: {len(vehs)}")
        for v in vehs:
            print(f"  {v['plate']} ({v['vehicle_type']}) - whitelisted={v.get('whitelisted', False)}")

        # Persons count
        r = await c.get(f"{API}/persons", headers=h)
        persons = r.json()
        print(f"Persons: {len(persons)}")
        for p in persons:
            print(f"  {p['full_name']} ({p['department']})")

asyncio.run(main())
