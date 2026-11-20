"""Run the Richardson Index: games in, every output table out.

    python scripts/run_index.py data/toy/games.csv --out toy_outputs
    python scripts/run_index.py data/raw/games.csv --out my_outputs

The games file follows data/SCHEMA.md. Writes one CSV per table (ratings, league_gaps, tiers, tier_teams, ladder,
tier_vs_tier, matched_share, game_shares); see the README for what each holds.
"""
import argparse
import time

import richardson_index as ri


def main():
    ap = argparse.ArgumentParser(description="Games in, every Richardson Index table out.")
    ap.add_argument("games", help="CSV of games (data/SCHEMA.md)")
    ap.add_argument("--out", default="my_outputs", help="folder for the output CSVs")
    ap.add_argument("--min-tier-league", type=int, default=8, help="split leagues of at least this many teams into tiers")
    ap.add_argument("--through", metavar="SEASON:WEEK", help="stop at this regular-season week, e.g. 2026:11")
    a = ap.parse_args()
    t0 = time.time()
    games = ri.load_games(a.games)
    if a.through:
        season, week = (int(x) for x in a.through.split(":"))
        games = ri.data.through_week(games, season, week)
        games = games[games.season <= season]
    print(f"richardson-index {ri.__version__}: {len(games)} played games, seasons {games.season.min()}-{games.season.max()}",
          flush=True)
    tables = ri.run(games, min_tier_league=a.min_tier_league)
    ri.pipeline.write(tables, a.out)
    print(f"wrote {len(tables)} tables to {a.out}/ in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
