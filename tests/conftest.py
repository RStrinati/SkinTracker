import sys, os, types
import pytest

# Ensure project root is on PYTHONPATH for tests
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

@pytest.fixture
def anyio_backend():
    """Configure the async test backend to use asyncio only."""
    return 'asyncio'

@pytest.fixture(autouse=True)
async def setup_teardown():
    """Setup and teardown for all async tests."""
    yield
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Provide default environment variables required by the application. Individual
# tests may override these as needed using ``monkeypatch``.
os.environ.setdefault("NEXT_PUBLIC_SUPABASE_URL", "url")
os.environ.setdefault("NEXT_PUBLIC_SUPABASE_ANON_KEY", "anon")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "token")
os.environ.setdefault("OPENAI_API_KEY", "openai")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "service")
os.environ.setdefault("BASE_URL", "http://localhost")

# Stub modules for external dependencies to allow tests to run without
# installing the full dependency set in this execution environment.
sys.modules.setdefault("dotenv", types.SimpleNamespace(load_dotenv=lambda: None))
sys.modules.setdefault(
    "supabase", types.SimpleNamespace(create_client=lambda url, key: None, Client=object)
)
sys.modules.setdefault("PIL", types.SimpleNamespace(Image=object))
sys.modules.setdefault(
    "telegram",
    types.SimpleNamespace(
        File=object,
        Bot=object,
        InlineKeyboardButton=object,
        InlineKeyboardMarkup=object,
        Update=object,
        BotCommand=object,
    ),
)
sys.modules.setdefault("openai", types.SimpleNamespace(AsyncOpenAI=object))
sys.modules.setdefault("cv2", types.SimpleNamespace(CV_8U=0, CV_16U=0, CV_32S=0))
class _DummyProvider:
    def analyze(self, *args, **kwargs):
        return {}

sys.modules.setdefault(
    "analysis_providers.insightface_provider",
    types.SimpleNamespace(InsightFaceProvider=_DummyProvider),
)
