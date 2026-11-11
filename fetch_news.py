#!/usr/bin/env python3
"""
AI News Wire — gathers AI headlines from international news feeds
and appends them to news.json (a growing archive). It also builds needs.json:
AI stories about food, health, water & shelter and education in places
facing hunger and food insecurity, tagged by need, place and stage.

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


# ---------------------------------------------------------------- BASIC NEEDS
# A second archive, needs.json: AI stories about meeting basic needs (food, health,
# water & shelter, education) in places facing hunger and food insecurity.
NEEDS_FILE = Path(__file__).parent / "needs.json"
NEEDS_MAX = 800

def gnews(q):
    from urllib.parse import quote_plus
    return "https://news.google.com/rss/search?q=" + quote_plus(q) + "&hl=en&gl=US&ceid=US:en"

AI_Q = '("artificial intelligence" OR AI OR "machine learning")'
# Specialist sources: development, humanitarian and science newsrooms.
SPECIALIST_SITES = ["reliefweb.int", "thenewhumanitarian.org", "scidev.net", "restofworld.org", "devex.com",
                    "cgiar.org", "gatesfoundation.org", "wfp.org", "fao.org", "unicef.org", "who.int", "ifpri.org"]
NEEDS_FEEDS = [
    # Most specialist sites block or break their own RSS, so they are reached through
    # Google News searches restricted to those sites. The New Humanitarian's feed works directly.
    ("The New Humanitarian",   "International", "https://www.thenewhumanitarian.org/rss/all.xml", False),
    ("Specialist sites (1)",   "International", gnews(AI_Q + " (" + " OR ".join("site:" + d for d in SPECIALIST_SITES[:6]) + ")"), False),
    ("Specialist sites (2)",   "International", gnews(AI_Q + " (" + " OR ".join("site:" + d for d in SPECIALIST_SITES[6:]) + ")"), False),
    ("Google News: famine",    "International", gnews(AI_Q + ' (famine OR "food insecurity" OR hunger OR malnutrition)'), False),
    ("Google News: farmers",   "International", gnews(AI_Q + ' (farmers OR smallholder OR crops OR agriculture) (Africa OR India OR Kenya OR Nigeria OR Ethiopia OR Malawi OR Bangladesh OR Pakistan OR Uganda OR Tanzania)'), False),
    ("Google News: health",    "International", gnews(AI_Q + ' (malnutrition OR clinic OR diagnosis OR "health workers" OR cholera OR malaria OR tuberculosis OR maternal) (Africa OR India OR Sudan OR Yemen OR Haiti OR Gaza OR refugee OR humanitarian)'), False),
    ("Google News: water",     "International", gnews(AI_Q + ' (water OR drought OR flood OR shelter OR sanitation OR "early warning") (Africa OR India OR Pakistan OR Bangladesh OR Somalia OR Sahel OR humanitarian)'), False),
    ("Google News: education", "International", gnews(AI_Q + ' (school OR literacy OR teachers OR classroom) (Africa OR India OR refugee OR "low-income" OR Afghanistan OR Sudan OR Yemen)'), False),
    ("Google News: Gates",     "International", gnews(AI_Q + ' "Gates Foundation" (agriculture OR health OR farmers OR nutrition OR education)'), False),
]

# Specific basic-needs terms only (generic words like "health", "education" or
# "learning" let in startup and gadget news, and "learning" matches "machine learning").
NEEDS = {
    "food":   r"\b(famine|hunger|hungry|food (in)?security|malnutrition|malnourish\w*|farmers?|farming|agricultur\w*|crops?|harvests?|yields?|livestock|pests?|locusts?|seeds?|irrigation|smallholder\w*|soil health|food prices?)\b",
    "health": r"\b(malaria|cholera|tuberculosis|TB|HIV|maternal|newborns?|child mortality|malnutrition|vaccin\w*|outbreaks?|epidemics?|community health|health workers?|frontline workers?|primary (health )?care|clinics?|rural hospitals?|screening|diagnos\w*)\b",
    "water":  r"\b(drinking water|clean water|water (access|supply|scarcity|shortages?)|groundwater|drought\w*|floods?|flooding|sanitation|shelters?|housing|displac\w*|refugee camps?|early warning|cyclones?|heatwaves?|monsoon)\b",
    "education": r"\b(literacy|schools?|schooling|school ?children|out-of-school|classrooms?|teachers?|pupils?|tutoring|students? in (rural|refugee))\b",
}
NEEDS_RE = {k: re.compile(v, re.I) for k, v in NEEDS.items()}
HUMANITARIAN = re.compile(r"\b(famine|hunger|food insecurity|humanitarian|refugees?|aid agenc\w*|crisis|smallholder\w*|low-income|global south|developing countries|poverty|poor|rural|villages?|NGOs?|WFP|UNICEF|FAO|WHO|USAID|Gates Foundation|public health)\b")

# Places facing hunger / food insecurity, with a map point (lon, lat).
COUNTRIES = {
    "Sudan": (30.2, 15.6), "South Sudan": (30.3, 7.3), "Gaza": (34.4, 31.4), "Palestine": (35.2, 31.9),
    "Haiti": (-72.3, 18.9), "Mali": (-2.0, 17.6), "Yemen": (48.5, 15.6), "Somalia": (46.2, 5.2),
    "Ethiopia": (39.6, 8.6), "Afghanistan": (66.0, 33.9), "Congo": (23.6, -2.9), "DRC": (23.6, -2.9),
    "Nigeria": (8.7, 9.1), "Burkina Faso": (-1.6, 12.2), "Chad": (18.7, 15.4), "Niger": (8.1, 17.6),
    "Syria": (38.5, 35.0), "Myanmar": (96.0, 21.0), "Bangladesh": (90.4, 23.7), "Pakistan": (69.3, 30.4),
    "India": (78.9, 21.0), "Kenya": (37.9, 0.0), "Malawi": (34.3, -13.3), "Mozambique": (35.5, -18.7),
    "Zimbabwe": (29.2, -19.0), "Zambia": (27.8, -13.1), "Madagascar": (46.9, -18.8), "Uganda": (32.3, 1.4),
    "Tanzania": (34.9, -6.4), "Rwanda": (29.9, -1.9), "Burundi": (29.9, -3.4), "Central African Republic": (20.9, 6.6),
    "Cameroon": (12.4, 7.4), "Lebanon": (35.9, 33.9), "Eritrea": (39.8, 15.2), "Ghana": (-1.0, 7.9),
    "Senegal": (-14.5, 14.5), "Mauritania": (-10.9, 21.0), "Sierra Leone": (-11.8, 8.5), "Liberia": (-9.4, 6.4),
    "Guatemala": (-90.2, 15.8), "Honduras": (-86.2, 15.2), "Nepal": (84.1, 28.4), "Lesotho": (28.2, -29.6),
    "Angola": (17.9, -11.2), "Rwanda ": (29.9, -1.9), "Bihar": (85.3, 25.1), "Odisha": (85.1, 20.9),
    "Maharashtra": (75.7, 19.7), "Telangana": (79.0, 18.1), "Andhra Pradesh": (79.7, 15.9), "Punjab": (75.3, 31.1),
    "Tigray": (39.0, 14.0), "Darfur": (24.9, 13.5), "Sahel": (2.0, 15.0), "Rohingya": (92.2, 21.2),
}
REGION_OF = {"Gaza": "Palestine", "DRC": "Congo", "Rwanda ": "Rwanda", "Bihar": "India", "Odisha": "India",
             "Maharashtra": "India", "Telangana": "India", "Andhra Pradesh": "India", "Punjab": "India",
             "Tigray": "Ethiopia", "Darfur": "Sudan", "Rohingya": "Bangladesh"}
COUNTRY_RE = [(re.compile(r"\b" + re.escape(k.strip()) + r"(?:n|ns|ese|ian|ians|i|is)?\b"), k) for k in sorted(COUNTRIES, key=len, reverse=True)]

STAGE_PILOT = re.compile(r"\b(pilot\w*|trials?|trialled|tests?|testing|launch\w*|rolls? out|rolling out|deploy\w*)\b", re.I)
STAGE_PROPOSED = re.compile(r"\b(could|may|might|would|plans?|planned|proposal|proposes?|aims? to|seeks? to|promise\w*|potential|future|vision|call\w* for|should)\b", re.I)
CRITICAL = re.compile(r"\b(fail\w*|harm\w*|risks?|bias\w*|warn\w*|concerns?|criticis\w*|surveillance|hype|exclusion|privacy|backlash|doubts?|threats?|dangers?|terrible|worse|blow|attacks?|hacks?|misinformation)\b", re.I)


def classify(item, summary=""):
    """Tag a story with needs, places and stage. Returns None if it is not a basic-needs story."""
    summary = (summary or "").replace(item.get("source", ""), " ")
    text = f"{item['title']} {summary}"
    if not is_ai(text):
        return None
    needs = [k for k, r in NEEDS_RE.items() if r.search(text)]
    if not needs:
        return None
    places = []
    scan = text
    for r, k in COUNTRY_RE:           # longest names first; blank each match so
        if r.search(scan):            # "South Sudan" is not also counted as "Sudan"
            scan = r.sub(" ", scan)
            name = REGION_OF.get(k, k.strip())
            if name not in [p["name"] for p in places]:
                lon, lat = COUNTRIES[k]
                places.append({"name": name, "lon": lon, "lat": lat})
    # Needs a humanitarian or development signal, or a place plus a need named in the headline itself.
    title_need = any(r.search(item["title"]) for r in NEEDS_RE.values())
    if not HUMANITARIAN.search(text) and not (places and title_need):
        return None
    if CRITICAL.search(text):
        stage = "critique"
    elif STAGE_PROPOSED.search(text):
        stage = "proposed"
    elif STAGE_PILOT.search(text):
        stage = "pilot"
    else:
        stage = "reported"
    out = dict(item)
    out.update({"needs": needs, "places": places[:3], "stage": stage})
    return out


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
            "_summary": summary[:600],
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


def merge(existing, new, limit=MAX_ITEMS):
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
    return merged[:limit]


SOURCE_LOG = []

def gather(feeds, label):
    gathered, ok = [], 0
    for name, region, url, ai_only in feeds:
        try:
            got = parse_feed(fetch(url), name, region, ai_only)
            gathered += got
            ok += 1
            print(f"  ✓ {name:28} {len(got):3} AI stories")
            SOURCE_LOG.append({"name": name, "set": label, "ok": True, "ai_stories": len(got)})
        except Exception as e:
            SOURCE_LOG.append({"name": name, "set": label, "ok": False, "error": e.__class__.__name__ + ": " + str(e)[:120]})
            print(f"  ✗ {name:28} skipped ({e.__class__.__name__})", file=sys.stderr)
    print(f"{label}: {ok}/{len(feeds)} sources reached")
    return gathered, ok


def load(path):
    try:
        return json.loads(path.read_text())["items"]
    except Exception:
        return []


def save(path, items, ok):
    path.write_text(json.dumps({
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources_reached": ok,
        "sources": SOURCE_LOG,
        "items": items,
    }, ensure_ascii=False, indent=1))


def main():
    print("General AI wire")
    general, ok_g = gather(FEEDS, "General")
    print("Basic needs")
    special, ok_n = gather(NEEDS_FEEDS, "Basic needs")

    if ok_g == 0 and ok_n == 0:
        print("No feeds reachable — leaving archives unchanged.", file=sys.stderr)
        sys.exit(1)

    # Basic-needs archive: anything from either set of sources that classifies,
    # plus a re-check of the existing archives so new rules apply to old stories.
    candidates = special + general + load(NEEDS_FILE) + load(OUT_FILE)
    needs = []
    for it in candidates:
        tagged = classify(it, it.get("_summary", ""))
        if tagged:
            needs.append(tagged)
    for it in needs:
        it.pop("_summary", None)
    needs = merge([], needs, NEEDS_MAX)
    save(NEEDS_FILE, needs, ok_n)
    print(f"needs.json now holds {len(needs)} stories.")

    for it in general:
        it.pop("_summary", None)
    if ok_g:
        items = merge(load(OUT_FILE), general)
        save(OUT_FILE, items, ok_g)
        print(f"news.json now holds {len(items)} headlines.")


if __name__ == "__main__":
    main()
