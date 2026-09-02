from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Vehicle, WhitelistPermission
from ..routers.auth import get_current_user, require_role
from ..services.permit_service import import_permits, parse_workbook

router = APIRouter(prefix="/permits", tags=["permits"])
require_admin = Depends(require_role("admin"))
require_user = Depends(get_current_user)

MAX_UPLOAD = 2 * 1024 * 1024  # 2 MB


@router.post("/upload")
async def upload_preapprovals(
    file: UploadFile = File(...),
    user: dict = require_admin,
    db: AsyncSession = Depends(get_db),
):
    """Upload an Excel (.xlsx) pre-approval sheet (columns: plate, date, [notes])."""
    if not (file.filename or "").lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Please upload a .xlsx file")
    data = await file.read()
    if len(data) > MAX_UPLOAD:
        raise HTTPException(status_code=400, detail="File too large (max 2 MB)")

    try:
        entries, parse_errors = parse_workbook(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not entries and not parse_errors:
        raise HTTPException(status_code=400, detail="No data rows found in the sheet")

    summary = await import_permits(db, entries, user.get("username") or "admin")
    if parse_errors:
        summary["errors"] = parse_errors
    summary["rows_processed"] = len(entries)
    return summary


@router.get("")
async def list_permits(
    days: int = 14,
    user: dict = require_user,
    db: AsyncSession = Depends(get_db),
):
    """Current + upcoming permits (and expired ones within the past day)."""
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=max(1, min(days, 90)))
    cutoff = now - timedelta(days=1)
    result = await db.execute(
        select(WhitelistPermission, Vehicle.plate_number)
        .join(Vehicle, WhitelistPermission.vehicle_id == Vehicle.id)
        .where(
            WhitelistPermission.is_active.is_(True),
            WhitelistPermission.valid_until >= cutoff,
            WhitelistPermission.valid_from <= end,
        )
        .order_by(WhitelistPermission.valid_from.asc())
    )
    rows = result.all()
    return [
        {
            "id": str(p.id),
            "plate": plate,
            "valid_from": p.valid_from.isoformat(),
            "valid_until": p.valid_until.isoformat(),
            "authorized_by": p.authorized_by,
            "notes": p.notes,
            "active": now <= p.valid_until and p.valid_from <= now,
        }
        for p, plate in rows
    ]


@router.delete("/{permit_id}")
async def revoke_permit(
    permit_id: UUID,
    user: dict = require_admin,
    db: AsyncSession = Depends(get_db),
):
    permit = await db.get(WhitelistPermission, permit_id)
    if permit is None:
        raise HTTPException(status_code=404, detail="Permit not found")
    await db.delete(permit)
    await db.commit()
    return {"revoked": str(permit_id)}