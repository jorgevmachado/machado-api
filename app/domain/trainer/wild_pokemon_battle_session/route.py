from app.domain.trainer.battle.route import (
    Session,
    flee_battle,
    get_active_battle,
    list_battle_logs,
    router,
    switch_battle_pokemon,
    use_battle_move,
)
from app.domain.trainer.wild_pokemon_battle_session.service import (
    WildPokemonBattleSessionService,
)


def get_wild_pokemon_battle_session_service(
    session: Session,
) -> WildPokemonBattleSessionService:
    return WildPokemonBattleSessionService.from_session(session)
