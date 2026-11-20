"""Make data/toy/games.csv: three made-up seasons of three made-up leagues, so the whole method runs with no key.

Every team and score is invented. Each league plays a full round robin, teams play a few games against other leagues,
and the best teams meet in a short postseason. True strengths are planted in tiers (written to data/toy/truth.csv), so
you can see whether the method finds them.

    python scripts/make_toy.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
LEAGUES = {
    "Northern": (["Ashford", "Brookline", "Carrow", "Dunmore", "Elsworth", "Fenwick", "Garland", "Hollis", "Irvine",
                  "Jasper"], [14, 13, 6, 5, 5, 4, -3, -4, -5, -12]),
    "Coastal": (["Kingsport", "Lowell", "Marlow", "Newbury", "Oakham", "Penrith", "Quarry", "Redfield", "Selby",
                 "Thornton"], [9, 2, 1, 1, 0, -1, -2, -8, -9, -9]),
    "Prairie": (["Upton", "Vale", "Westbrook", "Yardley", "Zephyr", "Alder", "Birch", "Cedar"],
                [3, -4, -5, -6, -6, -7, -14, -15]),
}
SEASONS, NOISE, HOME, CROSS = (2024, 2025, 2026), 14.0, 2.5, 4


def main():
    rng = np.random.default_rng(2026)
    team_league = {t: L for L, (ts, _) in LEAGUES.items() for t in ts}
    base = {t: s for _, (ts, ss) in LEAGUES.items() for t, s in zip(ts, ss)}
    rows, truth, gid = [], [], 1
    for season in SEASONS:
        strength = {t: base[t] + rng.normal(0, 1.0) for t in base}
        truth += [dict(season=season, team=t, league=team_league[t], true_rating=round(v, 2)) for t, v in strength.items()]
        games = []
        for L, (ts, _) in LEAGUES.items():
            for i in range(len(ts)):
                for j in range(i + 1, len(ts)):
                    games.append((ts[i], ts[j]) if rng.random() < 0.5 else (ts[j], ts[i]))
        teams = list(base)
        for t in teams:
            others = [u for u in teams if team_league[u] != team_league[t]]
            for u in rng.choice(others, CROSS // 2, replace=False):
                games.append((t, u) if rng.random() < 0.5 else (u, t))
        order = rng.permutation(len(games))
        for k, gi in enumerate(order):
            h, a = games[gi]
            m = strength[h] - strength[a] + HOME + rng.normal(0, NOISE)
            hp = max(0, int(round(24 + m / 2)))
            ap = max(0, int(round(24 - m / 2)))
            if hp == ap:
                hp += 1 if m >= 0 else 0
                ap += 0 if m >= 0 else 1
            rows.append(dict(game_id=gid, season=season, week=1 + k * 12 // len(order), season_type="regular", home=h,
                             away=a, home_league=team_league[h], away_league=team_league[a], neutral=False,
                             home_points=hp, away_points=ap))
            gid += 1
        top = sorted(base, key=lambda t: -strength[t])[:6]
        for i in range(0, 6, 2):
            h, a = top[i], top[5 - i]
            m = strength[h] - strength[a] + rng.normal(0, NOISE)
            hp, ap = max(0, int(round(24 + m / 2))), max(0, int(round(24 - m / 2)))
            hp += hp == ap
            rows.append(dict(game_id=gid, season=season, week=1, season_type="postseason", home=h, away=a,
                             home_league=team_league[h], away_league=team_league[a], neutral=True, home_points=hp,
                             away_points=ap))
            gid += 1
    out = ROOT / "data/toy"
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out / "games.csv", index=False)
    pd.DataFrame(truth).to_csv(out / "truth.csv", index=False)
    print(f"wrote {out / 'games.csv'}: {len(rows)} games, {len(base)} teams, {len(SEASONS)} seasons")


if __name__ == "__main__":
    main()
