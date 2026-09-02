# ACUSEEK App

Factory monitoring & AI surveillance platform — LPR gate control, face recognition, restricted-zone intrusion alerts, and AcuSeek-style text-to-image search.

## Quick Start

```bash
# 1. Configure
cp .env.example .env     # edit secrets + Cloudflare tunnel token

# 2. Start everything (builds + boots all containers)
make up

# 3. Register 90 cameras + zones
make seed
```

## Access

| Layer | URL |
|---|---|
| Dashboard (LAN) | `http://192.168.10.50/` |
| Dashboard (remote) | `https://dash.yourfactory.com` |
| API docs | `http://192.168.10.50/api/docs` |
| MinIO Console | `http://192.168.10.50/minio-console/` |

## Services

| Service | Description |
|---|---|
| `api` | FastAPI business logic + REST API + JWT auth |
| `celery-worker` | Background: image indexing + retention cleanup |
| `ai-engine` | GPU microservice: InsightFace + OpenCLIP + YOLOv8 (CUDA) |
| `lpr-listener` | Hikvision ISAPI plate event receiver → gate logic |
| `stream-processor` | RTSP sub-stream sampling + restricted-zone intrusion detection |
| `dashboard` | Jinja2 + HTMX + Tailwind responsive UI |
| `postgres` | PostgreSQL 16 + pgvector(HNSW) |
| `redis` | Cache + Celery broker |
| `minio` | Object storage (snapshots, face/plate crops) |
| `mosquitto` | MQTT broker for gate relays |
| `nginx` | Unified LAN reverse proxy (single port 80) |
| `cloudflared` | Remote access via Cloudflare Tunnel (no open ports) |

## Configuration

### Cameras
Edit `services/lpr-listener/app/main.py` (`LPR_CAMERAS`) and
`services/stream-processor/app/zone_monitor.py` (`RESTRICTED_CAMERAS`)
with your real Hikvision IP/credentials.

### Camera RTSP URLs (Hikvision)
```
rtsp://<user>:<pass>@<IP>:554/Streaming/Channels/101   # main stream
rtsp://<user>:<pass>@<IP>:554/Streaming/Channels/102   # sub stream (AI)
```

### LPR HTTP push
Point Hikvision ANPR cameras' alarm output to:
```
http://192.168.10.50:8001/api/v1/gates/lpr-event
```
with header `X-Secret: <LPR_EVENT_SECRET>`.

## Tests (no cameras needed)

```bash
# simulate a whitelist check / exit approval
python scripts/simulate_event.py --plate YOURPLATE --in
python scripts/simulate_event.py --plate YOURPLATE --out

# simulate a restricted-zone intrusion alert
python scripts/simulate_event.py --intrusion
```

## Backup

```bash
make backup     # pg_dump to ./backups
```

## Rollout reference
See `HARDWARE_SHOPPING_LIST_40CAM.md` for the 40-camera baseline hardware & Hikvision camera bill of materials (the 90-camera deployment is described in the root `PROCEDURE.md`).
