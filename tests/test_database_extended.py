import pytest
from unittest.mock import MagicMock

from database import Database

@pytest.mark.anyio
async def test_database_connection_failure(monkeypatch):
    """Test that database connection failure raises an exception."""
    supabase_client = MagicMock()
    table = MagicMock()
    table.select = MagicMock(return_value=table)
    table.limit = MagicMock(return_value=table)
    table.execute = MagicMock(side_effect=Exception("Connection failed"))
    supabase_client.table.return_value = table
    supabase_client.storage = MagicMock()
    supabase_client.storage.get_bucket.return_value = MagicMock()

    monkeypatch.setattr('services.supabase.supabase.client', supabase_client)

    db = Database()
    with pytest.raises(Exception):
        await db.initialize()

@pytest.mark.anyio
async def test_create_user_duplicate_id(monkeypatch):
    """Test that creating a user with an existing ID raises an exception."""
    def mock_execute():
        raise Exception("Duplicate user")

    supabase_client = MagicMock()
    table = MagicMock()
    table.select = MagicMock(return_value=table)
    table.eq = MagicMock(return_value=table)
    table.execute = mock_execute
    supabase_client.table.return_value = table
    supabase_client.storage = MagicMock()
    supabase_client.storage.get_bucket.return_value = MagicMock()

    monkeypatch.setattr('services.supabase.supabase.client', supabase_client)

    db = Database()
    with pytest.raises(Exception):
        await db.create_user(telegram_id=1, username="test")
