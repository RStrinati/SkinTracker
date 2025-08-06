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

