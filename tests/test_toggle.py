import json
import pytest
from httpx import AsyncClient, ASGITransport
from toggle_service.app import create_app


@pytest.mark.asyncio
async def test_persistence_roundtrip(tmp_path):
    path = tmp_path / "toggles.json"
    app = create_app(str(path))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost:8009") as ac:
        # create a toggle
        r = await ac.post("/create")
        assert r.status_code == 200
        data = r.json()
        guid = data["guid"]
        assert data["state"] is False

        # toggle it
        r2 = await ac.post(f"/toggle/{guid}")
        assert r2.status_code == 200
        assert r2.json()["state"] is True

    # After the client context, the app should have run shutdown and saved the file
    content = json.loads(path.read_text(encoding="utf-8"))
    assert content.get(guid) is True


@pytest.mark.asyncio
async def test_loads_on_startup(tmp_path):
    guid = "58a2bbac-e534-4479-8da2-5f344d91de79"
    data = {guid: True}
    path = tmp_path / "toggles.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    print(f"[DEBUG] Using temp path: {path}")

    app = create_app(str(path))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost:8009") as ac:
        r = await ac.get(f"/status/{guid}")
        assert r.status_code == 200
        assert r.json()["state"] is True
