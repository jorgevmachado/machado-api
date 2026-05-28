from app.domain.trainer.encounter.repository import TrainerEncounterRepository
from app.domain.trainer.owned_pokemon.move.repository import OwnedPokemonMoveRepository
from app.domain.trainer.owned_pokemon.repository import OwnedPokemonRepository
from app.domain.trainer.pokedex.pokedex_entry.repository import PokedexEntryRepository
from app.domain.trainer.pokedex.repository import PokedexRepository
from app.domain.trainer.repository import TrainerRepository
from app.models import (
    OwnedPokemon,
    OwnedPokemonMove,
    Pokedex,
    PokedexEntry,
    Trainer,
    TrainerEncounter,
)


def test_trainer_repositories_expose_expected_models() -> None:
    assert TrainerRepository.model is Trainer
    assert TrainerEncounterRepository.model is TrainerEncounter
    assert OwnedPokemonRepository.model is OwnedPokemon
    assert OwnedPokemonMoveRepository.model is OwnedPokemonMove
    assert PokedexRepository.model is Pokedex
    assert PokedexEntryRepository.model is PokedexEntry
