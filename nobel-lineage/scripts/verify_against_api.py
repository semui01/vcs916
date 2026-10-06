"""Diff the transcribed motivations in data/prizes.py against the Nobel Prize API.

Run where api.nobelprize.org is reachable (it was blocked in the build environment):
    python3 -I scripts/verify_against_api.py
Prints every prize whose transcribed motivation does not match a laureate motivation
from the API, and any laureate names the API lists that the dataset lacks.
It was not run during the build because the API was blocked.
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
from prizes import PRIZES  # noqa: E402

URL = "https://api.nobelprize.org/2.1/nobelPrizes?nobelPrizeCategory=phy&limit=200&format=json"


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower().replace("–", "-")).strip()


api = json.load(urllib.request.urlopen(URL, timeout=30))["nobelPrizes"]
by_year = {}
for p in api:
    y = int(p["awardYear"])
    mots, names = [], []
    for l in p.get("laureates", []):
        mots.append(norm(l.get("motivation", {}).get("en", "")))
        names.append(l.get("knownName", {}).get("en") or l.get("fullName", {}).get("en", ""))
    by_year[y] = (mots, names)

problems = 0
for nid, year, laur, mot, *_ in PRIZES:
    mots, names = by_year.get(year, ([], []))
    m = norm(mot)
    if not any(a and (a in m or m in a) for a in mots):
        problems += 1
        print(f"[motivation] {nid}: dataset='{mot}'\n    api={mots}")
for y, (mots, names) in sorted(by_year.items()):
    ours = {x for nid, yy, laur, *_ in PRIZES if yy == y for x in laur}
    if len(ours) != len(names):
        problems += 1
        print(f"[laureates] {y}: dataset={sorted(ours)} api={names}")
print("done,", problems, "items to review")
