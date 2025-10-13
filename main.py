from fastapi import FastAPI, HTTPException, Request
import uuid

app = FastAPI(title="Toggle Service")
toggles = {}  # dict: {guid: bool}

@app.middleware("http")
async def log_request(request: Request, call_next):
    body = await request.body()
    print(f"Incoming request: {request.method} {request.url}")
    print(f"Headers: {dict(request.headers)}")
    if body:
        print(f"Body: {body.decode('utf-8')}")
    response = await call_next(request)
    return response

@app.post("/create")
def create_toggle():
    guid = str(uuid.uuid4())
    toggles[guid] = False
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

