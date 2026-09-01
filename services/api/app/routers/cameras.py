from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Camera, Zone
from ..schemas.camera import CameraCreate, CameraOut, ZoneCreate, ZoneOut

router = APIRouter(prefix="/cameras", tags=["cameras"])


@router.post("", response_model=CameraOut)
async def create_camera(payload: CameraCreate, db: AsyncSession = Depends(get_db)):
    camera = Camera(**payload.model_dump())
    db.add(camera)
    await db.commit()
    await db.refresh(camera)
    return camera


@router.get("", response_model=list[CameraOut])
async def list_cameras(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Camera))
    return result.scalars().all()


@router.get("/zones", response_model=list[ZoneOut])
async def list_zones(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Zone))
    return result.scalars().all()


@router.post("/zones", response_model=ZoneOut)
async def create_zone(payload: ZoneCreate, db: AsyncSession = Depends(get_db)):
    zone = Zone(**payload.model_dump())
    db.add(zone)
    await db.commit()
    await db.refresh(zone)
    return zone


@router.get("/{camera_id}")
async def camera_detail(camera_id: UUID, db: AsyncSession = Depends(get_db)):
    camera = await db.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera
