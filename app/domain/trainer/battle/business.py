from app.models import OwnedPokemonMove, TrainerParty, PokedexEntry


def build_trainer_party_snapshot(party: TrainerParty) -> list[dict]:
    owned_pokemon = party.owned_pokemon
    return [
        {
            "id": str(party.id),
            "hp": owned_pokemon.hp,
            "slot": party.slot,
            "name": owned_pokemon.name,
            "moves": [build_snapshot_move(move) for move in owned_pokemon.moves],
            "level": owned_pokemon.level,
            "speed": owned_pokemon.speed,
            "max_hp": owned_pokemon.max_hp,
            "attack": owned_pokemon.attack,
            "defense": owned_pokemon.defense,
            "nickname": owned_pokemon.nickname,
            "experience": owned_pokemon.experience,
            "is_active": party.is_active,
            "pokemon_id": str(owned_pokemon.pokemon_id),
            "capture_rate": owned_pokemon.pokemon.capture_rate,
            "special_attack": owned_pokemon.special_attack,
            "special_defense": owned_pokemon.special_defense,
            "owned_pokemon_id": str(owned_pokemon.id),
        }
    ]


def build_snapshot_move(move: OwnedPokemonMove) -> dict:
    return {
        "id": str(move.id),
        "pp": move.pp,
        "name": move.pokemon_move.name,
        "type": move.pokemon_move.type,
        "power": move.pokemon_move.power,
        "max_pp": move.max_pp,
        "accuracy": move.pokemon_move.accuracy,
        "pokemon_move_id": str(move.pokemon_move_id),
    }


def build_wild_pokemon_snapshot(wild_pokemon: PokedexEntry) -> dict:
    return {
        "id": str(wild_pokemon.id),
        "hp": wild_pokemon.hp,
        "slot": 0,
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
                "pokemon_move_id": str(move.id),
            }
            for move in wild_pokemon.pokemon.moves[:4]
        ],
        "level": wild_pokemon.level,
        "speed": wild_pokemon.speed,
        "max_hp": wild_pokemon.hp,
        "attack": wild_pokemon.attack,
        "defense": wild_pokemon.defense,
        "nickname": wild_pokemon.pokemon.name,
        "is_active": True,
        "experience": wild_pokemon.experience,
        "pokemon_id": str(wild_pokemon.pokemon_id),
        "capture_rate": wild_pokemon.pokemon.capture_rate,
        "special_attack": wild_pokemon.special_attack,
        "special_defense": wild_pokemon.special_defense,
    }
