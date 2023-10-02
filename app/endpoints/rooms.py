from fastapi import APIRouter, HTTPException, Response
from app.models import Room
from app.schemas import ConnectionCredentials, NewRoomSchema, RoomSchema, RoomJoiningInfo

from pony.orm import db_session
from app.services.exceptions import DuplicatePlayerNameException, InvalidRoomException
from app.services.rooms import RoomsService

from database.database import db


router = APIRouter()

@router.post("/create")
def create_room(new_room: NewRoomSchema) -> ConnectionCredentials:
    """
    Crea partida con la configuración recibida 
    y devuelve un token correspondiente al jugador host
    """
    rs = RoomsService(db)

    token = rs.create_room(room = new_room)
    return ConnectionCredentials(token=token)

@router.post("/join")
def join_room(joining_info: RoomJoiningInfo) -> ConnectionCredentials:
    """
    Une a un jugador a la partida especificada
    """

    rs = RoomsService(db)

    try:
        token = rs.join_player(joining_info.name, joining_info.room_id)
        return ConnectionCredentials(token=token)
    except DuplicatePlayerNameException as e:
        raise HTTPException(status_code=400, detail="Duplicate player name")
    except InvalidRoomException as e:
        raise HTTPException(status_code=404, detail="Invalid room id")

@router.get("/all")
def listar_partida():
    with db_session:
        raw_room = Room.select()
        rooms = [RoomSchema.model_validate(room, from_attributes=True) for room in raw_room]

    return rooms;
