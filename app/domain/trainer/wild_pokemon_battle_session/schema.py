from app.domain.trainer.battle.schema import (
    BattleLogSchema,
    BattleMoveSchema,
    BattleSessionSchema,
    BattleSideSchema,
    BattleTurnSchema,
    SwitchBattlePokemonSchema,
    UseBattleMoveSchema,
)


class WildPokemonBattleSessionSchema(BattleSessionSchema):
    """Deprecated compatibility shim over the neutral battle session schema."""
