
import enum

class StatusCode(enum.Enum):
    SUCCESS = (0, "")
    NOT_ENOUGH_PLAYERS = 1


class DuplicatePlayerNameException(Exception):
    pass

class InvalidRoomException(Exception):
    pass

class InvalidTokenException(Exception):
    pass

class InvalidSidException(Exception):
    pass

class InvalidCidException(Exception):
    pass

class InvalidCardException(Exception):
    pass

class NotOwnerExeption(Exception):
    pass

class NotInLobbyException(Exception):
    pass

class NotEnoughPlayersException(Exception):
    pass

class TooManyPlayersException(Exception):
    pass

class InvalidAccionException(Exception):
    pass
class CardNotInPlayerHandExeption(Exception):
    pass

class PlayerNotInTurn(Exception):
    pass