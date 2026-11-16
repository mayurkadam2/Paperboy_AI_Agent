"""
AI Agent Service for Paperboy.
Powered by Google Gemini API with native Function Calling (Tools) and Conversation Support:
  - Answers questions & counter-questions based on current news cache.
  - update_feed(): Fetches RSS and updates central news_cache.json.
  - personalize_feed(topic): Filters news_cache.json to topic-relevant articles.
  - summarize_feed(): Generates concise news briefing.
"""

import json
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional

import config
import rss_service
import storage_service


# =============================================================================
# Primary Function A: update_feed()
# =============================================================================

def update_feed() -> Dict[str, Any]:
    """
    Fetches news from all configured RSS sources and updates the central news cache.
    Manual only, no LLM. Updates data/news_cache.json and data/raw_news_cache.json.
    """
    try:
        articles = rss_service.fetch_and_parse_feeds(limit=config.MAX_NEWS_ITEMS)
        count = len(articles)
        return {
            "status": "ok",
            "action": "update_feed",
            "count": count,
            "message": f"Successfully updated central news cache with {count} fresh stories from multiple sources.",
            "response": f"✅ Central news feed has been refreshed with {count} latest stories from all sources.",
            "items": articles
        }
    except Exception as e:
        print(f"[AIService] Error in update_feed: {e}")
        return {
            "status": "error",
            "action": "update_feed",
            "count": 0,
            "message": f"Failed to update feed: {e}",
            "response": f"⚠️ Failed to update feed: {e}",
            "items": []
        }


# =============================================================================
# Primary Function B: summarize_feed()
# =============================================================================

def summarize_feed() -> Dict[str, Any]:
    """
    Reads the collected news from data/news_cache.json and generates an understandable
    news briefing using the Gemini LLM.
    """
    articles = storage_service.load_news_cache()

    if not articles:
        return {
            "status": "empty",
            "action": "summarize_feed",
            "count": 0,
            "summary": "The central news cache is currently empty. Please click **Refresh Feed** to load news stories first.",
            "response": "The central news cache is currently empty. Please click **Refresh Feed** to load news stories first."
        }

    selected = articles[:15]
    # Minimize token usage by sending only headings and sources
    context_blocks = [
        f"[{idx+1}] {item.get('title')} ({item.get('source')})"
        for idx, item in enumerate(selected)
        if item.get('title')
    ]
    prompt = (
        "Here are today's top news headlines:\n\n"
        + "\n".join(context_blocks)
        + "\n\nTask: Provide a concise, engaging, and professional news briefing summarizing the major developments and themes across these headlines."
    )

    llm_summary = call_gemini_raw(prompt, system_instruction="You are Paperboy AI, an expert news anchor. Provide clear, structured news summaries based on current headlines.")

    if not llm_summary:
        # Extractive fallback
        bullet_points = "\n".join(
            f"- **{a.get('title')}** ({a.get('source')}): {a.get('content')}"
            for a in selected[:6]
        )
        llm_summary = (
            "### 📰 Today's News Briefing\n\n"
            + bullet_points
        )

    return {
        "status": "ok",
        "action": "summarize_feed",
        "count": len(articles),
        "summary": llm_summary,
        "response": llm_summary
    }


# =============================================================================
# Primary Function C: personalize_feed(topic)
# =============================================================================

def personalize_feed(topic: str) -> Dict[str, Any]:
    """
    Filters the news collection according to the user's requested topic.
    Updates data/news_cache.json as the active working dataset while preserving
    data/raw_news_cache.json.
    """
    topic_clean = topic.strip()
    if not topic_clean:
        return {
            "status": "error",
            "action": "personalize_feed",
            "topic": "",
            "count": 0,
            "message": "Please specify a topic to personalize your feed (e.g., 'gaming', 'AI', 'sports').",
            "response": "Please specify a topic to personalize your feed (e.g., 'gaming', 'AI', 'sports').",
            "items": []
        }

    # Start from raw baseline cache if available, else current working cache
    source_articles = storage_service.load_raw_cache()
    if not source_articles:
        source_articles = storage_service.load_news_cache()

    if not source_articles:
        return {
            "status": "empty",
            "action": "personalize_feed",
            "topic": topic_clean,
            "count": 0,
            "message": "News cache is empty. Please refresh the feed first.",
            "response": "News cache is empty. Please refresh the feed first.",
            "items": []
        }

    # Keyword and semantic matching
    topic_terms = [t.lower() for t in topic_clean.split() if len(t) > 2]
    if not topic_terms:
        topic_terms = [topic_clean.lower()]

    relevant_articles = []
    for item in source_articles:
        text = f"{item.get('title', '')} {item.get('content', '')} {item.get('source', '')}".lower()
        if any(term in text for term in topic_terms):
            relevant_articles.append(item)

    if relevant_articles:
        # Update working dataset directly
        storage_service.save_news_cache(relevant_articles)
        msg = f"Filtered your feed for **'{topic_clean}'**. Showing {len(relevant_articles)} matching stories."
        return {
            "status": "ok",
            "action": "personalize_feed",
            "topic": topic_clean,
            "count": len(relevant_articles),
            "message": msg,
            "response": msg,
            "items": relevant_articles
        }
    else:
        msg = f"No stories found matching topic **'{topic_clean}'** in the current feed. Your feed was left unchanged."
        return {
            "status": "no_match",
            "action": "personalize_feed",
            "topic": topic_clean,
            "count": 0,
            "message": msg,
            "response": msg,
            "items": []
        }


# =============================================================================
# Gemini API Tools & Function Calling Definition
# =============================================================================

GEMINI_TOOLS_DECLARATION = [
    {
        "function_declarations": [
            {
                "name": "update_feed",
                "description": "Refreshes and updates the latest news from RSS feeds into the central cache. Call this when the user explicitly asks to refresh, update, fetch latest, or reload the news feed.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {}
                }
            },
            {
                "name": "personalize_feed",
                "description": "Filters the news feed to only articles relevant to a requested topic or category, updating the user's working feed.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "topic": {
                            "type": "STRING",
                            "description": "The specific topic or category to filter the feed by (e.g. 'gaming', 'AI', 'space', 'politics', 'economy')."
                        }
                    },
                    "required": ["topic"]
                }
            },
            {
                "name": "summarize_feed",
                "description": "Generates a general news briefing of current headlines in the feed. Call this when the user asks for a news summary, recap, or briefing.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {}
                }
            }
        ]
    }
]


# =============================================================================
# Gemini Low-Level HTTP Client
# =============================================================================

def _get_candidate_models() -> List[str]:
    """
    Returns prioritized list of Gemini models with fallbacks for high availability.
    """
    primary = config.get_gemini_model()
    candidates = [primary, "gemini-3-flash-preview", "gemini-flash-lite-latest", "gemini-3.8-flash"]
    seen = set()
    result = []
    for m in candidates:
        if m and m not in seen:
            seen.add(m)
            result.append(m)
    return result


def call_gemini_raw(prompt: str, system_instruction: str = "") -> Optional[str]:
    """
    Sends a simple text prompt to the Gemini API and returns the text response.
    Tries candidate models automatically if the primary model is busy or unavailable.
    """
    api_key = config.get_gemini_api_key()
    if not api_key or api_key == "your_gemini_api_key_here":
        return None

    payload: Dict[str, Any] = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 800
        }
    }
    if system_instruction:
        payload["system_instruction"] = {
            "parts": [{"text": system_instruction}]
        }

    for model in _get_candidate_models():
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=req_data, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    for part in parts:
                        if "text" in part:
                            return part["text"].strip()
        except Exception as e:
            print(f"[AIService] Model '{model}' raw call note: {e}. Trying fallback if available...")
            continue

    return None


# =============================================================================
# Gemini Agent Dispatcher with Function Calling & Multi-Turn Conversation
# =============================================================================

def build_system_instruction(news_items: List[Dict[str, Any]]) -> str:
    """
    Constructs the system prompt injecting only headlines (no full text)
    to minimize token usage and latency.
    """
    headlines = []
    for idx, item in enumerate(news_items[:25], start=1):
        title = item.get("title", "").strip()
        source = item.get("source", "").strip()
        if title:
            entry = f"[{idx}] {title}"
            if source:
                entry += f" ({source})"
            headlines.append(entry)

    feed_text = "\n".join(headlines) if headlines else "No headlines currently loaded in feed."

    return (
        "You are Paperboy AI, an intelligent, friendly news assistant and analyst.\n\n"
        "TODAY'S NEWS HEADLINES IN THE FEED (HEADLINES ONLY):\n"
        "------------------------------------\n"
        f"{feed_text}\n"
        "------------------------------------\n\n"
        "CORE CAPABILITIES & TOOLS AVAILABLE:\n"
        "- `update_feed()`: Refreshes the central news cache with latest stories from all RSS feeds.\n"
        "- `personalize_feed(topic)`: Filters and updates the active feed to stories matching a topic (e.g. AI, gaming, crypto, politics, economy, science).\n"
        "- `summarize_feed()`: Generates a concise news briefing of current headlines.\n\n"
        "BEHAVIOR RULES & INSTRUCTIONS:\n"
        "1. UNRELATED QUESTIONS, GREETINGS & CASUAL CHAT:\n"
        "   If the user asks greetings (e.g., 'hello', 'hi bro', 'how are you?'), casual questions, or anything totally unrelated to the news headlines:\n"
        "   - DO NOT search the headlines for a match or say you couldn't find news about it.\n"
        "   - Greet the user warmly as Paperboy AI.\n"
        "   - Provide clear, helpful instructions on how to use Paperboy AI, explaining key capabilities:\n"
        "     * 🎯 **Personalizing Feed**: Ask me to filter news by topic (e.g., 'Personalize for AI', 'Show me gaming news').\n"
        "     * 📰 **Summarizing Feed**: Ask me for an executive summary of current headlines (e.g., 'Summarize feed', 'Give me a briefing').\n"
        "     * 🔄 **Updating / Refreshing Feed**: Ask me to fetch fresh stories (e.g., 'Update feed', 'Refresh news').\n"
        "     * 💬 **Discussing Headlines**: Ask about any of today's headlines to explore what is happening.\n\n"
        "2. NEWS INQUIRIES & COUNTER-QUESTIONS:\n"
        "   - When the user asks about topics or events present in the headlines, discuss them clearly, cite the headline and source, and offer to personalize the feed or summarize further.\n\n"
        "3. TOOL CALLING:\n"
        "   - When the user asks to refresh or update: call `update_feed()`.\n"
        "   - When the user asks to filter or personalize by topic: call `personalize_feed(topic)`.\n"
        "   - When the user asks for a summary or briefing: call `summarize_feed()`.\n\n"
        "4. TONE & STYLE:\n"
        "   Keep responses concise, welcoming, well-structured, and easy to read using markdown formatting."
    )


def dispatch_agent_tool(user_input: str, history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Main entry point for user requests.
    Sends user query and history to Gemini with tool definitions and token-efficient headline context.
    Executes functions if requested by Gemini, and returns the response and feed state.
    """
    api_key = config.get_gemini_api_key()
    news_items = storage_service.load_news_cache()

    # Format contents history for Gemini API
    gemini_contents: List[Dict[str, Any]] = []

    if history:
        for turn in history[-6:]:  # Keep last 3 exchanges for context
            role = "user" if turn.get("role") == "user" else "model"
            content = turn.get("content", "")
            if content:
                gemini_contents.append({
                    "role": role,
                    "parts": [{"text": content}]
                })

    # Append current user prompt
    gemini_contents.append({
        "role": "user",
        "parts": [{"text": user_input}]
    })

    # If Gemini API Key is available, call Gemini with Tools
    if api_key and api_key != "your_gemini_api_key_here":
        payload = {
            "system_instruction": {
                "parts": [{"text": build_system_instruction(news_items)}]
            },
            "contents": gemini_contents,
            "tools": GEMINI_TOOLS_DECLARATION,
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 800
            }
        }

        for model in _get_candidate_models():
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            try:
                req_data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(url, data=req_data, headers={"Content-Type": "application/json"}, method="POST")

                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    candidates = data.get("candidates", [])
                    if not candidates:
                        continue
                    parts = candidates[0].get("content", {}).get("parts", [])

                    # Check for Function Call / Tool Call
                    for part in parts:
                        if "functionCall" in part:
                            fn_call = part["functionCall"]
                            fn_name = fn_call.get("name")
                            fn_args = fn_call.get("args", {})

                            print(f"[AIService] Model '{model}' triggered tool: {fn_name} with args {fn_args}")

                            if fn_name == "update_feed":
                                result = update_feed()
                                return {
                                    "status": "ok",
                                    "action": "update_feed",
                                    "response": result.get("response"),
                                    "feed_updated": True,
                                    "items": result.get("items", [])
                                }

                            elif fn_name == "personalize_feed":
                                topic = fn_args.get("topic", "")
                                result = personalize_feed(topic)
                                return {
                                    "status": result.get("status", "ok"),
                                    "action": "personalize_feed",
                                    "response": result.get("response"),
                                    "feed_updated": result.get("status") == "ok",
                                    "items": result.get("items", [])
                                }

                            elif fn_name == "summarize_feed":
                                result = summarize_feed()
                                return {
                                    "status": "ok",
                                    "action": "summarize_feed",
                                    "response": result.get("response"),
                                    "feed_updated": False,
                                    "items": []
                                }

                        # Normal conversational text answer
                        if "text" in part:
                            return {
                                "status": "ok",
                                "action": "answer",
                                "response": part["text"].strip(),
                                "feed_updated": False,
                                "items": []
                            }
            except Exception as e:
                print(f"[AIService] Model '{model}' call note: {e}. Trying next model...")
                continue

    # Fallback if API key is not configured or all models were unreachable
    return fallback_agent_dispatch(user_input, news_items)


def fallback_agent_dispatch(user_input: str, news_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Fallback agent logic when Gemini API key is not set or network is unreachable.
    """
    text = user_input.strip().lower()

    # Rule 1: Explicit Refresh Feed
    if any(p in text for p in ("refresh", "refresh feed", "update feed", "reload feed", "refresh news", "update news")):
        res = update_feed()
        return {
            "status": "ok",
            "action": "update_feed",
            "response": res.get("response"),
            "feed_updated": True,
            "items": res.get("items", [])
        }

    # Rule 2: Explicit Summary
    if any(p in text for p in ("summarize", "summarize news", "news summary", "briefing", "give me a briefing")):
        res = summarize_feed()
        return {
            "status": "ok",
            "action": "summarize_feed",
            "response": res.get("response"),
            "feed_updated": False,
            "items": []
        }

    # Rule 3: Explicit Personalize
    if text.startswith("filter by ") or text.startswith("personalize for ") or text.startswith("personalize by "):
        topic = text.split("by ", 1)[-1] if "by " in text else text.split("for ", 1)[-1]
        res = personalize_feed(topic)
        return {
            "status": res.get("status", "ok"),
            "action": "personalize_feed",
            "response": res.get("response"),
            "feed_updated": res.get("status") == "ok",
            "items": res.get("items", [])
        }

    # Match headlines (title & source only)
    q_words = [w for w in text.split() if len(w) > 2]
    matched = []
    for item in news_items:
        corpus = f"{item.get('title','')} {item.get('source','')}".lower()
        if any(w in corpus for w in q_words):
            matched.append(item)

    if matched:
        lines = [
            f"Here are top stories matching **\"{user_input}\"** in today's headlines:\n"
        ]
        for item in matched[:4]:
            lines.append(
                f"- **[{item.get('title')}]({item.get('link')})** ({item.get('source')})\n"
            )
        lines.append("\n💡 *Tip: You can ask me to **'personalize for <topic>'** or **'summarize feed'** anytime!*")
        return {
            "status": "ok",
            "action": "answer",
            "response": "\n".join(lines),
            "feed_updated": False,
            "items": []
        }
    else:
        # User asked something unrelated, greeting, or casual chat
        instructions = (
            "👋 Hello! I'm **Paperboy AI**, your intelligent news assistant.\n\n"
            "I'm here to keep you informed with live news and smart feed management. Here is what you can ask me to do:\n\n"
            "- 🎯 **Personalize Your Feed**: Filter news by topic (e.g. *\"Personalize for AI\"*, *\"Filter by gaming\"*, or *\"Show sports news\"*).\n"
            "- 📰 **Summarize The Feed**: Get an executive summary of current headlines (e.g. *\"Summarize feed\"* or *\"Give me a news briefing\"*).\n"
            "- 🔄 **Refresh News**: Fetch the latest stories across all RSS sources (e.g. *\"Update feed\"* or *\"Refresh news\"*).\n"
            "- 💬 **Explore Any Headline**: Ask questions about any news headline in the feed to dive deeper!\n"
        )
        return {
            "status": "ok",
            "action": "answer",
            "response": instructions,
            "feed_updated": False,
            "items": []
        }
