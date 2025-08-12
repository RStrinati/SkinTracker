import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")
pytest.importorskip("mediapipe")

from skin_analysis import process_skin_image


def test_process_skin_image_no_face(tmp_path):
    """Processing a blank image should return None as no face is detected."""
    img = np.full((300, 300, 3), 255, dtype=np.uint8)
    img_path = tmp_path / "blank.png"
    cv2.imwrite(str(img_path), img)

    result = process_skin_image(str(img_path), "user", "img", client=None)

    assert result is None


def test_temp_files_removed_after_upload_failure(tmp_path, monkeypatch):
    """Temporary files are cleaned up even if upload fails."""
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    import skin_analysis as sa

    img = np.full((300, 300, 3), 255, dtype=np.uint8)
    img_path = tmp_path / "input.png"
    cv2.imwrite(str(img_path), img)

    def fake_align(image):
        normalized = np.zeros((300, 300, 3), dtype=np.uint8)
        rotated_points = np.zeros((1, 2), dtype=np.float32)
        face_mask = np.ones((300, 300), dtype=np.uint8)
        return normalized, rotated_points, face_mask

    def fake_detect(normalized, rotated_points, face_mask):
        blemish_mask = np.zeros((300, 300), dtype=np.uint8)
        face_area = int(np.count_nonzero(face_mask))
        return blemish_mask, 0, face_area, 0.0

    monkeypatch.setattr(sa, "_align_face", fake_align)
    monkeypatch.setattr(sa, "_detect_blemishes", fake_detect)

    class DummyBucket:
        def upload(self, *_args, **_kwargs):
            raise RuntimeError("upload failed")

    class DummyStorage:
        def from_(self, _name):
            return DummyBucket()

    class DummyTable:
        def insert(self, _record):
            return self

        def execute(self):
            return None

    class DummyClient:
        storage = DummyStorage()

        def table(self, _name):
            return DummyTable()

    with pytest.raises(RuntimeError):
        sa.process_skin_image(str(img_path), "user", "img", client=DummyClient())

    remaining = list(tmp_path.iterdir())
    assert remaining == [img_path]

