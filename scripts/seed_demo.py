"""Seed demo data for testing ACUSEEK without real cameras.

Creates:
  - A few whitelisted vehicles
  - A couple of personnel
  - Indexed placeholder snapshots (embedded via the CPU ai-engine)
    so the AcuSeek-style image search returns results.

Requires the full stack running (api + ai-engine + postgres + minio).
Run inside the api container:
    docker compose exec api python ./seed_demo.py

Environment needed (set by docker compose):
  DATABASE_URL, MINIO_ENDPOINT, MINIO_ROOT_USER, MINIO_ROOT_PASSWORD,
  MINIO_PUBLIC_BASE, ADMIN_USERNAME, ADMIN_PASSWORD, API_URL, AI_ENGINE_URL
"""
import asyncio
import io
import json
import os
import uuid
from datetime import datetime, timezone

import asyncpg
import httpx
from PIL import Image, ImageDraw

API_URL = os.environ.get("API_URL", "http://localhost:8000/api/v1")
AI_ENGINE_URL = os.environ.get("AI_ENGINE_URL", "http://ai-engine:8100")
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://acuseek:acuseek_secret@postgres:5432/acuseek")

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "acuseek")

MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "minio:9000")
MINIO_ROOT_USER = os.environ.get("MINIO_ROOT_USER", "acuseek")
MINIO_ROOT_PASSWORD = os.environ.get("MINIO_ROOT_PASSWORD", "acuseek_minio_secret")
MINIO_PUBLIC_BASE = os.environ.get("MINIO_PUBLIC_BASE", "http://localhost/minio")


def _asyncpg_dsn(url: str) -> str:
    """asyncpg cannot handle SQLAlchemy-style drivers like postgresql+asyncpg://."""
    return url.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgres+asyncpg://", "postgres://"
    )


def make_placeholder_image(text: str, color: tuple) -> bytes:
    img = Image.new("RGB", (320, 200), color)
    ImageDraw.Draw(img).text((10, 10), text, fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def save_snapshot(data: bytes) -> str:
    from minio import Minio

    client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ROOT_USER,
        secret_key=MINIO_ROOT_PASSWORD,
        secure=False,
    )
    bucket = "snapshots"
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
    key = f"{datetime.now(timezone.utc).strftime('%Y/%m/%d')}/{uuid.uuid4().hex}.jpg"
    client.put_object(bucket, key, io.BytesIO(data), length=len(data), content_type="image/jpeg")
    return f"{MINIO_PUBLIC_BASE}/{bucket}/{key}"


SNAPSHOTS = [
    {"text": "red truck", "color": (200, 60, 60)},
    {"text": "forklift", "color": (240, 180, 60)},
    {"text": "person yellow vest", "color": (240, 240, 80)},
    {"text": "white van", "color": (220, 220, 220)},
    {"text": "worker helmet", "color": (70, 130, 180)},
    {"text": "blue sedan at gate", "color": (60, 90, 200)},
]


async def seed():
    async with httpx.AsyncClient(timeout=60) as client:
        # login (vehicles/persons require a JWT)
        login_resp = await client.post(
            f"{API_URL}/auth/login",
            json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
        )
        if login_resp.status_code != 200:
            raise SystemExit(
                f"Login failed ({login_resp.status_code}) — check ADMIN_USERNAME/ADMIN_PASSWORD"
            )
        headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}
        client.headers.update(headers)

        # ----- vehicles -----
        vehicles = [
            {"plate_number": "ABC-1234", "owner_name": "Ahmed Ali", "vehicle_type": "truck",
             "department": "Logistics", "is_whitelisted": True},
            {"plate_number": "DEF-5678", "owner_name": "Sara Mostafa", "vehicle_type": "van",
             "department": "Procurement", "is_whitelisted": True},
            {"plate_number": "GHI-9012", "owner_name": "Mohamed Tarek", "vehicle_type": "sedan",
             "department": "Management", "is_whitelisted": True},
        ]
        for v in vehicles:
            r = await client.post(f"{API_URL}/vehicles", json=v)
            print(f"vehicle {v['plate_number']} -> {r.status_code}")

        # ----- persons -----
        persons = [
            {"full_name": "Ahmed Ali", "department": "Security", "access_level": "security"},
            {"full_name": "Sara Mostafa", "department": "Admin", "access_level": "manager"},
            {"full_name": "Mohamed Tarek", "department": "Operations", "access_level": "standard"},
        ]
        for p in persons:
            r = await client.post(f"{API_URL}/persons", json=p)
            print(f"person {p['full_name']} -> {r.status_code}")

        # ----- indexed image search (direct DB insert via AI engine embeddings) -----
        conn = await asyncpg.connect(_asyncpg_dsn(DATABASE_URL))
        for i, snap in enumerate(SNAPSHOTS):
            data = make_placeholder_image(snap["text"], snap["color"])
            # CLIP embedding for the image via the ai-engine (text keyword ~ image semantics)
            tresp = await client.post(
                f"{AI_ENGINE_URL}/embed/text",
                json={"text": snap["text"]},
            )
            tre = tresp.json()["embedding"]
            if not tre:
                raise SystemExit("ai-engine returned an empty embedding")

            # Persist the placeholder so the stored URL renders via nginx /minio.
            image_url = save_snapshot(data)

            image_id = await conn.fetchval(
                "INSERT INTO image_store (image_url, metadata) VALUES ($1, $2::jsonb) RETURNING id",
                image_url,
                json.dumps({"caption": snap["text"]}),
            )
            emb_str = "[" + ",".join(str(f"{v:.6f}") for v in tre) + "]"
            await conn.execute(
                "INSERT INTO image_embeddings (image_id, clip_embedding) VALUES ($1, $2::vector)",
                image_id,
                emb_str,
            )
            print(f"indexed snapshot {i}: {snap['text']} (id={image_id})")

        await conn.close()

    print("\n=== Demo seed complete ===")
    print('Try:  curl -s "http://localhost:8001/api/v1/search/images?q=red%20truck"')


if __name__ == "__main__":
    asyncio.run(seed())