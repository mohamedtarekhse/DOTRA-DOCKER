from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Camera, Zone
from ..routers.auth import get_current_user
from ..schemas.camera import CameraCreate, CameraOut, CameraUpdate, ZoneCreate, ZoneOut

router = APIRouter(prefix="/cameras", tags=["cameras"], dependencies=[Depends(get_current_user)])


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


@router.patch("/{camera_id}", response_model=CameraOut)
async def update_camera(camera_id: UUID, payload: CameraUpdate, db: AsyncSession = Depends(get_db)):
    camera = await db.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(status_code=404, detail="Camera not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(camera, key, value)
    await db.commit()
    await db.refresh(camera)
    return camera


@router.delete("/{camera_id}")
async def delete_camera(camera_id: UUID, db: AsyncSession = Depends(get_db)):
    camera = await db.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(status_code=404, detail="Camera not found")
    await db.delete(camera)
    await db.commit()
    return {"deleted": str(camera_id)}
