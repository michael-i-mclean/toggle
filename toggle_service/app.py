from fastapi import FastAPI, HTTPException, Request
import uuid
import asyncio
from typing import Dict, Optional
from .persistence import load as _load_from_disk, save as _save_to_disk
from contextlib import asynccontextmanager

def create_app(toggles_file: Optional[str] = "toggles.json") -> FastAPI:
    """
    Factory to create a FastAPI app with an encapsulated in-memory store
    and persistence to `toggles_file`.
    """
    toggles: Dict[str, bool] = {}
    _store_lock = asyncio.Lock()
    TOGGLES_FILE = toggles_file or "toggles.json"

    # --- lifecycle ---
    async def on_startup():
        print(f"[DEBUG] on_startup TOGGLES_FILE {TOGGLES_FILE}")
        data = await _load_from_disk(TOGGLES_FILE)
        toggles.clear()
        toggles.update(data)

    async def on_shutdown():
        async with _store_lock:
            await _save_to_disk(TOGGLES_FILE, toggles)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        print("App starting up")
        await on_startup()
        yield
        await on_shutdown()
        print("App shutting down")


    app = FastAPI(title="Toggle Service", lifespan=lifespan) 

    # --- middleware ---
    @app.middleware("http")
    async def log_request(request: Request, call_next):
        body = await request.body()
        print(f"Incoming request: {request.method} {request.url}")
        print(f"Headers: {dict(request.headers)}")
        if body:
            try:
                print(f"Body: {body.decode('utf-8')}")
            except Exception:
                print("Body: <binary data>")
        response = await call_next(request)
        return response

    # --- endpoints ---
    @app.post("/create")
    async def create_toggle():
        guid = str(uuid.uuid4())
        async with _store_lock:
            toggles[guid] = False
            await _save_to_disk(TOGGLES_FILE, toggles)
        return {"guid": guid, "state": False}

    @app.post("/toggle/{guid}")
    async def toggle_state(guid: str):
        async with _store_lock:
            if guid not in toggles:
                raise HTTPException(status_code=404, detail="Toggle not found")
            toggles[guid] = not toggles[guid]
            await _save_to_disk(TOGGLES_FILE, toggles)
            return {"guid": guid, "state": toggles[guid]}

    @app.get("/status/{guid}")
    async def get_status(guid: str):
        if guid not in toggles:
            raise HTTPException(status_code=404, detail="Toggle not found")
        return {"guid": guid, "state": toggles[guid]}

    # expose internals for testing (lightweight)
    app.state._toggles = toggles
    app.state._store_lock = _store_lock
    app.state._toggles_file = TOGGLES_FILE

    return app

