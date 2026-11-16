"""
RSS Parsing & Processing Layer for Paperboy AI Agent.
Uses Feedparser and Python standard library to aggregate and clean RSS feeds
from multiple real-world news sources.
"""

import re
import html
import time
import calendar
from typing import List, Dict, Any, Optional
import feedparser

from config import DEFAULT_RSS_FEEDS, MAX_NEWS_ITEMS
import storage_service


def clean_html(raw_html: Optional[str]) -> str:
    """
    Strips HTML tags, resolves HTML entities, and normalizes whitespace
    using Python standard library regex and html modules.
    """
    if not raw_html:
        return ""
    # Strip HTML tags
    clean_text = re.sub(r"<[^>]+>", " ", raw_html)
    # Unescape HTML entities (&amp;, &nbsp;, &quot;, &#39;, etc.)
    clean_text = html.unescape(clean_text)
    # Normalize whitespace
    clean_text = re.sub(r"\s+", " ", clean_text).strip()
    return clean_text


def format_pub_date(entry: Any) -> str:
    """
    Formats the published date into a clean, human-readable string.
    """
    parsed_time = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if parsed_time:
        try:
            return time.strftime("%b %d, %Y • %I:%M %p", parsed_time)
        except Exception:
            pass
    raw_date = getattr(entry, "published", "") or getattr(entry, "updated", "")
    return clean_html(raw_date)


def fetch_and_parse_feeds(
    feeds: Optional[List[Dict[str, str]]] = None,
    limit: int = MAX_NEWS_ITEMS,
    use_cache_on_fail: bool = True
) -> List[Dict[str, Any]]:
    """
    Fetches news from configured real-world RSS feeds across multiple sources.
    Cleans, deduplicates, sorts by recency, and updates data/news_cache.json.

    Args:
        feeds: List of dicts with 'name' and 'url'
        limit: Max number of news items to return (default 20)
        use_cache_on_fail: If network fails, fallback to JSON cache

    Returns:
        List[Dict[str, Any]]: Clean list of news items
    """
    if feeds is None:
        feeds = DEFAULT_RSS_FEEDS

    collected_items: List[Dict[str, Any]] = []
    seen_links = set()
    seen_titles = set()

    for feed_info in feeds:
        source_name = feed_info.get("name", "Unknown Source")
        url = feed_info.get("url")
        if not url:
            continue

        try:
            parsed = feedparser.parse(url)
            for entry in parsed.entries:
                link = getattr(entry, "link", "").strip()
                raw_title = getattr(entry, "title", "").strip()
                clean_title = clean_html(raw_title)

                # Skip invalid or duplicate articles
                title_key = clean_title.lower()
                if not link or link in seen_links or not clean_title or title_key in seen_titles:
                    continue

                seen_links.add(link)
                seen_titles.add(title_key)

                # Extract content/summary
                raw_summary = (
                    getattr(entry, "summary", "")
                    or getattr(entry, "description", "")
                )
                summary = clean_html(raw_summary)
                if not summary or len(summary) < 15:
                    summary = "Click to read the complete article on the original source."

                # Truncate overly long summaries to keep cards balanced
                if len(summary) > 280:
                    summary = summary[:277].rsplit(" ", 1)[0] + "..."

                # Publication timestamp for sorting
                # BUG FIX: feedparser gives published_parsed as UTC struct_time.
                # time.mktime() treats its argument as local time, introducing a
                # timezone offset error on non-UTC machines (e.g. IST = UTC+5:30
                # would shift every timestamp by -19800 seconds, corrupting sort order).
                # calendar.timegm() correctly interprets the struct as UTC.
                parsed_time = (
                    getattr(entry, "published_parsed", None)
                    or getattr(entry, "updated_parsed", None)
                )
                timestamp = calendar.timegm(parsed_time) if parsed_time else 0.0
                pub_display = format_pub_date(entry)

                collected_items.append({
                    "title": clean_title,
                    "content": summary,
                    "source": source_name,
                    "link": link,
                    "published": pub_display,
                    "timestamp": timestamp,
                })
        except Exception as e:
            print(f"[RSSService] Error fetching feed {source_name} ({url}): {e}")

    # Fallback to local storage cache if network fetch yielded nothing
    if not collected_items and use_cache_on_fail:
        cached = storage_service.load_news_cache()
        if cached:
            return cached[:limit]

    # Sort collected items by recency (newest timestamp first)
    collected_items.sort(key=lambda x: x.get("timestamp", 0.0), reverse=True)

    # Slice to the requested limit (e.g. 20)
    final_items = collected_items[:limit]

    # Persist the fresh feed to data/news_cache.json and data/raw_news_cache.json
    if final_items:
        storage_service.save_news_cache(final_items)
        storage_service.save_raw_cache(final_items)
        print(f"[RSSService] Successfully aggregated {len(final_items)} stories from multiple sources.")

    return final_items
