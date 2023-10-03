from fastapi import APIRouter, HTTPException
from app.schemas import ConnectionCredentials, NewRoomSchema, RoomJoiningInfo
from app.services.exceptions import DuplicatePlayerNameException, InvalidRoomException, TooManyPlayersException
from app.services.rooms import RoomsService
from app.services.games import GamesService
from app.models import db


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
    except TooManyPlayersException as e:
        raise HTTPException(status_code=404, detail="Maximun people capacity reached")


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
        
#este endpoint esta de mas, por ahora lo dejamos por si se quiere testear el estado de una partida con api rest
@router.get("/game_status/{room_id}")
def room_status(room_id : int):
    """
    muestra el estado de una partida especificada como argumento
    """
    try:
        gs = GamesService(db)
        ret = gs.get_game_status_by_rid(room_id)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500)
    return {"gameStatus" : ret} 
    