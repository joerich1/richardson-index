# Method

Notation: There are n teams in a season, ratings r (points on a neutral field), home field h, game noise sigma.

## 1. Ratings

For game g with home team i and away team j:

    margin_g = r_i - r_j + h * (1 if not neutral) + e_g,   e_g ~ Normal(0, sigma^2)

This is Massey's least-squares rating (Massey 1997). Each team's prior is Normal(m_i, tau^2):

- m_i = carry^(years since last seen) * (the team's last season-end rating);
- a team new to the data starts at the 5th percentile of last season's ratings;
- home field's prior is Normal(2.5, 2.0^2).

With X the game-by-team design matrix (+1 home, -1 away, last column home field) and P the diagonal prior precision,
the posterior is Gaussian:

    cov = (X'X / sigma^2 + P)^-1,   mean = cov (X'y / sigma^2 + P m)

As ridge regression, each team is pulled toward its starting rating with penalty (sigma / tau)^2. At sigma 15 and tau
8 that is about 3.5 games of evidence.

Seasons are fit in order. The season-end fit carried into next season uses sigma = 15. The fit reported for each
season re-estimates sigma from that season's residuals, corrected for the effective number of fitted ratings:

    sigma_hat = sd(residuals) * sqrt(N / (N - trace(X cov X') / 15^2))

**Settings** (`Settings` in `ratings.py`): carry 1.0, tau 8, sigma 15, newcomer quantile 0.05. They were chosen by a
grid search on walk-forward forecasts of FBS games. Each game was predicted from earlier games only. The settings
were tuned on 2003 to 2023 and checked on 2024 and 2025. Every setting in the grid was scored the same way.

## 2. League gaps and their range

With c the vector that averages league A's teams minus league B's, the gap is c'mean. Its range adds two variances:

- **Rating doubt:** c' cov c.
- **Linking error:** a jackknife over the bridge games, the games between a team of A or B and a team of another league.
  Leave out each bridge game k in turn and refit exactly with a rank-one update:

      cov_(-k) = cov + (cov x_k)(cov x_k)' / (sigma^2 - x_k' cov x_k)
      mean_(-k) = mean - cov_(-k) x_k (y_k - x_k' mean) / sigma^2

  The variance is (K - 1)/K * sum_k (gap_(-k) - mean gap)^2 over the K bridge games.

The 90% range is gap plus or minus 1.645 * sqrt(rating doubt + linking error). The idea of a linking error comes from
test equating, where two exams are linked through shared items. See Kolen and Brennan, *Test Equating, Scaling,
and Linking*.

**Check:** Ratings were planted from real seasons, with games simulated at three noise levels. The 90% range covered
the true gap 91% to 95% of the time in every band of direct games, including pairs that never met. Without the linking
error, coverage fell to 85% to 88%.

## 3. The schedule as a circuit

Each game is a 1-ohm wire between two teams. With L the schedule's Laplacian (games per team on the diagonal, minus one
per game between two teams off it), the effective resistance between leagues A and B is

    R = c' L+ c

with L+ the pseudoinverse. With no prior, the A-minus-B gap has variance sigma^2 R. So sigma * sqrt(R) is the doubt
the schedule alone leaves (`sd_schedule`, at sigma 15). The voltages are v = L+ c. Game g's share of the comparison is

    share_g = (v_home - v_away)^2 / R

the power its wire uses over the total. The shares sum to 1. Each is that game's share of the variance of the
schedule-only gap. If no chain of games links the two leagues, R is infinite. Then they can't be compared through the
schedule. That happened in 2020, when several leagues played only league games in the regular season.

Franceschet and Bozzo (2017) read Massey's method as a measure on the network of games. Hendrickx, Olshevsky and
Saligrama (2019) showed that effective resistance governs rating error in pairwise comparisons.

## 4. Tiers

For two teams in one league, P(i better than j) = Phi((r_i - r_j) / sqrt(var_i + var_j - 2 cov_ij)).

**Complete linkage** (the tiers in `outputs/`). Sort the league's teams best first. Start with every team alone.
Repeatedly join the two neighboring groups whose most clearly different cross pair is least clearly different. Stop
before any group would hold two teams 95% or more sure to differ. Tiers are named top tier, second tier, third tier and
so on, with the last called the bottom tier.

**Credible set** (an alternative for the top and the bottom). Draw the ratings 2,000 times from the posterior. The
credible top is the fewest top teams, in rating order, that together hold the true best team 90% of the time. The
credible bottom is the same from the bottom.

**Checks** on planted leagues with real rating noise:

- Whole-league split: 2 to 5 true tiers of random sizes, 5 to 15 points apart. Complete linkage scored an adjusted
  Rand index of 0.47 (1 = the true split, 0 = chance), the best of four locked splits tried. Smooth leagues with no
  real tiers still came out in about 4 tiers. A tier means "these teams can't be told apart", not a proven step.
- Top group: 1 to 4 equal teams planted 8 to 12 points clear. Ten methods were compared. The rule was fixed before
  the run: Recover the planted group, never group two teams 95% sure to differ, then separate cleanly. Complete
  linkage and the credible set came out level, with overlap of 0.77 and 0.76 with the planted group. Mixture models, Ward
  clustering and spectral clustering did worse.

**Comparing tiers.** For tiers with averaging vectors a and b, the gap is (a - b)'mean. Between leagues, its standard
deviation is widened by the league pair's full range over its rating-only range, so tier ranges include the linking
error. The win chance is the average over team pairs of Phi(d / sqrt(var_d + sigma^2)). Matched share compares a tier
spanning shares s1 to s2 of its league with the teams covering the same span of the other league. A team on the
edge is weighted by the part it covers. Tier membership is taken as given, so ranges leave out the doubt about which tier a
borderline team belongs to.

## 5. Does a game help later forecasts?

`upsets.game_influence` refits before each week from that season's earlier regular-season games. For each game, it
redoes every later fit without that game, with the same rank-one update, and rescores both teams' later games. The
influence is the change in log loss: Negative means keeping the game helped.

## References

- Massey, K. (1997). *Statistical Models Applied to the Rating of Sports Teams.* Honors thesis, Bluefield College.
  https://masseyratings.com/theory/massey97.pdf
- Franceschet, M. and Bozzo, E. (2017). The Massey's method for sport rating: A network science perspective.
  https://arxiv.org/abs/1701.03363
- Hendrickx, J., Olshevsky, A. and Saligrama, V. (2019). Graph resistance and learning from pairwise comparisons.
  *ICML.* https://proceedings.mlr.press/v97/hendrickx19a.html
- Kolen, M. J. and Brennan, R. L. (2014). *Test Equating, Scaling, and Linking* (3rd ed.). Springer.
