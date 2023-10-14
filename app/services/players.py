from pony.orm import db_session
from app.models import Player, Card
from app.services.exceptions import *
from app.services.mixins import DBSessionMixin

class PlayersService(DBSessionMixin):
    @db_session
    def connect_player(self, sent_token : str, actual_sid : str):
        expected_player = Player.get(token=sent_token)
        if expected_player is None:
            raise InvalidTokenException()
        # habria que ver si se estaba usando ese jugador, levantar exepcion y en su handler matar la coneccion vieja
        # if expected_player.sid is not None:
        # raise UsedTokenException()
        expected_player.sid = actual_sid
    
    @db_session
    def disconnect_player(self, actual_sid : str):
        expected_player = Player.get(sid=actual_sid)
        if expected_player is None:
            raise InvalidSidException()
        (expected_player.playing).players.remove(expected_player)
        expected_player.delete()
        #falta borrar el player de la base de datos

    @db_session
    def is_host(self, actual_sid : str):
        expected_player = Player.get(sid=actual_sid)
        if expected_player is None:
            raise InvalidSidException()
        return (expected_player.is_host)

    @db_session
    def has_card(self, player : Player, card : Card):
        return card in player.hand

    def get_name(self, sent_sid : str):
        player = Player.get(sid = sent_sid)
        if player is None:
            raise InvalidSidException()
        return player.name