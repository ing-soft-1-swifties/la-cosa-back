from pony.orm import db_session
from app.models import Player
# from app.schemas import NewRoomSchema
from app.services.exceptions import InvalidTokenException
from app.services.mixins import DBSessionMixin

class PlayersService(DBSessionMixin):
    @db_session
    def connect_player(self, sent_token : str, actual_sid : str):
        # TODO: verificar que el token este linkeado a un player, 
        # linkear player a el sid de la conexion
        expected_player = Player.get(token=sent_token)
        if expected_player is None:
            raise InvalidTokenException()
        # habria que ver si se estaba usando ese jugador, levantar exepcion y en su handler matar la coneccion vieja
        # if expected_player.sid is not None:
        # raise UsedTokenException()
        expected_player.sid = actual_sid
    