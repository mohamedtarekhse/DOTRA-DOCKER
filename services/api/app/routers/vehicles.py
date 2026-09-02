from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Vehicle, VehicleEvent
from ..routers.auth import get_current_user
from ..schemas.vehicle import VehicleCreate, VehicleOut, VehicleUpdate

router = APIRouter(prefix="/vehicles", tags=["vehicles"], dependencies=[Depends(get_current_user)])


@router.post("", response_model=VehicleOut)
async def create_vehicle(payload: VehicleCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Vehicle).where(Vehicle.plate_number == payload.plate_number.upper()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Plate already exists")
    vehicle = Vehicle(**payload.model_dump())
    vehicle.plate_number = vehicle.plate_number.upper()
    db.add(vehicle)
    await db.commit()
    await db.refresh(vehicle)
    return vehicle


@router.get("", response_model=list[VehicleOut])
async def list_vehicles(
    q: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Vehicle)
    if q:
        stmt = stmt.where(Vehicle.plate_number.ilike(f"%{q.upper()}%"))
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{plate}/status")
async def vehicle_status(plate: str, db: AsyncSession = Depends(get_db)):
    vehicle = await db.execute(select(Vehicle).where(Vehicle.plate_number == plate.upper()))
    v = vehicle.scalar_one_or_none()
    if v is None:
        return {"plate": plate.upper(), "whitelisted": False}
    return {
        "plate": v.plate_number,
        "whitelisted": v.is_whitelisted,
        "requires_exit_permission": v.requires_exit_permission,
        "vehicle_type": v.vehicle_type,
        "department": v.department,
    }


@router.delete("/{vehicle_id}")
async def delete_vehicle(vehicle_id: UUID, db: AsyncSession = Depends(get_db)):
    vehicle = await db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    await db.delete(vehicle)
    await db.commit()
    return {"deleted": str(vehicle_id)}


@router.patch("/{vehicle_id}", response_model=VehicleOut)
async def update_vehicle(vehicle_id: UUID, payload: VehicleUpdate, db: AsyncSession = Depends(get_db)):
    vehicle = await db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(vehicle, key, value)
    await db.commit()
    await db.refresh(vehicle)
    return vehicle


@router.get("/{plate}/events")
async def vehicle_events(plate: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(VehicleEvent)
        .where(VehicleEvent.plate_number == plate.upper())
        .order_by(VehicleEvent.event_time.desc())
        .limit(50)
    )
    events = result.scalars().all()
    return [
        {
            "id": str(e.id),
            "event_type": e.event_type,
            "direction": e.direction,
            "snapshot_url": e.snapshot_url,
            "approved_by": e.approved_by,
            "event_time": str(e.event_time),
        }
        for e in events
    ]
