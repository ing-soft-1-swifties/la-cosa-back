
import enum

class StatusCode(enum.Enum):
    SUCCESS = (0, "")
    NOT_ENOUGH_PLAYERS = 1


class DuplicatePlayerNameException(Exception):
    pass

class InvalidRoomException(Exception):
    pass
