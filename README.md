# The Richardson Index

How much better is one league than another, when they barely play each other? The Richardson Index answers with a gap
in points, a range that admits how few games link the leagues, and tiers inside each league.

It was built for the college football essay "SEC Versus Big Ten, Through Everyone Else" on
[josephrichardson.dev](https://josephrichardson.dev). It works for any sport with leagues and scores.

## One result

The SEC's average team would beat the Big Ten's by 4.9 points on a neutral field (2026 season through week 11). The
90% range is 0.7 to 9.0 points. The two leagues played each other three times. The answer rests on 69 games
between one of them and some other league.

Tier against tier, the SEC's lead grows down the league:

| Tier | SEC teams | Big Ten teams | SEC lead, points | 90% range | Verdict |
|---|---|---|---|---|---|
| Top tier | 2 | 2 | 4.2 | -4.3 to 12.6 | Too close to call |
| Second tier | 4 | 7 | 5.7 | -0.1 to 11.5 | Too close to call |
| Third tier | 7 | 7 | 6.7 | 1.4 to 11.9 | SEC better |
| Bottom tier | 3 | 2 | 10.2 | 2.3 to 18.2 | SEC better |

"Better" means the ratings are at least 95% sure. Every number is in [`outputs/`](outputs/).

## Quickstart

Python 3.11 or newer.

```bash
git clone https://github.com/joerich1/richardson-index.git
cd richardson-index
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
python scripts/run_index.py data/toy/games.csv --out toy_outputs
```

The toy data is three made-up seasons of three made-up leagues. The run takes about a second. It prints one line per
season, then writes eight tables to `toy_outputs/`:

```
richardson-index 1.0.0: 531 played games, seasons 2024-2026
== season 2024: 28 teams, 3 league pairs, noise 15.3 ==
...
wrote 8 tables to toy_outputs/ in 0 s
```

The true strengths behind the toy games are in `data/toy/truth.csv`, so you can check what the method found.

## Using real data

1. Get a free key from [CollegeFootballData](https://collegefootballdata.com/key).
2. Copy `.env.example` to `.env` and put your key after `CFBD_API_KEY=`.
3. Download the games. This uses 52 calls, two per season, and takes about a minute:
   ```bash
   python scripts/fetch_cfbd.py --first 2001 --last 2026
   ```
4. Run the index. Every season from 2001 takes about 6 seconds on a laptop:
   ```bash
   python scripts/run_index.py data/raw/games.csv --out my_outputs
   ```

Add `--through 2026:11` to stop at a given week. That run reproduces the numbers in `outputs/`. The downloaded games
stay on your machine: CollegeFootballData's terms let you publish what you compute, not its data.

## What's in the outputs

Each file opens in a spreadsheet. Ratings are points on a neutral field, and the average FBS team is near 0. A "90%
range" is where the true value lies with 90% probability.

| File | One row per | What it tells you |
|---|---|---|
| `ratings.csv` | team and season | Rating and its uncertainty, national rank, rank and tier in its league |
| `league_gaps.csv` | pair of leagues and season | Gap between the leagues' average teams, its 90% range, and the chance the first league is better |
| `tier_teams.csv` | team and season | Each team's tier, for leagues of 8 or more teams |
| `tiers.csv` | tier and season | The tier's teams and average rating |
| `ladder.csv` | tier and season | Every tier in the country, best to worst |
| `tier_vs_tier.csv` | pair of tiers and season | Gap, 90% range, verdict and the win chance of a random team from each |
| `matched_share.csv` | tier, other league and season | A tier against the same share of another league, for leagues of different sizes |
| `game_shares.csv` | game, pair of leagues and season | The 15 games that carry most of each league comparison, and each one's share |

Column names are spelled out in plain words. `A` and `B` name the two sides, and every gap is A minus B.

## How it works

**Ratings.** Each game's margin is the home team's rating minus the away team's, plus home field, plus noise. This is
Massey's method. Each team starts the season at last season's rating, with a spread of 8 points around it.

**League gaps.** The gap is one league's average rating minus the other's. Its range adds the ratings' own
uncertainty and a linking error. The linking error leaves out each game between a league team and an outsider in turn,
and sees how far the gap moves.

**The schedule as a circuit.** Every game is a wire between two teams. Effective resistance measures how well two
leagues are connected by games. It gives the doubt the schedule alone leaves in the gap, and each game's share of it.
For SEC against Big Ten in 2026, the schedule alone leaves 3.8 points of doubt. Minnesota against Mississippi State
carries 5% of it, more than any other game.

**Tiers.** Teams the ratings can't tell apart share a tier. Tiers are built by joining neighboring teams, and never hold
two teams the ratings are 95% sure differ. The number of tiers is chosen by the data, and one team can be a tier.

The math, the tests behind each choice and the papers it builds on are in [`docs/METHOD.md`](docs/METHOD.md).

## Using it on other data

Any sport with leagues and scores works. Make a CSV with the columns in [`data/SCHEMA.md`](data/SCHEMA.md): one row
per game, with the two teams, their leagues and the score. Then run `scripts/run_index.py` on it.
[`examples/other_sport.py`](examples/other_sport.py) builds a small soccer-style table by hand and runs it.

The default settings were tuned on college football, where the game-to-game noise is about 14 points. For another
sport, pass your own `Settings` to `fit_seasons`; the comments in `src/richardson_index/ratings.py` explain each one.

## Cite

If you use this, please cite it with the "Cite this repository" button on GitHub, or:

> Richardson, J. (2026). *The Richardson Index* (version 1.0.0). https://github.com/joerich1/richardson-index

## License and data credits

- Code: MIT ([`LICENSE`](LICENSE)).
- Results in `outputs/`: CC BY 4.0 ([`LICENSE-data`](LICENSE-data)). Use them freely with credit.
- Data provided by [CollegeFootballData.com](https://collegefootballdata.com). No game data is included here.
- Team and league names belong to their owners.

Made by [Joseph Richardson](https://josephrichardson.dev).
