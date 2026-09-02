from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import AlertEvent
from ..routers.auth import get_current_user, require_device
from ..schemas.alert import AlertOut, AlertUpdate
from ..services.alert_service import alert_service

router = APIRouter(prefix="/alerts", tags=["alerts"])


class IntrusionIn(BaseModel):
    zone: str
    camera: str
    detections: list[dict] = []


@router.post("/intrusion")
async def intrusion(payload: IntrusionIn, db: AsyncSession = Depends(get_db),
                    device: dict = Depends(require_device)):
    """Called by stream-processor when a restricted zone breach is detected."""
    desc = f"Unauthorized movement in {payload.zone}: " + ", ".join(
        f"{d.get('label','?')}({(d.get('confidence') or 0):.2f})" for d in payload.detections
    )
    alert = await alert_service.create_alert(
        db,
        alert_type="restricted_intrusion",
        description=desc,
        severity="critical",
        zone_name=payload.zone,
        camera_name=payload.camera,
    )
    return {"alert_id": str(alert.id)}


@router.get("", response_model=list[AlertOut])
async def list_alerts(status: str | None = None, db: AsyncSession = Depends(get_db),
                      user: dict = Depends(get_current_user)):
    stmt = select(AlertEvent).order_by(AlertEvent.created_at.desc())
    if status:
        stmt = stmt.where(AlertEvent.status == status)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.patch("/{alert_id}", response_model=AlertOut)
async def update_alert(alert_id: UUID, payload: AlertUpdate, db: AsyncSession = Depends(get_db),
                       user: dict = Depends(get_current_user)):
    alert = await db.get(AlertEvent, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    if payload.status:
        alert.status = payload.status
    if payload.resolved_by:
        alert.resolved_by = payload.resolved_by
        alert.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(alert)
    return alert
