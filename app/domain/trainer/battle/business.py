from app.models import OwnedPokemonMove, TrainerParty, PokedexEntry


def build_trainer_party_snapshot(party: TrainerParty) -> list[dict]:
    owned_pokemon = party.owned_pokemon
    return [
        {
            "slot": party.slot,
            "name": owned_pokemon.name,
            "moves": [build_snapshot_move(move) for move in owned_pokemon.moves],
            "speed": owned_pokemon.speed,
            "level": owned_pokemon.level,
            "max_hp": owned_pokemon.max_hp,
            "attack": owned_pokemon.attack,
            "defense": owned_pokemon.defense,
            "nickname": owned_pokemon.nickname,
            "is_active": party.is_active,
            "current_hp": owned_pokemon.hp,
            "special_attack": owned_pokemon.special_attack,
            "special_defense": owned_pokemon.special_defense,
            "owned_pokemon_id": str(owned_pokemon.id),
        }
    ]


def build_snapshot_move(move: OwnedPokemonMove) -> dict:
    return {
        "id": str(move.id),
        "pp": move.pp,
        "type": move.pokemon_move.type,
        "name": move.pokemon_move.name,
        "power": move.pokemon_move.power,
        "max_pp": move.max_pp,
        "accuracy": move.pokemon_move.accuracy,
        "pokemon_move_id": str(move.pokemon_move_id),
    }


def build_wild_pokemon_snapshot(wild_pokemon: PokedexEntry) -> dict:
    return {
        "id": str(wild_pokemon.id),
        "name": wild_pokemon.pokemon.name,
        "moves": [
            {
                "id": str(move.id),
                "pp": move.pp,
                "name": move.name,
                "type": move.type,
                "power": move.power,
                "max_pp": move.pp,
                "accuracy": move.accuracy,
            }
            for move in wild_pokemon.pokemon.moves[:4]
        ],
        "level": wild_pokemon.level,
        "speed": wild_pokemon.speed,
        "attack": wild_pokemon.attack,
        "max_hp": wild_pokemon.hp,
        "defense": wild_pokemon.defense,
        "current_hp": wild_pokemon.hp,
        "pokemon_id": str(wild_pokemon.pokemon_id),
        "capture_rate": wild_pokemon.pokemon.capture_rate,
        "special_attack": wild_pokemon.special_attack,
        "special_defense": wild_pokemon.special_defense,
    }
