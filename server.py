"""
Server Layer for Paperboy AI Agent.
Built with Python Standard Library (ThreadingHTTPServer, json, mimetypes, urllib).
Serves the Vanilla JS frontend and exposes endpoints for news and AI operations:
  - GET  /api/news        : Reads from central data/news_cache.json
  - POST /api/refresh     : Invokes update_feed() (manual RSS refresh)
  - POST /api/summarize   : Invokes summarize_feed()
  - POST /api/personalize : Invokes personalize_feed(topic)
  - POST /api/search      : Invokes dispatch_agent_tool(query)
"""

from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import json
import mimetypes
from pathlib import Path
from typing import Dict, Any

import config
import ai_service
import storage_service


class PaperboyHTTPHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler serving static assets and REST API endpoints."""

    def _send_json_response(self, data: Dict[str, Any], status: int = 200) -> None:
        """Sends a JSON response with proper headers."""
        response_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(response_bytes)

    def _serve_file(self, file_path: Path) -> None:
        """Serves a static file with appropriate MIME type."""
        if not file_path.exists() or not file_path.is_file():
            self.send_error(404, "File Not Found")
            return

        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = "application/octet-stream"

        try:
            with open(file_path, "rb") as f:
                content = f.read()

            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Error reading file: {e}")

    def do_GET(self) -> None:
        """Handles GET requests for static assets and news feeds."""
        parsed_path = self.path.split("?")[0]

        # API: Read from Central News Cache (data/news_cache.json)
        # Note: No auto-refresh. Only reads existing cache.
        if parsed_path == "/api/news":
            items = storage_service.load_news_cache()
            if not items:
                # If cache is missing on first-ever launch, initialize once
                res = ai_service.update_feed()
                items = res.get("items", [])
            self._send_json_response({
                "status": "ok",
                "count": len(items),
                "items": items[:config.MAX_NEWS_ITEMS]
            })
            return

        # Static file routing
        if parsed_path in ("/", "/index.html"):
            target_file = config.STATIC_DIR / "index.html"
        else:
            rel_path = parsed_path.lstrip("/")
            target_file = config.STATIC_DIR / rel_path

        self._serve_file(target_file)

    def do_POST(self) -> None:
        """Handles POST requests for AI functions and manual feed operations."""
        parsed_path = self.path.split("?")[0]
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b""
        payload = json.loads(body.decode("utf-8")) if body else {}

        # 1. API: Manual Refresh Feed -> update_feed()
        if parsed_path == "/api/refresh":
            result = ai_service.update_feed()
            self._send_json_response(result)
            return

        # 2. API: Summarize Feed -> summarize_feed()
        if parsed_path == "/api/summarize":
            result = ai_service.summarize_feed()
            self._send_json_response(result)
            return

        # 3. API: Personalize Feed -> personalize_feed(topic)
        if parsed_path == "/api/personalize":
            topic = payload.get("topic", "").strip()
            result = ai_service.personalize_feed(topic)
            self._send_json_response(result)
            return

        # 4. API: Agent Dispatcher (Gemini tool selection, QA, and counter-questions)
        if parsed_path == "/api/search":
            query = payload.get("query", "").strip()
            history = payload.get("history", [])
            if not query:
                self._send_json_response({
                    "status": "error",
                    "message": "Query cannot be empty"
                }, status=400)
                return

            agent_result = ai_service.dispatch_agent_tool(query, history=history)

            # Format uniform response structure for frontend
            action = agent_result.get("action", "answer")
            response_text = (
                agent_result.get("response")
                or agent_result.get("summary")
                or agent_result.get("message")
                or "No response."
            )
            feed_updated = bool(agent_result.get("feed_updated", False))
            items = agent_result.get("items", [])

            self._send_json_response({
                "status": agent_result.get("status", "ok"),
                "action": action,
                "query": query,
                "response": response_text,
                "feed_updated": feed_updated,
                "items": items,
            })
            return

        self.send_error(404, "Endpoint Not Found")

    def log_message(self, format: str, *args: Any) -> None:
        """Custom logging format."""
        print(f"[PaperboyServer] {self.address_string()} - {format % args}")


def run_server(host: str = config.HOST, port: int = config.PORT) -> None:
    """Starts the ThreadingHTTPServer."""
    config.STATIC_DIR.mkdir(parents=True, exist_ok=True)
    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, PaperboyHTTPHandler)
    print(f"\n=======================================================")
    print(f"📰 Paperboy AI Agent Server Running!")
    print(f"🌐 Access URL: http://{host}:{port}")
    print(f"=======================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[PaperboyServer] Shutting down...")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
