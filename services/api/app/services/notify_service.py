import httpx
from ..config import settings


class NotifyService:
    async def send_telegram(self, text: str, buttons: list[list[dict]] | None = None):
        if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
            print(f"[TELEGRAM-DISABLED] {text}")
            return
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": settings.TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
        }
        if buttons:
            payload["reply_markup"] = {
                "inline_keyboard": buttons,
            }
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
            except Exception as exc:
                print(f"[TELEGRAM-ERROR] {exc}")

    async def send_exit_approval_request(self, event_id: str, plate: str):
        buttons = [
            [
                {"text": "✅ Approve Exit", "callback_data": f"approve_exit:{event_id}"},
                {"text": "🚫 Deny Exit", "callback_data": f"deny_exit:{event_id}"},
            ]
        ]
        await self.send_telegram(
            f"🔔 <b>Vehicle Exit Approval Request</b>\n\n"
            f"Plate: <b>{plate}</b>\n"
            f"Event: {event_id}\n\n"
            f"Tap a button to allow or deny the vehicle leaving the factory.",
            buttons,
        )

    async def send_intrusion_alert(self, zone: str, camera: str, snapshot: str | None = None):
        text = (
            f"🚨 <b>RESTRICTED AREA INTRUSION</b>\n\n"
            f"Zone: <b>{zone}</b>\n"
            f"Camera: <b>{camera}</b>\n"
            f"Time: unauthorized movement detected.\n"
        )
        if snapshot:
            text += f"\nSnapshot: {snapshot}"
        await self.send_telegram(text)

    async def send_unknown_vehicle(self, plate: str, gate: str):
        await self.send_telegram(
            f"⚠️ <b>Unknown Vehicle</b>\n\n"
            f"Plate: <b>{plate}</b>\n"
            f"Gate: <b>{gate}</b>\n"
            f"Not on whitelist — access control decision required."
        )


notify = NotifyService()
