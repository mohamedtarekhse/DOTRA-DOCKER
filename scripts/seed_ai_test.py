#!/usr/bin/env python3
"""ACUSEEK comprehensive seed + AI test script.

Creates cameras (CCTV, LPR, PTZ), generates 10 synthetic test images,
uploads them to MinIO, creates DB records, generates AI embeddings,
and benchmarks GPU/AI performance.

Run inside the API container:
    docker exec -it acuseek-api-1 python /app/scripts/seed_ai_test.py
"""

import asyncio
import io
import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone, timedelta
from uuid import uuid4

import httpx
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://acuseek:acuseek_secret@postgres:5432/acuseek",
)
AI_ENGINE_URL = os.environ.get("AI_ENGINE_URL", "http://ai-engine:8100")
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "minio:9000")
MINIO_USER = os.environ.get("MINIO_ROOT_USER", "acuseek")
MINIO_PASS = os.environ.get("MINIO_ROOT_PASSWORD", "acuseek_minio_secret")
MINIO_PUBLIC_BASE = os.environ.get("MINIO_PUBLIC_BASE", "http://89.169.112.175/minio")
# Internal URL for AI engine to fetch images from MinIO (must be reachable inside Docker network)
MINIO_INTERNAL_URL = os.environ.get("MINIO_INTERNAL_URL", "http://minio:9000")

engine = create_async_engine(DATABASE_URL, pool_size=5)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
PASS = FAIL = 0
TIMINGS = []


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        tag = "PASS"
    else:
        FAIL += 1
        tag = "FAIL"
    print(f"  [{tag}] {name}" + (f"  ({detail})" if detail else ""))


def bench(name, elapsed_ms):
    TIMINGS.append((name, elapsed_ms))
    print(f"  [BENCH] {name}: {elapsed_ms:.1f}ms")


# ---------------------------------------------------------------------------
# MinIO upload via minio library (available in API container)
# ---------------------------------------------------------------------------
from minio import Minio


def get_minio():
    return Minio(MINIO_ENDPOINT, access_key=MINIO_USER, secret_key=MINIO_PASS, secure=False)


def upload_to_minio(client, bucket, data: bytes, ext="jpg") -> tuple:
    """Returns (public_url, internal_url)."""
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
    key = f"seed/{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}.{ext}"
    data_stream = io.BytesIO(data)
    client.put_object(bucket, key, data_stream, length=len(data), content_type=f"image/{ext}")
    public = f"{MINIO_PUBLIC_BASE}/{bucket}/{key}"
    internal = f"{MINIO_INTERNAL_URL}/{bucket}/{key}"
    return public, internal


# ---------------------------------------------------------------------------
# Synthetic image generation
# ---------------------------------------------------------------------------
def _gradient_image(w, h, color1, color2, direction="horizontal"):
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    for i in range(w if direction == "horizontal" else h):
        ratio = i / (w if direction == "horizontal" else h)
        r = int(color1[0] + (color2[0] - color1[0]) * ratio)
        g = int(color1[1] + (color2[1] - color1[1]) * ratio)
        b = int(color1[2] + (color2[2] - color1[2]) * ratio)
        if direction == "horizontal":
            draw.line([(i, 0), (i, h)], fill=(r, g, b))
        else:
            draw.line([(0, i), (w, i)], fill=(r, g, b))
    return img


def _add_text(draw, text, x, y, size=20, color=(255, 255, 255)):
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    except Exception:
        font = ImageFont.load_default()
    draw.text((x, y), text, fill=color, font=font)


def _draw_person_silhouette(draw, cx, cy, scale=1.0):
    """Draw a simple stick figure person."""
    s = scale
    # Head
    draw.ellipse([cx - 12*s, cy - 70*s, cx + 12*s, cy - 46*s], fill=(200, 170, 130), outline=(100, 80, 60))
    # Body
    draw.line([(cx, cy - 46*s), (cx, cy + 10*s)], fill=(50, 50, 150), width=int(4*s))
    # Arms
    draw.line([(cx - 25*s, cy - 25*s), (cx + 25*s, cy - 25*s)], fill=(50, 50, 150), width=int(3*s))
    # Legs
    draw.line([(cx, cy + 10*s), (cx - 20*s, cy + 50*s)], fill=(50, 50, 150), width=int(3*s))
    draw.line([(cx, cy + 10*s), (cx + 20*s, cy + 50*s)], fill=(50, 50, 150), width=int(3*s))


def _draw_car(draw, cx, cy, color=(30, 30, 180)):
    """Draw a simple car shape."""
    # Body
    draw.rectangle([cx - 60, cy - 15, cx + 60, cy + 15], fill=color, outline=(0, 0, 0))
    # Roof
    draw.polygon([(cx - 35, cy - 15), (cx - 25, cy - 35), (cx + 25, cy - 35), (cx + 35, cy - 15)],
                 fill=color, outline=(0, 0, 0))
    # Wheels
    draw.ellipse([cx - 45, cy + 10, cx - 25, cy + 28], fill=(30, 30, 30))
    draw.ellipse([cx + 25, cy + 10, cx + 45, cy + 28], fill=(30, 30, 30))


def _draw_truck(draw, cx, cy, color=(180, 30, 30)):
    """Draw a simple truck shape."""
    # Cab
    draw.rectangle([cx - 30, cy - 20, cx + 10, cy + 20], fill=color, outline=(0, 0, 0))
    # Cargo
    draw.rectangle([cx + 10, cy - 30, cx + 70, cy + 20], fill=(100, 100, 100), outline=(0, 0, 0))
    # Wheels
    draw.ellipse([cx - 25, cy + 15, cx - 10, cy + 28], fill=(30, 30, 30))
    draw.ellipse([cx + 45, cy + 15, cx + 60, cy + 28], fill=(30, 30, 30))


def _draw_plate(draw, x, y, plate_text="ABC-1234"):
    """Draw a license plate."""
    draw.rectangle([x, y, x + 120, y + 35], fill=(255, 255, 255), outline=(0, 0, 0), width=2)
    _add_text(draw, plate_text, x + 10, y + 5, size=18, color=(0, 0, 0))


def generate_test_images():
    """Generate 10 distinct test images for AI benchmarking."""
    images = []

    # 1. Red truck at loading dock
    img = _gradient_image(640, 480, (180, 200, 170), (120, 140, 110), "vertical")
    draw = ImageDraw.Draw(img)
    _draw_truck(draw, 320, 300, (200, 30, 30))
    _add_text(draw, "Loading Dock A", 20, 20, 24, (255, 255, 255))
    _add_text(draw, "TRUCK IN ZONE", 20, 50, 16, (255, 200, 0))
    images.append(("cctv_loading_dock_truck.jpg", img))

    # 2. Person at gate (face visible)
    img = Image.new("RGB", (640, 480), (60, 120, 180))
    draw = ImageDraw.Draw(img)
    # Sky gradient
    for y in range(240):
        ratio = y / 240
        draw.line([(0, y), (639, y)], fill=(int(100 + 100*ratio), int(150 + 50*ratio), 220))
    # Ground
    draw.rectangle([0, 240, 639, 479], fill=(100, 120, 90))
    # Person with face
    _draw_person_silhouette(draw, 320, 350, 2.0)
    _add_text(draw, "GATE 1 - ENTRY", 20, 20, 24, (255, 255, 255))
    _add_text(draw, "VISITOR APPROACHING", 20, 50, 16, (0, 255, 0))
    images.append(("lpr_gate1_person.jpg", img))

    # 3. Car with plate at gate
    img = _gradient_image(640, 480, (130, 130, 130), (80, 80, 80), "vertical")
    draw = ImageDraw.Draw(img)
    _draw_car(draw, 320, 280, (30, 30, 180))
    _draw_plate(draw, 270, 300, "EGY-4521")
    _add_text(draw, "GATE 2 - LPR", 20, 20, 24, (255, 255, 255))
    _add_text(draw, "Plate: EGY-4521", 20, 50, 16, (0, 200, 255))
    images.append(("lpr_gate2_plate.jpg", img))

    # 4. Warehouse interior (forklift)
    img = Image.new("RGB", (640, 480), (180, 170, 150))
    draw = ImageDraw.Draw(img)
    # Floor
    draw.rectangle([0, 300, 639, 479], fill=(150, 140, 120))
    # Shelves
    for i in range(4):
        x = 80 + i * 150
        draw.rectangle([x, 100, x + 100, 300], fill=(139, 90, 43), outline=(80, 50, 25))
        for j in range(3):
            draw.rectangle([x + 5, 120 + j*55, x + 95, 165 + j*55], fill=(160, 140, 80))
    # Forklift shape
    draw.rectangle([280, 260, 380, 340], fill=(255, 180, 0), outline=(0, 0, 0))
    draw.rectangle([370, 240, 380, 340], fill=(100, 100, 100))
    draw.rectangle([365, 200, 385, 240], fill=(100, 100, 100))
    _add_text(draw, "WAREHOUSE ZONE", 20, 20, 24, (255, 255, 255))
    _add_text(draw, "Forklift Operating", 20, 50, 16, (255, 165, 0))
    images.append(("cctv_warehouse_forklift.jpg", img))

    # 5. Restricted zone - two persons
    img = Image.new("RGB", (640, 480), (40, 40, 50))
    draw = ImageDraw.Draw(img)
    # Red warning stripes
    for i in range(0, 640, 40):
        draw.line([(i, 0), (i + 20, 480)], fill=(150, 0, 0), width=8)
    # Persons
    _draw_person_silhouette(draw, 250, 340, 2.0)
    _draw_person_silhouette(draw, 400, 330, 2.2)
    _add_text(draw, "RESTRICTED ZONE", 20, 20, 24, (255, 0, 0))
    _add_text(draw, "UNAUTHORIZED ACCESS", 20, 50, 16, (255, 255, 0))
    _add_text(draw, "2 persons detected", 20, 80, 14, (255, 100, 100))
    images.append(("ptz_restricted_persons.jpg", img))

    # 6. Production hall - multiple vehicles
    img = _gradient_image(640, 480, (200, 200, 210), (160, 160, 170), "horizontal")
    draw = ImageDraw.Draw(img)
    # Floor
    draw.rectangle([0, 280, 639, 479], fill=(170, 170, 180))
    # Multiple cars
    _draw_car(draw, 150, 350, (30, 120, 30))
    _draw_car(draw, 350, 340, (180, 180, 30))
    _draw_car(draw, 520, 360, (120, 30, 120))
    _add_text(draw, "PRODUCTION HALL", 20, 20, 24, (255, 255, 255))
    _add_text(draw, "3 vehicles in zone", 20, 50, 16, (100, 200, 255))
    images.append(("cctv_production_vehicles.jpg", img))

    # 7. Night scene - single car with headlights
    img = Image.new("RGB", (640, 480), (10, 10, 25))
    draw = ImageDraw.Draw(img)
    # Headlight beams
    for i in range(200):
        alpha = max(0, 255 - i * 2)
        r = int(alpha * 0.9)
        g = int(alpha * 0.85)
        b = int(alpha * 0.5)
        draw.ellipse([200 - i, 200 - i, 200 + i, 200 + i], outline=(r, g, b))
    _draw_car(draw, 320, 280, (40, 40, 60))
    # Headlights
    draw.ellipse([260, 268, 280, 285], fill=(255, 250, 200))
    draw.ellipse([370, 268, 390, 285], fill=(255, 250, 200))
    _add_text(draw, "NIGHT MODE", 20, 20, 24, (255, 255, 255))
    _add_text(draw, "Low visibility vehicle", 20, 50, 16, (200, 200, 200))
    images.append(("ptz_night_vehicle.jpg", img))

    # 8. Loading dock B - truck with person
    img = _gradient_image(640, 480, (140, 160, 130), (90, 110, 80), "vertical")
    draw = ImageDraw.Draw(img)
    _draw_truck(draw, 400, 260, (50, 50, 50))
    _draw_person_silhouette(draw, 200, 320, 1.8)
    _add_text(draw, "LOADING DOCK B", 20, 20, 24, (255, 255, 255))
    _add_text(draw, "Truck + Personnel", 20, 50, 16, (0, 255, 100))
    _draw_plate(draw, 360, 280, "TRK-7890")
    images.append(("lpr_dockb_truck.jpg", img))

    # 9. Parking lot overview (PTZ wide angle)
    img = _gradient_image(640, 480, (150, 170, 200), (100, 130, 160), "horizontal")
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 320, 639, 479], fill=(120, 120, 120))
    # Parking lines
    for i in range(8):
        x = 40 + i * 75
        draw.line([(x, 320), (x, 479)], fill=(255, 255, 255), width=2)
    # Cars
    colors = [(30, 30, 180), (200, 30, 30), (30, 150, 30), (180, 180, 30)]
    for i, c in enumerate(colors):
        _draw_car(draw, 80 + i * 150, 390, c)
    _add_text(draw, "PARKING LOT - PTZ", 20, 20, 24, (255, 255, 255))
    _add_text(draw, "4 vehicles overview", 20, 50, 16, (200, 220, 255))
    images.append(("ptz_parking_overview.jpg", img))

    # 10. Close-up face for face recognition test
    img = Image.new("RGB", (640, 480), (180, 150, 130))
    draw = ImageDraw.Draw(img)
    # Face oval
    draw.ellipse([200, 80, 440, 400], fill=(220, 185, 155), outline=(150, 120, 90))
    # Eyes
    draw.ellipse([270, 180, 305, 210], fill=(255, 255, 255))
    draw.ellipse([335, 180, 370, 210], fill=(255, 255, 255))
    draw.ellipse([280, 185, 300, 205], fill=(60, 40, 20))
    draw.ellipse([345, 185, 365, 205], fill=(60, 40, 20))
    # Nose
    draw.line([(320, 220), (310, 280), (330, 280)], fill=(180, 150, 120), width=3)
    # Mouth
    draw.arc([280, 300, 360, 350], 0, 180, fill=(180, 80, 80), width=3)
    # Hair
    draw.ellipse([210, 70, 430, 200], fill=(60, 40, 20))
    draw.rectangle([210, 120, 430, 170], fill=(60, 40, 20))
    _add_text(draw, "FACE ENROLLMENT TEST", 20, 20, 24, (255, 255, 255))
    images.append(("cctv_face_enroll.jpg", img))

    return images


# ---------------------------------------------------------------------------
# Main seed + test flow
# ---------------------------------------------------------------------------
CAMERA_SEED_DATA = [
    # (name, ip, type, zone_name, rtsp, isapi)
    ("Gate 1 LPR", "192.168.1.101", "lpr", "Gate 1",
     "rtsp://admin:pass@192.168.1.101:554/Streaming/Channels/101",
     "http://192.168.1.101/ISAPI/Streaming/channels/101"),
    ("Gate 2 LPR", "192.168.1.102", "lpr", "Gate 2",
     "rtsp://admin:pass@192.168.1.102:554/Streaming/Channels/101",
     "http://192.168.1.102/ISAPI/Streaming/channels/101"),
    ("Loading Dock A CCTV", "192.168.1.103", "cctv", "Loading Dock A",
     "rtsp://admin:pass@192.168.1.103:554/Streaming/Channels/101",
     None),
    ("Loading Dock B CCTV", "192.168.1.104", "cctv", "Loading Dock B",
     "rtsp://admin:pass@192.168.1.104:554/Streaming/Channels/101",
     None),
    ("Warehouse Overview", "192.168.1.105", "cctv", "Warehouse",
     "rtsp://admin:pass@192.168.1.105:554/Streaming/Channels/101",
     None),
    ("Production Hall Main", "192.168.1.106", "cctv", "Production Hall",
     "rtsp://admin:pass@192.168.1.106:554/Streaming/Channels/101",
     None),
    ("Restricted Zone 1 PTZ", "192.168.1.107", "ptz", "Restricted Zone 1",
     "rtsp://admin:pass@192.168.1.107:554/Streaming/Channels/101",
     "http://192.168.1.107/ISAPI/Streaming/channels/101"),
    ("Restricted Zone 2 PTZ", "192.168.1.108", "ptz", "Restricted Zone 2",
     "rtsp://admin:pass@192.168.1.108:554/Streaming/Channels/101",
     "http://192.168.1.108/ISAPI/Streaming/channels/101"),
    ("Parking Lot PTZ", "192.168.1.109", "ptz", "Gate 1",
     "rtsp://admin:pass@192.168.1.109:554/Streaming/Channels/101",
     "http://192.168.1.109/ISAPI/Streaming/channels/101"),
    ("Production Hall PTZ", "192.168.1.110", "ptz", "Production Hall",
     "rtsp://admin:pass@192.168.1.110:554/Streaming/Channels/101",
     None),
]

# Maps image index to camera name (for realistic assignment)
IMAGE_CAMERA_MAP = {
    0: "Loading Dock A CCTV",     # red truck at loading dock
    1: "Gate 1 LPR",              # person at gate
    2: "Gate 2 LPR",              # car with plate
    3: "Warehouse Overview",       # forklift
    4: "Restricted Zone 1 PTZ",   # 2 persons restricted
    5: "Production Hall Main",     # multiple vehicles
    6: "Restricted Zone 2 PTZ",   # night vehicle
    7: "Loading Dock B CCTV",     # truck + person dock B
    8: "Parking Lot PTZ",         # parking overview
    9: "Production Hall PTZ",     # face enrollment
}

PERSON_SEED_DATA = [
    ("EMP-001", "Ahmed Hassan", "Security", "admin"),
    ("EMP-002", "Sara Ibrahim", "Operations", "operator"),
    ("EMP-003", "Mohamed Ali", "IT", "admin"),
]


async def run():
    global PASS, FAIL
    print("=" * 72)
    print("ACUSEEK SEED DATABASE + GPU/AI PERFORMANCE TEST")
    print("=" * 72)
    t_total = time.time()

    # ------------------------------------------------------------------
    # Phase 0: Check prerequisites
    # ------------------------------------------------------------------
    print("\n== Phase 0: Prerequisites ==")

    async with httpx.AsyncClient(timeout=10) as hc:
        try:
            r = await hc.get(f"{AI_ENGINE_URL}/health")
            check("AI engine reachable", r.status_code == 200, f"status={r.status_code}")
        except Exception as e:
            check("AI engine reachable", False, str(e))
            print("\nFATAL: AI engine not reachable. Cannot proceed.")
            return 1

    async with SessionLocal() as db:
        result = await db.execute(text("SELECT COUNT(*) FROM zones"))
        zone_count = result.scalar()
        check(f"Zones exist ({zone_count})", zone_count > 0)

        result = await db.execute(text("SELECT COUNT(*) FROM cameras"))
        cam_count = result.scalar()
        check(f"Current cameras: {cam_count}", True)

        result = await db.execute(text("SELECT id, name FROM zones"))
        zones = {row.name: str(row.id) for row in result.fetchall()}
        print(f"  Zones: {list(zones.keys())}")

    # ------------------------------------------------------------------
    # Phase 1: Seed cameras
    # ------------------------------------------------------------------
    print("\n== Phase 1: Seed Cameras ==")
    created_cameras = {}

    async with SessionLocal() as db:
        for name, ip, ctype, zone_name, rtsp, isapi in CAMERA_SEED_DATA:
            zone_id = zones.get(zone_name)
            if not zone_id:
                check(f"Camera {name}", False, f"zone '{zone_name}' not found")
                continue

            existing = await db.execute(
                text("SELECT id FROM cameras WHERE ip_address = :ip LIMIT 1"), {"ip": ip}
            )
            row = existing.first()
            if row:
                created_cameras[name] = str(row[0])
                check(f"Camera {name} (already exists)", True, ip)
                continue

            cam_id = uuid4()
            await db.execute(
                text("""
                    INSERT INTO cameras (id, zone_id, name, ip_address, camera_type, rtsp_url, isapi_url, is_active, config, created_at)
                    VALUES (:id, :zone_id, :name, :ip, :type, :rtsp, :isapi, true, '{}', :now)
                """),
                {"id": str(cam_id), "zone_id": zone_id, "name": name, "ip": ip,
                 "type": ctype, "rtsp": rtsp, "isapi": isapi, "now": datetime.now(timezone.utc)},
            )
            created_cameras[name] = str(cam_id)
            check(f"Camera {name} ({ctype})", True, ip)

        await db.commit()

    print(f"\n  Total cameras: {len(created_cameras)}")
    type_counts = {}
    for cam_name in created_cameras:
        for cdata in CAMERA_SEED_DATA:
            if cdata[0] == cam_name:
                ctype = cdata[2]
                type_counts[ctype] = type_counts.get(ctype, 0) + 1
                break
    for t, c in type_counts.items():
        print(f"    {t.upper()}: {c}")

    # ------------------------------------------------------------------
    # Phase 2: Seed vehicles (for gate testing)
    # ------------------------------------------------------------------
    print("\n== Phase 2: Seed Vehicles ==")
    vehicles_data = [
        ("EGY-4521", "Ahmed Trucking", "truck", "Red", "Operations", True, True),
        ("TRK-7890", "Sara Logistics", "truck", "Black", "Logistics", True, False),
        ("ABC-1234", "Mohamed Motors", "car", "Blue", "IT", True, True),
        ("XYZ-9999", "Unknown Vehicle", "car", "White", "External", False, False),
    ]
    async with SessionLocal() as db:
        for plate, owner, vtype, color, dept, wl, req_exit in vehicles_data:
            existing = await db.execute(
                text("SELECT id FROM vehicles WHERE plate_number = :p LIMIT 1"), {"p": plate}
            )
            if existing.first():
                check(f"Vehicle {plate}", True, "(exists)")
                continue
            vid = uuid4()
            await db.execute(
                text("""
                    INSERT INTO vehicles (id, plate_number, owner_name, vehicle_type, color, department, is_whitelisted, requires_exit_permission, created_at)
                    VALUES (:id, :plate, :owner, :type, :color, :dept, :wl, :req, :now)
                """),
                {"id": str(vid), "plate": plate, "owner": owner, "type": vtype,
                 "color": color, "dept": dept, "wl": wl, "req": req_exit, "now": datetime.now(timezone.utc)},
            )
            check(f"Vehicle {plate}", True, f"{owner} ({vtype})")
        await db.commit()

    # ------------------------------------------------------------------
    # Phase 3: Seed persons
    # ------------------------------------------------------------------
    print("\n== Phase 3: Seed Persons ==")
    person_ids = {}
    async with SessionLocal() as db:
        for emp_id, name, dept, access in PERSON_SEED_DATA:
            existing = await db.execute(
                text("SELECT id FROM persons WHERE employee_id = :eid LIMIT 1"), {"eid": emp_id}
            )
            row = existing.first()
            if row:
                person_ids[emp_id] = str(row[0])
                check(f"Person {name}", True, "(exists)")
                continue
            pid = uuid4()
            await db.execute(
                text("""
                    INSERT INTO persons (id, employee_id, full_name, department, access_level, is_active, created_at)
                    VALUES (:id, :eid, :name, :dept, :access, true, :now)
                """),
                {"id": str(pid), "eid": emp_id, "name": name, "dept": dept,
                 "access": access, "now": datetime.now(timezone.utc)},
            )
            person_ids[emp_id] = str(pid)
            check(f"Person {name}", True, f"{dept} ({access})")
        await db.commit()

    # ------------------------------------------------------------------
    # Phase 4: Generate + upload + embed 10 images
    # ------------------------------------------------------------------
    print("\n== Phase 4: Generate + Upload + Embed 10 Images ==")
    images = generate_test_images()
    minio = get_minio()
    image_records = []

    for idx, (filename, img_obj) in enumerate(images):
        print(f"\n  --- Image {idx+1}/10: {filename} ---")

        # Convert PIL Image to bytes
        buf = io.BytesIO()
        img_obj.save(buf, format="JPEG", quality=90)
        img_bytes = buf.getvalue()
        print(f"  Size: {len(img_bytes)} bytes ({img_obj.size[0]}x{img_obj.size[1]})")

        # Upload to MinIO
        t0 = time.time()
        bucket = "snapshots"
        public_url, internal_url = upload_to_minio(minio, bucket, img_bytes, "jpg")
        bench(f"MinIO upload {filename}", (time.time() - t0) * 1000)
        check(f"Upload {filename}", public_url.startswith("http"), public_url[:80])

        # Get camera_id
        cam_name = IMAGE_CAMERA_MAP.get(idx, "Gate 1 LPR")
        camera_id = created_cameras.get(cam_name)

        # Create ImageStore record (store public URL for dashboard display)
        async with SessionLocal() as db:
            img_id = uuid4()
            captured_at = datetime.now(timezone.utc) - timedelta(minutes=10 * (10 - idx))
            await db.execute(
                text("""
                    INSERT INTO image_store (id, camera_id, image_url, captured_at, metadata)
                    VALUES (:id, :cam, :url, :captured, :meta)
                """),
                {"id": str(img_id), "cam": camera_id, "url": public_url,
                 "captured": captured_at, "meta": json.dumps({"filename": filename, "seed": True})},
            )
            await db.commit()

        # AI: CLIP embedding (embed/image) — use internal URL for AI engine
        t0 = time.time()
        try:
            async with httpx.AsyncClient(timeout=60) as ai:
                r = await ai.post(f"{AI_ENGINE_URL}/embed/image", json={"image_url": internal_url})
                if r.status_code == 200:
                    clip_data = r.json()
                    clip_vec = clip_data.get("embedding", [])
                    bench("CLIP embed " + filename, (time.time() - t0) * 1000)
                    check(f"CLIP embedding {filename}", len(clip_vec) == 512, f"dim={len(clip_vec)}")

                    # Store embedding
                    vec_str = "[" + ",".join(f"{v:.6f}" for v in clip_vec) + "]"
                    async with SessionLocal() as db2:
                        emb_id = uuid4()
                        await db2.execute(
                            text("""
                                INSERT INTO image_embeddings (id, image_id, clip_embedding, created_at)
                                VALUES (:id, :img_id, :vec::vector, :now)
                            """),
                            {"id": str(emb_id), "img_id": str(img_id),
                             "vec": vec_str, "now": datetime.now(timezone.utc)},
                        )
                        await db2.commit()
                    check(f"Store CLIP embedding {filename}", True)
                else:
                    bench("CLIP embed " + filename, (time.time() - t0) * 1000)
                    check(f"CLIP embedding {filename}", False, f"status={r.status_code}: {r.text[:200]}")
        except Exception as e:
            bench("CLIP embed " + filename, (time.time() - t0) * 1000)
            check(f"CLIP embedding {filename}", False, str(e)[:100])

        image_records.append((idx, filename, public_url, internal_url, img_id))

    # ------------------------------------------------------------------
    # Phase 5: Face embedding for person
    # ------------------------------------------------------------------
    print("\n== Phase 5: Face Embedding Test ==")
    face_img_url = image_records[9][3]  # face enrollment image (internal URL for AI)
    face_img_public = image_records[9][2]  # public URL for storage

    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=60) as ai:
            r = await ai.post(f"{AI_ENGINE_URL}/face/embed", json={"image_url": face_img_url})
            bench("Face embed (synthetic face)", (time.time() - t0) * 1000)
            if r.status_code == 200:
                face_data = r.json()
                found = face_data.get("found", False)
                emb = face_data.get("embedding")
                check("Face detection", found, f"embedding={'yes' if emb else 'none'}")
                if emb and len(emb) > 0:
                    vec_str = "[" + ",".join(f"{v:.6f}" for v in emb) + "]"
                    async with SessionLocal() as db:
                        fe_id = uuid4()
                        await db.execute(
                            text("""
                                INSERT INTO face_embeddings (id, person_id, embedding, sample_image_url, created_at)
                                VALUES (:id, :pid, :vec::vector, :url, :now)
                            """),
                            {"id": str(fe_id), "pid": person_ids.get("EMP-001"),
                              "vec": vec_str, "url": face_img_public,
                             "now": datetime.now(timezone.utc)},
                        )
                        await db.commit()
                    check("Store face embedding", True)
                else:
                    check("Face detection on synthetic image", False,
                          "AI did not detect face (expected for synthetic image)")
            else:
                check("Face embed request", False, f"status={r.status_code}")
    except Exception as e:
        check("Face embed", False, str(e)[:100])

    # ------------------------------------------------------------------
    # Phase 6: YOLO detection test
    # ------------------------------------------------------------------
    print("\n== Phase 6: YOLO Detection Test ==")
    detect_targets = [
        (0, "Loading Dock Truck"),
        (2, "Gate Plate"),
        (3, "Warehouse Forklift"),
        (4, "Restricted Persons"),
        (5, "Production Vehicles"),
        (8, "Parking Overview"),
    ]

    for img_idx, label in detect_targets:
        url = image_records[img_idx][3]  # internal URL for AI engine
        t0 = time.time()
        try:
            async with httpx.AsyncClient(timeout=60) as ai:
                r = await ai.post(f"{AI_ENGINE_URL}/detect", json={"image_url": url})
                bench(f"YOLO detect {label}", (time.time() - t0) * 1000)
                if r.status_code == 200:
                    det_data = r.json()
                    detections = det_data.get("detections", [])
                    labels = [d.get("label", "?") for d in detections]
                    confs = [d.get("confidence", 0) for d in detections]
                    check(f"YOLO {label}", len(detections) > 0,
                          f"found: {labels} conf={[f'{c:.2f}' for c in confs]}")
                else:
                    check(f"YOLO {label}", False, f"status={r.status_code}")
        except Exception as e:
            check(f"YOLO {label}", False, str(e)[:100])

    # ------------------------------------------------------------------
    # Phase 7: Text search test (end-to-end CLIP)
    # ------------------------------------------------------------------
    print("\n== Phase 7: Text-to-Image Search (End-to-End) ==")
    search_queries = [
        "red truck",
        "person walking",
        "license plate",
        "warehouse with shelves",
        "forklift",
        "night scene vehicle",
        "parking lot cars",
        "face close-up",
        "restricted area",
        "loading dock",
    ]

    for query in search_queries:
        t0 = time.time()
        try:
            async with httpx.AsyncClient(timeout=30) as ai:
                r = await ai.post(f"{AI_ENGINE_URL}/embed/text", json={"text": query})
                if r.status_code == 200:
                    text_vec = r.json().get("embedding", [])
                    bench(f"Text embed '{query}'", (time.time() - t0) * 1000)

                    # Now do pgvector search
                    if text_vec:
                        vec_str = "[" + ",".join(f"{v:.6f}" for v in text_vec) + "]"
                        async with SessionLocal() as db:
                            t1 = time.time()
                            result = await db.execute(
                                text("""
                                    SELECT ie.image_id, is2.image_url,
                                           1 - (ie.clip_embedding <=> :vec::vector) AS score
                                    FROM image_embeddings ie
                                    JOIN image_store is2 ON is2.id = ie.image_id
                                    ORDER BY ie.clip_embedding <=> :vec::vector
                                    LIMIT 3
                                """),
                                {"vec": vec_str},
                            )
                            rows = result.fetchall()
                            bench(f"pgvector search '{query}'", (time.time() - t1) * 1000)
                            if rows:
                                top = rows[0]
                                check(f"Search '{query}'", top.score > 0.15,
                                      f"top_score={top.score:.4f} ({len(rows)} results)")
                            else:
                                check(f"Search '{query}'", False, "no results")
                else:
                    bench(f"Text embed '{query}'", (time.time() - t0) * 1000)
                    check(f"Search '{query}'", False, f"embed status={r.status_code}")
        except Exception as e:
            check(f"Search '{query}'", False, str(e)[:100])

    # ------------------------------------------------------------------
    # Phase 8: GPU info
    # ------------------------------------------------------------------
    print("\n== Phase 8: GPU / AI Engine Info ==")
    try:
        async with httpx.AsyncClient(timeout=10) as ai:
            r = await ai.get(f"{AI_ENGINE_URL}/health")
            check("AI engine health", r.status_code == 200)
    except Exception as e:
        check("AI engine health", False, str(e)[:100])

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    elapsed = time.time() - t_total
    print("\n" + "=" * 72)
    print(f"SEED + AI TEST COMPLETE: {PASS} passed, {FAIL} failed ({PASS+FAIL} total)")
    print(f"Total time: {elapsed:.1f}s")
    print("=" * 72)

    if TIMINGS:
        print("\n  Performance Summary (avg ms):")
        by_prefix = {}
        for name, ms in TIMINGS:
            prefix = name.split(" ")[0]
            by_prefix.setdefault(prefix, []).append(ms)
        for prefix, vals in sorted(by_prefix.items()):
            avg = sum(vals) / len(vals)
            mn, mx = min(vals), max(vals)
            print(f"    {prefix:20s}  avg={avg:7.1f}ms  min={mn:7.1f}ms  max={mx:7.1f}ms  (n={len(vals)})")

    if FAIL > 0:
        print("\n  FAILED:")
        # (we already printed them inline)

    await engine.dispose()
    return 1 if FAIL > 0 else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
