"""Web search / fetch / Wikipedia / news."""

import re
import urllib.parse

from . import tool
from ._http import http_get, http_json


@tool(
    description="Search the web and return the top results with titles, URLs, and snippets.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 10},
        },
        "required": ["query"],
    },
)
def web_search(query: str, max_results: int = 5) -> str:
    # attempt 1: DuckDuckGo HTML
    try:
        url = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
        html = http_get(url)
        results = []
        pattern = re.compile(
            r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?'
            r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
            re.DOTALL,
        )
        for m in pattern.finditer(html):
            link, title, snip = m.group(1), m.group(2), m.group(3)
            title = re.sub(r"<.*?>", "", title).strip()
            snip = re.sub(r"<.*?>", "", snip).strip()
            qs = urllib.parse.urlparse(link).query
            real = urllib.parse.parse_qs(qs).get("uddg", [link])[0]
            results.append(f"- {title}\n  {real}\n  {snip}")
            if len(results) >= max_results:
                break
        if results:
            return "\n".join(results)
    except Exception:
        pass

    # attempt 2: DDG Lite
    try:
        url = "https://lite.duckduckgo.com/lite/?" + urllib.parse.urlencode({"q": query})
        html = http_get(url)
        results = []
        for m in re.finditer(r'<a[^>]+rel="nofollow"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
                              html, re.DOTALL):
            link = m.group(1)
            title = re.sub(r"<.*?>", "", m.group(2)).strip()
            if not title or link.startswith("/"):
                continue
            qs = urllib.parse.urlparse(link).query
            real = urllib.parse.parse_qs(qs).get("uddg", [link])[0]
            results.append(f"- {title}\n  {real}")
            if len(results) >= max_results:
                break
        if results:
            return "\n".join(results)
    except Exception:
        pass

    # attempt 3: DDG Instant-Answer JSON
    try:
        url = "https://api.duckduckgo.com/?" + urllib.parse.urlencode({
            "q": query, "format": "json", "no_html": 1, "no_redirect": 1,
        })
        data = http_json(url)
        out = []
        if data.get("AbstractText"):
            out.append(f"- {data.get('Heading','')}\n  {data.get('AbstractURL','')}\n"
                       f"  {data['AbstractText']}")
        for r in (data.get("RelatedTopics") or [])[:max_results]:
            if "Text" in r and "FirstURL" in r:
                out.append(f"- {r['Text']}\n  {r['FirstURL']}")
        if out:
            return "\n".join(out[:max_results])
    except Exception:
        pass

    return "No results (search providers blocked or rate-limited)."


@tool(
    description="Fetch the readable text content of a web page (first ~4000 chars).",
    parameters={
        "type": "object",
        "properties": {"url": {"type": "string"}},
        "required": ["url"],
    },
)
def fetch_url(url: str) -> str:
    html = http_get(url, timeout=15)
    html = re.sub(r"<script.*?</script>", "", html, flags=re.S | re.I)
    html = re.sub(r"<style.*?</style>", "", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:4000]


@tool(
    description="Look up a short summary of a topic from Wikipedia.",
    parameters={
        "type": "object",
        "properties": {"topic": {"type": "string"}},
        "required": ["topic"],
    },
)
def wikipedia(topic: str) -> str:
    url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + \
          urllib.parse.quote(topic.replace(" ", "_"))
    try:
        data = http_json(url)
        return f"{data.get('title')}: {data.get('extract','(no summary)')}"
    except Exception as e:
        return f"Wikipedia error: {e}"


@tool(
    description="Get top news headlines (BBC RSS, no key).",
    parameters={
        "type": "object",
        "properties": {"max_items": {"type": "integer", "default": 5, "maximum": 15}},
    },
)
def news(max_items: int = 5) -> str:
    xml = http_get("https://feeds.bbci.co.uk/news/rss.xml")
    titles = re.findall(r"<title><!\[CDATA\[(.*?)\]\]></title>", xml) \
          or re.findall(r"<title>(.*?)</title>", xml)
    titles = [t for t in titles if t.lower() not in ("bbc news", "")][:max_items]
    return "\n".join(f"- {t}" for t in titles) or "No headlines."
