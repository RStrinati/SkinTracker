import os
import pytest
from unittest.mock import MagicMock

from openai_service import OpenAIService

class FakeCompletion:
    def __init__(self, content):
        self.choices = [MagicMock(message=MagicMock(content=content))]

class FakeChat:
    def __init__(self, content):
        self.completions = MagicMock()
        self.completions.create = MagicMock(return_value=FakeCompletion(content))

class FakeClient:
    def __init__(self, content):
        self.chat = FakeChat(content)

def fake_openai(api_key=None):
    return FakeClient("summary")

@pytest.mark.asyncio
async def test_generate_summary(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'key')
    monkeypatch.setattr('openai_service.OpenAI', fake_openai)

    service = OpenAIService()
    result = await service.generate_summary({'products': [], 'triggers': [], 'symptoms': [], 'photos': []})
    assert result == "summary"
