# from fastapi import APIRouter, HTTPException, Response
from app.models import Player
# from app.schemas import ConnectionCredentials, NewRoomSchema, RoomSchema, RoomJoiningInfo

from pony.orm import db_session
from app.services.exceptions import DuplicatePlayerNameException, InvalidRoomException
from app.services.players import PlayersService
from app.services.rooms import RoomsService
from app.services.games import GamesService

from app.models import db
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
async def connect(sid, environ, auth):
    # autenticar jugador con token
    # guardar en jugador el socket id
    ps = PlayersService(db)
    gs = GamesService(db)
    try:
        token = auth["token"]
        ps.connect_player(token, sid)
    except Exception as e:
        return False
    rs = RoomsService(db)
    try:
        players_sid = rs.get_players_sid(sid)
    except Exception as e:
        return False
    for player_sid in players_sid:
        if player_sid != sid:
            await sio_server.emit("room/newPlayer", {"gameState": gs.get_game_status_by_sid(sid)}, player_sid)   #notar que hay que tener cuidado con si falla alguna conexion
    await sio_server.emit("newGameState", {"gameState": gs.get_game_status_by_sid(sid)}, sid)
    return True

@sio_server.event
def start_game(sid):
    # Aquí puedes realizar la lógica para iniciar la partida
    rs = RoomsService(db)
    gs = GamesService(db)
    try:
        rs.start_game(sid)
    except Exception as e:
        return False
    print(f"Partida iniciada por el usuario {sid}")
    try:
        players_sid = rs.get_players_sid(sid)
    except Exception as e:
        return False
    for player_sid in players_sid:
        aux = sio_server.emit("room/start", {"gameState": gs.get_game_status_by_sid(sid)}, player_sid)   #notar que hay que tener cuidado con si falla alguna conexion
        #sio.emit("mensaje_desde_servidor", {"mensaje": mensaje}, room=connection_id)


    
@sio_server.event
def get_game_status(sid):
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
        aux = sio_server.emit("room/start", player_sid)   #notar que hay que tener cuidado con si falla alguna conexion
        #sio.emit("mensaje_desde_servidor", {"mensaje": mensaje}, room=connection_id)
    return 
