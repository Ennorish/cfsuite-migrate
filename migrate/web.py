"""Local web UI for CFSuite migration tool."""
import json
import queue
import threading
import webbrowser
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import StreamingResponse

from migrate.auth import assert_not_production, get_credentials, list_orgs
from migrate.models import ProductionOrgError, SFCLINotFoundError
from migrate.pipeline import run_migration
from migrate.sf_api import build_client

app = FastAPI(title="CFSuite Migration")

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/", response_class=HTMLResponse)
def index():
    return (STATIC_DIR / "index.html").read_text()


@app.get("/api/orgs")
def get_orgs():
    try:
        orgs = list_orgs()
    except SFCLINotFoundError as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    return [asdict(o) for o in orgs]


@app.get("/api/objects")
def get_objects():
    return [
        "Entitlement",
        "CFSuite Request Flow",
        "CFSuite Community Request",
        "CFSuite Preferred Comms Config",
    ]


@app.post("/api/migrate")
def do_migrate(payload: dict):
    source_alias = payload.get("source")
    target_alias = payload.get("target")
    objects = payload.get("objects", [])

    if not source_alias or not target_alias or not objects:
        return JSONResponse({"error": "Missing source, target, or objects"}, status_code=400)

    if source_alias == target_alias:
        return JSONResponse({"error": "Source and target must be different orgs"}, status_code=400)

    # Production guard
    try:
        orgs = list_orgs()
    except SFCLINotFoundError as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    target_org = next((o for o in orgs if o.alias == target_alias), None)
    if target_org is None:
        return JSONResponse({"error": f"Target org '{target_alias}' not found"}, status_code=400)
    try:
        assert_not_production(target_org)
    except ProductionOrgError as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    # Build clients
    try:
        source_creds = get_credentials(source_alias)
        target_creds = get_credentials(target_alias)
        source_client = build_client(source_creds)
        target_client = build_client(target_creds)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    # Stream SSE progress events in real-time using a queue
    q = queue.Queue()

    def on_progress(name, event, data):
        q.put(json.dumps({"name": name, "event": event, "detail": data}))

    def run_in_thread():
        try:
            results = run_migration(source_client, target_client, objects, on_progress=on_progress)
            q.put(json.dumps({"event": "complete", "status": "success", "results": results}))
        except Exception as e:
            q.put(json.dumps({"event": "error", "error": str(e)}))
        q.put(None)  # sentinel

    threading.Thread(target=run_in_thread, daemon=True).start()

    def event_stream():
        while True:
            item = q.get()
            if item is None:
                break
            yield f"data: {item}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def serve(port: int = 8765):
    """Start the web UI server and open browser."""
    import uvicorn

    def open_browser():
        webbrowser.open(f"http://localhost:{port}")

    threading.Timer(1.0, open_browser).start()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
