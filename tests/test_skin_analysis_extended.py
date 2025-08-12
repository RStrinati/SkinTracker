import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")
pytest.importorskip("mediapipe")

from skin_analysis import process_skin_image

def test_process_skin_image_with_face(tmp_path):
    """Processing an image with a face should return valid results."""
    # Create a mock image with a face (replace with actual test image if available)
    img = np.full((300, 300, 3), 255, dtype=np.uint8)
    cv2.circle(img, (150, 150), 50, (0, 0, 0), -1)  # Simulate a face
    img_path = tmp_path / "face.png"
    cv2.imwrite(str(img_path), img)

    result = process_skin_image(str(img_path), "user", "img", client=None)

    assert result is not None

def test_process_skin_image_invalid_format(tmp_path):
    """Processing an unsupported image format should raise an error."""
    invalid_img_path = tmp_path / "invalid.txt"
    invalid_img_path.write_text("This is not an image.")

    with pytest.raises(Exception):
        process_skin_image(str(invalid_img_path), "user", "img", client=None)
