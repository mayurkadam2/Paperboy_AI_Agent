/**
 * Paperboy AI Agent - Vanilla JavaScript Frontend Layer
 * Handles state, live clock, REST API communication, view switching,
 * multi-turn conversation (counter-questions), and markdown rendering.
 */

// ── DOM Element References ──────────────────────────────────────────────────
const liveDateTimeEl = document.getElementById("liveDateTime");
const logoTextEl = document.getElementById("logoText");
const btnRefreshEl = document.getElementById("btnRefresh");
const feedSectionEl = document.getElementById("feedSection");
const newsGridEl = document.getElementById("newsGrid");
const feedCountEl = document.getElementById("feedCount");

const responseSectionEl = document.getElementById("responseSection");
const responseQueryTagEl = document.getElementById("responseQueryTag");
const loadingContainerEl = document.getElementById("loadingContainer");
const responseCardEl = document.getElementById("responseCard");
const responseBodyEl = document.getElementById("responseBody");
const btnBackEl = document.getElementById("btnBack");

const searchFormEl = document.getElementById("searchForm");
const searchInputEl = document.getElementById("searchInput");

// ── State ───────────────────────────────────────────────────────────────────
let currentNews = [];
let conversationHistory = []; // Stores [{role: 'user'|'model', content: string}] for counter-questions

// ── 1. Live Real-Time Clock ─────────────────────────────────────────────────
function updateClock() {
  const now = new Date();
  const options = {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
  };
  liveDateTimeEl.textContent = `🕒 ${now.toLocaleDateString("en-US", options).replace(" at ", " • ")}`;
}
setInterval(updateClock, 1000);
updateClock();

// ── 2. Markdown Formatter ───────────────────────────────────────────────────
function formatMarkdown(text) {
  if (!text) return "";

  // Escape HTML special chars to prevent XSS
  let html = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Headers (before bold/italic so # chars are consumed first)
  html = html
    .replace(/^### (.*$)/gim, "<h3>$1</h3>")
    .replace(/^## (.*$)/gim, "<h2>$1</h2>")
    .replace(/^# (.*$)/gim, "<h1>$1</h1>");

  // Markdown links must run BEFORE bold/italic
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer">$1 &#8599;</a>');

  // Bold & Italics
  html = html
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>");

  // Horizontal rules
  html = html.replace(/^---$/gim, "<hr style='margin: 1rem 0; opacity: 0.2;' />");

  // Consecutive bullet lines wrapped in <ul>
  html = html.replace(/((?:(?:^|\n)\s*[-*]\s+[^\n]+)+)/gm, (block) => {
    const items = block.trim().split(/\n/).filter(l => l.trim())
      .map(l => `<li>${l.replace(/^\s*[-*]\s+/, "")}</li>`).join("");
    return `<ul>${items}</ul>`;
  });

  // Wrap plain text paragraphs
  html = html.split("\n\n").map((para) => {
    para = para.trim();
    if (!para) return "";
    if (para.startsWith("<h") || para.startsWith("<ul") || para.startsWith("<hr") || para.startsWith("<p") || para.startsWith("<div")) {
      return para;
    }
    return `<p>${para.replace(/\n/g, "<br>")}</p>`;
  }).join("");

  return html;
}

// ── 3. Render News Cards ────────────────────────────────────────────────────
function renderNewsCards(items) {
  newsGridEl.innerHTML = "";
  if (!items || items.length === 0) {
    newsGridEl.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 2rem; color: #64748b;">
        No news articles available. Click <strong>Refresh Feed</strong> to aggregate stories.
      </div>`;
    feedCountEl.textContent = "0 stories";
    return;
  }

  feedCountEl.textContent = `Showing ${items.length} curated stories`;

  items.forEach((news) => {
    const card = document.createElement("a");
    card.className = "news-card";

    const title = news.title || "Untitled";
    const content = news.content || "No description available.";
    const link = news.link || "#";
    const source = news.source || "News";

    card.href = link;
    card.target = "_blank";
    card.rel = "noopener noreferrer";

    card.innerHTML = `
      <div>
        <div class="news-title">${title}</div>
        <p class="news-content">${content}</p>
      </div>
      <div class="news-footer">
        <span class="news-source-tag">${source}</span>
        <span class="news-link-btn">
          Read Source &#8599;
        </span>
      </div>
    `;

    newsGridEl.appendChild(card);
  });
}

// ── 4. API: Fetch News Feed ─────────────────────────────────────────────────
async function fetchNews() {
  feedCountEl.textContent = "Loading stories...";
  try {
    const response = await fetch("/api/news");
    const data = await response.json();
    if (data.status === "ok" && Array.isArray(data.items)) {
      currentNews = data.items;
      renderNewsCards(currentNews);
    } else {
      renderNewsCards([]);
    }
  } catch (err) {
    console.error("Failed to fetch news:", err);
    feedCountEl.textContent = "Error loading news";
  }
}

// ── 5. API: Refresh News Feed ───────────────────────────────────────────────
async function refreshNews() {
  const refreshIcon = btnRefreshEl.querySelector(".refresh-icon");
  if (refreshIcon) refreshIcon.style.display = "inline-block";
  btnRefreshEl.disabled = true;
  btnRefreshEl.style.opacity = "0.7";

  showFeedView();
  conversationHistory = []; // Reset conversation on fresh feed refresh

  try {
    const response = await fetch("/api/refresh", { method: "POST" });
    const data = await response.json();
    if (data.status === "ok" && Array.isArray(data.items)) {
      currentNews = data.items;
      renderNewsCards(currentNews);
    }
  } catch (err) {
    console.error("Failed to refresh feed:", err);
  } finally {
    btnRefreshEl.disabled = false;
    btnRefreshEl.style.opacity = "1";
  }
}

// ── 6. View Switchers ───────────────────────────────────────────────────────
function showFeedView() {
  responseSectionEl.style.display = "none";
  feedSectionEl.style.display = "block";
  searchInputEl.value = "";
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function showResponseView(query) {
  // Feed vanishes immediately
  feedSectionEl.style.display = "none";
  responseSectionEl.style.display = "block";

  responseQueryTagEl.textContent = `Conversation with Paperboy AI`;
  loadingContainerEl.style.display = "flex";
  responseCardEl.style.display = "block";
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// ── 7. Render Conversation Thread (Supports Counter-Questions) ──────────────
function renderConversation() {
  responseBodyEl.innerHTML = "";

  conversationHistory.forEach((turn, idx) => {
    const bubble = document.createElement("div");
    if (turn.role === "user") {
      bubble.style.cssText = "background: #f1f5f9; border-left: 4px solid #4f4fff; padding: 0.75rem 1rem; border-radius: 8px; margin-bottom: 1rem; font-weight: 600; color: #1e293b;";
      bubble.innerHTML = `<span>👤 You:</span> ${turn.content}`;
    } else {
      bubble.style.cssText = "background: #ffffff; padding: 0.5rem 0.2rem 1.25rem 0.2rem; border-bottom: 1px solid rgba(79, 79, 255, 0.15); margin-bottom: 1.25rem;";
      bubble.innerHTML = formatMarkdown(turn.content);
    }
    responseBodyEl.appendChild(bubble);
  });
}

// ── 8. API: Execute Search / Chat / Counter-Question ────────────────────────
async function executeSearch(query) {
  showResponseView(query);

  // Add user query to conversation history immediately
  conversationHistory.push({ role: "user", content: query });
  renderConversation();

  try {
    const response = await fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: query,
        history: conversationHistory.slice(0, -1) // Send previous context
      }),
    });

    const data = await response.json();
    loadingContainerEl.style.display = "none";

    let aiReply = data.response || "No response received.";

    // If feed was updated by a tool (update_feed or personalize_feed)
    if (data.feed_updated && Array.isArray(data.items) && data.items.length > 0) {
      currentNews = data.items;
      renderNewsCards(currentNews);
      aiReply += `\n\n---\n**[📰 View Updated News Feed (${data.items.length} stories)]**`;
    }

    // Add model response to history
    conversationHistory.push({ role: "model", content: aiReply });
    renderConversation();

  } catch (err) {
    console.error("Search error:", err);
    loadingContainerEl.style.display = "none";
    conversationHistory.push({
      role: "model",
      content: `⚠️ Error connecting to server: ${err.message}`
    });
    renderConversation();
  }
}

// ── 9. Event Listeners ──────────────────────────────────────────────────────
searchFormEl.addEventListener("submit", (e) => {
  e.preventDefault();
  const query = searchInputEl.value.trim();
  if (query) {
    searchInputEl.value = "";
    executeSearch(query);
  }
});

btnRefreshEl.addEventListener("click", () => {
  refreshNews();
});

btnBackEl.addEventListener("click", () => {
  showFeedView();
});

logoTextEl.addEventListener("click", () => {
  showFeedView();
});

// Delegate click on "[📰 View Updated News Feed]" inside chat
responseBodyEl.addEventListener("click", (e) => {
  if (e.target && e.target.textContent && e.target.textContent.includes("View Updated News Feed")) {
    showFeedView();
  }
});

// ── Initial Boot ────────────────────────────────────────────────────────────
fetchNews();
