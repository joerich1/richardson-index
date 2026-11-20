"""Team ratings from game margins (Massey's method with a starting point carried from last season).

The model, for every game:  home margin = home rating - away rating + home field + noise,
noise ~ Normal(0, sigma). Ratings are in points on a neutral field; the average team sits near 0.

Each team starts the season at its last season-end rating times ``carry`` (1 = carried in full), with a prior spread
of ``prior_sd`` points around it, so the fit is ridge regression pulled toward last season. A team new to the data
starts at the ``newcomer_quantile`` of last season's ratings. Home field has its own prior.

``fit_seasons`` walks season by season. The season-end fit that is carried forward uses the fixed ``noise``; the fit
reported for each season then re-estimates the noise from that season's own results.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd

# numpy on Apple's Accelerate can raise false divide/overflow warnings on ordinary matrix products.
warnings.filterwarnings("ignore", message=".*encountered in matmul", category=RuntimeWarning)


@dataclass(frozen=True)
class Settings:
    """Model settings. The defaults were chosen by a walk-forward search on 2003-2023 FBS seasons, checked on 2024-25."""
    carry: float = 1.0               # share of last season's rating carried over (1 = all of it)
    prior_sd: float = 8.0            # points: how far a team may move from its starting rating before data pushes back
    noise: float = 15.0              # points: game-to-game noise for the carried fit
    newcomer_quantile: float = 0.05  # a new team starts at this quantile of last season's ratings
    home_mean: float = 2.5           # points: prior home-field advantage
    home_sd: float = 2.0
    include_postseason: bool = True  # count bowl and playoff games in the season-end fit


def design(home_idx: np.ndarray, away_idx: np.ndarray, neutral: np.ndarray, n: int) -> np.ndarray:
    """One row per game: +1 in the home team's column, -1 in the away team's, last column home field (0 if neutral)."""
    X = np.zeros((len(home_idx), n + 1))
    rows = np.arange(len(home_idx))
    X[rows, home_idx] = 1.0
    X[rows, away_idx] = -1.0
    X[:, n] = (~np.asarray(neutral, bool)).astype(float)
    return X


def fit_gaussian(X, y, prior_mean, prior_prec, sigma):
    """Posterior mean and covariance of the ratings (ridge regression toward ``prior_mean``)."""
    A = X.T @ X / sigma**2 + np.diag(prior_prec)
    cov = np.linalg.inv(A)
    return cov @ (X.T @ y / sigma**2 + prior_prec * prior_mean), cov


@dataclass
class SeasonFit:
    """One season's ratings. ``mean`` and ``cov`` have one entry per team plus home field (last)."""
    season: int
    teams: list
    mean: np.ndarray
    cov: np.ndarray
    noise: float              # noise estimated from this season's results
    games: pd.DataFrame       # the games in the fit
    X: np.ndarray
    y: np.ndarray
    prior_mean: np.ndarray
    prior_prec: np.ndarray

    @property
    def n(self) -> int:
        return len(self.teams)

    @property
    def index(self) -> dict:
        return {t: i for i, t in enumerate(self.teams)}

    @property
    def home_field(self) -> float:
        return float(self.mean[self.n])

    def ratings(self) -> pd.DataFrame:
        """Each team's rating and its standard deviation (points)."""
        return pd.DataFrame({"team": self.teams, "rating": self.mean[:self.n],
                             "sd": np.sqrt(np.diag(self.cov)[:self.n])})


def _prior(carried: dict, last_seen: dict, teams: list, season: int, s: Settings):
    pool = np.array(list(carried.values())) if carried else np.zeros(1)
    newcomer = float(np.quantile(pool, s.newcomer_quantile))
    m0 = np.array([s.carry ** (season - last_seen[t]) * carried[t] if t in carried else newcomer for t in teams]
                  + [s.home_mean])
    prec = np.array([1 / s.prior_sd**2] * len(teams) + [1 / s.home_sd**2])
    return m0, prec


def estimate_noise(X, y, prior_mean, prior_prec, sigma0=15.0) -> float:
    """Noise from the season's own residuals, corrected for the number of effectively fitted ratings."""
    m, c = fit_gaussian(X, y, prior_mean, prior_prec, sigma0)
    res = y - X @ m
    fitted = np.trace(X @ c @ X.T) / sigma0**2
    return float(res.std() * np.sqrt(len(y) / max(len(y) - fitted, 1)))


def fit_seasons(games: pd.DataFrame, settings: Settings = Settings(), last_season: int | None = None) -> dict:
    """Fit every season from the first in ``games`` to ``last_season``; return {season: SeasonFit}.

    ``games`` comes from ``data.load_games``. Every team that played in a season is rated that season.
    """
    s = settings
    last_season = int(games.season.max()) if last_season is None else last_season
    carried, last_seen, fits = {}, {}, {}
    for season in range(int(games.season.min()), last_season + 1):
        sg = games[games.season == season]
        if sg.empty:
            continue
        teams = sorted(set(sg.home) | set(sg.away))
        ix = {t: i for i, t in enumerate(teams)}
        X = design(sg.home.map(ix).to_numpy(), sg.away.map(ix).to_numpy(), sg.neutral.to_numpy(), len(teams))
        y = sg.margin.to_numpy(float)
        m0, prec = _prior(carried, last_seen, teams, season, s)
        use = (sg.season_type == "regular").to_numpy() | (s.include_postseason & (sg.season_type == "postseason").to_numpy())
        carry_mean, _ = fit_gaussian(X[use], y[use], m0, prec, s.noise)
        if not np.isfinite(carry_mean).all():
            raise FloatingPointError(f"season {season}: the fit did not converge")
        for t, i in ix.items():
            carried[t], last_seen[t] = float(carry_mean[i]), season
        Xu, yu = X[use], y[use]
        sigma = estimate_noise(Xu, yu, m0, prec, s.noise)
        mean, cov = fit_gaussian(Xu, yu, m0, prec, sigma)
        fits[season] = SeasonFit(season, teams, mean, cov, sigma, sg[use].reset_index(drop=True), Xu, yu, m0, prec)
    return fits
