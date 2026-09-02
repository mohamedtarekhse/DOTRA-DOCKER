from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..schemas import LoginRequest, Token

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def create_token(username: str, role: str = "admin") -> str:
    payload = {
        "sub": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"username": payload.get("sub"), "role": payload.get("role")}


def require_role(*roles: str):
    """Return a dependency that requires any valid user, optionally restricted to roles."""
    async def _dep(user: dict = Depends(get_current_user)):
        if roles and user.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Insufficient privileges")
        return user
    return _dep


async def require_device(x_secret: str | None = Header(None, alias="X-Secret")):
    """Authenticate internal services (LPR camera push, intrusion detections)."""
    if x_secret is None or x_secret != settings.LPR_EVENT_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")
    return {"source": "device"}


@router.post("/login", response_model=Token)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    if payload.username == settings.ADMIN_USERNAME and payload.password == settings.ADMIN_PASSWORD:
        return Token(access_token=create_token(payload.username, "admin"))
    raise HTTPException(status_code=401, detail="Invalid credentials")


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user
