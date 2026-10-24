#!/usr/bin/env python3
"""Refresh Pilzradar's data: edible-mushroom finds from GBIF and the fruiting
weather from MET Norway. Rewrites the data block inside index.html and writes
data.json next to it. Run by .github/workflows/update.yml four times a day.

Only uses the Python standard library.
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "index.html"
DATA_JSON = ROOT / "data.json"
TZ = ZoneInfo("Europe/Zurich")
USER_AGENT = "Pilzradar/1.0 (+https://github.com/celestinetan/pilzradar)"
BLOCK = re.compile(r'(<script id="pilz-data" type="application/json">)(.*?)(</script>)', re.S)

# GBIF taxon keys of the edible species in the guide.
TAXON_KEYS = [
    5954958, 5954691, 7832732, 9623860, 2554662, 2554536, 8871787, 2513763,
    8914748, 5242048, 2550247, 7987658, 2551542, 5248629, 7925734, 5248788,
    2525027, 2526530, 9072021, 2520104, 2526021, 9173236, 5243458, 5243403,
]

CANTONS = {
    "zürich": "ZH", "zurich": "ZH", "bern": "BE", "berne": "BE", "lucerne": "LU", "luzern": "LU",
    "uri": "UR", "schwyz": "SZ", "obwalden": "OW", "nidwalden": "NW", "glarus": "GL",
    "zug": "ZG", "fribourg": "FR", "freiburg": "FR", "solothurn": "SO",
    "basel-stadt": "BS", "basel-landschaft": "BL", "schaffhausen": "SH",
    "appenzell ausserrhoden": "AR", "appenzell innerrhoden": "AI",
    "sankt gallen": "SG", "st. gallen": "SG", "st.gallen": "SG", "st gallen": "SG",
    "graubünden": "GR", "graubunden": "GR", "grisons": "GR", "aargau": "AG",
    "thurgau": "TG", "ticino": "TI", "vaud": "VD", "valais": "VS", "wallis": "VS",
    "neuchâtel": "NE", "neuchatel": "NE", "genève": "GE", "geneve": "GE", "geneva": "GE",
    "jura": "JU",
}


def get_json(url, tries=3):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.load(r)
        except Exception as e:  # network hiccups: retry, then give up on this source
            if i == tries - 1:
                print(f"  failed: {url} ({e})", file=sys.stderr)
                return None
            time.sleep(3 * (i + 1))


# ---------- weather ----------

def daily_from_metno(payload):
    """Aggregate a MET Norway locationforecast into local calendar days."""
    days = {}
    for e in payload["properties"]["timeseries"]:
        t = datetime.fromisoformat(e["time"].replace("Z", "+00:00")).astimezone(TZ)
        d = t.date().isoformat()
        day = days.setdefault(d, {"rain": 0.0, "temps": []})
        temp = e["data"]["instant"]["details"].get("air_temperature")
        if temp is not None:
            day["temps"].append(temp)
        nxt1 = e["data"].get("next_1_hours")
        nxt6 = e["data"].get("next_6_hours")
        if nxt1:
            day["rain"] += nxt1["details"].get("precipitation_amount", 0.0)
        elif nxt6:
            # After the hourly part ends, steps are 6 hours apart, so this never double counts.
            day["rain"] += nxt6["details"].get("precipitation_amount", 0.0)
    out = []
    for d, v in sorted(days.items()):
        if len(v["temps"]) < 2:
            continue  # a partial day with one sample
        tmin, tmax = min(v["temps"]), max(v["temps"])
        if tmin == tmax:
            continue
        out.append({"date": d, "rain": round(v["rain"], 1), "tmin": round(tmin, 1), "tmax": round(tmax, 1)})
    return out


def merge_weather(stored, fresh, today):
    by_date = {d["date"]: d for d in stored}
    for d in fresh:
        if d["date"] < today:
            continue
        if not (0 <= d["rain"] <= 120 and d["tmin"] <= d["tmax"] and -30 <= d["tmin"] and d["tmax"] <= 38):
            continue
        old = by_date.get(d["date"])
        if d["date"] == today and old:
            by_date[d["date"]] = {"date": d["date"], "rain": max(old["rain"], d["rain"]),
                                   "tmin": min(old["tmin"], d["tmin"]), "tmax": max(old["tmax"], d["tmax"])}
        else:
            by_date[d["date"]] = d
    cutoff = (date.fromisoformat(today) - timedelta(days=14)).isoformat()
    return [by_date[k] for k in sorted(by_date) if k >= cutoff]


def update_weather(data, today):
    fresh_regions = []
    for reg in data["regions"]:
        url = ("https://api.met.no/weatherapi/locationforecast/2.0/compact?"
               f"lat={reg['lat']:.3f}&lon={reg['lng']:.3f}")
        payload = get_json(url)
        if not payload:
            continue
        days = daily_from_metno(payload)
        data["weather"][reg["id"]] = merge_weather(data["weather"].get(reg["id"], []), days, today)
        fresh_regions.append(reg["id"])
        time.sleep(1)  # be polite to MET Norway
    return fresh_regions


# ---------- finds ----------

def short_name(rec):
    """Scientific name without author, e.g. 'Boletus edulis Bull.' -> 'Boletus edulis'."""
    name = rec.get("scientificName") or rec.get("species") or ""
    parts = name.split()
    if len(parts) >= 2 and parts[1][:1].islower() and not parts[1].startswith("("):
        return f"{parts[0]} {parts[1]}"
    return parts[0] if parts else ""


def canton_code(rec, cantons):
    names = [((rec.get("gadm") or {}).get("level1") or {}).get("name"), rec.get("stateProvince")]
    for n in names:
        if n and n.strip().lower() in CANTONS:
            return CANTONS[n.strip().lower()]
    lat, lng = rec["decimalLatitude"], rec["decimalLongitude"]
    return min(cantons, key=lambda c: (c["lat"] - lat) ** 2 + (c["lng"] - lng) ** 2)["c"]


def place(rec):
    gadm = rec.get("gadm") or {}
    p = (gadm.get("level3") or {}).get("name") or rec.get("locality") or (gadm.get("level2") or {}).get("name") or "Switzerland"
    return re.sub(r"\s*\(.*?\)\s*", " ", p).strip()[:60] or "Switzerland"


def update_finds(data, start, today):
    found, failed = {}, 0
    for key in TAXON_KEYS:
        offset = 0
        while True:
            q = urllib.parse.urlencode({"country": "CH", "eventDate": f"{start},{today}", "taxonKey": key,
                                        "hasCoordinate": "true", "hasGeospatialIssue": "false",
                                        "limit": 300, "offset": offset})
            page = get_json(f"https://api.gbif.org/v1/occurrence/search?{q}")
            if page is None:
                failed += 1
                break
            for rec in page.get("results", []):
                if rec.get("decimalLatitude") is None or rec.get("decimalLongitude") is None:
                    continue
                name = short_name(rec)
                if not name or not rec.get("eventDate"):
                    continue
                found[rec["key"]] = {
                    "k": rec["key"], "d": rec["eventDate"][:10], "n": name,
                    "lat": round(rec["decimalLatitude"], 6), "lng": round(rec["decimalLongitude"], 6),
                    "p": place(rec), "c": canton_code(rec, data["cantons"]),
                }
            if page.get("endOfRecords", True) or offset >= 1200:
                break
            offset += 300
    if failed == len(TAXON_KEYS):
        return None
    merged = {s["k"]: s for s in data["sightings"]}
    merged.update(found)
    return sorted((s for s in merged.values() if start <= s["d"] <= today), key=lambda s: (s["d"], s["k"]))


def main():
    html = PAGE.read_text(encoding="utf-8")
    m = BLOCK.search(html)
    if not m:
        sys.exit("No pilz-data block found in index.html")
    data = json.loads(m.group(2))

    now = datetime.now(TZ)
    today = now.date().isoformat()
    start = (now.date() - timedelta(days=30)).isoformat()

    print("Weather…")
    fresh = update_weather(data, today)
    print("Finds…")
    sightings = update_finds(data, start, today)

    if not fresh and sightings is None:
        sys.exit("All sources failed; nothing written.")
    if sightings is not None:
        data["sightings"] = sightings
    data["sightingsWindow"] = [start, today]
    if data["sightings"]:
        data["latestRecord"] = max(s["d"] for s in data["sightings"])
    data["updated"] = now.replace(microsecond=0, second=0).isoformat()

    text = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    PAGE.write_text(html[:m.start(2)] + text + html[m.end(2):], encoding="utf-8")
    DATA_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(data['sightings'])} finds, newest {data.get('latestRecord')}, fresh weather: {', '.join(fresh) or 'none'}")


if __name__ == "__main__":
    main()
