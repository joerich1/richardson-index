"""From games to every output table, for every season."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .circuit import league_resistance
from .compare import compare_tiers
from .data import league_of
from .gaps import league_gaps
from .ratings import Settings, fit_seasons
from .tiers import league_tiers

OUTPUTS = ["ratings", "league_gaps", "tiers", "tier_teams", "ladder", "tier_vs_tier", "matched_share", "game_shares"]


def run(games: pd.DataFrame, settings: Settings = Settings(), min_tier_league: int = 8,
        share_pairs: list[tuple[str, str]] | None = None, log=print) -> dict[str, pd.DataFrame]:
    """Every output table. ``share_pairs``: league pairs whose game shares to list (default: every pair, top 15 games)."""
    fits = fit_seasons(games, settings)
    out = {k: [] for k in OUTPUTS}
    for season, fit in fits.items():
        lo = league_of(games, season)
        gaps = league_gaps(fit, lo)
        tiers = league_tiers(fit, lo, min_teams=min_tier_league)
        r = fit.ratings()
        r.insert(0, "season", season)
        r.insert(2, "league", [lo.get(t, "Independent") for t in r.team])
        r["rank_national"] = r.rating.rank(ascending=False, method="min").astype(int)
        if not tiers.empty:
            r = r.merge(tiers[["team", "rank", "tier", "tier_name"]].rename(columns={"rank": "rank_in_league"}),
                        on="team", how="left")
            cmp = compare_tiers(fit, tiers, gaps)
            for k in ("tiers", "ladder", "tier_vs_tier", "matched_share"):
                out[k].append(cmp[k])
            out["tier_teams"].append(tiers)
        out["ratings"].append(r.assign(home_field=fit.home_field, noise=fit.noise))
        out["league_gaps"].append(gaps)
        reg = fit.games[fit.games.season_type == "regular"]
        pairs = share_pairs if share_pairs is not None else list(zip(gaps.A, gaps.B))
        for A, B in pairs:
            if A not in set(lo.values()) or B not in set(lo.values()):
                continue
            res = league_resistance(reg, lo, A, B, settings.noise)
            if not res["connected"]:
                continue
            top = res["shares"].nlargest(15, "share")
            out["game_shares"].append(top[["season", "week", "home", "away"]].assign(
                A=A, B=B, R=res["R"], sd_schedule=res["sd_schedule"], share=top.share.to_numpy(),
                rank=range(1, len(top) + 1)))
        log(f"== season {season}: {fit.n} teams, {len(gaps)} league pairs, noise {fit.noise:.1f} ==")
    return {k: (pd.concat(v, ignore_index=True) if v else pd.DataFrame()) for k, v in out.items()}


def write(tables: dict[str, pd.DataFrame], folder: str | Path) -> None:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    for k, df in tables.items():
        df.round(4).to_csv(folder / f"{k}.csv", index=False)
