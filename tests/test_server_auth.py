import importlib
import hmac
import hashlib
import time
import asyncio
import types
import sys


class HTTPException(Exception):
    def __init__(self, status_code: int, detail=None):
        self.status_code = status_code
        self.detail = detail


class DummyAPIRouter:
    def __init__(self, *args, **kwargs):
        pass
    def include_router(self, router):
        pass
    def get(self, *args, **kwargs):
        def decorator(func):
            return func
        return decorator
    def post(self, *args, **kwargs):
        def decorator(func):
            return func
        return decorator
    def delete(self, *args, **kwargs):
        def decorator(func):
            return func
        return decorator


class DummyFastAPI(DummyAPIRouter):
    def on_event(self, *args, **kwargs):
        def decorator(func):
            return func
        return decorator


class DummyBaseModel:
    def __init__(self, **data):
        for k, v in data.items():
            setattr(self, k, v)
    def dict(self, **kwargs):
        return self.__dict__


def setup_framework_stubs():
    sys.modules['fastapi'] = types.SimpleNamespace(
        FastAPI=DummyFastAPI,
        Request=object,
        HTTPException=HTTPException,
        BackgroundTasks=object,
        APIRouter=DummyAPIRouter,
    )
    sys.modules['fastapi.responses'] = types.SimpleNamespace(JSONResponse=dict)
    sys.modules['pydantic'] = types.SimpleNamespace(BaseModel=DummyBaseModel)


def test_telegram_auth_persists_token(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret")
    monkeypatch.setenv("SESSION_DB_PATH", str(tmp_path / "sessions.db"))
    setup_framework_stubs()

    class DummyBot:
        def __init__(self):
            self.database = types.SimpleNamespace(client=types.SimpleNamespace(table=lambda name: types.SimpleNamespace(select=lambda *a, **k: types.SimpleNamespace(limit=lambda *a, **k: types.SimpleNamespace(execute=lambda: None)))))
            self.openai_service = types.SimpleNamespace(analyze_ingredients=lambda *a, **k: None)
        async def initialize(self):
            pass
        async def shutdown(self):
            pass
        async def process_update(self, data):
            pass
        async def set_webhook(self, url):
            return True
        async def delete_webhook(self):
            return True

    sys.modules['bot'] = types.SimpleNamespace(SkinHealthBot=DummyBot)
    api_mod = types.ModuleType("api")
    routers_mod = types.ModuleType("api.routers")
    analysis_mod = types.ModuleType("api.routers.analysis")
    analysis_mod.router = None
    sys.modules['api'] = api_mod
    sys.modules['api.routers'] = routers_mod
    sys.modules['api.routers.analysis'] = analysis_mod

    import server
    importlib.reload(server)

    now = int(time.time())
    payload = {"id": 1, "auth_date": now, "first_name": "Alice"}
    data_check_string = "\n".join(
        f"{k}={payload[k]}" for k in sorted(payload.keys())
    )
    secret_key = hashlib.sha256("secret".encode()).digest()
    payload["hash"] = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    req = server.TelegramAuthRequest(**payload)
    result = asyncio.run(server.telegram_auth(req))
    token = result["token"]

    assert server.get_user_id_from_token(token) == 1


def test_token_expires_and_purged(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret")
    monkeypatch.setenv("SESSION_DB_PATH", str(tmp_path / "sessions.db"))
    monkeypatch.setenv("SESSION_TTL", "1")
    setup_framework_stubs()

    class DummyBot:
        def __init__(self):
            self.database = types.SimpleNamespace(client=types.SimpleNamespace(table=lambda name: types.SimpleNamespace(select=lambda *a, **k: types.SimpleNamespace(limit=lambda *a, **k: types.SimpleNamespace(execute=lambda: None)))))
            self.openai_service = types.SimpleNamespace(analyze_ingredients=lambda *a, **k: None)
        async def initialize(self):
            pass
        async def shutdown(self):
            pass
        async def process_update(self, data):
            pass
        async def set_webhook(self, url):
            return True
        async def delete_webhook(self):
            return True

    sys.modules['bot'] = types.SimpleNamespace(SkinHealthBot=DummyBot)
    api_mod = types.ModuleType("api")
    routers_mod = types.ModuleType("api.routers")
    analysis_mod = types.ModuleType("api.routers.analysis")
    analysis_mod.router = None
    sys.modules['api'] = api_mod
    sys.modules['api.routers'] = routers_mod
    sys.modules['api.routers.analysis'] = analysis_mod

    import server
    importlib.reload(server)

    base_time = 1000
    monkeypatch.setattr(server.time, "time", lambda: base_time)

    payload = {"id": 2, "auth_date": base_time}
    data_check_string = "\n".join(
        f"{k}={payload[k]}" for k in sorted(payload.keys())
    )
    secret_key = hashlib.sha256("secret".encode()).digest()
    payload["hash"] = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    req = server.TelegramAuthRequest(**payload)
    result = asyncio.run(server.telegram_auth(req))
    token = result["token"]

    assert server.get_user_id_from_token(token) == 2

    # Advance time beyond TTL and ensure token is invalidated and removed
    monkeypatch.setattr(server.time, "time", lambda: base_time + 2)
    assert server.get_user_id_from_token(token) is None
    cur = server._session_conn.execute("SELECT COUNT(*) FROM auth_sessions")
    assert cur.fetchone()[0] == 0
