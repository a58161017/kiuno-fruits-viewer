"""Project configuration: paths, API endpoints, rate limits."""
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"
RAW = ROOT / "raw"

FRUITS_JSON = DATA / "fruits.json"
COVERS_DIR = DATA / "covers"
CACHE_DIR = DATA / "cache"
SEED_YAML = RAW / "fruits_seed.yaml"
UNRESOLVED = DATA / "unresolved.json"

# Allowed regions for the prices[].region field
PRICE_REGIONS = ["北部", "中部", "南部", "東部"]

WIKIPEDIA_ZH_API = "https://zh.wikipedia.org/api/rest_v1"
WIKIPEDIA_ZH_W = "https://zh.wikipedia.org/w/api.php"
WIKIPEDIA_COMMONS = "https://commons.wikimedia.org/w/api.php"

ANTHROPIC_MODEL = "claude-sonnet-4-6"

RATE_LIMITS = {
    "wikipedia": 0.5,
    "commons": 0.5,
    "anthropic": 0.3,
}

REQUEST_TIMEOUT = 20
RETRY_MAX = 3
RETRY_BACKOFF = 2.0

ENRICH_TTL_DAYS = 90
COVER_MAX_PX = 800

USER_AGENT = "kiuno-fruits-viewer/0.1 (personal use; honghua-jhong@sunspark-group.com)"

SERVE_PORT = 8000
SERVE_HOST = "127.0.0.1"
