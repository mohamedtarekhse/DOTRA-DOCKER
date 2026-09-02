from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AlertEvent
from ..tasks import enqueue_index
from ..routers.websocket import manager
from ..services.mqtt_service import mqtt_service
from ..services.notify_service import notify


class AlertService:
    async def create_alert(
        self, db: AsyncSession, alert_type: str, description: str,
        zone_id=None, camera_id=None, severity: str = "high",
        snapshot_url: str | None = None, zone_name: str | None = None,
        camera_name: str | None = None,
    ) -> AlertEvent:
        alert = AlertEvent(
            zone_id=zone_id,
            camera_id=camera_id,
            alert_type=alert_type,
            severity=severity,
            description=description,
            snapshot_url=snapshot_url,
            status="new",
        )
        db.add(alert)
        await db.commit()
        await db.refresh(alert)

        await manager.broadcast({
            "type": "alert",
            "alert_id": str(alert.id),
            "alert_type": alert_type,
            "severity": severity,
            "description": description,
            "status": alert.status,
            "zone": zone_name,
            "camera": camera_name,
            "created_at": alert.created_at.isoformat() if alert.created_at else None,
        })

        mqtt_service.publish("acuseek/alerts", {
            "alert_id": str(alert.id),
            "alert_type": alert_type,
            "severity": severity,
            "description": description,
            "zone": zone_name,
            "camera": camera_name,
        })

        if severity in ("high", "critical") and alert_type in (
            "restricted_intrusion", "gate_forced", "unknown_vehicle",
        ):
            await notify.send_intrusion_alert(
                zone_name or "Unknown Zone",
                camera_name or "Unknown Camera",
                snapshot_url,
            )

        if snapshot_url:
            enqueue_index(snapshot_url, camera_id=str(camera_id) if camera_id else None,
                          metadata={"alert_id": str(alert.id), "alert_type": alert_type})

        return alert


alert_service = AlertService()
