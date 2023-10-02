from fastapi import HTTPException
from pony.orm import db_session
from pony.orm.dbapiprovider import uuid4
from app.models import Player, Room
from app.schemas import NewRoomSchema
#from app.services.exceptions import DuplicatePlayerNameException, InvalidRoomException
from app.services.exceptions import *
from app.services.mixins import DBSessionMixin


class RoomsService(DBSessionMixin):

    @db_session
    def join_player(self, name: str, room_id: int):
        # TODO: validar partida y union del jugador
        
        expected_room = Room.get(id=room_id)
        if expected_room is None:
            raise InvalidRoomException()

        token = str(uuid4())

        if expected_room.players.select(lambda player : player.name == name).count() > 0:
            raise DuplicatePlayerNameException()
            

        new_player = Player(name = name, token=token, playing=expected_room, is_host = False)

        expected_room.players.add(new_player)

        return token

    @db_session
    def create_room(self, room: NewRoomSchema) -> str:
        # crear instancia de jugador y partida nueva que lo referencie
        token = str(uuid4())
        new_room = Room(
                min_players = room.min_players, 
                max_players = room.max_players, 
                status=0, 
                is_private=room.is_private,
                name = room.room_name
        )
        Player(name=room.host_name, token=token, playing=new_room, is_host=True)
        self.db.commit()
        return token

    @db_session
    def get_players_sid(self, actual_sid):
        expected_player = Player.get(sid = actual_sid)
        expected_room = Room.get(lambda room : room.players.__contains__(expected_player.id))
        if expected_room is None:
            raise InvalidRoomException()
        return [(Player.get(id = player_id)).sid for player_id in expected_room.players()]

    @db_session
    def start_game(self, actual_sid : str):
        #si el jugador es propietario de una partida y esta no esta iniciada
        #dadas las condiciones para que se pueda iniciar una partida, esta se inicia
        expected_player = Player.get(sid = actual_sid)
        if expected_player is None:
            raise InvalidSidException()
        if expected_player.is_host == False:
            raise NotOwnerExeption()
        # expected_room = Room.get(id = expected_player.hosting)
        expected_room = Room.get(lambda room : room.players.__contains__(expected_player.id))
        if expected_room is None:
            raise InvalidRoomException()
        if expected_room.status != 0:   #not in lobby
            raise NotInLobbyException()
        if len(expected_room.playes) < expected_room.min_players:
            raise NotEnoughPlayersException()
        if len(expected_room.players) > expected_room.max_players:
            raise TooManyPlayersException()
        expected_room.status = 1    #in game
        #capaz falta algo