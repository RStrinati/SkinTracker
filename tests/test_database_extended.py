import pytest
from unittest.mock import MagicMock

pytest.skip("extended database tests require full environment", allow_module_level=True)

from database import Database

@pytest.mark.anyio
async def test_database_connection_failure(monkeypatch):
    monkeypatch.setattr('database.create_client', lambda url, key: None)

    db = Database()
    with pytest.raises(Exception):
        await db.get_user_logs(1, days=7)

@pytest.mark.anyio
async def test_create_user_duplicate_id(monkeypatch):
    supabase_client = MagicMock()
    table = MagicMock()
    supabase_client.table.return_value = table
    table.select.return_value = table
    table.eq.return_value = table
    table.execute.return_value = MagicMock(data=[{"id": 1}])  # Simulate existing user

    monkeypatch.setattr('database.create_client', lambda url, key: supabase_client)

    db = Database()
    with pytest.raises(Exception):
        await db.create_user(telegram_id=1, username="duplicate")
