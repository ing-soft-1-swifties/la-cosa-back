# from fastapi import APIRouter, HTTPException, Response
from app.models import Player
# from app.schemas import ConnectionCredentials, NewRoomSchema, RoomSchema, RoomJoiningInfo

from pony.orm import db_session
from app.services.exceptions import DuplicatePlayerNameException, InvalidRoomException
from app.services.players import PlayersService
from app.services.rooms import RoomsService

from database.database import db
import socketio


sio_server = socketio.AsyncServer(
        async_mode = "asgi",
        cors_allowed_origins="*"
)

sio_app = socketio.ASGIApp(
    socketio_server=sio_server,
    socketio_path="/"
)

@sio_server.event
async def connect(sid):
    print("hola")
    return True
    # autenticar jugador con token
    # guardar en jugador el socket id
    ps = PlayersService(db)
    token = auth.token
    try:
        ps.connect_player(token, sid)
    except Exception as e:
        return False

@sio_server.event
def start_game(sid):
    # Aquí puedes realizar la lógica para iniciar la partida
    rs = RoomsService(db)
    try:
        rs.start_game(sid)
    except Exception as e:
        return False
    print(f"Partida iniciada por el usuario {sid}")
    try:
        players_sid = rs.get_players_sid()
    except Exception as e:
        return False
    for player_sid in players_sid:
        sio_server.emit("room/start", player_sid)   #notar que hay que tener cuidado con si falla alguna conexion
        #sio.emit("mensaje_desde_servidor", {"mensaje": mensaje}, room=connection_id)

    
