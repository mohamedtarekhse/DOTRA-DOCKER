from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db


async def seed_database():
    """Seed zones + 40 cameras if empty. Called on startup."""
    async for db in get_db():
        count = await db.execute(text("SELECT COUNT(*) FROM zones"))
        if count.scalar() > 0:
            return

        zones = [
            ("Gate 1", "gate", False),
            ("Gate 2", "gate", False),
            ("Loading Dock A", "loading_dock", True),
            ("Loading Dock B", "loading_dock", True),
            ("Warehouse", "warehouse", False),
            ("Production Hall", "production", False),
            ("Restricted Zone 1", "restricted", True),
            ("Restricted Zone 2", "restricted", True),
        ]
        from ..models import Zone
        zone_objs = []
        for name, ztype, restricted in zones:
            z = Zone(name=name, zone_type=ztype, is_restricted=restricted)
            db.add(z)
            zone_objs.append(z)
        await db.commit()
        for z in zone_objs:
            await db.refresh(z)
        print(f"[SEED] Added {len(zone_objs)} zones")
