"""Download FBS games from CollegeFootballData with your own free key, into data/raw/games.csv.

    python scripts/fetch_cfbd.py --first 2001 --last 2026

Get a key at https://collegefootballdata.com/key and put it in a file named .env at the repo's top level:
    CFBD_API_KEY=your-key-here
Two calls per season (regular season and postseason). Each season is saved as it arrives under data/raw/cfbd/, so a
rerun skips seasons already fetched; use --refresh to fetch the current season again for new games.
Only games between two FBS teams are kept. data/raw/ is never committed: CollegeFootballData's terms do not allow
republishing its data, only what you compute from it.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw"
BASE = "https://api.collegefootballdata.com/games"
FIELDS = ["game_id", "season", "week", "season_type", "home", "away", "home_league", "away_league", "neutral",
          "home_points", "away_points"]


def api_key() -> str:
    if os.environ.get("CFBD_API_KEY"):
        return os.environ["CFBD_API_KEY"]
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.strip().startswith("CFBD_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"')
    sys.exit("No key found. Put CFBD_API_KEY=... in .env at the repo's top level (see .env.example).")


def get(season: int, season_type: str, key: str, floor: int) -> list:
    url = BASE + "?" + urllib.parse.urlencode({"year": season, "seasonType": season_type})
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}", "Accept": "application/json"})
    for wait in (0, 30, 60, 120):
        time.sleep(wait or 0.5)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                left = int(r.headers.get("X-CallLimit-Remaining", -1))
                body = json.load(r)
            if 0 <= left < floor:
                sys.exit(f"Stopping: {left} calls left this month, under --floor {floor}. Rerun later to resume.")
            return body
        except urllib.error.HTTPError as e:
            if e.code != 429:  # 429 = too many calls per minute: wait and retry
                sys.exit(f"HTTP {e.code} for {season} {season_type}: {e.reason}")
    sys.exit(f"Still rate-limited for {season} {season_type}; rerun later to resume.")


def rows(games: list) -> list[dict]:
    out = []
    for g in games:
        if g.get("homeClassification") != "fbs" or g.get("awayClassification") != "fbs":
            continue
        out.append(dict(game_id=g["id"], season=g["season"], week=g["week"], season_type=g["seasonType"],
                        home=g["homeTeam"], away=g["awayTeam"], home_league=g.get("homeConference") or "",
                        away_league=g.get("awayConference") or "", neutral=bool(g.get("neutralSite")),
                        home_points=g.get("homePoints"), away_points=g.get("awayPoints")))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--first", type=int, default=2001)
    ap.add_argument("--last", type=int, required=True)
    ap.add_argument("--refresh", action="store_true", help="fetch the last season again even if saved")
    ap.add_argument("--floor", type=int, default=50, help="stop if fewer monthly calls than this would remain")
    a = ap.parse_args()
    key = api_key()
    (RAW / "cfbd").mkdir(parents=True, exist_ok=True)
    print(f"seasons {a.first}-{a.last}, saving to {RAW}", flush=True)
    for season in range(a.first, a.last + 1):
        for st in ("regular", "postseason"):
            dest = RAW / "cfbd" / f"{season}_{st}.json"
            if dest.exists() and not (a.refresh and season == a.last):
                continue
            body = get(season, st, key, a.floor)
            tmp = dest.with_suffix(".tmp")
            tmp.write_text(json.dumps(body))
            tmp.rename(dest)
        print(f"  {season} done", flush=True)
    allrows = []
    for season in range(a.first, a.last + 1):
        for st in ("regular", "postseason"):
            allrows += rows(json.loads((RAW / "cfbd" / f"{season}_{st}.json").read_text()))
    with open(RAW / "games.csv", "w", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        w.writerows(allrows)
    played = sum(r["home_points"] is not None for r in allrows)
    print(f"wrote {RAW / 'games.csv'}: {len(allrows)} FBS games, {played} played")


if __name__ == "__main__":
    main()
