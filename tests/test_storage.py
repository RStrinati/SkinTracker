
import os
import sys
import types
import asyncio
import pytest
from types import SimpleNamespace

# Stub PIL.Image since Pillow is not available
class _DummyImage:
    def __init__(self, path: str | None = None):
        self.path = path

    def thumbnail(self, size):
        pass

    def save(self, path, optimize=True, quality=85):
        with open(path, "wb") as f:
            f.write(b"data")
        self.path = path


def _open_stub(path):
    return _DummyImage(path)


def _new_stub(mode, size, color=None):
    return _DummyImage()


_image_module = types.SimpleNamespace(open=_open_stub, new=_new_stub)
_pil_module = types.ModuleType("PIL")
_pil_module.Image = _image_module
sys.modules.setdefault("PIL", _pil_module)
sys.modules.setdefault("PIL.Image", _image_module)

supabase_stub = types.SimpleNamespace(Client=object)
sys.modules.setdefault("supabase", supabase_stub)
telegram_stub = types.SimpleNamespace(File=object)
sys.modules.setdefault("telegram", telegram_stub)

from services.storage import StorageService


class FakeFile:
    def __init__(self, file_path="photo.jpg"):
        self.file_path = file_path
        self.downloaded_path = None

    async def download_to_drive(self, path):
        self.downloaded_path = path
        img = _new_stub("RGB", (10, 10), color="white")
        img.save(path)


class FakeBucket:
    def upload(self, *args, **kwargs):
        return SimpleNamespace(error=None)

    def get_public_url(self, filename):
        return f"https://example.com/{filename}"


class FakeStorage:
    def from_(self, name):
        assert name == "skin-photos"
        return FakeBucket()


class FakeClient:
    storage = FakeStorage()


def test_temp_file_retained_until_cleanup():
    client = FakeClient()
    service = StorageService(client)
    file = FakeFile()

    public_url, temp_path, image_id = asyncio.run(service.save_photo(123, file))

    assert public_url == f"https://example.com/uploads/123/{image_id}.jpg"
    assert temp_path == file.downloaded_path
    assert os.path.exists(temp_path)
    os.unlink(temp_path)
    assert not os.path.exists(temp_path)
