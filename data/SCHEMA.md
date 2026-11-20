# Games file

One row per game, as CSV. `scripts/fetch_cfbd.py` writes this file for college football. For another sport, write it
yourself.

| Column | Type | Meaning | CollegeFootballData field |
|---|---|---|---|
| `game_id` | integer or text | Unique per game | `id` |
| `season` | integer | Season year | `season` |
| `week` | integer | Week within the season | `week` |
| `season_type` | `regular` or `postseason` | Postseason games are counted after the last regular week | `seasonType` |
| `home` | text | Home team (on a neutral site, the team listed first) | `homeTeam` |
| `away` | text | Away team | `awayTeam` |
| `home_league` | text | Home team's league that season; empty for an independent | `homeConference` |
| `away_league` | text | Away team's league | `awayConference` |
| `neutral` | true or false | Played on a neutral site | `neutralSite` |
| `home_points` | number | Home team's points; empty if not played yet | `homePoints` |
| `away_points` | number | Away team's points | `awayPoints` |

Rules:
- Team names must be spelled the same way every season. A team's rating carries over by its name.
- A team's league each season is taken from its regular-season games.
- Teams with no league, or a league listed in `load_games(..., independents=...)`, are rated but belong to no league.
  For college football that is "FBS Independents".
- Unplayed games (empty points) are dropped.
- Only games between two teams you want rated belong in the file. The college football script keeps FBS against FBS.
