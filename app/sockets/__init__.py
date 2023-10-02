# from fastapi import APIRouter, HTTPException, Response
from app.models import Player
# from app.schemas import ConnectionCredentials, NewRoomSchema, RoomSchema, RoomJoiningInfo

from pony.orm import db_session
from app.services.exceptions import DuplicatePlayerNameException, InvalidRoomException
from app.services.players import PlayersService

from database.database import db
import socketio


sio_server = socketio.AsyncServer(
        async_mode = "asgi",
        cors_allowed_origins= ["*"]
)

sio_app = socketio.ASGIApp(
    socketio_server=sio_server,
    socketio_path="sockets"
)

@sio_server.event
async def connect(sid, environ, auth):
    # autenticar jugador con token
    # guardar en jugador el socket id
    # ack de conexion para el cliente si es que es necesario
    # token = environ.get("QUERY_STRING")
    token = auth.token
    try:
        connect_player(token, sid)
    except Exception as e:
        return False

# @sio.event
# def connect(sid, environ):
#     token = environ.get("QUERY_STRING")  # Obtén el token de la query string
#     if validar_token(token):
#         print(f"Usuario {sid} conectado con token válido")
#     else:
#         print(f"Usuario {sid} intentó conectar con token inválido")
#         return False  # Esto evitará que la conexión sea aceptada
