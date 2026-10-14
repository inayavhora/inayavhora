#!/usr/bin/env python3
"""
AI News Wire — gathers AI headlines from international news feeds
and appends them to news.json (a growing archive).

No dependencies beyond Python 3.9+. Run:  python fetch_news.py
"""

import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path

OUT_FILE = Path(__file__).parent / "news.json"
MAX_ITEMS = 400          # how many headlines the archive keeps
TIMEOUT = 20

# ai_only=True  -> the feed is already about AI, keep everything
# ai_only=False -> general/tech feed, keep only items that mention AI
FEEDS = [
    # name,                       region,          url,                                                                 ai_only
    ("The Guardian",              "UK",            "https://www.theguardian.com/technology/artificialintelligenceai/rss", True),
    ("BBC News",                  "UK",            "https://feeds.bbci.co.uk/news/technology/rss.xml",                    False),
    ("Al Jazeera",                "Qatar",         "https://www.aljazeera.com/xml/rss/all.xml",                           False),
    ("DW",                        "Germany",       "https://rss.dw.com/rdf/rss-en-all",                                   False),
    ("ABC News",                  "Australia",     "https://www.abc.net.au/news/feed/51120/rss.xml",                      False),
    ("South China Morning Post",  "Hong Kong",     "https://www.scmp.com/rss/36/feed",                                    False),
    ("The New York Times",        "US",            "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",        False),
    ("NPR",                       "US",            "https://feeds.npr.org/1019/rss.xml",                                  False),
    ("MIT Technology Review",     "US",            "https://www.technologyreview.com/feed/",                              False),
    ("TechCrunch",                "US",            "https://techcrunch.com/category/artificial-intelligence/feed/",      True),
    ("The Verge",                 "US",            "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",  True),
    ("Google News (world)",       "International", "https://news.google.com/rss/search?q=%22artificial+intelligence%22&hl=en&gl=US&ceid=US:en", True),
]

# Case-sensitive acronyms, case-insensitive phrases
AI_ACRONYMS = re.compile(r"\b(AI|A\.I\.|AGI|LLMs?|GPT-?\d*)\b")
AI_WORDS = re.compile(
    r"\b(artificial intelligence|machine learning|deep learning|neural net\w*|"
    r"chatbots?|chatgpt|openai|anthropic|deepmind|gemini|copilot|"
    r"large language models?|generative|deepfakes?|robot\w*|algorithm\w*)\b",
    re.IGNORECASE,
)


def is_ai(text: str) -> bool:
    return bool(AI_ACRONYMS.search(text) or AI_WORDS.search(text))


def local(tag: str) -> str:
    """Strip XML namespace: '{http://...}title' -> 'title'."""
    return tag.rsplit("}", 1)[-1]


def child_text(el, *names):
    for c in el:
        if local(c.tag) in names:
            if local(c.tag) == "link" and c.get("href"):   # Atom link
                return c.get("href")
            if c.text and c.text.strip():
                return c.text.strip()
    return ""


def clean(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", unescape(s or ""))
    return re.sub(r"\s+", " ", s).strip()


def parse_date(s: str):
    if not s:
        return None
    for parser in (parsedate_to_datetime,
                   lambda x: datetime.fromisoformat(x.replace("Z", "+00:00"))):
        try:
            d = parser(s.strip())
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            return d.astimezone(timezone.utc)
        except Exception:
            continue
    return None


def parse_feed(xml_bytes: bytes, name: str, region: str, ai_only: bool):
    root = ET.fromstring(xml_bytes)
    items = [el for el in root.iter() if local(el.tag) in ("item", "entry")]
    out = []
    for it in items:
        title = clean(child_text(it, "title"))
        link = child_text(it, "link", "guid").strip()
        summary = clean(child_text(it, "description", "summary", "content"))
        date = parse_date(child_text(it, "pubDate", "published", "updated", "date"))
        source = name
        # Google News: real outlet is in <source>, title ends " - Outlet"
        if "news.google.com" in link or name.startswith("Google News"):
            outlet = child_text(it, "source")
            if outlet:
                source = outlet
                title = re.sub(r"\s+-\s+" + re.escape(outlet) + r"$", "", title)
            region = "International"
        if not title or not link:
            continue
        if not ai_only and not is_ai(f"{title} {summary}"):
            continue
        out.append({
            "title": title,
            "url": link,
            "source": source,
            "region": region,
            "published": (date or datetime.now(timezone.utc)).isoformat(timespec="seconds"),
        })
    return out


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (AI News Wire; personal art project)",
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read()


def norm(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", title.lower())[:80]


def merge(existing, new):
    seen_urls, seen_titles, merged = set(), set(), []
    # new first so fresher metadata wins, then sort by date
    for item in new + existing:
        key_t = norm(item["title"])
        if item["url"] in seen_urls or key_t in seen_titles:
            continue
        seen_urls.add(item["url"])
        seen_titles.add(key_t)
        merged.append(item)
    merged.sort(key=lambda i: i["published"], reverse=True)
    return merged[:MAX_ITEMS]


def main():
    try:
        existing = json.loads(OUT_FILE.read_text())["items"]
    except Exception:
        existing = []

    gathered, ok = [], 0
    for name, region, url, ai_only in FEEDS:
        try:
            got = parse_feed(fetch(url), name, region, ai_only)
            gathered += got
            ok += 1
            print(f"  ✓ {name:28} {len(got):3} AI stories")
        except Exception as e:
            print(f"  ✗ {name:28} skipped ({e.__class__.__name__})", file=sys.stderr)

    if ok == 0:
        print("No feeds reachable — leaving news.json unchanged.", file=sys.stderr)
        sys.exit(1)

    items = merge(existing, gathered)
    OUT_FILE.write_text(json.dumps({
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources_reached": ok,
        "items": items,
    }, ensure_ascii=False, indent=1))
    print(f"Archive now holds {len(items)} headlines.")


if __name__ == "__main__":
    main()
