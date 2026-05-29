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


class TrainerLogEventEnum(str, Enum):
    WON = "WON"
    LOST = "LOST"
    FLEE = "FLEE"
    SHOWN = "SHOWN"
    MOVED = "MOVED"
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    DELETED = "DELETED"
    CAPTURED = "CAPTURED"
    DISCOVERED = "DISCOVERED"

class LogStatusEnum(str, Enum):
    INFO = "INFO"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"

class LogTypeEnum(str, Enum):
    PARTY = "PARTY"
    BATTLE = "BATTLE"
    POKEDEX = "POKEDEX"
    TRAINER = "TRAINER"
    POKEMON = "POKEMON"
    ENCOUNTER = "ENCOUNTER"
    