"""Does a game help or hurt later forecasts? Leave it out and score both teams' later games.

The ratings are refit before each week from that season's earlier regular-season games, as a forecaster would. For a
game played in week w, every later fit of the season is redone without it (an exact rank-one removal), and both teams'
later games are predicted again. influence = sum over those later games of (log loss with the game) minus (log loss
without it): negative means keeping the game made later forecasts better; positive means leaving it out would have.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm

from .ratings import design, fit_gaussian


def log_loss(p: np.ndarray, home_win: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return -(home_win * np.log(p) + (1 - home_win) * np.log(1 - p))


def game_influence(season_games: pd.DataFrame, prior_mean: np.ndarray, prior_prec: np.ndarray, noise: float = 15.0) -> pd.DataFrame:
    """For one season (games sorted by week): each game's pregame home win chance, influence and later-game count.

    ``prior_mean`` and ``prior_prec`` are the season's starting point (``SeasonFit.prior_mean``, ``.prior_prec``),
    for teams sorted by name plus home field.
    """
    sg = season_games.reset_index(drop=True)
    teams = sorted(set(sg.home) | set(sg.away))
    ix = {t: i for i, t in enumerate(teams)}
    X = design(sg.home.map(ix).to_numpy(), sg.away.map(ix).to_numpy(), sg.neutral.to_numpy(), len(teams))
    y, win, wk = sg.margin.to_numpy(float), sg.home_win.to_numpy(float), sg.sort_week.to_numpy()
    reg = (sg.season_type == "regular").to_numpy()
    fits = {}
    for w in sorted(set(wk)):
        use = (wk < w) & reg
        fits[w] = (fit_gaussian(X[use], y[use], prior_mean, prior_prec, noise) if use.any()
                   else (prior_mean.copy(), np.diag(1 / prior_prec)))
    pre = np.empty(len(sg))
    for w, (m, c) in fits.items():
        now = wk == w
        pre[now] = norm.cdf(X[now] @ m / np.sqrt(noise**2 + np.einsum("ij,jk,ik->i", X[now], c, X[now])))
    h, a = sg.home.to_numpy(), sg.away.to_numpy()
    infl, n_later = np.zeros(len(sg)), np.zeros(len(sg), int)
    for g in np.where(reg)[0]:
        later = (wk > wk[g]) & ((h == h[g]) | (a == h[g]) | (h == a[g]) | (a == a[g]))
        if not later.any():
            continue
        x, tot = X[g], 0.0
        for w in sorted(set(wk[later])):
            m, c = fits[w]
            cx = c @ x
            c_d = c + np.outer(cx, cx) / (noise**2 - x @ cx)
            m_d = m - c_d @ x * (y[g] - x @ m) / noise**2
            rows = later & (wk == w)
            Xr = X[rows]
            p_with = norm.cdf(Xr @ m / np.sqrt(noise**2 + np.einsum("ij,jk,ik->i", Xr, c, Xr)))
            p_wo = norm.cdf(Xr @ m_d / np.sqrt(noise**2 + np.einsum("ij,jk,ik->i", Xr, c_d, Xr)))
            tot += (log_loss(p_with, win[rows]) - log_loss(p_wo, win[rows])).sum()
        infl[g], n_later[g] = tot, later.sum()
    winner_p = np.where(win == 1, pre, 1 - pre)
    return sg[["game_id", "season", "week", "season_type", "home", "away"]].assign(
        pregame_home_win_chance=pre, winner_pregame_chance=winner_p, influence=infl, later_games=n_later)
