from fastapi import FastAPI, HTTPException, Request
import uuid
import asyncio
import os
import tempfile
import json

app = FastAPI(title="Toggle Service")

# file used to persist
# TODO - understand how TOGGLES_FILE will be injected by compose etc
TOGGLES_FILE = os.getenv("TOGGLES_FILE", "toggles.json")

# in-memory store
toggles = {} 

# fancy async lock for concurrnecy
_store_lock = asyncio.Lock()

# ---------- Persistence helpers ----------
def _save_sync(path: str, data: dict) -> None:
    """
    Perform an atomic write of `data` to `path` by writing to a temp file
    in the same directory and replacing the target file.
    This function is synchronous and intended to be run in a thread.
    """
    dirpath = os.path.dirname(os.path.abspath(path)) or "."
    # Make sure directory exists
    os.makedirs(dirpath, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=dirpath)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        # Atomic replace
        os.replace(tmp_path, path)
    finally:
        # If anything left, remove temp file
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def _load_sync(path: str) -> dict:
    """
    Synchronously load toggles from path. Returns empty dict on missing
    or invalid JSON.
    """
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure returned structure is a dict of str->bool
            if isinstance(data, dict):
                return {str(k): bool(v) for k, v in data.items()}
    except (OSError, json.JSONDecodeError):
        # Could log an error here; return empty store to avoid crashing
        return {}
    return {}


async def save_toggles() -> None:
    """
    Async wrapper that offloads the synchronous atomic write to a thread.
    Call this while holding _store_lock to ensure consistent writes.
    """
    await asyncio.to_thread(_save_sync, TOGGLES_FILE, toggles)


async def load_toggles() -> None:
    """
    Async wrapper that offloads loading to a thread and updates the in-memory store.
    """
    data = await asyncio.to_thread(_load_sync, TOGGLES_FILE)
    toggles.clear()
    toggles.update(data)


# ---------- Lifecycle events ----------
@app.on_event("startup")
async def on_startup():
    await load_toggles()


@app.on_event("shutdown")
async def on_shutdown():
    # Try to persist final state on shutdown
    async with _store_lock:
        await save_toggles()

# ---------- Middleware ----------
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

# ---------- Endpoints ----------
@app.post("/create")
async def create_toggle():
    guid = str(uuid.uuid4())
    async with _store_lock:
        toggles[guid] = False
        await save_toggles()
    return {"guid": guid, "state": False}

@app.post("/toggle/{guid}")
def toggle_state(guid: str):
    if guid not in toggles:
        raise HTTPException(status_code=404, detail="Toggle not found")
    toggles[guid] = not toggles[guid]
    return {"guid": guid, "state": toggles[guid]}

@app.get("/status/{guid}")
def get_status(guid: str):
    if guid not in toggles:
        raise HTTPException(status_code=404, detail="Toggle not found")
    return {"guid": guid, "state": toggles[guid]}

