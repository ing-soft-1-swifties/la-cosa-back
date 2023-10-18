
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
    def __init__(self, msg):
        self.msg = msg

class CardNotInPlayerHandExeption(Exception):
    pass

class PlayerNotInTurn(Exception):
    pass

class InvalidDataException(Exception):
    pass

class InvalidExchangeParticipants(Exception):
    pass

class RoleCardExchange(Exception):
    pass

class InvalidCardExchange(Exception):
    pass