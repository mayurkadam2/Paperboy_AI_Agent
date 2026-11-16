"""
Configuration settings for Paperboy AI Agent.
Modularized to decouple settings from UI, Gemini AI runtime, and RSS parsing layers.
"""

import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"
CACHE_FILE = DATA_DIR / "news_cache.json"
RAW_CACHE_FILE = DATA_DIR / "raw_news_cache.json"
ENV_FILE = BASE_DIR / ".env"

# ── Load .env File Automatically (No third-party dependencies required) ─────
def load_env_file() -> None:
    """Parses a local .env file into os.environ if present."""
    if not ENV_FILE.exists():
        return
    try:
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("\"'")
                if key:
                    os.environ[key] = val
    except Exception as e:
        print(f"[Config] Error loading .env: {e}")

load_env_file()

# Server Settings
HOST = os.getenv("SERVER_HOST", "127.0.0.1")
PORT = int(os.getenv("SERVER_PORT", "8000"))

# Feed Settings
MAX_NEWS_ITEMS = 20

# ── Real Data RSS Feeds Across Multiple Trusted Sources ──────────────────────
DEFAULT_RSS_FEEDS = [
    {
        "name": "BBC Tech",
        "url": "https://feeds.bbci.co.uk/news/technology/rss.xml",
    },
    {
        "name": "BBC World",
        "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
    },
    {
        "name": "TechCrunch",
        "url": "https://techcrunch.com/feed/",
    },
    {
        "name": "The Verge",
        "url": "https://www.theverge.com/rss/index.xml",
    },
    {
        "name": "Ars Technica",
        "url": "https://feeds.arstechnica.com/arstechnica/index",
    },
    {
        "name": "Wired",
        "url": "https://www.wired.com/feed/rss",
    },
    {
        "name": "NPR News",
        "url": "https://feeds.npr.org/1001/rss.xml",
    },
]

# ── Gemini AI API Settings ───────────────────────────────────────────────────
def get_gemini_api_key() -> str:
    """Always returns the live Gemini API key from os.environ or .env."""
    load_env_file()
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("AI_API_KEY", "")

def get_gemini_model() -> str:
    return os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview")

# App Branding
APP_NAME = "Paperboy AI"
APP_TAGLINE = "Your Autonomous AI News Assistant"
APP_ICON = "📰"
