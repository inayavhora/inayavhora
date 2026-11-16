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
    "Angola": (17.9, -11.2), "Bihar": (85.3, 25.1), "Odisha": (85.1, 20.9),
    "Maharashtra": (75.7, 19.7), "Telangana": (79.0, 18.1), "Andhra Pradesh": (79.7, 15.9), "Punjab": (75.3, 31.1),
    "Tigray": (39.0, 14.0), "Darfur": (24.9, 13.5), "Sahel": (2.0, 15.0), "Rohingya": (92.2, 21.2),
}
REGION_OF = {"Gaza": "Palestine", "Bihar": "India", "Odisha": "India",
             "Maharashtra": "India", "Telangana": "India", "Andhra Pradesh": "India", "Punjab": "India",
             "Tigray": "Ethiopia", "Darfur": "Sudan", "Rohingya": "Bangladesh"}
COUNTRY_RE = [(re.compile(r"\b" + re.escape(k.strip()) + r"(?:n|ns|ese|ian|ians|i|is)?\b"), k) for k in sorted(COUNTRIES, key=len, reverse=True)]

# ---- Precise places: towns named in a story, looked up in GeoNames (towns of 5,000+ people).
ISO2 = {"Sudan": "SD", "South Sudan": "SS", "Palestine": "PS", "Haiti": "HT", "Mali": "ML", "Yemen": "YE",
        "Somalia": "SO", "Ethiopia": "ET", "Afghanistan": "AF", "Congo": "CD", "Nigeria": "NG", "Burkina Faso": "BF",
        "Chad": "TD", "Niger": "NE", "Syria": "SY", "Myanmar": "MM", "Bangladesh": "BD", "Pakistan": "PK", "India": "IN",
        "Kenya": "KE", "Malawi": "MW", "Mozambique": "MZ", "Zimbabwe": "ZW", "Zambia": "ZM", "Madagascar": "MG",
        "Uganda": "UG", "Tanzania": "TZ", "Rwanda": "RW", "Burundi": "BI", "Central African Republic": "CF",
        "Cameroon": "CM", "Lebanon": "LB", "Eritrea": "ER", "Ghana": "GH", "Senegal": "SN", "Mauritania": "MR",
        "Sierra Leone": "SL", "Liberia": "LR", "Guatemala": "GT", "Honduras": "HN", "Nepal": "NP", "Lesotho": "LS", "Angola": "AO"}
_TOWNS = None
NOT_TOWNS = {"Mango", "Asia", "Africa", "Data", "Google", "Gates", "Bill", "Union", "Delta", "Victoria", "Bay", "Aid",
             "Kisan", "Bharat", "Digital", "Smart", "Green", "Sun", "Rose", "Bali", "Agra"}  # words that are also town names

def towns():
    """name (accents removed) -> list of towns, only in the countries this wire follows."""
    global _TOWNS
    if _TOWNS is None:
        _TOWNS = {}
        try:
            import unicodedata
            import geonamescache
            plain = lambda t: unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
            keep = set(ISO2.values())
            for c in geonamescache.GeonamesCache(min_city_population=5000).get_cities().values():
                if c["countrycode"] not in keep:
                    continue
                names = {plain(c["name"])}   # official name only: alternate names misfire (Chittagong is also "Islamabad")
                for n in names:
                    if len(n) >= 4 and n not in NOT_TOWNS:
                        _TOWNS.setdefault(n, []).append(c)
        except Exception as e:
            print(f"  towns unavailable ({e.__class__.__name__}); places stay at region or country level", file=sys.stderr)
    return _TOWNS

CAPS = re.compile(r"\b[A-Z][a-z]+(?:[ -][A-Z][a-z]+){0,2}\b")

def find_towns(text, countries):
    """Towns named in the text. A town counts only if its country is also named, or it has 500,000+ people."""
    idx, codes, found = towns(), {ISO2[c] for c in countries if c in ISO2}, []
    if not idx:
        return found
    for m in CAPS.finditer(text):
        words = m.group(0).replace("-", " ").split()
        for n in range(len(words), 0, -1):            # longest name first: "Navi Mumbai" before "Mumbai"
            for i in range(0, len(words) - n + 1):
                cand = " ".join(words[i:i + n])
                if cand in COUNTRIES or cand + " " in COUNTRIES:   # a state or country, not a town
                    continue
                hits = [c for c in idx.get(cand, []) if c["countrycode"] in codes or c["population"] >= 500000]
                if hits:
                    c = max(hits, key=lambda c: c["population"])
                    country = next((k for k, v in ISO2.items() if v == c["countrycode"]), "")
                    place = {"name": f"{cand}, {country}", "lon": round(c["longitude"], 4), "lat": round(c["latitude"], 4), "precision": "town"}
                    if place["name"] not in [p["name"] for p in found]:
                        found.append(place)
    return found


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
    countries, regions = [], []
    scan = text
    for r, k in COUNTRY_RE:           # longest names first; blank each match so
        if r.search(scan):            # "South Sudan" is not also counted as "Sudan"
            scan = r.sub(" ", scan)
            lon, lat = COUNTRIES[k]
            if k.strip() == "DRC":
                k = "Congo"
            if k in REGION_OF:        # a state or region: keep its own point
                country = REGION_OF[k]
                regions.append({"name": f"{k.strip()}, {country}", "lon": lon, "lat": lat, "precision": "region"})
                if country not in countries:
                    countries.append(country)
            elif k.strip() not in countries:
                countries.append(k.strip())
    town_places = find_towns(text, countries)
    named = {p["name"].split(", ")[1] for p in town_places + regions}
    places = town_places + regions + [
        {"name": c, "lon": COUNTRIES[c][0], "lat": COUNTRIES[c][1], "precision": "country"}
        for c in countries if c not in named and c in COUNTRIES]
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


# ================================================================ DATA CENTRES
# Where new data centres are being built, and what they look like. Design and architecture press first
# (their feeds carry the article's lead photo), plus industry news for locations.
DC_FILE = Path(__file__).parent / "datacentres.json"
DC_MAX = 400
DC_RE = re.compile(r"\bdata[ -]?cent(er|re)s?\b|\bhyperscale\w*\b|\bserver farms?\b|\bAI (campus|factory|factories)\b|\bcompute campus\b", re.I)
SUBNATIONAL = {n: "IN" for n in ["Gujarat", "Maharashtra", "Tamil Nadu", "Telangana", "Karnataka", "Uttar Pradesh", "Andhra Pradesh",
                                  "Kerala", "Odisha", "Bihar", "Punjab", "Haryana", "Rajasthan", "West Bengal", "Madhya Pradesh", "Assam"]}
SUBNATIONAL.update({"Johor": "MY", "Selangor": "MY", "Bavaria": "DE", "Ontario": "CA", "Quebec": "CA", "Alberta": "CA",
                    "New South Wales": "AU", "Victoria": "AU", "Queensland": "AU", "Sao Paulo": "BR", "Queretaro": "MX", "Gauteng": "ZA"})
US_STATE_CENTRES = {   # approximate geographic centres, for stories that name only a state
    "AL": (-86.8, 32.8), "AZ": (-111.7, 34.3), "AR": (-92.4, 34.9), "CA": (-119.5, 37.2), "CO": (-105.5, 39.0), "CT": (-72.7, 41.6),
    "DE": (-75.5, 39.0), "FL": (-81.7, 28.6), "GA": (-83.4, 32.7), "ID": (-114.6, 44.4), "IL": (-89.2, 40.0), "IN": (-86.3, 39.9),
    "IA": (-93.5, 42.1), "KS": (-98.4, 38.5), "KY": (-85.3, 37.5), "LA": (-92.0, 31.1), "ME": (-69.2, 45.4), "MD": (-76.8, 39.0),
    "MA": (-71.8, 42.3), "MI": (-84.7, 43.7), "MN": (-94.3, 46.3), "MS": (-89.7, 32.7), "MO": (-92.5, 38.4), "MT": (-109.6, 47.0),
    "NE": (-99.8, 41.5), "NV": (-116.9, 39.3), "NH": (-71.6, 43.7), "NJ": (-74.7, 40.2), "NM": (-106.1, 34.4), "NY": (-75.5, 42.9),
    "NC": (-79.4, 35.6), "ND": (-100.5, 47.5), "OH": (-82.8, 40.3), "OK": (-97.5, 35.6), "OR": (-120.6, 43.9), "PA": (-77.8, 40.9),
    "RI": (-71.5, 41.7), "SC": (-80.9, 33.9), "SD": (-100.2, 44.4), "TN": (-86.3, 35.9), "TX": (-99.3, 31.5), "UT": (-111.7, 39.3),
    "VT": (-72.7, 44.1), "VA": (-78.8, 37.5), "WA": (-120.4, 47.4), "WV": (-80.6, 38.6), "WI": (-89.8, 44.6), "WY": (-107.5, 43.0),
}
DESIGN_SITES = ["dezeen.com", "designboom.com", "archdaily.com", "architecturaldigest.com", "wallpaper.com", "archpaper.com", "architectsjournal.co.uk", "dwell.com"]
DC_FEEDS = [
    ("Dezeen: data centres",  "Design", "https://www.dezeen.com/tag/data-centres/feed/"),
    ("Dezeen",                "Design", "https://www.dezeen.com/feed/"),
    ("designboom",            "Design", "https://www.designboom.com/feed/"),
    ("ArchDaily",             "Design", "https://www.archdaily.com/feed"),
    ("Architectural Digest",  "Design", "https://www.architecturaldigest.com/feed/rss"),
    ("Wallpaper*",            "Design", "https://www.wallpaper.com/feeds/all"),
    ("Google News: design press", "Design", gnews('("data center" OR "data centre") (' + " OR ".join("site:" + d for d in DESIGN_SITES) + ")")),
    ("Google News: architecture", "Design", gnews('("data center" OR "data centre") (architecture OR architects OR design) (new OR unveiled OR completed OR planned)')),
    ("DatacenterDynamics",    "Industry", "https://www.datacenterdynamics.com/en/rss/"),
    # beyond the US and Europe, so the map shows where compute is (and is not) being built
    ("Google News: India",    "Industry", gnews('("data center" OR "data centre") (India OR Mumbai OR Chennai OR Hyderabad OR Navi Mumbai OR Noida OR Pune) when:14d')),
    ("Google News: Africa",   "Industry", gnews('("data center" OR "data centre") (Africa OR Nigeria OR Kenya OR Lagos OR Nairobi OR "South Africa" OR Johannesburg OR Egypt OR Morocco OR Ethiopia) when:30d')),
    ("Google News: Asia",     "Industry", gnews('("data center" OR "data centre") (Malaysia OR Johor OR Indonesia OR Jakarta OR Thailand OR Vietnam OR Philippines OR Bangladesh OR Pakistan) when:14d')),
    ("Google News: Gulf",     "Industry", gnews('("data center" OR "data centre") ("Saudi Arabia" OR UAE OR "Abu Dhabi" OR Dubai OR Qatar OR Oman) when:14d')),
    ("Google News: Latin America", "Industry", gnews('("data center" OR "data centre") (Brazil OR "Sao Paulo" OR Mexico OR Queretaro OR Chile OR Santiago OR Colombia) when:14d')),
    ("Google News: new builds", "Industry", gnews('("data center" OR "data centre") (construction OR "breaks ground" OR approved OR campus) when:7d')),
]
IMG_RE = re.compile(r"<img[^>]+src=[\"']([^\"']+)", re.I)

def item_image(it):
    """The lead photo a feed attaches to an item: media:content / media:thumbnail / enclosure / first <img>."""
    for el in it.iter():
        t = local(el.tag)
        if t in ("content", "thumbnail") and el.get("url") and (el.get("medium") == "image" or re.search(r"\.(jpe?g|png|webp)(\?|$)", el.get("url"), re.I) or t == "thumbnail"):
            return el.get("url")
        if t == "enclosure" and el.get("url") and (el.get("type") or "").startswith("image"):
            return el.get("url")
    for el in it.iter():
        if el.text and "<img" in el.text:
            m = IMG_RE.search(el.text)
            if m:
                return m.group(1)
    return ""

_WORLD = None
def world_index():
    """Towns of 15,000+ people worldwide, country names and US states, for placing data centres."""
    global _WORLD
    if _WORLD is None:
        _WORLD = ({}, {}, {})
        try:
            import unicodedata, geonamescache
            gc = geonamescache.GeonamesCache(min_city_population=15000)
            plain = lambda t: unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
            for c in gc.get_cities().values():
                n = plain(c["name"])
                if len(n) >= 4:
                    _WORLD[0].setdefault(n, []).append(c)
            for code, c in gc.get_countries().items():
                _WORLD[1][c["name"]] = code
            for code, st in gc.get_us_states().items():
                _WORLD[2][st["name"]] = code
        except Exception as e:
            print(f"  world towns unavailable ({e.__class__.__name__})", file=sys.stderr)
    return _WORLD

COMMON = {"Mobile", "Reading", "Independence", "Commerce", "Energy", "Power", "Ocean", "Data", "Center", "Centre", "Cloud",
          "Google", "Meta", "Amazon", "Oracle", "Microsoft", "Apple", "Nvidia", "Stargate", "Phoenix Data", "Victoria", "Florence",
          "Paris Agreement", "Columbia", "Marion", "Lincoln", "Jackson", "Franklin", "Clinton", "Washington Post", "Sherman"}

def place_worldwide(text):
    towns, countries, states = world_index()
    if not towns:
        return []
    named_cc = {code for name, code in countries.items() if re.search(r"\b" + re.escape(name) + r"\b", text)}
    named_cc |= {code for name, code in SUBNATIONAL.items() if re.search(r"\b" + re.escape(name) + r"\b", text)}
    named_st = {code for name, code in states.items() if re.search(r"\b" + re.escape(name) + r"\b(?! City)", text)}   # "Kansas City" is not Kansas
    if named_st:
        named_cc.add("US")
    found = []
    for m in CAPS.finditer(text):
        words = m.group(0).replace("-", " ").split()
        for n in range(len(words), 0, -1):
            for i in range(0, len(words) - n + 1):
                cand = " ".join(words[i:i + n])
                if cand in COMMON or cand in countries or cand in states:
                    continue
                hits = [c for c in towns.get(cand, [])
                        if (c["countrycode"] == "US" and c["admin1code"] in named_st)
                        or (c["countrycode"] != "US" and c["countrycode"] in named_cc)
                        or c["population"] >= 1000000]
                if hits:
                    c = max(hits, key=lambda c: c["population"])
                    where = c["admin1code"] if c["countrycode"] == "US" else next((k for k, v in countries.items() if v == c["countrycode"]), c["countrycode"])
                    place = {"name": f"{cand}, {where}", "lon": round(c["longitude"], 4), "lat": round(c["latitude"], 4), "precision": "town"}
                    if place["name"] not in [p["name"] for p in found] and not any(cand in p["name"].split(",")[0] for p in found):
                        found.append(place)
    if not found:
        for name, code in states.items():
            if code in US_STATE_CENTRES and re.search(r"\b" + re.escape(name) + r"\b(?! City)", text):
                lon, lat = US_STATE_CENTRES[code]
                found.append({"name": f"{name}, US", "lon": lon, "lat": lat, "precision": "region"})
                break
    return found[:2]

OG_RE = re.compile(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)|<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image', re.I)

def og_image(url):
    """The article's own lead photo (og:image), read from the publisher's page."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (The Wire; personal art project)"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            html = r.read(400000).decode("utf-8", "ignore")
        m = OG_RE.search(html)
        return (m.group(1) or m.group(2)) if m else ""
    except Exception:
        return ""

def gather_datacentres():
    got, ok = [], 0
    for name, kind, url in DC_FEEDS:
        try:
            root = ET.fromstring(fetch(url))
            n = 0
            for it in [el for el in root.iter() if local(el.tag) in ("item", "entry")]:
                title = clean(child_text(it, "title"))
                link = child_text(it, "link", "guid").strip()
                if not link:
                    for el in it:
                        if local(el.tag) == "link" and el.get("href"):
                            link = el.get("href"); break
                summary = clean(child_text(it, "description", "summary", "content"))
                if not title or not link or not DC_RE.search(f"{title} {summary}"):
                    continue
                source = name
                if name.startswith("Google News"):
                    outlet = child_text(it, "source")
                    if outlet:
                        source = outlet
                        title = re.sub(r"\s+-\s+" + re.escape(outlet) + r"$", "", title)
                design = kind == "Design" or any(d.split(".")[0] in source.lower().replace(" ", "") for d in DESIGN_SITES)
                date = parse_date(child_text(it, "pubDate", "published", "updated", "date"))
                got.append({
                    "title": title, "url": link, "source": source, "kind": "design" if design else "industry",
                    "image": item_image(it),
                    "published": (date or datetime.now(timezone.utc)).isoformat(timespec="seconds"),
                    "places": place_worldwide(title),
                })
                n += 1
            ok += 1
            print(f"  ✓ {name:28} {n:3} data-centre stories")
            SOURCE_LOG.append({"name": name, "set": "Data centres", "ok": True, "stories": n})
        except Exception as e:
            print(f"  ✗ {name:28} skipped ({e.__class__.__name__})", file=sys.stderr)
            SOURCE_LOG.append({"name": name, "set": "Data centres", "ok": False, "error": e.__class__.__name__ + ": " + str(e)[:120]})
    return got, ok


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

FEATURED_FILE = Path(__file__).parent / "featured.json"

def apply_featured(items):
    """Stories drawn in the weekly batch: attach the drawing, and the exact place when one is known."""
    try:
        feats = {f["url"]: f for f in json.loads(FEATURED_FILE.read_text())["items"]}
    except Exception:
        return
    for it in items:
        f = feats.get(it["url"])
        if not f:
            continue
        it["drawing"] = f.get("drawing")
        it["drawing_note"] = f.get("note", "")
        if f.get("place"):
            it["places"] = [f["place"]] + [p for p in it.get("places", []) if p["name"] != f["place"]["name"]][:2]


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

    print("Data centres")
    dcs, ok_d = gather_datacentres()

    if ok_g == 0 and ok_n == 0 and ok_d == 0:
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
    apply_featured(needs)
    save(NEEDS_FILE, needs, ok_n)
    print(f"needs.json now holds {len(needs)} stories.")

    if ok_d:
        old = load(DC_FILE)
        for it in old:   # re-place older stories with the current rules (headline only)
            it["places"] = place_worldwide(it["title"])
        # lead photos for design-press stories that arrived without one (direct links only, a few per run)
        tries = 0
        for it in dcs + old:
            if tries >= 12:
                break
            if not it.get("image") and it.get("kind") == "design" and "news.google.com" not in it["url"]:
                it["image"] = og_image(it["url"]); tries += 1
        dc_items = merge(old, dcs, DC_MAX)
        save(DC_FILE, dc_items, ok_d)
        print(f"datacentres.json now holds {len(dc_items)} stories.")

    for it in general:
        it.pop("_summary", None)
    if ok_g:
        items = merge(load(OUT_FILE), general)
        save(OUT_FILE, items, ok_g)
        print(f"news.json now holds {len(items)} headlines.")


if __name__ == "__main__":
    main()
