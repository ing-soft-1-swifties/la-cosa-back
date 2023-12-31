from pony.orm import db_session
from app.models import Player, Card
from app.services.exceptions import *
from app.services.mixins import DBSessionMixin

class PlayersService(DBSessionMixin):

    def get_player_by_pid(self, pid: str) -> Player:
        return Player.get(id=pid)

    def get_player_by_sid(self, sid: str) -> Player:
        return Player.get(sid=sid)

    @db_session
    def connect_player(self, sent_token: str, actual_sid: str):
        player = Player.get(token=sent_token)

        if player is None:
            raise InvalidTokenException()
        
        # habria que ver si se estaba usando ese jugador, levantar exepcion y en su handler matar la coneccion vieja
        # if expected_player.sid is not None:
        #   raise UsedTokenException()
        player.sid = actual_sid
        return [
            {
                "name": "on_room_new_player",
                "body": {},
                "broadcast":True
            }
        ]
    
    @db_session
    def disconnect_player(self, sent_sid : str):

        # obtenemos el jugador
        player = Player.get(sid=sent_sid)

        if player is None:
            raise InvalidSidException()

        # obtenemos la room y eliminamos al jugador
        from .rooms import RoomsService
        rs = RoomsService(self.db)
        player_sids = rs.get_players_sid(sent_sid)
        player_sids.remove(player.sid)
        room = player.playing
        room.players.remove(player)
        player.delete()

        return [
            {
                "name": "on_room_left_player",
                "body": {},
                "sid_list" : player_sids
            }
        ]

    @db_session
    def is_host(self, actual_sid : str):
        expected_player = Player.get(sid=actual_sid)
        if expected_player is None:
            raise InvalidSidException()
        return (expected_player.is_host)

    @db_session
    def has_card(self, player : Player, card : Card):
        return card in player.hand

    @db_session
    def get_name(self, sent_sid : str):
        player = Player.get(sid = sent_sid)
        if player is None:
            raise InvalidSidException()
        return player.name