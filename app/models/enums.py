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


class BattleSessionStatusEnum(str, Enum):
    ACTIVE = "ACTIVE"
    WON = "WON"
    LOST = "LOST"
    FLED = "FLED"


class BattleActorEnum(str, Enum):
    TRAINER = "TRAINER"
    WILD = "WILD"


class BattleActionTypeEnum(str, Enum):
    USE_MOVE = "USE_MOVE"
    SWITCH = "SWITCH"
    FLEE = "FLEE"
    AUTO_RESPONSE = "AUTO_RESPONSE"


class BattleLogTypeEnum(str, Enum):
    SESSION_STARTED = "SESSION_STARTED"
    MOVE_USED = "MOVE_USED"
    DAMAGE_DEALT = "DAMAGE_DEALT"
    SWITCHED = "SWITCHED"
    FLED = "FLED"
    SESSION_FINISHED = "SESSION_FINISHED"
