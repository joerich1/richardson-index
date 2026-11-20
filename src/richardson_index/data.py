"""Load games from a CSV that follows data/SCHEMA.md, and check it.

One row per game. Required columns:
    game_id, season, week, season_type, home, away, home_league, away_league, neutral, home_points, away_points
season_type is "regular" or "postseason". Games not yet played may leave the points empty; they are dropped.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REQUIRED = ["game_id", "season", "week", "season_type", "home", "away", "home_league", "away_league", "neutral",
            "home_points", "away_points"]
POSTSEASON_WEEK = 99  # postseason games sort after every regular-season week
INDEPENDENT = "Independent"


def load_games(source: str | Path | pd.DataFrame, independents: tuple[str, ...] = ("FBS Independents",)) -> pd.DataFrame:
    """Read and check games; return them sorted by season, week and game id, with a home-minus-away margin.

    Teams whose league is empty or listed in ``independents`` are marked "Independent": they are rated like everyone
    else but belong to no league.
    """
    g = source.copy() if isinstance(source, pd.DataFrame) else pd.read_csv(source)
    missing = [c for c in REQUIRED if c not in g.columns]
    if missing:
        raise ValueError(f"games are missing columns {missing}; see data/SCHEMA.md")
    bad = set(g.season_type) - {"regular", "postseason"}
    if bad:
        raise ValueError(f"season_type must be 'regular' or 'postseason', found {sorted(bad)}")
    g = g.dropna(subset=["home_points", "away_points"]).copy()
    if not g.game_id.is_unique:
        raise ValueError("game_id repeats")
    for side in ("home_league", "away_league"):
        g[side] = g[side].where(g[side].notna() & ~g[side].isin(independents), INDEPENDENT).astype(str)
    g["neutral"] = g.neutral.astype(str).str.lower().isin(["true", "1", "yes"])
    g["sort_week"] = np.where(g.season_type == "postseason", POSTSEASON_WEEK, g.week)
    g["margin"] = (g.home_points - g.away_points).astype(float)
    g["home_win"] = np.where(g.margin > 0, 1.0, np.where(g.margin < 0, 0.0, 0.5))
    return g.sort_values(["season", "sort_week", "game_id"]).reset_index(drop=True)


def through_week(games: pd.DataFrame, season: int, week: int) -> pd.DataFrame:
    """Drop every game of ``season`` after regular-season ``week`` (and that season's postseason): ratings "as of" then."""
    late = (games.season == season) & ((games.season_type == "postseason") | (games.week > week))
    return games[~late | (games.season < season)].reset_index(drop=True)


def league_of(games: pd.DataFrame, season: int) -> dict[str, str]:
    """Each team's league in one season, from its regular-season games (the label a fan would use)."""
    r = games[(games.season == season) & (games.season_type == "regular")]
    return dict(zip(r.home, r.home_league)) | dict(zip(r.away, r.away_league))
