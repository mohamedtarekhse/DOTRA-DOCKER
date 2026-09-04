import html
import os
from pathlib import Path
from urllib.parse import quote, urlsplit

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

API_URL = os.environ.get("API_URL", "http://api:8000/api/v1")
COOKIE_NAME = "acuseek_token"

app = FastAPI(title="ACUSEEK Dashboard")

BASE = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")


def _token(request: Request) -> str | None:
    return request.cookies.get(COOKIE_NAME)


def _auth_headers(request: Request) -> dict:
    token = _token(request)
    return {"Authorization": f"Bearer {token}"} if token else {}


def logged_in(request: Request) -> bool:
    return bool(_token(request))


def local_url(url: str) -> str:
    """Rewrite absolute URLs to same-origin relative paths (works on LAN + domain)."""
    if not url:
        return ""
    try:
        parsed = urlsplit(url)
        if parsed.scheme and parsed.netloc:
            return parsed.path + (f"?{parsed.query}" if parsed.query else "")
    except ValueError:
        pass
    return url


async def api_get(request: Request, path: str, **params):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{API_URL}{path}", params=params, headers=_auth_headers(request)
            )
            if resp.status_code == 200:
                return resp.json(), True
    except httpx.HTTPError:
        pass
    return [], False


async def api_mutate(request: Request, method: str, path: str, data=None, params=None):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.request(
                method, f"{API_URL}{path}", json=data, params=params,
                headers=_auth_headers(request),
            )
            return resp
    except httpx.HTTPError:
        return None


async def _html(request: Request, name: str, context: dict | None = None):
    if not logged_in(request):
        return RedirectResponse("/login", status_code=303)
    data = context or {}
    data["request"] = request
    return templates.TemplateResponse(name, data)


# ---------------------------------------------------------------- auth pages
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = ""):
    if logged_in(request):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@app.post("/login")
async def login(request: Request):
    form = await request.form()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{API_URL}/auth/login",
                json={"username": form.get("username", ""), "password": form.get("password", "")},
            )
            if resp.status_code != 200:
                return RedirectResponse("/login?error=1", status_code=303)
            token = resp.json()["access_token"]
    except httpx.HTTPError:
        return RedirectResponse("/login?error=1", status_code=303)

    response = RedirectResponse("/", status_code=303)
    response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax", max_age=86400)
    return response


@app.post("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    return response


@app.get("/api/health")
async def health():
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{API_URL.replace('/api/v1', '')}/health")
            ok = resp.status_code == 200
    except httpx.HTTPError:
        ok = False
    return {"status": "ok" if ok else "error"}


# ---------------------------------------------------------------- pages
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    vehicles, _ = await api_get(request, "/vehicles")
    alerts, _ = await api_get(request, "/alerts")
    cameras, _ = await api_get(request, "/cameras")
    return await _html(request, "dashboard.html", {
        "vehicles": vehicles, "alerts": alerts, "cameras": cameras,
    })


@app.get("/gates", response_class=HTMLResponse)
async def gates(request: Request):
    return await _html(request, "gates.html")


@app.get("/vehicles", response_class=HTMLResponse)
async def vehicles(request: Request):
    data, ok = await api_get(request, "/vehicles")
    if not ok:
        data = []
    return await _html(request, "vehicles.html", {"vehicles": data, "api_ok": ok})


@app.get("/persons", response_class=HTMLResponse)
async def persons(request: Request):
    data, ok = await api_get(request, "/persons")
    if not ok:
        data = []
    msg = request.query_params.get("msg", "")
    error_msg = msg[6:] if msg.startswith("error:") else ""
    msg = msg if not msg.startswith("error:") else ""
    return await _html(request, "persons.html", {
        "persons": data, "api_ok": ok,
        "msg": msg, "error_msg": error_msg,
    })


@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    q = request.query_params.get("q", "")
    return await _html(request, "search.html", {"q": q})


@app.get("/alerts", response_class=HTMLResponse)
async def alerts_page(request: Request):
    data, ok = await api_get(request, "/alerts")
    if not ok:
        data = []
    for a in data:
        a["_local_url"] = local_url(a.get("snapshot_url", ""))
    return await _html(request, "alerts.html", {"alerts": data, "api_ok": ok})


@app.get("/settings", response_class=HTMLResponse)
async def settings(request: Request):
    cameras, _ = await api_get(request, "/cameras")
    zones, _ = await api_get(request, "/cameras/zones")
    msg = request.query_params.get("msg", "")
    return await _html(request, "settings.html", {
        "cameras": cameras or [], "zones": zones or [], "msg": msg,
    })


@app.get("/preapprovals", response_class=HTMLResponse)
async def preapprovals_page(request: Request):
    data, ok = await api_get(request, "/permits", days=14)
    if not ok:
        data = []
    active = [p for p in data if p.get("active")]
    upcoming = [p for p in data if not p.get("active")]
    msg = request.query_params.get("msg", "")
    error_msg = msg[6:] if msg.startswith("error:") else ""
    msg = msg if not msg.startswith("error:") else ""
    return await _html(request, "preapprovals.html", {
        "permits": data, "active": active, "upcoming": upcoming, "api_ok": ok,
        "msg": msg, "error_msg": error_msg,
    })


@app.post("/preapprovals/upload")
async def preapprovals_upload(request: Request):
    if not logged_in(request):
        return RedirectResponse("/login", status_code=303)
    form = await request.form()
    upload = form.get("file")
    if upload is None or not getattr(upload, "filename", ""):
        return RedirectResponse("/preapprovals?msg=no-file", status_code=303)
    content = await upload.read()
    if not content:
        return RedirectResponse("/preapprovals?msg=empty", status_code=303)
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{API_URL}/permits/upload",
                files={"file": (upload.filename, content, upload.content_type or "application/octet-stream")},
                headers=_auth_headers(request),
            )
    except httpx.HTTPError:
        resp = None
    if resp is None or resp.status_code != 200:
        detail = ""
        if resp is not None:
            try:
                detail = resp.json().get("detail", resp.text[:300])
            except ValueError:
                detail = resp.text[:300]
        return RedirectResponse(f"/preapprovals?msg=error:{detail}.", status_code=303)
    report = resp.json()
    msg = (f"Imported {report['rows_processed']} rows — {report['permits_created']} created, "
           f"{report['permits_updated']} updated, {report['vehicles_created']} new vehicles"
           + (f"; skipped {len(report['errors'])} rows" if report.get("errors") else "") + ".")
    return RedirectResponse(f"/preapprovals?msg={quote(msg)}", status_code=303)


@app.get("/api/search-results", response_class=HTMLResponse)
async def search_results(request: Request, q: str):
    if not logged_in(request):
        return HTMLResponse('<div class="col-span-3 text-red-400 text-center py-8">Not authorized.</div>')
    if len(q) > 200:
        q = q[:200]
    results, ok = await api_get(request, "/search/images", q=q, limit=18)
    if not ok:
        return HTMLResponse(
            '<div class="col-span-3 text-red-400 text-center py-8">Search failed — API unreachable or not authorized.</div>'
        )
    cards = []
    for r in results:
        img = html.escape(local_url(str(r.get("image_url", ""))), quote=True)
        score = html.escape(str(r.get("score", "")), quote=True)
        camera = html.escape(str(r.get("camera_name", "") or ""), quote=True)
        captured = html.escape(str(r.get("captured_at", "")), quote=True)
        cards.append(
            f'<div class="bg-slate-50 rounded-lg p-3 shadow">'
            f'<img src="{img}" alt="snapshot" class="w-full h-48 object-cover rounded mb-2" '
            f'onerror="this.style.display=\'none\'">'
            f'<div class="text-xs text-slate-500">Score: {score}</div>'
            f'<div class="text-xs text-slate-500">{camera}</div>'
            f'<div class="text-xs text-slate-400">{captured}</div>'
            f'</div>'
        )
    if not cards:
        html_body = '<div class="col-span-3 text-slate-400 text-center py-10">No matching images found.</div>'
    else:
        html_body = " ".join(cards)
    return HTMLResponse(html_body)


# ---------------------------------------------------------------- actions
@app.post("/settings/cameras/add")
async def settings_camera_add(request: Request):
    if not logged_in(request):
        return RedirectResponse("/login", status_code=303)
    form = await request.form()
    payload = {
        "name": (form.get("name") or "").strip(),
        "ip_address": (form.get("ip_address") or "").strip(),
        "camera_type": (form.get("camera_type") or "lpr").strip(),
        "rtsp_url": (form.get("rtsp_url") or "").strip(),
    }
    if payload["name"] and payload["ip_address"] and payload["rtsp_url"]:
        resp = await api_mutate(request, "POST", "/cameras", data=payload)
        if resp is not None and resp.status_code == 200:
            return RedirectResponse("/settings?msg=camera-added", status_code=303)
    return RedirectResponse("/settings?msg=Failed+to+add+camera", status_code=303)


@app.post("/settings/zones/add")
async def settings_zone_add(request: Request):
    if not logged_in(request):
        return RedirectResponse("/login", status_code=303)
    form = await request.form()
    payload = {
        "name": (form.get("name") or "").strip(),
        "zone_type": (form.get("zone_type") or "general").strip(),
        "is_restricted": form.get("is_restricted") == "on",
    }
    if payload["name"]:
        resp = await api_mutate(request, "POST", "/cameras/zones", data=payload)
        if resp is not None and resp.status_code == 200:
            return RedirectResponse("/settings?msg=zone-added", status_code=303)
    return RedirectResponse("/settings?msg=Failed+to+add+zone", status_code=303)


@app.post("/vehicles/add")
async def vehicles_add(request: Request):
    if not logged_in(request):
        return RedirectResponse("/login", status_code=303)
    form = await request.form()
    payload = {
        "plate_number": (form.get("plate_number") or "").strip().upper(),
        "owner_name": form.get("owner_name") or None,
        "vehicle_type": form.get("vehicle_type") or None,
        "department": form.get("department") or None,
        "color": form.get("color") or None,
        "is_whitelisted": True,
    }
    if payload["plate_number"]:
        await api_mutate(request, "POST", "/vehicles", data=payload)
    return RedirectResponse("/vehicles", status_code=303)


@app.post("/vehicles/{vehicle_id}/delete")
async def vehicles_delete(request: Request, vehicle_id: str):
    if not logged_in(request):
        return RedirectResponse("/login", status_code=303)
    await api_mutate(request, "DELETE", f"/vehicles/{vehicle_id}")
    return RedirectResponse("/vehicles", status_code=303)


@app.post("/persons/add")
async def persons_add(request: Request):
    if not logged_in(request):
        return RedirectResponse("/login", status_code=303)
    form = await request.form()
    payload = {
        "full_name": (form.get("full_name") or "").strip(),
        "department": form.get("department") or None,
        "access_level": form.get("access_level") or "standard",
    }
    if payload["full_name"]:
        await api_mutate(request, "POST", "/persons", data=payload)
    return RedirectResponse("/persons", status_code=303)


@app.post("/persons/enroll-upload")
async def persons_enroll_upload(request: Request):
    if not logged_in(request):
        return RedirectResponse("/login", status_code=303)
    form = await request.form()
    person_id = str(form.get("person_id") or "")
    upload = form.get("file")
    if not person_id or upload is None or not getattr(upload, "filename", ""):
        return RedirectResponse("/persons?msg=no-file", status_code=303)
    content = await upload.read()
    if not content:
        return RedirectResponse("/persons?msg=empty", status_code=303)
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(
                f"{API_URL}/persons/enroll-upload",
                data={"person_id": person_id},
                files={"file": (upload.filename, content, upload.content_type or "image/jpeg")},
                headers=_auth_headers(request),
            )
    except httpx.HTTPError:
        resp = None
    if resp is None or resp.status_code != 200:
        detail = ""
        if resp is not None:
            try:
                detail = resp.json().get("detail", resp.text[:200])
            except ValueError:
                detail = resp.text[:200]
        return RedirectResponse(f"/persons?msg=error:{detail}.", status_code=303)
    return RedirectResponse("/persons?msg=enrolled", status_code=303)


@app.post("/alerts/{alert_id}/update")
async def alerts_update(request: Request, alert_id: str):
    if not logged_in(request):
        return RedirectResponse("/login", status_code=303)
    form = await request.form()
    payload = {
        "status": form.get("status") or "resolved",
        "resolved_by": form.get("resolved_by") or "dashboard",
    }
    await api_mutate(request, "PATCH", f"/alerts/{alert_id}", data=payload)
    return RedirectResponse("/alerts", status_code=303)


@app.post("/preapprovals/{permit_id}/revoke")
async def preapprovals_revoke(request: Request, permit_id: str):
    if not logged_in(request):
        return RedirectResponse("/login", status_code=303)
    await api_mutate(request, "DELETE", f"/permits/{permit_id}")
    return RedirectResponse("/preapprovals", status_code=303)


@app.post("/gates/{gate_id}/override")
async def gates_override(request: Request, gate_id: str):
    if not logged_in(request):
        return RedirectResponse("/login", status_code=303)
    form = await request.form()
    action = form.get("action") or "open"
    await api_mutate(request, "POST", f"/gates/{gate_id}/manual-override", params={"action": action})
    return RedirectResponse("/gates", status_code=303)