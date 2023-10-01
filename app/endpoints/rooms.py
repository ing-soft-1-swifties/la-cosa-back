from fastapi import APIRouter, Response
from app.models import Room
from app.schemas import ConnectionCredentials, NewRoomSchema, RoomSchema, RoomJoiningInfo

from pony.orm import db_session
from app.services.rooms import RoomsService

from database.database import db


router = APIRouter()

@router.post("/create")
def create_room(new_room: NewRoomSchema):
    rs = RoomsService(db)

    try:
        token = rs.create_room(room = new_room)
        return ConnectionCredentials(token=token)
    except Exception as e:
        # TODO: mejorar este handling
        raise e

@router.post("/join")
def join_room(joining_info: RoomJoiningInfo) -> ConnectionCredentials:

    rs = RoomsService(db)

    try:
        token = rs.join_player(joining_info.name, joining_info.room_id)
        return ConnectionCredentials(token=token)
    except Exception as e:
        # TODO: mejorar este handling
        raise e

@router.get("/all")
def listar_partida():
    with db_session:
        raw_room = Room.select()
        rooms = [RoomSchema.model_validate(room, from_attributes=True) for room in raw_room]

    return rooms;
