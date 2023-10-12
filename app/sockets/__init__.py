from app.models import Player
from pony.orm import db_session
from app.services.exceptions import DuplicatePlayerNameException, InvalidRoomException, InvalidSidException
from app.services.players import PlayersService
from app.services.rooms import RoomsService
from app.services.games import GamesService
from app.models import db
from app.logger import rootlog
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
    rs = RoomsService(db)
    try:
        token = auth["token"]
        ps.connect_player(token, sid)
        players_sid = rs.get_players_sid(sid)
    except Exception as e:
        return False
    for player_sid in players_sid:
        await sio_server.emit("on_room_new_player", {"gameState": gs.get_game_status_by_sid(sid)}, to=player_sid)   #notar que hay que tener cuidado con si falla alguna conexion
    return True

@sio_server.event
async def disconnect(sid : str):
    # por ahora no vamos a hacer nada ya que no lo especifica el cliente
    # si la persona intenta volver a conectarse con su token, el sistema 
    # lo vuelve a reconectar.
    try:
        try:
            await room_quit_game(sid)
        except InvalidSidException:
            pass
        
        #si este es el host, se mata la partida
        #abria que definir bien que pasa si la partida ya inicio
    except Exception as e:
        rootlog.exception("Error eliminado la partida al desconectarse un jugador.")
        return False
    return True

@sio_server.event
async def room_quit_game(sid : str):
    ps = PlayersService(db)
    gs = GamesService(db)
    rs = RoomsService(db)
    try:
        if ps.is_host(sid):
            await end_game(sid)
        else:
            players_sid = rs.get_players_sid(sid)
            ps.disconnect_player(sid)
            for player_sid in players_sid:
                if player_sid != sid:
                    await sio_server.emit("on_room_left_player", {"gameState": gs.get_game_status_by_sid(player_sid)}, to=player_sid)   #notar que hay que tener cuidado con si falla alguna conexion
            await sio_server.disconnect(sid)
    except InvalidSidException as e:
        raise e
    except Exception:
        rootlog.exception(f"fallo al intentar sacar de la partida al jugador con sid{sid}")
        #falta ver como le comunicamos el incoveniente al cliente
        return True
    return False    #se cierra la conexion

# @sio_server.event
# TODO! Check (room_quit_game)
async def end_game(sid : str):
    rs = RoomsService(db)
    try:
        players_sid = rs.get_players_sid(sid)
        rs.end_game(sid)
    except Exception as e:
        print(f"fallo al querer terminar la partida del jugador con sid:{sid}")
        return True
    for player_sid in players_sid:
        await sio_server.emit("on_room_cancelled_game", to=player_sid)   #notar que hay que tener cuidado con si falla alguna conexion
        await sio_server.disconnect(player_sid)
    return False    #se cierra la conexion

@sio_server.event
async def room_start_game(sid : str): 
    # Aquí puedes realizar la lógica para iniciar la partida
    rs = RoomsService(db)
    gs = GamesService(db)
    try:
        rs.start_game(sid)
        players_sid = rs.get_players_sid(sid)
        for player_sid in players_sid:
            await sio_server.emit("on_room_start_game", {"gameState": gs.get_personal_game_status_by_sid(sid)}, to=player_sid)   #notar que hay que tener cuidado con si falla alguna conexion
    except Exception as e:
        rootlog.exception(f"error al querer iniciar la partida del jugador con sid: {sid}")
        #hay que determinar si eliminamos la partida si ocurre un error
        return True
    print(f"Partida iniciada por el usuario {sid}")
    
# @sio_server.event
# def get_game_status(sid: str):
#     gs = GamesService(db)
#     rs = RoomsService(db)
#     try:
#         players_sid = rs.get_players_sid()
#     except Exception as e:
#         return False
#     for player_sid in players_sid:
#         aux = sio_server.emit("room/status",{"gameState": gs.get_personal_game_status_by_sid(sid)}, player_sid)   #notar que hay que tener cuidado con si falla alguna conexion
#     return True 
