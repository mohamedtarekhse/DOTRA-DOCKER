from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Vehicle, VehicleEvent, WhitelistPermission
from ..routers.websocket import manager
from ..services.mqtt_service import mqtt_service
from ..services.notify_service import notify


class GateService:
    async def process_lpr_entry(
        self, db: AsyncSession, plate: str, direction: str,
        camera_id, confidence: float | None, snapshot_url: str | None,
    ) -> dict:
        """Core gate logic: entry auto-allow for whitelisted, exit requires manager approval."""
        plate = plate.upper().replace(" ", "")
        result = await db.execute(select(Vehicle).where(Vehicle.plate_number == plate))
        vehicle = result.scalar_one_or_none()

        permitted = False
        if vehicle and vehicle.is_whitelisted:
            now = datetime.now(timezone.utc)
            validity = await db.execute(
                select(WhitelistPermission)
                .where(
                    WhitelistPermission.vehicle_id == vehicle.id,
                    WhitelistPermission.is_active.is_(True),
                    WhitelistPermission.valid_from <= now,
                    WhitelistPermission.valid_until >= now,
                )
            )
            permit = validity.scalars().first()
            if permit is not None:
                permitted = True

        if direction == "in":
            if permitted:
                event_type = "entry_granted"
                decision = {"action": "open_gate", "plate": plate, "allowed": True}
            else:
                event_type = "entry_denied"
                decision = {"action": "keep_closed", "plate": plate, "allowed": False}
                await notify.send_unknown_vehicle(plate, "Gate")

        else:  # direction == "out"
            if permitted and vehicle.requires_exit_permission:
                # Hold barrier, request manager approval
                event_type = "exit_pending"
                decision = {
                    "action": "request_manager_approval",
                    "plate": plate,
                    "allowed": False,
                    "pending": True,
                }
            elif permitted and not vehicle.requires_exit_permission:
                event_type = "exit_granted"
                decision = {"action": "open_gate", "plate": plate, "allowed": True}
            else:
                event_type = "exit_denied"
                decision = {"action": "keep_closed", "plate": plate, "allowed": False}

        event = VehicleEvent(
            vehicle_id=vehicle.id if vehicle else None,
            camera_id=camera_id,
            plate_number=plate,
            event_type=event_type,
            direction=direction,
            snapshot_url=snapshot_url,
            confidence=confidence,
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)

        if event_type == "exit_pending":
            await notify.send_exit_approval_request(str(event.id), plate)

        await manager.broadcast({
            "type": "gate_event",
            "event_id": str(event.id),
            "event_type": event_type,
            "plate": plate,
            "direction": direction,
            "decision": decision,
            "event_time": event.event_time.isoformat() if event.event_time else None,
        })

        mqtt_service.publish("acuseek/gate", {
            "event_id": str(event.id),
            "event_type": event_type,
            "plate": plate,
            "direction": direction,
            "decision": decision,
        })

        return {"event_id": str(event.id), "event_type": event_type, "decision": decision}

    async def resolve_exit(
        self, db: AsyncSession, event_id: str, approved: bool, approved_by: str,
    ) -> dict:
        try:
            event_uuid = UUID(event_id)
        except ValueError:
            return {"error": "event not found"}
        evt = await db.get(VehicleEvent, event_uuid)
        if evt is None:
            return {"error": "event not found"}

        evt.event_type = "exit_granted" if approved else "exit_denied"
        evt.approved_by = approved_by
        await db.commit()

        await manager.broadcast({
            "type": "gate_event",
            "event_id": str(event_id),
            "event_type": evt.event_type,
            "plate": evt.plate_number,
            "approved": approved,
            "manager": approved_by,
        })

        return {
            "event_id": str(event_id),
            "event_type": evt.event_type,
            "action": "open_gate" if approved else "keep_closed",
        }


gate_service = GateService()
