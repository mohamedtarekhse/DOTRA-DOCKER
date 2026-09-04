import httpx
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..models import Person, FaceEmbedding
from ..routers.auth import get_current_user
from ..schemas.person import PersonCreate, PersonOut, FaceEnrollIn, FaceMatchIn
from ..services.storage_service import storage

router = APIRouter(prefix="/persons", tags=["persons"], dependencies=[Depends(get_current_user)])


@router.post("", response_model=PersonOut)
async def create_person(payload: PersonCreate, db: AsyncSession = Depends(get_db)):
    person = Person(**payload.model_dump())
    db.add(person)
    await db.commit()
    await db.refresh(person)
    return person


@router.get("", response_model=list[PersonOut])
async def list_persons(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Person))
    return result.scalars().all()


@router.post("/enroll")
async def enroll_face(payload: FaceEnrollIn, db: AsyncSession = Depends(get_db)):
    """Enroll a face photo -> generate embedding via AI engine -> store."""
    person = await db.get(Person, payload.person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{settings.AI_ENGINE_URL}/face/embed",
            json={"image_url": payload.image_url},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="AI engine face embedding failed")
        embedding = resp.json()["embedding"]

    face = FaceEmbedding(
        person_id=person.id,
        embedding=embedding,
        sample_image_url=payload.image_url,
    )
    db.add(face)
    await db.commit()
    return {"person_id": str(person.id), "enrolled": True, "dim": len(embedding)}


@router.post("/enroll-upload")
async def enroll_face_upload(
    person_id: UUID = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Enroll a face photo (multipart upload) -> store to MinIO -> AI embedding -> save."""
    person = await db.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty image file")
    ext = (file.filename or "jpg").rsplit(".", 1)[-1].lower() or "jpg"
    if ext not in ("jpg", "jpeg", "png", "webp", "bmp"):
        raise HTTPException(status_code=400, detail="Unsupported image type")
    image_url = storage.save_image("face-crops", data, ext if ext in ("jpg", "png") else "jpg")

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{settings.AI_ENGINE_URL}/face/embed",
            json={"image_url": image_url},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="AI engine face embedding failed")
        embedding = resp.json()["embedding"]

    face = FaceEmbedding(
        person_id=person.id,
        embedding=embedding,
        sample_image_url=image_url,
    )
    db.add(face)
    await db.commit()
    return {"person_id": str(person.id), "enrolled": True, "dim": len(embedding), "image_url": image_url}


@router.post("/match")
async def match_face(payload: FaceMatchIn, db: AsyncSession = Depends(get_db)):
    """Find matching person for a face snapshot (gate verification / intrusion)."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{settings.AI_ENGINE_URL}/face/embed",
            json={"image_url": payload.image_url},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="AI engine face embedding failed")
        face_vec = resp.json()["embedding"]

    embeds = await db.execute(select(FaceEmbedding, Person).join(Person, FaceEmbedding.person_id == Person.id))
    best = None
    best_score = payload.threshold
    for fe, p in embeds.all():
        score = _cosine(face_vec, fe.embedding)
        if score > best_score:
            best_score = score
            best = p
    if best is None:
        return {"match": False, "person": None}
    return {
        "match": True,
        "score": round(best_score, 4),
        "person": {
            "id": str(best.id),
            "full_name": best.full_name,
            "department": best.department,
            "access_level": best.access_level,
        },
    }


def _cosine(a, b) -> float:
    import math
    if isinstance(a, str):
        a = __import__("json").loads(a)
    if isinstance(b, str):
        b = __import__("json").loads(b)
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0
