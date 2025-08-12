import asyncio
import time

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

try:
    from api.routers.analysis import router
except Exception:
    router = None
    pytest.skip("analysis router unavailable", allow_module_level=True)


@pytest.mark.anyio
async def test_analyze_face_heavy_concurrent(monkeypatch):
    app = FastAPI()
    app.include_router(router)

    def fake_download(bucket: str, obj: str) -> str:
        time.sleep(0.1)
        return "/tmp/test.png"

    def fake_analyze(path: str):
        time.sleep(0.1)
        return {"faces": [], "face_count": 0}

    def fake_upload(bucket: str, key: str, data: dict) -> None:
        return None

    monkeypatch.setattr("api.routers.analysis.download_from_bucket", fake_download)
    monkeypatch.setattr("api.routers.analysis._provider.analyze", fake_analyze)
    monkeypatch.setattr("api.routers.analysis.upload_json_to_bucket", fake_upload)

    async with AsyncClient(app=app, base_url="http://test") as client:
        async def call():
            resp = await client.post(
                "/analysis/face/heavy", json={"bucket": "b", "object_path": "p"}
            )
            assert resp.status_code == 200
            assert resp.json()["ok"] is True

        start = time.perf_counter()
        await asyncio.gather(*[call() for _ in range(3)])
        duration = time.perf_counter() - start

    # If calls were processed sequentially, duration would be ~0.6s.
    # Allow generous upper bound to account for CI variability.
    assert duration < 0.5
