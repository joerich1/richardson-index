"""The same method on a different sport: two made-up soccer leagues that meet only in a cup.

Goals are small numbers, so the noise is about 1.6 goals instead of 15 points; pass your own Settings.

    python examples/other_sport.py
"""
import numpy as np
import pandas as pd

import richardson_index as ri

rng = np.random.default_rng(7)
north = ["Ambers", "Bridgeton", "Calder", "Dunford", "Eastleigh", "Fairhaven"]
south = ["Granton", "Harrow", "Ilford", "Jarrow", "Kelso", "Linton"]
strength = dict(zip(north + south, [1.0, 0.6, 0.3, 0.1, -0.2, -0.5, 0.4, 0.2, 0.0, -0.3, -0.6, -0.9]))
league = {t: "North" for t in north} | {t: "South" for t in south}

rows, gid = [], 0
for teams in (north, south):  # double round robin inside each league
    for h in teams:
        for a in teams:
            if h != a:
                rows.append((h, a, "regular"))
for h, a in zip(rng.permutation(north), rng.permutation(south)):  # one cup round between the leagues
    rows.append((h, a, "postseason"))
games = []
for h, a, st in rows:
    hg = rng.poisson(np.exp(0.35 + 0.5 * (strength[h] - strength[a]) / 2 + 0.15))
    ag = rng.poisson(np.exp(0.35 - 0.5 * (strength[h] - strength[a]) / 2))
    games.append(dict(game_id=gid, season=2030, week=1 + gid // 6, season_type=st, home=h, away=a,
                      home_league=league[h], away_league=league[a], neutral=False, home_points=hg, away_points=ag))
    gid += 1

g = ri.load_games(pd.DataFrame(games))
settings = ri.Settings(prior_sd=1.0, noise=1.6, home_mean=0.3, home_sd=0.3)
fit = ri.fit_seasons(g, settings)[2030]
print(fit.ratings().sort_values("rating", ascending=False).round(2).to_string(index=False))
print(ri.league_gaps(fit, ri.league_of(g, 2030))[["A", "B", "gap", "lo90", "hi90", "bridge_games"]].round(2))
