"""Checks that the method does what it says: recovers known answers, shortcuts match full computations, shares add up."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import richardson_index as ri
from richardson_index.circuit import laplacian
from richardson_index.gaps import drop_game
from richardson_index.ratings import design, fit_gaussian
from richardson_index.upsets import game_influence

ROOT = Path(__file__).resolve().parent.parent
TOY = ROOT / "data/toy/games.csv"


def simulated_season(seed=1, leagues=4, per=12, cross=3, noise=14.0):
    """A round robin inside each league plus a few games across leagues, from known strengths."""
    rng = np.random.default_rng(seed)
    teams = [f"T{i:02d}" for i in range(leagues * per)]
    league = {t: f"L{i // per}" for i, t in enumerate(teams)}
    strength = {t: rng.normal(0, 8) + 3 * (int(league[t][1:]) - 1.5) for t in teams}
    pairs = [(a, b) for a in teams for b in teams if a < b and league[a] == league[b]]
    for t in teams:
        pairs += [(t, u) for u in rng.choice([u for u in teams if league[u] != league[t]], cross, replace=False)]
    rows = []
    for k, (h, a) in enumerate(pairs):
        m = strength[h] - strength[a] + 2.5 + rng.normal(0, noise)
        rows.append(dict(game_id=k, season=2030, week=1 + k % 12, season_type="regular", home=h, away=a,
                         home_league=league[h], away_league=league[a], neutral=False,
                         home_points=50 + m / 2, away_points=50 - m / 2))
    return ri.load_games(pd.DataFrame(rows)), strength, league


def test_ratings_recover_known_strengths():
    games, strength, _ = simulated_season()
    fit = ri.fit_seasons(games)[2030]
    r = fit.ratings().set_index("team").rating
    true = pd.Series(strength)[r.index]
    assert np.corrcoef(r, true)[0, 1] > 0.9
    assert 10 < fit.noise < 18  # the planted noise is 14


def test_league_gap_range_covers_truth_mostly():
    hits = 0
    for seed in range(20):
        games, strength, league = simulated_season(seed)
        fit = ri.fit_seasons(games)[2030]
        g = ri.league_gaps(fit, ri.league_of(games, 2030))
        s = pd.Series(strength)
        lg = pd.Series(league)
        true = {L: s[lg == L].mean() for L in set(league.values())}
        hits += sum((x.lo90 <= true[x.A] - true[x.B] <= x.hi90) for x in g.itertuples())
    assert hits / (20 * 6) > 0.8  # 90% ranges; allows for 120 draws and the prior's pull


def test_dropping_a_game_matches_a_full_refit():
    games, _, _ = simulated_season()
    fit = ri.fit_seasons(games)[2030]
    for g in (0, 17, len(fit.y) - 1):
        keep = np.arange(len(fit.y)) != g
        full, _ = fit_gaussian(fit.X[keep], fit.y[keep], fit.prior_mean, fit.prior_prec, fit.noise)
        assert np.allclose(drop_game(fit, g), full, atol=1e-8)


def test_circuit_shares_sum_to_one_and_match_the_flat_fit():
    games, _, league = simulated_season()
    res = ri.league_resistance(games, league, "L0", "L1", noise=14.0)
    assert res["connected"]
    assert res["shares"].share.sum() == pytest.approx(1.0)
    # with almost no prior, the gap's variance from a ratings fit equals noise^2 * R
    teams = sorted(set(games.home) | set(games.away))
    ix = {t: i for i, t in enumerate(teams)}
    X = design(games.home.map(ix).to_numpy(), games.away.map(ix).to_numpy(), np.ones(len(games), bool), len(teams))[:, :-1]
    _, cov = fit_gaussian(X, games.margin.to_numpy(), np.zeros(len(teams)), np.full(len(teams), 1e-8), 14.0)
    lg = np.array([league[t] for t in teams])
    c = (lg == "L0") / (lg == "L0").sum() - (lg == "L1") / (lg == "L1").sum()
    assert c @ cov @ c == pytest.approx(14.0**2 * res["R"], rel=1e-5)


def test_disconnected_leagues_are_flagged():
    games, _, league = simulated_season(cross=0)
    res = ri.league_resistance(games, league, "L0", "L1")
    assert not res["connected"] and np.isinf(res["R"])


def test_planted_tiers_are_found():
    rng = np.random.default_rng(3)
    r = np.array([20, 19.5, 10, 9.6, 9.2, 0, -0.4, -10.0])
    C = np.diag(np.full(len(r), 0.5**2))
    assert ri.complete_linkage(r + rng.normal(0, 0.05, len(r)), C) == [(0, 2), (2, 5), (5, 7), (7, 8)]


def test_credible_set_on_a_clear_and_a_tied_top():
    rng = np.random.default_rng(0)
    C = np.eye(5) * 1.0
    assert ri.credible_top(np.array([20.0, 5, 4, 3, 2]), C, rng) == 1
    assert ri.credible_top(np.array([10.0, 9.9, 9.8, 0, -1]), C, rng) == 3
    assert ri.credible_bottom(np.array([10.0, 5, 4, 3, -20]), C, rng) == 1


def test_tier_names():
    assert ri.tier_names(1) == ["whole league"]
    assert ri.tier_names(2) == ["top tier", "bottom tier"]
    assert ri.tier_names(5) == ["top tier", "second tier", "third tier", "fourth tier", "bottom tier"]


def test_upset_influence_matches_refit_without_the_game():
    games, _, _ = simulated_season()
    fit = ri.fit_seasons(games)[2030]
    infl = game_influence(fit.games, fit.prior_mean, fit.prior_prec, 15.0)
    assert len(infl) == len(fit.games) and np.isfinite(infl.influence).all()
    # brute force for one game: refit later weeks without it and rescore its teams' later games
    g = int(np.argmax(infl.later_games.to_numpy() > 0))
    sg = fit.games
    from scipy.stats import norm
    from richardson_index.upsets import log_loss
    teams = sorted(set(sg.home) | set(sg.away))
    ix = {t: i for i, t in enumerate(teams)}
    X = design(sg.home.map(ix).to_numpy(), sg.away.map(ix).to_numpy(), sg.neutral.to_numpy(), len(teams))
    y, wk, win = sg.margin.to_numpy(), sg.sort_week.to_numpy(), sg.home_win.to_numpy()
    h, a = sg.home.to_numpy(), sg.away.to_numpy()
    later = (wk > wk[g]) & ((h == h[g]) | (a == h[g]) | (h == a[g]) | (a == a[g]))
    tot = 0.0
    for w in sorted(set(wk[later])):
        use = wk < w
        out = use & (np.arange(len(sg)) != g)
        m1, c1 = fit_gaussian(X[use], y[use], fit.prior_mean, fit.prior_prec, 15.0)
        m2, c2 = fit_gaussian(X[out], y[out], fit.prior_mean, fit.prior_prec, 15.0)
        rows = later & (wk == w)
        p1 = norm.cdf(X[rows] @ m1 / np.sqrt(225 + np.einsum("ij,jk,ik->i", X[rows], c1, X[rows])))
        p2 = norm.cdf(X[rows] @ m2 / np.sqrt(225 + np.einsum("ij,jk,ik->i", X[rows], c2, X[rows])))
        tot += (log_loss(p1, win[rows]) - log_loss(p2, win[rows])).sum()
    assert infl.influence.iloc[g] == pytest.approx(tot, abs=1e-8)


def test_toy_run_reproduces_stored_answer():
    t = ri.run(ri.load_games(TOY), log=lambda *_: None)
    want = json.loads((ROOT / "tests/toy_expected.json").read_text())
    g = t["league_gaps"]
    for row in want["gaps_2026"]:
        x = g[(g.season == 2026) & (g.A == row["A"]) & (g.B == row["B"])].iloc[0]
        assert x.gap == pytest.approx(row["gap"], abs=1e-6)
        assert x.sd == pytest.approx(row["sd"], abs=1e-6)
    tt = t["tier_teams"]
    got = {L: [list(z.team) for _, z in q.groupby("tier")] for L, q in tt[tt.season == 2026].groupby("league")}
    assert got == want["tiers_2026"]
    assert set(t) == set(ri.pipeline.OUTPUTS)
