from fastapi import APIRouter, HTTPException
from database.database import get_db
from app.schemas import ConnectionCredentials, NewRoomSchema, RoomJoiningInfo
from app.services.exceptions import DuplicatePlayerNameException, InvalidRoomException
from app.services.rooms import RoomsService

db = get_db()

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


@router.get("/list")
def list_rooms():
    """
    lista los ids de las partidas disponibles
    """

    rs = RoomsService(db)

    try:
        return rs.list_rooms()
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500)
        