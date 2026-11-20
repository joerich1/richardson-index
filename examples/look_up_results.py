"""Look things up in the published results, with no key and no run: SEC against the Big Ten in 2026.

    python examples/look_up_results.py
"""
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parent.parent / "outputs"

gaps = pd.read_csv(OUT / "league_gaps.csv")
g = gaps[(gaps.season == 2026) & (gaps.A == "Big Ten") & (gaps.B == "SEC")].iloc[0]
print(f"2026: the SEC's average team is {-g.gap:.1f} points better than the Big Ten's "
      f"(90% range {-g.hi90:.1f} to {-g.lo90:.1f}), resting on {g.bridge_games} games against other leagues.")

tiers = pd.read_csv(OUT / "tiers.csv")
for league in ("SEC", "Big Ten"):
    print(f"\n{league}")
    for t in tiers[(tiers.season == 2026) & (tiers.league == league)].itertuples():
        print(f"  {t.tier_name:12s} {t.mean:+5.1f}  {t.teams}")

vs = pd.read_csv(OUT / "tier_vs_tier.csv")
q = vs[(vs.season == 2026) & (vs.A == "SEC") & (vs.B == "Big Ten") & (vs.tier_A == vs.tier_B)]
print("\nSEC tier against the same Big Ten tier")
for t in q.itertuples():
    print(f"  {t.tier_name_A:12s} {t.gap:+5.1f} ({t.lo90:+.1f} to {t.hi90:+.1f})  {t.verdict.replace('A better', 'SEC better').replace('B better', 'Big Ten better')}")
