"""League gaps: how many points the average team of one league is better than the other's, with an honest range.

Gap = league A's average rating minus league B's (every team counts the same within its league).
The range adds two kinds of doubt:
  rating doubt   from the fit's covariance (how sure the ratings are, given the games played)
  linking error  a jackknife over the "bridge" games, the games between a league team and an outsider: drop each one
                 in turn, refit exactly, and see how far the gap moves. Leagues are compared only through these games,
                 so a gap that rests on a few dozen of them should say so. The idea comes from test equating, where
                 two exams are linked through shared items.
Dropping a game is exact for this Gaussian model (a rank-one update of the covariance).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm

from .data import INDEPENDENT
from .ratings import SeasonFit

Z90 = norm.ppf(0.95)


def league_matrix(fit: SeasonFit, leagues_of: dict) -> tuple[list, np.ndarray, np.ndarray]:
    """Leagues (sorted), each team's league, and a matrix whose rows average each league's ratings."""
    team_league = np.array([leagues_of.get(t, INDEPENDENT) for t in fit.teams])
    leagues = sorted(set(team_league) - {INDEPENDENT})
    C = np.zeros((len(leagues), fit.n + 1))
    for i, L in enumerate(leagues):
        C[i, :fit.n] = (team_league == L) / (team_league == L).sum()
    return leagues, team_league, C


def drop_game(fit: SeasonFit, g: int) -> np.ndarray:
    """The ratings refit without game ``g`` (exact)."""
    x = fit.X[g]
    cx = fit.cov @ x
    cov_d = fit.cov + np.outer(cx, cx) / (fit.noise**2 - x @ cx)
    return fit.mean - cov_d @ x * (fit.y[g] - x @ fit.mean) / fit.noise**2


def both_ways(gaps: pd.DataFrame) -> pd.DataFrame:
    """Each pair listed both ways round (A, B and B, A), so a reader can find either league first."""
    f = gaps.rename(columns={"A": "B", "B": "A", "nA": "nB", "nB": "nA"}).copy()
    f["gap"], f["lo90"], f["hi90"], f["p_A_better"] = -gaps.gap, -gaps.hi90, -gaps.lo90, 1 - gaps.p_A_better
    return pd.concat([gaps, f[gaps.columns]], ignore_index=True).sort_values(["season", "A", "B"]).reset_index(drop=True)


def league_gaps(fit: SeasonFit, leagues_of: dict, min_teams: int = 4) -> pd.DataFrame:
    """Every pair of leagues in one season: gap, rating doubt, linking error, 90% range, chance A is better.

    Columns: season, A, B, nA, nB, direct_games, bridge_games, gap, sd_rating, sd_link, sd, lo90, hi90,
    p_A_better, small_league (a league under ``min_teams`` teams; flagged, not dropped).
    """
    leagues, team_league, C = league_matrix(fit, leagues_of)
    ix = fit.index
    hc = np.array([team_league[ix[t]] for t in fit.games.home])
    ac = np.array([team_league[ix[t]] for t in fit.games.away])
    bridge = np.where(hc != ac)[0]
    avg = C @ fit.mean
    drops = np.array([C @ drop_game(fit, g) for g in bridge]).reshape(len(bridge), len(leagues))
    sizes = {L: int((team_league == L).sum()) for L in leagues}
    rows = []
    for a in range(len(leagues)):
        for b in range(a + 1, len(leagues)):
            A, B = leagues[a], leagues[b]
            c = C[a] - C[b]
            touch = [j for j, g in enumerate(bridge) if A in (hc[g], ac[g]) or B in (hc[g], ac[g])]
            gd = drops[touch, a] - drops[touch, b]
            var_link = (len(gd) - 1) / len(gd) * ((gd - gd.mean()) ** 2).sum() if len(gd) > 1 else 0.0
            sd_r = float(np.sqrt(c @ fit.cov @ c))
            sd = float(np.sqrt(sd_r**2 + var_link))
            gap = float(avg[a] - avg[b])
            rows.append(dict(season=fit.season, A=A, B=B, nA=sizes[A], nB=sizes[B],
                             direct_games=int((((hc == A) & (ac == B)) | ((hc == B) & (ac == A))).sum()),
                             bridge_games=len(touch), gap=gap, sd_rating=sd_r, sd_link=float(np.sqrt(var_link)), sd=sd,
                             lo90=gap - Z90 * sd, hi90=gap + Z90 * sd, p_A_better=float(norm.cdf(gap / sd)),
                             small_league=min(sizes[A], sizes[B]) < min_teams))
    return pd.DataFrame(rows)
