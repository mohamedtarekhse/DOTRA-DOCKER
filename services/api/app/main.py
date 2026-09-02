from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .routers import auth, vehicles, gates, persons, search, cameras, alerts, websocket, permits
from .services.storage_service import storage


@asynccontextmanager
async def lifespan(app: FastAPI):
    storage._ensure_bucket("snapshots")
    storage._ensure_bucket("face-crops")
    storage._ensure_bucket("plate-crops")
    from .seed import seed_database
    await seed_database()
    yield


app = FastAPI(
    title="ACUSEEK API",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(vehicles.router, prefix=API_PREFIX)
app.include_router(gates.router, prefix=API_PREFIX)
app.include_router(persons.router, prefix=API_PREFIX)
app.include_router(search.router, prefix=API_PREFIX)
app.include_router(cameras.router, prefix=API_PREFIX)
app.include_router(alerts.router, prefix=API_PREFIX)
app.include_router(permits.router, prefix=API_PREFIX)
app.include_router(websocket.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "api"}


@app.get("/")
async def root():
    return {"message": "ACUSEEK API", "docs": "/api/docs"}
