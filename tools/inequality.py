"""
Rich and poor, per country, from the World Bank (most recent year with data).
Writes inequality.json, keyed by country name (World Bank and GeoNames spellings).
Run monthly by .github/workflows/update-data.yml; the figures themselves change about once a year.
"""
import json, urllib.request
from pathlib import Path

INDICATORS = {
    "top10": "SI.DST.10TH.10",   # income share held by the highest 10%
    "bottom10": "SI.DST.FRST.10",  # income share held by the lowest 10%
    "bottom50": None,
    "gini": "SI.POV.GINI",       # Gini index, 0-100
    "poverty": "SI.POV.DDAY",    # % of people below the international extreme-poverty line
}
OUT = Path(__file__).resolve().parent.parent / "inequality.json"


def get(code):
    url = f"https://api.worldbank.org/v2/country/all/indicator/{code}?format=json&mrnev=1&per_page=500"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (The Wire; personal art project)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        meta, rows = json.load(r)
    return rows or []


def main():
    data, labels = {}, {}
    for key, code in INDICATORS.items():
        if not code:
            continue
        for row in get(code):
            iso3, val = row.get("countryiso3code"), row.get("value")
            if not iso3 or val is None:
                continue
            labels[key] = row["indicator"]["value"]
            d = data.setdefault(iso3, {"name": row["country"]["value"]})
            d[key] = round(float(val), 1)
            d[key + "_year"] = row.get("date")
    # also key by GeoNames spellings, which the map uses
    names = {}
    try:
        import geonamescache
        for c in geonamescache.GeonamesCache().get_countries().values():
            if c.get("iso3") in data:
                names[c["name"]] = c["iso3"]
    except Exception:
        pass
    items = {}
    for iso3, d in data.items():
        items[d["name"]] = d
        d["iso3"] = iso3
    for n, iso3 in names.items():
        items.setdefault(n, data[iso3])
    OUT.write_text(json.dumps({"source": "World Bank, World Development Indicators", "labels": labels, "items": items},
                              ensure_ascii=False, separators=(",", ":")))
    print(f"{len(data)} countries with at least one figure")


if __name__ == "__main__":
    main()
