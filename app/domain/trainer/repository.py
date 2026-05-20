from __future__ import annotations

from sqlalchemy.orm import selectinload

from app.core.repository.base import BaseRepository
from app.models import Pokedex, Pokemon, PokemonType, MyPokemon
from app.models.trainer import Trainer


class TrainerRepository(BaseRepository[Trainer]):
    model = Trainer
    relations = (
        selectinload(Trainer.pokedex),
        selectinload(Trainer.pokedex)
        .selectinload(Pokedex.pokemon)
        .selectinload(Pokemon.moves),
        selectinload(Trainer.pokedex)
        .selectinload(Pokedex.pokemon)
        .selectinload(Pokemon.abilities),
        selectinload(Trainer.pokedex)
        .selectinload(Pokedex.pokemon)
        .selectinload(Pokemon.growth_rate),
        selectinload(Trainer.pokedex)
        .selectinload(Pokedex.pokemon)
        .selectinload(Pokemon.types)
        .selectinload(PokemonType.strengths),
        selectinload(Trainer.pokedex)
        .selectinload(Pokedex.pokemon)
        .selectinload(Pokemon.types)
        .selectinload(PokemonType.weaknesses),
        selectinload(Trainer.pokedex)
        .selectinload(Pokedex.pokemon)
        .selectinload(Pokemon.evolutions),
        selectinload(Trainer.my_pokemons),
        selectinload(Trainer.my_pokemons)
        .selectinload(MyPokemon.pokemon)
        .selectinload(Pokemon.moves),
        selectinload(Trainer.my_pokemons)
        .selectinload(MyPokemon.pokemon)
        .selectinload(Pokemon.abilities),
        selectinload(Trainer.my_pokemons)
        .selectinload(MyPokemon.pokemon)
        .selectinload(Pokemon.growth_rate),
        selectinload(Trainer.my_pokemons)
        .selectinload(MyPokemon.pokemon)
        .selectinload(Pokemon.types)
        .selectinload(PokemonType.strengths),
        selectinload(Trainer.my_pokemons)
        .selectinload(MyPokemon.pokemon)
        .selectinload(Pokemon.types)
        .selectinload(PokemonType.weaknesses),
        selectinload(Trainer.my_pokemons)
        .selectinload(MyPokemon.pokemon)
        .selectinload(Pokemon.evolutions),
        selectinload(Trainer.my_pokemons)
        .selectinload(MyPokemon.pokemon)
        .selectinload(Pokemon.encounters),
    )
