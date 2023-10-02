from fastapi import HTTPException
from pony.orm import db_session
from pony.orm.dbapiprovider import uuid4
from app.models import Player, Room
from app.schemas import NewRoomSchema
from app.services.exceptions import DuplicatePlayerNameException, InvalidRoomException
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
            

        new_player = Player(name = name, token=token)

        expected_room.players.add(new_player)

        return token

    @db_session
    def create_room(self, room: NewRoomSchema) -> str:
        # crear instancia de jugador y partida nueva que lo referencie

        token = str(uuid4())

        host = Player(name=room.host_name, token=token)
        

        Room(
                min_players = room.min_players, 
                max_players = room.max_players, 
                host = host,
                status=0, 
                is_private=room.is_private,
                name = room.room_name
        )

        self.db.commit()

        return token
