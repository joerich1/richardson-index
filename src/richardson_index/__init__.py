"""The Richardson Index: compare sports leagues that rarely play each other, with an honest range."""
from .circuit import league_resistance
from .compare import compare_tiers
from .data import league_of, load_games, through_week
from .gaps import league_gaps
from .pipeline import run
from .ratings import Settings, fit_seasons
from .tiers import complete_linkage, credible_bottom, credible_top, league_tiers, tier_names
from .upsets import game_influence

__version__ = "1.0.0"
__all__ = ["Settings", "compare_tiers", "complete_linkage", "credible_bottom", "credible_top", "fit_seasons",
           "game_influence", "league_gaps", "league_of", "league_resistance", "league_tiers", "load_games", "run", "through_week",
           "tier_names"]
