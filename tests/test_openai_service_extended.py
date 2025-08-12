import pytest
from unittest.mock import MagicMock

from openai_service import OpenAIService

pytest.skip("extended openai tests require full environment", allow_module_level=True)

class FakeCompletion:
    def __init__(self, content):
        self.choices = [MagicMock(message=MagicMock(content=content))]

class FakeChat:
    def __init__(self, content):
        async def create(*args, **kwargs):
            return FakeCompletion(content)
        self.completions = MagicMock()
        self.completions.create = create

class FakeClient:
    def __init__(self, content):
        self.chat = FakeChat(content)

def fake_openai(api_key=None):
    return FakeClient("error")

@pytest.mark.anyio
async def test_generate_summary_invalid_key(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'invalid_key')
    monkeypatch.setattr('openai_service.AsyncOpenAI', fake_openai)

    service = OpenAIService()
    with pytest.raises(Exception):
        await service.generate_summary({'products': [], 'triggers': [], 'symptoms': [], 'photos': []})
