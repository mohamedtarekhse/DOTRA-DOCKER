# HOW TO TEST ACUSEEK

These instructions assume you are running the **CPU-safe mode** (no GPU), which works on Docker Cloud / Play with Docker / your own VPS.

## Prerequisites
- Docker + Docker Compose available.
- Docker daemon running (check: `docker version`).

## 1. Start the stack (CPU-safe)
```bash
cd app
cp .env.example .env          # edit secrets (optional for local test)
docker compose -f docker-compose.yml -f docker-compose.play.yml up --build
```
Wait for all services to be "healthy". GPU service `ai-engine` runs on CPU via `Dockerfile.cpu`.

## 2. Verify the API is up
```bash
curl http://localhost:8001/health
# -> {"status":"ok","service":"api"}
```

## 3. Run the business-logic smoke test (7 checks)
Executes inside the api container (all deps present):
```bash
docker compose -f docker-compose.yml -f docker-compose.play.yml exec api python ./smoke_test.py
```
Expected output:
```
== 2. Vehicles ==
  [PASS] create vehicle
  [PASS] vehicle status whitelisted
== 3. Gate LPR entry ...
  [PASS] whitelisted entry granted
  [PASS] unknown entry denied
  [PASS] exit pending ...
  [PASS] exit granted after approval
...
=== RESULT: 7 passed, 0 failed ===
```

## 4. Seed demo data (vehicles, persons, indexed search images)
```bash
docker compose -f docker-compose.yml -f docker-compose.play.yml exec api python ./seed_demo.py
```
This inserts whitelisted vehicles, personnel, and placeholder CLIP-embedded snapshots so the AcuSeek image search returns results.

## 5. Open the dashboard
- Local: `http://localhost:80` (Nginx) → Dashboard / Gates / Vehicles / Persons / Image Search / Alerts
- API docs: `http://localhost:8001/api/docs`

## 6. Simulate an LPR event (no real camera needed)
```bash
docker compose -f docker-compose.yml -f docker-compose.play.yml exec api python ./simulate_event.py --plate ABC-1234 --in
docker compose -f docker-compose.yml -f docker-compose.play.yml exec api python ./simulate_event.py --plate ABC-1234 --out
```

## 7. Test the AcuSeek text-to-image search
After seeding:
```bash
curl "http://localhost:8001/api/v1/search/images?q=red%20truck"
```

---

## Common issues

| Symptom | Fix |
|---|---|
| `ai-engine` fails to start (nvidia) | Use the CPU override: `-f docker-compose.play.yml` |
| `cloudflared` errors | It's disabled in CPU mode (no tunnel token needed). |
| Image search returns empty | Run `seed_demo.py` first to index placeholder images. |
| Port already in use (80/8001) | Change ports in `docker-compose.yml`. |
