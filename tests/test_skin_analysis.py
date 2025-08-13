import pytest
from unittest.mock import MagicMock

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")

from skin_analysis import process_skin_image


class NoFaceProvider:
    """Stub provider that returns no faces."""

    def analyze(self, image_path):  # type: ignore[override]
        return {"provider": "stub", "face_count": 0, "faces": []}


@pytest.fixture
def mock_cv2(monkeypatch):
    mock = MagicMock()
    mock.imwrite = MagicMock(return_value=True)
    mock.imread = MagicMock(return_value=np.zeros((300, 300, 3)))
    monkeypatch.setattr('skin_analysis.cv2', mock)
    return mock

def test_process_skin_image_no_face(tmp_path, mock_cv2):
    """Processing a blank image should return None as no face is detected."""
    img = np.full((300, 300, 3), 255, dtype=np.uint8)
    img_path = tmp_path / "blank.png"
    mock_cv2.imwrite(str(img_path), img)

    provider = NoFaceProvider()
    result = process_skin_image(str(img_path), "user", "img", client=None, provider=provider)

    assert result is None

