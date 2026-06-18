from pydantic import BaseModel


class AttributesCalculatedSchema(BaseModel):
    hp: int
    level: int
    speed: int
    attack: int
    max_hp: int
    defense: int
    level_up: bool
    experience: int
    special_attack: int
    special_defense: int
