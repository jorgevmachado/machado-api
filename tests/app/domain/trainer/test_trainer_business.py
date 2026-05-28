from app.domain.trainer.business import (
    DEFAULT_TRAINER_CAPTURE_RATE,
    DEFAULT_TRAINER_POKEBALLS,
    STARTER_POKEMON_NAMES,
)


def test_trainer_business_constants() -> None:
    assert STARTER_POKEMON_NAMES == {"bulbasaur", "charmander", "squirtle"}
    assert DEFAULT_TRAINER_POKEBALLS == 1
    assert DEFAULT_TRAINER_CAPTURE_RATE == 75
