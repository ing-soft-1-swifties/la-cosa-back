from pony.orm import db_session
from app.models import Player
from app.schemas import NewRoomSchema
from app.services.mixins import DBSessionMixin

class RoomsService(DBSessionMixin):

    def join_player(self, name: str, room_id: int):
        # TODO: validar partida y union del jugador

        return "dummy_token"

    def create_room(self, room: NewRoomSchema = NewRoomSchema(room_name="room", host_name="host", min_players=4, max_players=12)):
        # TODO: crear instancia de jugador y partida nueva que lo referencie

        return "dummy_token"
