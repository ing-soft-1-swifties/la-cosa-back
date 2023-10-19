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
        await sio_server.emit("on_room_new_player", {"gameState": gs.get_personal_game_status_by_sid(player_sid)}, to=player_sid)
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
                    await sio_server.emit("on_room_left_player", {"gameState": gs.get_personal_game_status_by_sid(player_sid)}, to=player_sid)   #notar que hay que tener cuidado con si falla alguna conexion
            await sio_server.disconnect(sid)
    except InvalidSidException as e:
        raise e
    except Exception:
        rootlog.exception(f"fallo al intentar sacar de la partida al jugador con sid{sid}")
        #falta ver como le comunicamos el incoveniente al cliente
        return True
    return False    #se cierra la conexion

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

async def give_card(sid : str):
    rs = RoomsService(db)
    gs = GamesService(db)
    ps = PlayersService(db)
    try:
        card_json, in_turn_player_sid = rs.next_turn(sid)   #entrega carta a quien le toca
        await notify_events([
        {
            "name":"on_game_player_turn",
            "body":{"player":ps.get_name(in_turn_player_sid)},
            "broadcast":True
        },
        {
            "name":"on_game_player_steal_card",
            "body":{"cards":[card_json]},
            "broadcast":False,
            "single_sid":in_turn_player_sid
        }
        ], sid)
    except Exception:
        rootlog.exception(f"error al querer repartir carta  en partida del jugador con sid: {sid}")
        #falta determinar que hacemos si falla
        pass

@sio_server.event
async def room_start_game(sid : str): 
    # Aquí puedes realizar la lógica para iniciar la partida
    rs = RoomsService(db)
    gs = GamesService(db)
    ps = PlayersService(db)
    try:
        events = rs.start_game(sid)  #prepara lo mazos y reparte
        #await notify_events(events)
        await notify_events([
        {
            "name":"on_room_start_game",
            "body":{},
            "broadcast":True
        }], sid)
    except Exception as e:
        rootlog.exception(f"error al querer iniciar la partida del jugador con sid: {sid}")
        #hay que determinar si eliminamos la partida si ocurre un error
        return True
    print(f"Partida iniciada por el jugador con socket_id = {sid}")
    try:
        await give_card(sid) #le entrego carta a la primera persona en jugar
    except Exception:
        rootlog.exception(f"error al querer repartir carta al primer jugador de la partida del jugador con sid: {sid}")

    
@sio_server.event
async def game_play_card(sid : str, data): 
    # Aquí puedes realizar la lógica para iniciar la partida
    rs = RoomsService(db)
    gs = GamesService(db)
    ps = PlayersService(db)
    cs = CardsService(db)
    try:
        events = gs.play_card(sid, data)
        for player_sid in rs.get_players_sid(sid):
            await sio_server.emit("on_game_player_play_card", {
                "player": ps.get_name(sid),
                "card" : cs.card_to_JSON_from_cid(data["card"]),
                "card_options" : data["card_options"],
                "gameState": gs.get_personal_game_status_by_sid(player_sid)}, 
                to=player_sid)
        for event in events:
            for player_sid in rs.get_players_sid(sid):
                json = {"gameState": gs.get_personal_game_status_by_sid(player_sid)}
                json.update(event[1])
                await sio_server.emit(event[0], json, to=player_sid)
        try:
            result, json = gs.end_game_condition(sid)
            if result != "GAME_IN_PROGRESS":
                for player_sid in rs.get_players_sid(sid):
                    json.update({"gameState": gs.get_personal_game_status_by_sid(player_sid)})
                    await sio_server.emit("on_game_end", json, to=player_sid)
                rs.end_game(sid)
            else:
                await give_card(sid)
                pass
        except Exception as e:
            rootlog.exception("Fallo al verificar si algun equipo ganó")
            #TODO! partida en posible estado inconsistente, matarla
    except InvalidAccionException as e:
        rootlog.exception("jugada invalida")
        await sio_server.emit("on_game_invalid_action", {"title":"Jugada Invalida", "message": e.msg, "gameState": gs.get_personal_game_status_by_sid(sid)}, to=sid)
    except Exception:
        rootlog.exception("ocurrio un error")
    return True

@sio_server.event
async def game_discard_card(sid : str, data): 
    # Aquí puedes realizar la lógica para iniciar la partida
    rs = RoomsService(db)
    gs = GamesService(db)
    ps = PlayersService(db)
    try:
        card_id = gs.discard_card(sid, data)
        for player_sid in rs.get_players_sid(sid):
            await sio_server.emit("on_game_player_discard_card", {"gameState": gs.get_personal_game_status_by_sid(player_sid)}, to=player_sid)
        #await give_card(sid)
    except InvalidAccionException as e:
        rootlog.exception("descarte invalido")
        await sio_server.emit("on_game_invalid_action", {"title":"Intercambio Invalido", "message": e.msg, "gameState": gs.get_personal_game_status_by_sid(sid)}, to=sid)
    except Exception:
        rootlog.exception("error al descartar carta")
    return True

@sio_server.event
async def game_exchange_card(sid : str, data):
    rs = RoomsService(db)
    gs = GamesService(db)
    ps = PlayersService(db)
    try:
        pass
        print(f"jugador {rs.get_name(sid)}, quiere intercambiar ", data)
        events = gs.exchange_card_manager(sid, data)
        notify_events(events)
        for player_sid in rs.get_players_sid(sid):
            pass
    except InvalidAccionException as e:
        rootlog.exception("intercambio invalido")
        await sio_server.emit("on_game_invalid_action", {"title":"Intercambio invalido", "message": e.msg, "gameState": gs.get_personal_game_status_by_sid(sid)}, to=sid)
    except Exception:
        rootlog.exception("error al descartar carta")
    return True

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

async def notify_events(events, sid):
    """
    recive una lista de eventos
    event = {name:
             body:
             broadcast:
             single_sid:
             }
    """
    rs = RoomsService(db)
    gs = GamesService(db)
    for event in events:
        if event["broadcast"]:
            for player_sid in rs.get_players_sid(sid):
                gameState = {"gameState": gs.get_personal_game_status_by_sid(player_sid)}
                event["body"].update(gameState)
                await sio_server.emit(event["name"], event["body"], to = player_sid)
        else:
            gameState = {"gameState": gs.get_personal_game_status_by_sid(event["single_sid"])}
            event["body"].update(gameState)
            await sio_server.emit(event["name"], event["body"], to = event["single_sid"])

