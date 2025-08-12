import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")

from skin_analysis import process_skin_image


class SingleFaceProvider:
    """Stub provider returning a single centered face."""

    def analyze(self, image_path):  # type: ignore[override]
        return {
            "provider": "stub",
            "face_count": 1,
            "faces": [
                {
                    "bbox_xyxy": [50.0, 50.0, 250.0, 250.0],
                    "landmarks_5": [
                        [80.0, 120.0],
                        [220.0, 120.0],
                        [150.0, 160.0],
                        [110.0, 200.0],
                        [190.0, 200.0],
                    ],
                }
            ],
        }

def test_process_skin_image_with_face(tmp_path):
    """Processing an image with a face should return valid results."""
    # Create a mock image with a face (replace with actual test image if available)
    img = np.full((300, 300, 3), 255, dtype=np.uint8)
    cv2.circle(img, (150, 150), 50, (0, 0, 0), -1)  # Simulate a face
    img_path = tmp_path / "face.png"
    cv2.imwrite(str(img_path), img)

    provider = SingleFaceProvider()
    result = process_skin_image(str(img_path), "user", "img", client=None, provider=provider)

    assert result is not None

def test_process_skin_image_invalid_format(tmp_path):
    """Processing an unsupported image format should raise an error."""
    invalid_img_path = tmp_path / "invalid.txt"
    invalid_img_path.write_text("This is not an image.")

    provider = SingleFaceProvider()
    with pytest.raises(Exception):
        process_skin_image(str(invalid_img_path), "user", "img", client=None, provider=provider)
