"""The schedule as an electrical circuit: how well two leagues are connected by games, and each game's share.

Picture every team as a junction and every game as a 1-ohm wire between the two teams. Send one unit of current
from league A's teams (spread evenly) to league B's. The effective resistance R between the leagues is how hard that
is: many games linking the leagues, directly or through common opponents, mean low resistance.

R has a direct statistical meaning. With game noise sigma and no prior, the doubt in the A-minus-B average gap from the
schedule alone is sigma * sqrt(R) points. A game's share of the comparison is the power its wire uses, divided by
the total; the shares sum to 1, and each equals that game's share of the variance of the schedule-only gap.
Effective resistance as the governor of rating error is from Hendrickx, Olshevsky and Saligrama (2019).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

from .data import INDEPENDENT


def laplacian(home: np.ndarray, away: np.ndarray, weights: np.ndarray, n: int) -> np.ndarray:
    """The schedule's Laplacian: each team's games on the diagonal, minus one per game between two teams off it."""
    L = np.zeros((n, n))
    np.add.at(L, (home, home), weights)
    np.add.at(L, (away, away), weights)
    np.add.at(L, (home, away), -weights)
    np.add.at(L, (away, home), -weights)
    return L


def league_resistance(games: pd.DataFrame, leagues_of: dict, A: str, B: str, noise: float = 15.0) -> dict:
    """Effective resistance between leagues A and B, the schedule-only doubt, and each game's share.

    ``games``: one season's games (any subset, for example regular season only). Returns
    {"R", "sd_schedule", "shares", "connected"}; ``shares`` is a copy of ``games`` with a ``share`` column (sums to 1).
    If no chain of games links some team of A to some team of B (2020, when several leagues played only each other),
    the leagues can't be compared through the schedule: R and sd_schedule are infinite and the shares empty.
    """
    teams = sorted(set(games.home) | set(games.away))
    ix = {t: i for i, t in enumerate(teams)}
    h, a = games.home.map(ix).to_numpy(), games.away.map(ix).to_numpy()
    w = np.ones(len(games))
    lg = np.array([leagues_of.get(t, INDEPENDENT) for t in teams])
    if not (lg == A).any() or not (lg == B).any():
        raise ValueError(f"no teams in {A!r} or {B!r} this season")
    c = (lg == A) / (lg == A).sum() - (lg == B) / (lg == B).sum()
    _, comp = connected_components(csr_matrix((w, (h, a)), shape=(len(teams), len(teams))), directed=False)
    if len(set(comp[c != 0])) > 1:
        return dict(R=np.inf, sd_schedule=np.inf, shares=games.assign(share=np.nan), connected=False)
    v = np.linalg.pinv(laplacian(h, a, w, len(teams))) @ c   # the voltage at each team
    R = float(c @ v)
    share = w * (v[h] - v[a]) ** 2 / R
    return dict(R=R, sd_schedule=float(noise * np.sqrt(R)), shares=games.assign(share=share), connected=True)
