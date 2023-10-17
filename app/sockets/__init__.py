from app.models import Player
from pony.orm import db_session
from app.services.exceptions import DuplicatePlayerNameException, InvalidAccionException, InvalidRoomException, InvalidSidException
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

async def end_game(sid : str):
    rs = RoomsService(db)
    try:
        rs.end_game(sid)
        # event on_room_cancelled_game
        for player_sid in rs.get_players_sid(sid):
            await sio_server.emit("on_room_cancelled_game", to=player_sid)   
            #notar que hay que tener cuidado con si falla alguna conexion
            await sio_server.disconnect(player_sid)

    except Exception as e:
        print(f"Fallo al querer terminar la partida del jugador con sid: {sid}")
        return True

    # se cierra la conexion
    return False    

@sio_server.event
async def room_quit_game(sid : str):
    ps = PlayersService(db)
    gs = GamesService(db)
    rs = RoomsService(db)
    try:
        # si el host sale de la lobby, eliminamos toda la partida
        if ps.is_host(sid):
            await end_game(sid)
       
        else:
            # desconectamos el jugador
            ps.disconnect_player(sid)

            # event on_room_left_player
            for player_sid in rs.get_players_sid(sid):
                if player_sid != sid:
                    json_response = {
                        "gameState": gs.get_personal_game_status_by_sid(player_sid)
                    }
                    await sio_server.emit("on_room_left_player", json_response, to=player_sid)   #notar que hay que tener cuidado con si falla alguna conexion
            # desconectamos el socket
            await sio_server.disconnect(sid)

    # error handling 
    except InvalidSidException as e:
        raise e
    
    except Exception:
        rootlog.exception(f"Fallo al intentar sacar de la partida al jugador con sid{sid}")
        return True
    
    return False

async def give_card(sid: str):

    # instanciamos los servicios
    rs = RoomsService(db)
    gs = GamesService(db)
    ps = PlayersService(db)

    try:
        card_json, in_turn_player_sid = gs.next_turn(sid)   #entrega carta a quien le toca
        players_sid = rs.get_players_sid(sid)
        # event on_game_player_turn
        for player_sid in players_sid:
            json_response = {
                "player": ps.get_name(in_turn_player_sid), 
                "gameState": gs.get_personal_game_status_by_sid(player_sid)
            }
            await sio_server.emit("on_game_player_turn", json_response, to = player_sid)  

        # event on_game_player_steal_card
        json_response = {
            "cards": [card_json], 
            "gameState": gs.get_personal_game_status_by_sid(in_turn_player_sid)
        }
        await sio_server.emit("on_game_player_steal_card", json_response, to=in_turn_player_sid)   
    
    # error handling
    except Exception:
        rootlog.exception(f"error al querer repartir carta  en partida del jugador con sid: {sid}")
        #falta determinar que hacemos si falla

@sio_server.event
async def room_start_game(sid : str): 
    rs = RoomsService(db)
    gs = GamesService(db)
    try:
        # prepara lo mazos y reparte
        rs.start_game(sid) 
        # evento on_room_start_game
        for player_sid in rs.get_players_sid(sid):
            json_response = {
                "gameState": gs.get_personal_game_status_by_sid(player_sid)
            }
            await sio_server.emit("on_room_start_game", json_response, to=player_sid)   
            # notar que hay que tener cuidado con si falla alguna conexion

    # error handling
    except Exception as e:
        rootlog.exception(f"error al querer iniciar la partida del jugador con sid: {sid}")
        #hay que determinar si eliminamos la partida si ocurre un error
        return True
    
    try:
        # le entrego carta a la primera persona en jugar
        await give_card(sid) 
    # error handling
    except Exception:
        rootlog.exception(f"error al querer repartir carta al primer jugador de la partida del jugador con sid: {sid}")

    
@sio_server.event
async def game_play_card(sid : str, data): 
    rs = RoomsService(db)
    gs = GamesService(db)
    
    try:
        events = gs.play_card(sid, data)
        
        # event on_game_player_play_card
        for player_sid in rs.get_players_sid(sid):
            json_response = {
                "card" : data["card"],
                "card_options" : data["card_options"],
                "gameState": gs.get_personal_game_status_by_sid(player_sid)
            }
            await sio_server.emit("on_game_player_play_card", json_response, to=player_sid)

        # event 
        for event in events:
            for player_sid in rs.get_players_sid(sid):
                json_response = {
                    "gameState": gs.get_personal_game_status_by_sid(player_sid)
                }
                json_response.update(event[1])
                await sio_server.emit(event[0], json_response, to=player_sid)
        
        
        try:
            # nos fijamos si termino la partida
            result, json = gs.end_game_condition(sid)
            # Si se termino
            if result != "GAME_IN_PROGRESS":
                # event on_game_end 
                for player_sid in rs.get_players_sid(sid):
                    json.update({"gameState": gs.get_personal_game_status_by_sid(player_sid)})
                    await sio_server.emit("on_game_end", json, to=player_sid)

            # si no se termino
            else:
                await give_card(sid)
        # error handling
        except Exception as e:
            rootlog.exception("Fallo al verificar si algun equipo ganó")
            #partida en posible estado inconsistente, matarla

    # error handlings
    except InvalidAccionException as e:
        rootlog.exception("jugada invalida")
        # evento on_game_invalid_action
        json_response = {
            "title":"Jugada Invalida", 
            "message": e.msg, 
            "gameState": gs.get_personal_game_status_by_sid(sid)
        }
        await sio_server.emit("on_game_invalid_action", json_response, to=sid)
        
    except Exception:
        rootlog.exception("ocurrio un error")

    return True


@sio_server.event
async def game_discard_card(sid : str, data): 
    rs = RoomsService(db)
    gs = GamesService(db)

    try:
        card_id = gs.discard_card(sid, data)

        # evento on_game_player_discard_card        
        for player_sid in rs.get_players_sid(sid):
            json_response = {
                "card":card_id,
                "gameState": gs.get_personal_game_status_by_sid(player_sid)
            }
            await sio_server.emit("on_game_player_discard_card", json_response, to=player_sid)

    # error handling
    except InvalidAccionException as e:
        rootlog.exception("descarte invalido")

        # evento on_game_invalid_action
        json_response = {
            "title":"Jugada Invalida", 
            "message": e.msg, 
            "gameState": gs.get_personal_game_status_by_sid(sid)
        }
        await sio_server.emit("on_game_invalid_action", json_response, to=sid)
    
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
