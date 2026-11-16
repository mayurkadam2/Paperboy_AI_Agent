"""
Storage Layer for Paperboy AI Agent.
Handles reading and writing news data using JSON files and Python list structures.
Centralizes all cache operations for both working news cache and raw RSS cache.
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from config import CACHE_FILE, DATA_DIR

RAW_CACHE_FILE = DATA_DIR / "raw_news_cache.json"


def ensure_data_dir() -> None:
    """Ensures the data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def save_news_cache(news_items: List[Dict[str, Any]]) -> bool:
    """
    Saves a list of news dictionaries to the primary working dataset (news_cache.json).

    Args:
        news_items: List of news item dicts
    Returns:
        bool: True if save succeeded, False otherwise
    """
    try:
        ensure_data_dir()
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(news_items, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[StorageService] Failed to save news cache: {e}")
        return False


def load_news_cache() -> List[Dict[str, Any]]:
    """
    Loads news items from the primary working dataset (news_cache.json).

    Returns:
        List[Dict[str, Any]]: Cached news items, or empty list if none found.
    """
    if not CACHE_FILE.exists():
        return []
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except Exception as e:
        print(f"[StorageService] Failed to load news cache: {e}")
        return []


def save_raw_cache(news_items: List[Dict[str, Any]]) -> bool:
    """
    Saves original unpersonalized RSS articles to raw_news_cache.json
    so original data is never accidentally lost during personalization.
    """
    try:
        ensure_data_dir()
        with open(RAW_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(news_items, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[StorageService] Failed to save raw cache: {e}")
        return False


def load_raw_cache() -> List[Dict[str, Any]]:
    """
    Loads original unpersonalized RSS articles from raw_news_cache.json.
    """
    if not RAW_CACHE_FILE.exists():
        return []
    try:
        with open(RAW_CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except Exception as e:
        print(f"[StorageService] Failed to load raw cache: {e}")
        return []
