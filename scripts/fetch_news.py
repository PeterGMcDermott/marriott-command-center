#!/usr/bin/env python3
"""Fetch Google News RSS headlines for the Marriott Command Center.

Writes data/news.json: the freshest Marriott headlines for the news scene
plus 3 per brand for the spotlight scene. The page fetches this file on
every load (same origin, so no CORS proxy is needed) and falls back to its
baked headlines if the file is missing or a list is empty.

Run by .github/workflows/refresh-news.yml every 6 hours, or by hand from
the repo root:  python3 scripts/fetch_news.py

Stdlib only: no pip dependencies.
"""
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

# key -> (Google News query, items wanted). The "marriott" feed is fetched
# with 7 items: the first 4 go to the news scene, the next 3 to MAR's
# spotlight, so the two scenes don't show the same headlines.
FEEDS = {
    "marriott": ('"Marriott International"', 7),
    "HLT": ('"Hilton Hotels"', 3),
    "IHG": ('"InterContinental Hotels Group"', 3),
    "H": ('"Hyatt Hotels"', 3),
    "WH": ('"Wyndham Hotels"', 3),
    "CHH": ('"Choice Hotels"', 3),
}

# Pure daily stock-move chatter, routine filings and boilerplate are noise on
# an ambient display; skip them when better headlines exist (spillover tops
# the list back up if needed). The layoffs filter is deliberate: Peter has a
# hard rule against layoff talk on anything work-visible.
NOISY = [
    re.compile(r"\bstock\b.{0,40}\b(underperform|outperform|rise|fall|drop|gain|climb|slip|tumble|soar)", re.I),
    re.compile(r"\bshares\b.{0,40}\b(rise|fall|drop|gain|climb|slip|tumble|soar)", re.I),
    re.compile(r"\bstock (price|moves?|today|forecasts?)", re.I),
    re.compile(r"what'?s (going on|happening) with .* (shares|stock)", re.I),
    re.compile(r"^Form 4\b", re.I),
    re.compile(r"transaction in own shares", re.I),
    re.compile(r"(purchased )?shares for cancellation", re.I),
    re.compile(r"has been appointed as", re.I),
    re.compile(r"declares?.{0,20}dividend", re.I),
    re.compile(r"quarterly dividend", re.I),
    re.compile(r"lay ?offs?\b", re.I),
]


def ct_label():
    """Human label for 'now' in America/Chicago, e.g. 'Fri Nov 13, 1:30pm CT'."""
    try:
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo("America/Chicago"))
    except Exception:
        now = datetime.now(timezone.utc)
    s = now.strftime("%a %b %d, %I:%M%p CT").replace(" 0", " ")
    return s.replace("AM", "am").replace("PM", "pm")


def fetch_feed(query, limit):
    url = ("https://news.google.com/rss/search?q="
           + urllib.parse.quote(query) + "&hl=en-US&gl=US&ceid=US:en")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        root = ET.fromstring(resp.read())
    items, spill, seen = [], [], set()
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        source = (it.findtext("source") or "").strip()
        if title and source and title.endswith(" - " + source):
            title = title[:-(len(source) + 3)].strip()
        # Google truncates long titles with ".." mid-word; end cleanly.
        if title.endswith(".."):
            title = title[:-2].rsplit(" ", 1)[0] + "\u2026"
        key = title.lower()
        if not title or key in seen:
            continue
        seen.add(key)
        pub = it.findtext("pubDate") or ""
        try:
            date_s = parsedate_to_datetime(pub).strftime("%b %d, %Y").replace(" 0", " ")
        except Exception:
            date_s = ""
        entry = {"h": title,
                 "s": source + (" \u00b7 " + date_s if date_s else ""),
                 "img": None,
                 "link": (it.findtext("link") or "")}
        if any(p.search(title) for p in NOISY):
            spill.append(entry)
        else:
            items.append(entry)
        if len(items) >= limit:
            break
    if len(items) < limit:
        items.extend(spill[:limit - len(items)])
    return items


def main():
    out = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "generated_at_ct": ct_label(),
           "marriott": [],
           "brands": {}}
    for key, (query, limit) in FEEDS.items():
        try:
            got = fetch_feed(query, limit)
        except Exception as exc:  # keep going; the page falls back to baked
            print("WARN: %s feed failed: %s" % (key, exc), file=sys.stderr)
            got = []
        if key == "marriott":
            out["marriott"] = got[:4]
            out["brands"]["MAR"] = got[4:7]
        else:
            out["brands"][key] = got
    if not out["marriott"]:
        print("ERROR: no Marriott headlines fetched; not writing news.json",
              file=sys.stderr)
        return 1
    with open("data/news.json", "w") as f:
        json.dump(out, f, indent=2)
    counts = {"marriott": len(out["marriott"])}
    counts.update({k: len(v) for k, v in out["brands"].items()})
    print("wrote data/news.json", counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
