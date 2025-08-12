import os
import pytest
from unittest.mock import MagicMock

from database import Database
import asyncio

def test_get_user_logs(monkeypatch):
    # Prepare fake supabase client
    supabase_client = MagicMock()
    supabase_client.storage = MagicMock()
    supabase_client.storage.get_bucket.return_value = MagicMock()

    def make_table_mock(return_data):
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.gte.return_value = table
        table.order.return_value = table
        table.execute.return_value = MagicMock(data=return_data)
        return table

    table_data = {
        'product_logs': [{'id': 1, 'product_name': 'A'}],
        'trigger_logs': [{'id': 2, 'trigger_name': 'B'}],
        'symptom_logs': [{'id': 3, 'symptom_name': 'C'}],
        'photo_logs': [{'id': 4, 'photo_url': 'url'}],
    }
    table_mocks = {name: make_table_mock(data) for name, data in table_data.items()}
    supabase_client.table.side_effect = lambda name: table_mocks[name]

    # Patch shared supabase client
    monkeypatch.setattr('services.supabase.supabase.client', supabase_client)

    db = Database()

    async def fake_get_user_by_telegram_id(tid):
        return {'id': 10, 'telegram_id': tid}

    monkeypatch.setattr(db, 'get_user_by_telegram_id', fake_get_user_by_telegram_id)

    logs = asyncio.run(db.get_user_logs(1, days=7))

    assert logs['products'] == table_data['product_logs']
    assert logs['triggers'] == table_data['trigger_logs']
    assert logs['symptoms'] == table_data['symptom_logs']
    assert logs['photos'] == table_data['photo_logs']


def test_create_user_with_defaults(monkeypatch):
    supabase_client = MagicMock()
    supabase_client.storage = MagicMock()
    supabase_client.storage.get_bucket.return_value = MagicMock()
    table = MagicMock()
    supabase_client.table.return_value = table
    table.select.return_value = table
    table.eq.return_value = table
    table.insert.return_value = table
    # First execute call for select (no existing user), second for insert
    table.execute.side_effect = [
        MagicMock(data=[]),
        MagicMock(data=[{"id": 1, "timezone": "UTC", "reminder_time": "09:00"}]),
    ]

    monkeypatch.setattr('services.supabase.supabase.client', supabase_client)

    db = Database()
    result = asyncio.run(db.create_user(telegram_id=1, username="test"))
    assert result["timezone"] == "UTC"
    assert result["reminder_time"] == "09:00"


def test_add_and_get_conditions(monkeypatch):
    supabase_client = MagicMock()
    supabase_client.storage = MagicMock()
    supabase_client.storage.get_bucket.return_value = MagicMock()
    table = MagicMock()
    supabase_client.table.return_value = table
    table.insert.return_value = table
    table.select.return_value = table
    table.eq.return_value = table
    table.execute.side_effect = [
        MagicMock(data=[{"id": 1, "name": "Acne", "condition_type": "existing"}]),
        MagicMock(data=[{"id": 1, "name": "Acne", "condition_type": "existing"}]),
    ]

    monkeypatch.setattr('services.supabase.supabase.client', supabase_client)

    db = Database()

    async def fake_get_user_by_telegram_id(tid):
        return {'id': 10, 'telegram_id': tid}

    monkeypatch.setattr(db, 'get_user_by_telegram_id', fake_get_user_by_telegram_id)

    result = asyncio.run(db.add_condition(1, 'Acne', 'existing'))
    assert result['name'] == 'Acne'
    assert table.insert.called

    conditions = asyncio.run(db.get_conditions(1))
    assert conditions[0]['condition_type'] == 'existing'
    assert table.select.called


def test_get_users_with_reminders(monkeypatch):
    supabase_client = MagicMock()
    supabase_client.storage = MagicMock()
    supabase_client.storage.get_bucket.return_value = MagicMock()
    table = MagicMock()
    supabase_client.table.return_value = table
    table.select.return_value = table
    table.execute.return_value = MagicMock(data=[{
        'telegram_id': 1,
        'reminder_time': '09:00',
        'timezone': 'UTC'
    }])

    monkeypatch.setattr('services.supabase.supabase.client', supabase_client)

    db = Database()
    users = asyncio.run(db.get_users_with_reminders())
    assert users[0]['telegram_id'] == 1
