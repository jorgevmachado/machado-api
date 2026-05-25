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
    ESCAPED = "ESCAPED"
    CAPTURED = "CAPTURED"
    WILD_POKEMON_DEFEATED = "WILD_POKEMON_DEFEATED"
    TRAINER_DEFEATED = "TRAINER_DEFEATED"


class BattleActorEnum(str, Enum):
    TRAINER = "TRAINER"
    WILD = "WILD"


class BattleActionTypeEnum(str, Enum):
    USE_MOVE = "USE_MOVE"
    SWITCH = "SWITCH"
    FLEE = "FLEE"
    CAPTURE = "CAPTURE"
    AUTO_RESPONSE = "AUTO_RESPONSE"


class BattleLogTypeEnum(str, Enum):
    SESSION_STARTED = "SESSION_STARTED"
    MOVE_USED = "MOVE_USED"
    DAMAGE_DEALT = "DAMAGE_DEALT"
    SWITCHED = "SWITCHED"
    ESCAPED = "ESCAPED"
    CAPTURE_ATTEMPT = "CAPTURE_ATTEMPT"
    CAPTURE_SUCCESS = "CAPTURE_SUCCESS"
    CAPTURE_FAILED = "CAPTURE_FAILED"
    SESSION_FINISHED = "SESSION_FINISHED"


class BattleCaptureOutcomeEnum(str, Enum):
    CAPTURED = "CAPTURED"
    FAILED_CHANCE = "FAILED_CHANCE"
    INELIGIBLE_CAPTURE_RATE = "INELIGIBLE_CAPTURE_RATE"
