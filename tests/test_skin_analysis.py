import pytest
from unittest.mock import MagicMock

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")
pytest.importorskip("mediapipe")

import skin_analysis
from skin_analysis import process_skin_image


def _dummy_align_face(image):
    normalized = np.zeros((300, 300, 3), dtype=np.uint8)
    rotated_points = np.array([[10, 10]], dtype=np.float32)
    face_mask = np.ones((300, 300), dtype=np.uint8)
    return normalized, rotated_points, face_mask


def _dummy_detect_blemishes(normalized, rotated_points, face_mask):
    return np.zeros_like(face_mask), 0, face_mask.size, 0.0


def test_process_skin_image_no_face(tmp_path):
    """Processing a blank image should return None as no face is detected."""
    img = np.full((300, 300, 3), 255, dtype=np.uint8)
    img_path = tmp_path / "blank.png"
    cv2.imwrite(str(img_path), img)

    result = process_skin_image(str(img_path), "user", "img", client=None)

    assert result is None


def test_process_skin_image_inserts_record(tmp_path, monkeypatch):
    monkeypatch.setattr(skin_analysis, "_align_face", _dummy_align_face)
    monkeypatch.setattr(skin_analysis, "_detect_blemishes", _dummy_detect_blemishes)

    img = np.full((10, 10, 3), 255, dtype=np.uint8)
    img_path = tmp_path / "face.png"
    cv2.imwrite(str(img_path), img)

    table = MagicMock()
    bucket = MagicMock()
    storage = MagicMock()
    storage.from_.return_value = bucket
    client = MagicMock()
    client.storage = storage
    client.table.return_value = table

    result = process_skin_image(str(img_path), "user", "img", client=client)

    client.table.assert_called_with("skin_kpis")
    assert table.insert.called
    assert result["image_id"] == "img"

