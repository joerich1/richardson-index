"""Tiers inside each league: top tier, second tier, third tier and so on, down to the bottom tier.

The number of tiers is chosen by the data each season; a single team can be a tier of its own.

Main method, complete linkage: start with every team alone, sorted by rating. Repeatedly join the two neighboring
groups whose most clearly different pair of teams is least clearly different, and stop before any tier would hold two
teams the ratings are 95% or more sure differ. A tier therefore means "the ratings can't tell these teams apart",
not a proven class of its own.

Alternative for the top and bottom, the credible set: the fewest top teams that together are 90% likely to include
the league's true best team (and, upside down, the true worst), from redraws of the ratings.

On planted leagues (2 to 5 true tiers with real rating noise) complete linkage scored an adjusted Rand index of 0.47
(1 = the true split, 0 = chance): useful, not perfect. Smooth leagues with no real tiers still come out in about four
tiers, so read tiers as "where the ratings can draw a line", not as proven steps.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm

from .data import INDEPENDENT
from .ratings import SeasonFit

ORDINALS = ["top", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth", "eleventh",
            "twelfth"]


def prob_better(r: np.ndarray, C: np.ndarray) -> np.ndarray:
    """P[i, j] = chance team i is truly better than team j, from ratings ``r`` and their covariance ``C``."""
    v = np.diag(C)
    sd = np.sqrt(np.maximum(v[:, None] + v[None, :] - 2 * C, 1e-9))
    return norm.cdf((r[:, None] - r[None, :]) / sd)


def complete_linkage(r: np.ndarray, C: np.ndarray, sure: float = 0.95) -> list[tuple[int, int]]:
    """Tiers of teams sorted best first, as (start, end) index ranges. No tier holds two teams ``sure`` to differ."""
    P = prob_better(r, C)
    groups = [[i] for i in range(len(r))]
    while len(groups) > 1:
        cost = [max(P[i, j] for i in groups[g] for j in groups[g + 1]) for g in range(len(groups) - 1)]
        g = int(np.argmin(cost))
        merged = groups[g] + groups[g + 1]
        if P[merged[0], merged[-1]] >= sure:
            break
        groups[g:g + 2] = [merged]
    return [(gg[0], gg[-1] + 1) for gg in groups]


def credible_top(r: np.ndarray, C: np.ndarray, rng: np.random.Generator, level: float = 0.90, draws: int = 2000) -> int:
    """Size of the credible set: the fewest top teams (sorted best first) holding the true best with ``level`` chance."""
    d = rng.multivariate_normal(r, C, size=draws, method="cholesky")
    p_best = np.bincount(d.argmax(1), minlength=len(r)) / draws
    return int(np.searchsorted(np.cumsum(p_best), level) + 1)


def credible_bottom(r: np.ndarray, C: np.ndarray, rng: np.random.Generator, level: float = 0.90, draws: int = 2000) -> int:
    """The same from the bottom: the fewest bottom teams holding the true worst with ``level`` chance."""
    return credible_top(-r[::-1], C[::-1, ::-1], rng, level, draws)


def tier_names(k: int) -> list[str]:
    """Names for k tiers, best first: top tier, second tier, ..., bottom tier."""
    if k == 1:
        return ["whole league"]
    if k - 1 > len(ORDINALS):
        raise ValueError(f"{k} tiers is more than this naming handles")
    return [f"{ORDINALS[i]} tier" for i in range(k - 1)] + ["bottom tier"]


def league_sorted(fit: SeasonFit, leagues_of: dict, league: str):
    """One league's teams sorted best first, their ratings and their covariance."""
    teams = np.array(fit.teams)
    m = np.array([leagues_of.get(t, INDEPENDENT) == league for t in fit.teams])
    r, C = fit.mean[:fit.n][m], fit.cov[:fit.n, :fit.n][np.ix_(m, m)]
    o = np.argsort(-r)
    return teams[m][o], r[o], C[np.ix_(o, o)]


def league_tiers(fit: SeasonFit, leagues_of: dict, min_teams: int = 8, sure: float = 0.95) -> pd.DataFrame:
    """Every league of at least ``min_teams`` teams, split into tiers by complete linkage.

    Columns: season, league, rank, team, rating, sd, tier (1 = top), tiers, tier_name, tier_size,
    widest_p_in_tier (how sure the ratings are that the tier's best beats its worst; 0.5 for a one-team tier).
    """
    lg = [leagues_of.get(t, INDEPENDENT) for t in fit.teams]
    rows = []
    for L in sorted(set(lg) - {INDEPENDENT}):
        if lg.count(L) < min_teams:
            continue
        tm, r, C = league_sorted(fit, leagues_of, L)
        P = prob_better(r, C)
        segs = complete_linkage(r, C, sure)
        names = tier_names(len(segs))
        for g, (s0, s1) in enumerate(segs):
            for i in range(s0, s1):
                rows.append(dict(season=fit.season, league=L, rank=i + 1, team=tm[i], rating=r[i], sd=float(np.sqrt(C[i, i])),
                                 tier=g + 1, tiers=len(segs), tier_name=names[g], tier_size=s1 - s0,
                                 widest_p_in_tier=float(P[s0, s1 - 1]) if s1 - s0 > 1 else 0.5))
    return pd.DataFrame(rows)
