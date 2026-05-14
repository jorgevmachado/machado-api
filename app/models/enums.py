from enum import Enum


class GenderEnum(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"


class StatusEnum(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    INCOMPLETE = "INCOMPLETE"


class RoleEnum(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class PokemonStatusEnum(str, Enum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"


class ExplorationEventTypeEnum(str, Enum):
    WILD_POKEMON = "WILD_POKEMON"
    POKEBALLS = "POKEBALLS"
