from pony.orm import db_session
from pony.orm.dbapiprovider import uuid4
from app.models import Player, Room
from app.schemas import NewRoomSchema
from app.services.mixins import DBSessionMixin

class RoomsService(DBSessionMixin):

    def join_player(self, name: str, room_id: int):
        # TODO: validar partida y union del jugador

        return "dummy_token"

    @db_session
    def create_room(self, room: NewRoomSchema):
        # TODO: crear instancia de jugador y partida nueva que lo referencie

        host = Player(name=room.host_name, token=str(uuid4))

        new_room = Room(
                min_players = room.min_players, 
                max_players = room.max_players, 
                host = host.id, 
                status=0, 
                is_private=room.is_private,
                name = room.room_name
        )

        self.db.commit()

        return host.token
