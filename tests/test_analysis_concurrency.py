import asyncio
import time
from unittest.mock import MagicMock

import numpy as np
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from api.routers.analysis import router


@pytest.mark.anyio
async def test_analyze_face_heavy_concurrent(monkeypatch):
    app = FastAPI()
    app.include_router(router)

    # Dummy image used throughout
    dummy_image = np.zeros((100, 100, 3), dtype=np.uint8)

    # Minimal cv2 shim used by skin_analysis.*
    class MockCV2:
        imread = MagicMock(return_value=dummy_image)
        cvtColor = MagicMock(return_value=dummy_image)
        GaussianBlur = MagicMock(return_value=dummy_image)
        threshold = MagicMock(return_value=(1, dummy_image))
        findContours = MagicMock(return_value=([np.array([[[0, 0], [10, 0], [10, 10], [0, 10]]])], None))
        contourArea = MagicMock(return_value=100.0)
        drawContours = MagicMock(return_value=None)
        countNonZero = MagicMock(return_value=1000)
        circle = MagicMock()
        warpAffine = MagicMock(return_value=dummy_image)
        resize = MagicMock(return_value=dummy_image)
        getRotationMatrix2D = MagicMock(return_value=np.array([[1, 0, 0], [0, 1, 0]]))
        bitwise_and = MagicMock(return_value=dummy_image)
        THRESH_BINARY_INV = 1
        THRESH_OTSU = 8
        RETR_EXTERNAL = 0
        CHAIN_APPROX_SIMPLE = 1
        COLOR_BGR2GRAY = 6

    def fake_download(bucket: str, obj: str) -> str:
        # Keep these small but nonzero to simulate work
        time.sleep(0.01)
        return "/tmp/test.png"

    class FakeProvider:
        def analyze(self, path: str):
            time.sleep(0.01)
            # Use lists for JSON-friendliness if the endpoint surfaces this
            return {
                "faces": [{"bbox_xyxy": [0, 0, 100, 100], "landmarks_5": np.random.rand(5, 2).tolist()}],
                "face_count": 1,
            }

    def fake_upload(bucket: str, key: str, data: dict) -> None:
        return None

    # Monkeypatch the analysis module internals used by the route
    provider = FakeProvider()
    monkeypatch.setattr("api.routers.analysis.supabase.download_from_bucket", fake_download)
    monkeypatch.setattr("api.routers.analysis._provider", provider)
    monkeypatch.setattr("api.routers.analysis.supabase.upload_json_to_bucket", fake_upload)

    # Patch helpers in skin_analysis module
    monkeypatch.setattr("skin_analysis.align_face",
                        lambda *args, **kwargs: (dummy_image, np.random.rand(5, 2), dummy_image))
    monkeypatch.setattr("skin_analysis.detect_blemishes",
                        lambda *args, **kwargs: (dummy_image, 100, 1000, 10.0))
    monkeypatch.setattr("skin_analysis.cv2", MockCV2())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async def call():
            resp = await client.post("/analysis/face/heavy", json={"bucket": "b", "object_path": "p"})
            assert resp.status_code == 200
            assert resp.json()["ok"] is True

        start = time.perf_counter()
        await asyncio.gather(*(call() for _ in range(3)))
        duration = time.perf_counter() - start

    # With the small sleeps, sequential would be ~0.06s+; allow a generous bound.
    assert duration < 0.5
