from typing import Any

from pydantic import BaseModel, ConfigDict


class NamedExternalResourceSchema(BaseModel):
    name: str
    url: str


class PokemonExternalListSchema(BaseModel):
    count: int | None = None
    next: str | None = None
    previous: str | None = None
    results: list[NamedExternalResourceSchema] = []


class PokeApiPayloadSchema(BaseModel):
    model_config = ConfigDict(extra="allow")


class PokemonImagesExternalSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    back_shiny: str | None
    back_female: str | None
    front_shiny: str | None
    back_default: str | None
    front_female: str | None
    front_default: str | None
    back_shiny_female: str | None
    front_shiny_female: str | None


class PokemonImagesOtherExternalSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    home: PokemonImagesExternalSchema | None = None
    showdown: PokemonImagesExternalSchema | None = None
    dream_world: PokemonImagesExternalSchema | None = None
    official_artwork: PokemonImagesExternalSchema | None = None


class PokemonSpritesExternalSchema(PokemonImagesExternalSchema):
    model_config = ConfigDict(extra="allow")

    other: PokemonImagesOtherExternalSchema | None = None
    versions: dict | None = None


class PokemonExternalSchema(PokeApiPayloadSchema):
    id: int
    name: str
    sprites: dict[str, Any] | None = None


class PokemonExternalSpeciesSchema(PokeApiPayloadSchema):
    id: int
    name: str


class PokemonExternalEffectEntrySchema(BaseModel):
    effect: str
    language: NamedExternalResourceSchema
    short_effect: str


class PokemonExternalFlavorTextEntrySchema(BaseModel):
    flavor_text: str
    language: NamedExternalResourceSchema
    version_group: NamedExternalResourceSchema


class PokemonExternalMoveSchema(PokeApiPayloadSchema):
    id: int
    pp: int
    name: str
    type: NamedExternalResourceSchema
    power: int | None = None
    target: NamedExternalResourceSchema
    priority: int
    accuracy: int | None = None
    damage_class: NamedExternalResourceSchema
    effect_chance: int | None = None
    effect_entries: list[PokemonExternalEffectEntrySchema] = []
    flavor_text_entries: list[PokemonExternalFlavorTextEntrySchema] = []


class PokemonExternalTypeSchema(PokeApiPayloadSchema):
    id: int
    name: str
    sprites: dict[str, Any] | None = None
    damage_relations: dict[str, Any] | None = None
    move_damage_class: NamedExternalResourceSchema | None = None


class PokemonExternalDescriptionSchema(BaseModel):
    language: NamedExternalResourceSchema
    description: str


class PokemonExternalMoveDamageClassSchema(PokeApiPayloadSchema):
    id: int
    name: str
    descriptions: list[PokemonExternalDescriptionSchema] = []


class PokemonExternalAbilitySchema(PokeApiPayloadSchema):
    id: int
    name: str
    effect_entries: list[PokemonExternalEffectEntrySchema] = []
    flavor_text_entries: list[PokemonExternalFlavorTextEntrySchema] = []


class PokemonExternalGrowthRateSchema(PokeApiPayloadSchema):
    id: int
    name: str
    descriptions: list[PokemonExternalDescriptionSchema] = []


class PokemonExternalEvolutionSchema(PokeApiPayloadSchema):
    id: int | None = None


class PokemonExternalEncounterSchema(PokeApiPayloadSchema):
    pass
