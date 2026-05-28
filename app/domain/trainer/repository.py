from sqlalchemy.orm import selectinload

from app.core.repository import BaseRepository
from app.models import OwnedPokemon, Pokemon, Trainer, Type


class TrainerRepository(BaseRepository[Trainer]):
    model = Trainer
    relations = (
        selectinload(Trainer.owned_pokemons)
        .selectinload(OwnedPokemon.pokemon)
        .selectinload(Pokemon.moves),
        selectinload(Trainer.owned_pokemons)
        .selectinload(OwnedPokemon.pokemon)
        .selectinload(Pokemon.abilities),
        selectinload(Trainer.owned_pokemons)
        .selectinload(OwnedPokemon.pokemon)
        .selectinload(Pokemon.growth_rate),
        selectinload(Trainer.owned_pokemons)
        .selectinload(OwnedPokemon.pokemon)
        .selectinload(Pokemon.types)
        .selectinload(Type.strengths),
        selectinload(Trainer.owned_pokemons)
        .selectinload(OwnedPokemon.pokemon)
        .selectinload(Pokemon.types)
        .selectinload(Type.weaknesses),
        selectinload(Trainer.owned_pokemons)
        .selectinload(OwnedPokemon.pokemon)
        .selectinload(Pokemon.evolutions),
        selectinload(Trainer.owned_pokemons)
        .selectinload(OwnedPokemon.pokemon)
        .selectinload(Pokemon.encounters),
    )
