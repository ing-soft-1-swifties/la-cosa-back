from app.models import Player
from pony.orm import db_session
from app.services.exceptions import DuplicatePlayerNameException, InvalidAccionException, InvalidRoomException, InvalidSidException
from app.services.players import PlayersService
from app.services.rooms import RoomsService
from app.services.games import GamesService
from app.services.cards import CardsService
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

rs = RoomsService(db)
gs = GamesService(db)
ps = PlayersService(db)
cs = CardsService(db)

@sio_server.event
async def connect(sid, environ, auth):
    # autenticar jugador con token
    # guardar en jugador el socket id
    print(auth["token"])
    try:
        token = auth["token"]
        events = ps.connect_player(token, sid)
        await notify_events(events, sid)
    except Exception as e:
        rootlog.exception("error al querer conectar a una persona")
        return False
    return True

@sio_server.event
async def disconnect(sid : str):
    return True #para debugear
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

    try:
        if ps.is_host(sid):
            await end_game(sid)
        else:
            events = ps.disconnect_player(sid)
            await sio_server.disconnect(sid)
            await notify_events(events, sid)
    except Exception:
        rootlog.exception(f"fallo al intentar sacar de la partida al jugador con sid{sid}")
        return True
    return False    #se cierra la conexion

async def end_game(sid : str):
    try:
        players_sid = rs.get_players_sid(sid)
        rs.end_game(sid)
    except Exception as e:
        print(f"fallo al querer terminar la partida del jugador con sid:{sid}")
        return True
    #no puedo usar notify_events por que consumen los sid de playes que fueron borrados
    for player_sid in players_sid:
        await sio_server.emit("on_room_cancelled_game", to=player_sid)   #notar que hay que tener cuidado con si falla alguna conexion
        await sio_server.disconnect(player_sid)
    return False    #se cierra la conexion

@sio_server.event
async def room_start_game(sid : str): 
    try:
        events = rs.start_game(sid)  #prepara lo mazos y reparte
        await notify_events(events, sid)
    except Exception as e:
        rootlog.exception(f"error al querer iniciar la partida del jugador con sid: {sid}")
        #hay que determinar si eliminamos la partida si ocurre un error
        return True
    print(f"Partida iniciada por el jugador con socket_id = {sid}")

@sio_server.event
async def game_play_card(sid : str, data): 
    try:
        events = gs.play_card_manager(sid, data)
        await notify_events(events, sid)
    except InvalidAccionException as e:
        return e.generate_event(sid)
    except Exception:
        rootlog.exception("ocurrio un error inesperado al jugar una carta, posible estado inconsistente")
    return True

@sio_server.event
async def game_play_defense_card(sid :str, data):
    try:
        events = gs.play_defense_card_manager(sid, data)
        await notify_events(events, sid)
    except InvalidAccionException as e:
        return e.generate_event(sid)
    except Exception:
        rootlog.exception("ocurrio un error inesperado al defenderse de una carta, posible estado inconsistente")
    return True
    
@sio_server.event
async def game_discard_card(sid : str, data): 
    try:
        events = gs.discard_card_manager(sid, data)
        await notify_events(events, sid)
    except Exception:
        rootlog.exception("error al descartar carta")
    return True

@sio_server.event
async def game_exchange_card(sid : str, data):
    try:
        print(data)
        events = gs.exchange_card_manager(sid, data)
        await notify_events(events, sid)
    except Exception:
        rootlog.exception("error al descartar carta")
    return True


@sio_server.event
async def game_new_message(sid : str, data):
    try:
        events = rs.new_message(sid, data)
        await notify_events(events, sid)
    except Exception:
        rootlog.exception("error al recivir un nuevo mensaje")
    return True
    
async def notify_events(events, sid):
    """
    recibe una lista de eventos
    event = {name: <Str>
             body: <Json>
             broadcast: <Bool>
             receiver_sid: <Str>
             except_sid: <Str>
             }
    """

    for event in events:
        if event["broadcast"]:
            for player_sid in rs.get_players_sid(sid):
                if event.get('except_sid') is not None:
                    if player_sid == event.get('except_sid'):
                        continue
                gameState = {"gameState": gs.get_personal_game_status_by_sid(player_sid)}
                event["body"].update(gameState)
                await sio_server.emit(event["name"], event["body"], to = player_sid)
        else:
            gameState = {"gameState": gs.get_personal_game_status_by_sid(event["receiver_sid"])}
            event["body"].update(gameState)
            await sio_server.emit(event["name"], event["body"], to = event["receiver_sid"])

