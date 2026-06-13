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
    EXPLORED = "CREATED"
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


class BattleActorEnum(str, Enum):
    WILD = "WILD"
    TRAINER = "TRAINER"


class BattleSessionStatusEnum(str, Enum):
    ACTIVE = "ACTIVE"
    ESCAPED = "ESCAPED"
    CAPTURED = "CAPTURED"
    TRAINER_DEFEATED = "TRAINER_DEFEATED"
    WILD_POKEMON_DEFEATED = "WILD_POKEMON_DEFEATED"


class BattleActionTypeEnum(str, Enum):
    FLEE = "FLEE"
    SWITCH = "SWITCH"
    CAPTURE = "CAPTURE"
    USE_MOVE = "USE_MOVE"
    AUTO_RESPONSE = "AUTO_RESPONSE"


class BattleLogTypeEnum(str, Enum):
    ESCAPED = "ESCAPED"
    SWITCHED = "SWITCHED"
    MOVE_USED = "MOVE_USED"
    DAMAGE_DEALT = "DAMAGE_DEALT"
    CAPTURE_FAILED = "CAPTURE_FAILED"
    SESSION_STARTED = "SESSION_STARTED"
    CAPTURE_ATTEMPT = "CAPTURE_ATTEMPT"
    CAPTURE_SUCCESS = "CAPTURE_SUCCESS"
    SESSION_FINISHED = "SESSION_FINISHED"


class ExplorationEventTypeEnum(str, Enum):
    POKEBALLS = "POKEBALLS"
    WILD_POKEMON = "WILD_POKEMON"
