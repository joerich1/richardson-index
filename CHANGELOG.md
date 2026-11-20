# Changelog

## 1.0.0 (2026-11-20)

First release. It has ratings, league gaps with linking error, the schedule as a circuit, and tiers inside each
league, from top tier to bottom tier. It also has tier comparisons and the game influence check. Results in `outputs/` cover FBS seasons
2001 to 2026, with 2026 through week 11.

Checked against the essay with two commands:

    python scripts/fetch_cfbd.py --first 2001 --last 2026
    python scripts/run_index.py data/raw/games.csv --through 2026:11 --out outputs

The SEC leads the Big Ten by 4.884 points (90% range 0.729 to 9.040), as in the essay. The SEC and Big Ten tiers
match the essay's.

The essay's own run used an earlier copy of the same CollegeFootballData games. The 2026 league gaps, ranges and tiers
are identical. Average ratings sit 0.05 points higher here, the same shift for every team, so no gap or order changes.
Seasons 2004 to 2007 and 2020 differ slightly, with league gaps up to 1.1 points apart. This download counts Notre
Dame in the ACC in 2020, and differs in a few games of teams then joining FBS.
