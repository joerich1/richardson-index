"""Tier against tier, within a league and between leagues, and every tier on one national ladder.

For two tiers: the gap between their average teams, a 90% range, the chance the first is better, a verdict at 95%,
and the neutral-field win chance of a random team from one against a random team from the other.
Between leagues the range is widened by that league pair's linking error (the league gap's full range divided by its
rating-only range), so tier comparisons are as honest as the league gap itself.

Leagues split into different numbers of tiers, so each tier is also compared with the same share of the other league
("matched share"): a tier holding a league's top 2 of 16 teams is set against the other league's top 12.5%,
counting a team that straddles the edge by the part it covers.
Caveat: tier membership is taken as given, so ranges leave out the doubt about which tier a borderline team is in.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm

from .ratings import SeasonFit

Z90 = norm.ppf(0.95)


def _verdict(p: float, sure: float = 0.95) -> str:
    return "A better" if p >= sure else "B better" if p <= 1 - sure else "too close to call"


def widen_factors(gaps: pd.DataFrame) -> tuple[dict, float]:
    """Per league pair, full range / rating-only range (from ``gaps.league_gaps``); plus the median for missing pairs."""
    f = gaps.sd / gaps.sd_rating
    d = {}
    for (A, B), x in zip(zip(gaps.A, gaps.B), f):
        d[(A, B)] = d[(B, A)] = float(x)
    return d, float(f.median())


def compare_tiers(fit: SeasonFit, tiers: pd.DataFrame, gaps: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """One season's tier summaries, ladder, tier-against-tier grid and matched-share comparisons."""
    n, ix, mean, cov, sig = fit.n, fit.index, fit.mean[:fit.n], fit.cov[:fit.n, :fit.n], fit.noise
    wd, wmed = widen_factors(gaps)
    T = []
    for (L, k), q in tiers.groupby(["league", "tier"]):
        idx = [ix[t] for t in q.sort_values("rank").team]
        c = np.zeros(n)
        c[idx] = 1 / len(idx)
        T.append(dict(season=fit.season, league=L, tier=int(k), tier_name=q.tier_name.iloc[0], n=len(idx),
                      teams=", ".join(q.sort_values("rank").team), mean=float(c @ mean), sd=float(np.sqrt(c @ cov @ c)),
                      c=c, idx=idx))
    summary = pd.DataFrame([{k: v for k, v in t.items() if k not in ("c", "idx")} for t in T])
    lad = sorted(T, key=lambda t: -t["mean"])
    ladder = pd.DataFrame([dict(season=fit.season, position=p + 1, league=t["league"], tier=t["tier"], tier_name=t["tier_name"],
                                n=t["n"], mean=t["mean"], lo90=t["mean"] - Z90 * t["sd"], hi90=t["mean"] + Z90 * t["sd"],
                                teams=t["teams"]) for p, t in enumerate(lad)])
    pairs = []
    for a in T:
        for b in T:
            if a is b:
                continue
            same = a["league"] == b["league"]
            w = 1.0 if same else wd.get((a["league"], b["league"]), wmed)
            c = a["c"] - b["c"]
            gap = float(c @ mean)
            sd = float(np.sqrt(c @ cov @ c)) * w
            p = float(norm.cdf(gap / sd))
            ia, ib = np.array(a["idx"]), np.array(b["idx"])
            d = mean[ia][:, None] - mean[ib][None, :]
            vd = cov[ia, ia][:, None] + cov[ib, ib][None, :] - 2 * cov[np.ix_(ia, ib)]
            pairs.append(dict(season=fit.season, A=a["league"], tier_A=a["tier"], tier_name_A=a["tier_name"], nA=a["n"],
                              B=b["league"], tier_B=b["tier"], tier_name_B=b["tier_name"], nB=b["n"], same_league=same,
                              gap=gap, lo90=gap - Z90 * sd, hi90=gap + Z90 * sd, p_A_better=p,
                              win_chance_A=float(norm.cdf(d / np.sqrt(vd * w**2 + sig**2)).mean()), verdict=_verdict(p)))
    order = {L: sorted([ix[t] for t in q.team], key=lambda i: -mean[i]) for L, q in tiers.groupby("league")}
    matched = []
    for a in T:
        nA = len(order[a["league"]])
        r0 = min(order[a["league"]].index(i) for i in a["idx"])
        lo_s, hi_s = r0 / nA, (r0 + a["n"]) / nA
        for B, ob in sorted(order.items()):
            if B == a["league"]:
                continue
            nB = len(ob)
            wts = np.array([max(0.0, min(hi_s * nB, j + 1) - max(lo_s * nB, j)) for j in range(nB)])
            cb = np.zeros(n)
            cb[ob] = wts / wts.sum()
            w = wd.get((a["league"], B), wmed)
            c = a["c"] - cb
            gap = float(c @ mean)
            sd = float(np.sqrt(c @ cov @ c)) * w
            p = float(norm.cdf(gap / sd))
            matched.append(dict(season=fit.season, A=a["league"], tier_A=a["tier"], tier_name_A=a["tier_name"], nA=a["n"],
                                share_from=lo_s, share_to=hi_s, B=B,
                                B_teams_covered=", ".join(fit.teams[ob[j]] for j in range(nB) if wts[j] > 0),
                                B_equivalent_teams=float(wts.sum()), gap=gap, lo90=gap - Z90 * sd, hi90=gap + Z90 * sd,
                                p_A_better=p, verdict=_verdict(p)))
    return dict(tiers=summary, ladder=ladder, tier_vs_tier=pd.DataFrame(pairs), matched_share=pd.DataFrame(matched))
