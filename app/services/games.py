from fastapi import HTTPException
from pony.orm import db_session
from pony.orm.dbapiprovider import uuid4
from app.models import Player, Room
from app.schemas import NewRoomSchema
#from app.services.exceptions import DuplicatePlayerNameException, InvalidRoomException
from app.services.exceptions import *
from app.services.mixins import DBSessionMixin


class GamesService(DBSessionMixin):

    @db_session
    def game_state(self, room : Room):
        # TODO: exporta en json el estado de la partida, para enviar al frontend
        json = {
            "game_status" : room.state,
            "turn" : room.turn,
        }
        return 
