import pytest
from unittest.mock import MagicMock, patch
import numpy as np

@pytest.fixture
def mock_cv2():
    with patch('skin_analysis.cv2') as mock:
        mock.imread = MagicMock(return_value=np.zeros((300, 300, 3)))
        mock.imwrite = MagicMock(return_value=True)
        mock.circle = MagicMock()
        mock.getRotationMatrix2D = MagicMock(return_value=np.array([[1, 0, 0], [0, 1, 0]]))
        mock.warpAffine = MagicMock(return_value=np.zeros((300, 300, 3)))
        mock.resize = MagicMock(return_value=np.zeros((300, 300, 3)))
        mock.cvtColor = MagicMock(return_value=np.zeros((300, 300)))
        mock.bitwise_and = MagicMock(return_value=np.zeros((300, 300)))
        mock.GaussianBlur = MagicMock(return_value=np.zeros((300, 300)))
        mock.threshold = MagicMock(return_value=(None, np.zeros((300, 300))))
        mock.findContours = MagicMock(return_value=([], None))
        mock.drawContours = MagicMock()
        mock.countNonZero = MagicMock(return_value=90000)  # 300x300 size
        mock.COLOR_BGR2GRAY = MagicMock()
        mock.THRESH_BINARY_INV = 0
        mock.THRESH_OTSU = 0
        mock.RETR_EXTERNAL = 0
        mock.CHAIN_APPROX_SIMPLE = 0
        yield mock

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

def test_process_skin_image_with_face(tmp_path, mock_cv2):
    """Processing an image with a face should return valid results."""
    # Create a mock image with a face
    img = np.full((300, 300, 3), 255, dtype=np.uint8)
    img_path = tmp_path / "face.png"
    mock_cv2.imwrite(str(img_path), img)

    provider = SingleFaceProvider()
    result = process_skin_image(str(img_path), "user", "img", client=None, provider=provider)

    assert result is not None
    mock_cv2.imread.assert_called_once_with(str(img_path))

def test_process_skin_image_invalid_format(tmp_path):
    """Processing an unsupported image format should raise an error."""
    invalid_img_path = tmp_path / "invalid.txt"
    invalid_img_path.write_text("This is not an image.")

    provider = SingleFaceProvider()
    with pytest.raises(Exception):
        process_skin_image(str(invalid_img_path), "user", "img", client=None, provider=provider)
