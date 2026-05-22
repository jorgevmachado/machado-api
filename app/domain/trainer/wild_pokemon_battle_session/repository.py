from app.domain.trainer.battle.repository import BattleSessionRepository


class WildPokemonBattleSessionRepository(BattleSessionRepository):
    """Deprecated compatibility shim over the neutral battle session repository."""
