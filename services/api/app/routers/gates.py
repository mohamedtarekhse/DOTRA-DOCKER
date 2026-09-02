from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..routers.auth import require_device, require_role
from ..services.gate_service import gate_service
from ..schemas.vehicle import VehicleEventIn, ExitApprovalIn

router = APIRouter(prefix="/gates", tags=["gates"])
require_operator = require_role("admin", "security")


def _check_secret(secret: str):
    if secret != settings.LPR_EVENT_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/lpr-event")
async def lpr_event(
    payload: VehicleEventIn,
    x_secret: str | None = Header(None, alias="X-Secret"),
    db: AsyncSession = Depends(get_db),
):
    # Secret accepted via the X-Secret header only (never in the URL/query string).
    _check_secret(x_secret or "")
    result = await gate_service.process_lpr_entry(
        db,
        plate=payload.plate_number,
        direction=payload.direction,
        camera_id=payload.camera_id,
        confidence=payload.confidence,
        snapshot_url=payload.snapshot_url,
    )
    return result


@router.post("/exit-approval")
async def exit_approval(
    payload: ExitApprovalIn,
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    result = await gate_service.resolve_exit(
        db, str(payload.event_id), payload.approved, payload.manager
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{gate_id}/manual-override")
async def manual_override(
    gate_id: str, action: str,
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Manual gate open/close from dashboard — for security override."""
    if action not in ("open", "close"):
        raise HTTPException(status_code=400, detail="action must be open/close")
    return {"gate_id": gate_id, "action": action, "source": "manual", "by": user.get("username")}


class TelegramUpdate(BaseModel):
    callback_query: dict | None = None
    message: dict | None = None


@router.post("/telegram-webhook")
async def telegram_webhook(
    payload: TelegramUpdate,
    x_telegram_secret: str | None = Header(None, alias="X-Telegram-Bot-Api-Secret-Token"),
    db: AsyncSession = Depends(get_db),
):
    """Handle Telegram inline button taps for vehicle exit approval.

    Protected by a webhook secret (set TELEGRAM_WEBHOOK_SECRET and configure it in
    BotFather /setWebhook / setWebhookAllowedUpdates). Fails closed when unset.
    """
    expected = settings.TELEGRAM_WEBHOOK_SECRET
    if not expected or x_telegram_secret != expected:
        raise HTTPException(status_code=403, detail="Forbidden")
    cq = payload.callback_query
    if cq is None:
        return {"ok": True}

    data = cq.get("data", "")
    if data.startswith("approve_exit:") or data.startswith("deny_exit:"):
        approved = data.startswith("approve_exit:")
        event_id = data.split(":", 1)[1]
        manager = cq.get("from", {}).get("username", "telegram")
        result = await gate_service.resolve_exit(db, event_id, approved, manager)
        return {"ok": True, "result": result}

    return {"ok": True}
