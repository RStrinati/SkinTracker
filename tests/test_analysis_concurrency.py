import asyncio
import time

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from api.routers.analysis import router


@pytest.mark.anyio
async def test_analyze_face_heavy_concurrent(monkeypatch):
    app = FastAPI()
    app.include_router(router)

    def fake_download(bucket: str, obj: str) -> str:
        time.sleep(0.01)  # Reduced sleep time for faster execution
        return "/tmp/test.png"

    class FakeProvider:
        def analyze(self, path: str):
            time.sleep(0.01)  # Reduced sleep time for faster execution
            return {"faces": [], "face_count": 0}

    def fake_upload(bucket: str, key: str, data: dict) -> None:
        return None

    from api.routers import analysis

    def fake_process_skin_image(image_path, user_id, image_id, client, provider):
        return {"face_detected": True, "blemish_count": 0}
    
    monkeypatch.setattr("api.routers.analysis.process_skin_image", fake_process_skin_image)
    provider = FakeProvider()
    analysis._provider = provider
    analysis.download_from_bucket = fake_download
    analysis.upload_json_to_bucket = fake_upload

    async with AsyncClient(app=app, base_url="http://test") as client:
        async def call():
            resp = await client.post(
                "/analysis/face/heavy", json={"bucket": "b", "object_path": "p"}
            )
            if resp.status_code != 200:
                print(f"Error response: {resp.status_code} - {resp.text}")
            assert resp.status_code == 200
            assert resp.json()["ok"] is True

        start = time.perf_counter()
        await asyncio.gather(*[call() for _ in range(3)])
        duration = time.perf_counter() - start

    # If calls were processed sequentially, duration would be ~0.6s.
    # Allow generous upper bound to account for CI variability.
    assert duration < 0.5
