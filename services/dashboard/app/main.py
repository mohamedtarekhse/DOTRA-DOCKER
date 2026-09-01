import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

API_URL = "http://api:8000/api/v1"

app = FastAPI(title="ACUSEEK Dashboard")

BASE = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")


async def api_get(path: str, **params):
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{API_URL}{path}", params=params)
        if resp.status_code == 200:
            return resp.json()
        return []


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    vehicles = await api_get("/vehicles")
    alerts = await api_get("/alerts")
    cameras = await api_get("/cameras")
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "vehicles": vehicles,
            "alerts": alerts,
            "cameras": cameras,
        },
    )


@app.get("/gates", response_class=HTMLResponse)
async def gates(request: Request):
    return templates.TemplateResponse("gates.html", {"request": request})


@app.get("/vehicles", response_class=HTMLResponse)
async def vehicles(request: Request):
    data = await api_get("/vehicles")
    return templates.TemplateResponse("vehicles.html", {"request": request, "vehicles": data})


@app.get("/persons", response_class=HTMLResponse)
async def persons(request: Request):
    data = await api_get("/persons")
    return templates.TemplateResponse("persons.html", {"request": request, "persons": data})


@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    return templates.TemplateResponse("search.html", {"request": request})


@app.get("/alerts", response_class=HTMLResponse)
async def alerts_page(request: Request):
    data = await api_get("/alerts")
    return templates.TemplateResponse("alerts.html", {"request": request, "alerts": data})


@app.get("/settings", response_class=HTMLResponse)
async def settings(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})


from fastapi.responses import HTMLResponse


@app.get("/api/search-results", response_class=HTMLResponse)
async def search_results(q: str):
    results = await api_get("/search/images", q=q, limit=18)
    html = ' '.join(
        f"""
        <div class="bg-slate-50 rounded-lg p-3 shadow">
            <img src="{r['image_url']}" class="w-full h-48 object-cover rounded mb-2" onerror="this.style.display='none'">
            <div class="text-xs text-slate-500">Score: {r['score']}</div>
            <div class="text-xs text-slate-500">{r.get('camera_name','')}</div>
            <div class="text-xs text-slate-400">{r['captured_at']}</div>
        </div>
        """
        for r in results
    )
    if not results:
        html = '<div class="col-span-3 text-slate-400 text-center py-10">No matching images found.</div>'
    return HTMLResponse(html)
