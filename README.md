# Paperboy AI Agent 📰

An autonomous RSS feed aggregator and AI news assistant with a **Vanilla JavaScript** frontend, **Feedparser** multi-source RSS aggregation, and **Google Gemini API** with native **Function Calling (Tools)** and **Multi-Turn Counter-Question** capabilities.

---

## 🏗️ Architecture

```
Paperboy_AI_Agent/
├── server.py           # Application & REST API Server (Python Standard Library)
├── config.py           # Configuration (Feeds, Gemini API Key, Port)
├── rss_service.py      # RSS Feed Parsing Across 7 Trusted Sources
├── ai_service.py       # Gemini AI Agent Core (Tools & Multi-Turn Conversation)
├── storage_service.py  # Centralized Cache Operations (Working & Raw Caches)
├── static/             # Vanilla JS Frontend (HTML5, CSS3, JS)
│   ├── index.html      # UI Structure (Sticky Topbar, Grid, Pinned Bottom Bar)
│   ├── style.css       # Clean Styling & Custom Colors
│   └── app.js          # Live Clock, Multi-Turn Chat, Counter-Questions, Tool State
├── data/
│   ├── news_cache.json     # Primary Working Dataset for AI operations
│   └── raw_news_cache.json # Preserved Raw Multi-Source RSS Data
├── .gitignore          # Excludes .env, secrets, caches, and pycache
├── .env.example        # Environment variables template for Gemini API
└── flow.txt            # Complete architecture & request flow document
```

---

## 🧠 Gemini AI Agent & Function Calling Tools

The AI agent uses the **Google Gemini API** (`gemini-3-flash-preview`) with native tool declarations:

1. **`update_feed()`**:
   Invoked when the user asks to refresh or update the feed. Re-aggregates live RSS stories across all sources.
2. **`personalize_feed(topic)`**:
   Invoked when the user asks to filter or personalize the feed (e.g., *"Show me gaming news"*, *"Filter for AI"*). Updates `data/news_cache.json` directly.
3. **`summarize_feed()`**:
   Invoked when the user asks for an overall news briefing or summary of today's headlines.
4. **Feed-Based QA & Counter-Questions**:
   When asking questions or counter-questions (e.g. *"What happened with GTA 6?"*, followed by *"Why was he in a hospital?"*), Gemini uses the conversation history and the active news feed articles to answer directly with citations.

---

## 🚀 Getting Started

### 1. Add your Gemini API Key
Create a `.env` file in the project root:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3-flash-preview
```
*(Get a free key at [Google AI Studio](https://aistudio.google.com/app/apikey))*

### 2. Start the Server
```bash
python server.py
```

### 3. Open in Browser
```
http://127.0.0.1:8000
```
