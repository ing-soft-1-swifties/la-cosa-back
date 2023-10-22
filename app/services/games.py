from pony.orm import db_session
from app.models import Player, Room, Card
from app.services.exceptions import *
from app.services.mixins import DBSessionMixin
from app.services.players import PlayersService
from app.services.rooms import RoomsService
from app.services.cards import CardsService
from app.logger import rootlog

class GamesService(DBSessionMixin):


    @db_session
    def game_state(self, room : Room):
        # TODO: exporta en json el estado de la partida, para enviar al frontend
        def player_state(player):
            return{
                "name" : player.name,
                "id" : player.id,
                "status" : player.status,
                "position" : player.position,
                "in_quarantine" : player.in_quarantine
            }
        game_state = {
            "config" : {
                "id" : room.id,
                "name" : room.name,
                "host" : room.get_host().name,
                "minPlayers" : room.min_players,
                "maxPlayers" : room.max_players
            },
            "status" : room.status,
            "turn" : room.turn,
            "players" : [player_state(player) for player in room.players]
        }
        return game_state
    
    @db_session
    def get_game_status_by_sid(self, sent_sid : str):
        return self.game_state(Player.get(sid = sent_sid).playing)

    @db_session
    def get_game_status_by_rid(self, sent_rid : int):
        return self.game_state(Room.get(id = sent_rid))

    @db_session
    def get_personal_game_status_by_sid(self, sent_sid : str):
        player = Player.get(sid = sent_sid)
        #devuelve un diccionario que representa el estado del juego desde la vision de un jugador
        player_in_game_state = self.game_state(player.playing)
        #agreguemos que cartas tiene esta persona y su estado
        player_in_game_state.update({"playerData": player.json()})
        return player_in_game_state

    @db_session
    def play_card_manager(self, sent_sid : str, payload):
        try:
            cs = CardsService(self.db)
            events = []     #lista de eventos a informar a los jugadores
            player = Player.get(sid = sent_sid)
            if player is None:
                raise InvalidSidException()
            sent_card_id = payload.get("card")
            card_options = payload.get("card_options")
            if sent_card_id is None or card_options is None:
                raise InvalidDataException()
            card = Card.get(id = sent_card_id) 
            if card is None:
                raise InvalidCidException()
            unplayable_cards = ["La cosa", "Infectado"]
            if card.name in unplayable_cards:
                raise InvalidAccionException(f"No se puede jugar {card.name}")
            room = player.playing
            ps = PlayersService(self.db)
            if ps.has_card(player, card) == False:
                raise InvalidCardException()
            if room.machine_state != "PLAYING":
                rootlog.exception("no correspondia jugar una carta")
                raise InvalidAccionException("No corresponde jugar")
            if room.machine_state_options["id"] != player.id:
                rootlog.exception(f"no era el turno de la persona que intento jugar {room.machine_state_options['id']} {player.id}")
                raise InvalidAccionException("No es tu turno")

            #caso: la carta jugada es lanzallamas ¡ruido de asadoo!
            events = []
            events.append({
                "name":"on_game_player_play_card",
                "body":{
                    "player": player.name,
                    "card" : card.json(),
                    "card_options" : payload["card_options"],
                },
                "broadcast":True
            }) 
            if card.name == "Lanzallamas":
                events.extend(cs.play_lanzallamas(player, room, card, card_options))

            rs = RoomsService(self.db)
            rs.recalculate_positions(sent_sid)
            player.hand.remove(card)
            room.discarted_cards.add(card)
            result, json = self.end_game_condition(sent_sid)
            if result != "GAME_IN_PROGRESS":
                events.append({
                    "name":"on_game_end",
                    "body":json,
                    "broadcast":True
                })
                #si hago esto cuando quireo notificar no existen mass los jugadores
                #TODO! ver como eliminar la partida
                #rs.end_game(sent_sid)
            else:
                events.extend(self.begin_end_of_turn_exchange(room))
            return events
        except InvalidAccionException as e:
            return e.generate_event(sent_sid)

    @db_session
    def discard_card_manager(self, sent_sid : str, payload):
        cs = CardsService(self.db)
        events = cs.discard_card(sent_sid, payload)
        return events

    @db_session
    def end_game_condition(self, sent_sid : str):
        """Chequea si se finalizo la partida.

        Args: room (Room): current valid room

        Returns: str: {'GAME_IN_PROGRESS', 'LA_COSA_WON', 'HUMANS_WON'}, json
        """
        player = Player.get(sid = sent_sid)
        info = {}
        # inputs validos
        if player is None:
            raise InvalidSidException()
        room: Room = player.playing
        
        roles = []
        for player in room.players:
            roles.append((player.name, player.rol))
        
        ret = 'GAME_IN_PROGRESS'
        # Si queda solo un sobreviviente     
        if len(room.players.select(lambda p: p.status != 'MUERTO')) == 1:
            survivor: Player = list(room.players.select(lambda p: p.status != 'MUERTO'))[0] # type: ignore
            # Chequeo si es la cosa
            if survivor.rol == 'LA_COSA':
                ret = 'LA_COSA_WON'
                info = {
                    "winner_team": "LA_COSA",
                    "winner": list(map(lambda x: x.name, list(room.players.select(rol='LA_COSA')))),
                    "roles":roles
                }                
            else: 
                ret = 'HUMANS_WON'
                info = {
                    "winner_team": "HUMANOS",
                    "winner": list(map(lambda x: x.name, list(room.players.select(rol='HUMANO')))),
                    "roles":roles
                }
        
        # Chequeo el estado de la cosa
        la_cosa: Player = list(room.players.select(lambda p: p.rol == 'LA_COSA'))[0] # type: ignore
        # la_cosa: Player = room.players.get(rol = 'LA_COSA') # type: ignore
        
        if la_cosa.status == 'MUERTO':
            ret = 'HUMANS_WON'
            info = {
                "winner_team": "HUMANOS",
                "winner": list(map(lambda x: x.name, list(room.players.select(rol='HUMANO')))),
                "roles": roles
            }
    
        qty_alive_players = len(room.players.select(lambda p : p.status != 'MUERTO'))
        qty_alive_non_human_players = len(room.players.select(lambda p : p.status != 'MUERTO' and p.rol != 'HUMANO'))
        if qty_alive_non_human_players == qty_alive_players: 
            ret='LA_COSA_WON'
            info = {"winner_team":"LA_COSA",
                        "winner": list(map(lambda x: x.name, list(room.players.select(rol='LA_COSA')))),
                        "roles":roles}   
                
        return ret, info
    
    @db_session
    def exchange_card_manager(self, sent_sid : str, payload):
        try:
            events = []
            player = Player.get(sid = sent_sid)
            if player is None:
                raise InvalidSidException()
            sent_card_id = payload.get("card")
            on_defense = payload.get("on_defense")
            if sent_card_id is None or on_defense is None:
                raise InvalidDataException()
            card = Card.get(id = sent_card_id)
            if card is None:
                raise InvalidCidException()
            unchangable_cards = ["La cosa"]
            if card.name in unchangable_cards:
                raise InvalidAccionException(f"No se puede intercambiar {card.name}")
            room = player.playing
            ps = PlayersService(self.db)
            if ps.has_card(player, card) == False:
                raise InvalidCardException()
            #maquina de estados
            if room.machine_state != "EXCHANGING":
                rootlog.exception("no correspondia intercambiar una carta")
                raise InvalidAccionException("No corresponde intercambiar")
            exchanging_players = room.machine_state_options.get("ids")
            if exchanging_players is None:
                rootlog.exception("deberia existir campo ids en estado intercambio")
                raise Exception()
            if player.id not in room.machine_state_options["ids"]:
                rootlog.exception(f"no corresponde que la persona intercambie. Estos ids intercambiaban {room.machine_state_options['ids']} y la persona tiene id={player.id}")
                raise InvalidAccionException("No corresponde iniciar un intercambio")
            first_player = exchanging_players[0] == player.id   #El primer id es el del que inica el intercambio
            if first_player:
                if on_defense:
                    raise InvalidAccionException("No te podes defender si sos el que inicia el intercambio")
            if room.machine_state_options["stage"] == "STARTING":
                room.machine_state = "EXCHANGING"
                room.machine_state_options = {"ids":room.machine_state_options["ids"], 
                                            "stage":"FINISHING",
                                            "card_id" : card.id,
                                            "player_id":player.id,
                                            "on_defense": on_defense if not first_player else False}    #falta verificar si se puede defender con esa carta
                # print("se completo la primera etapa del intercambio")
                return events
            elif room.machine_state_options["stage"] == "FINISHING" and player.id != room.machine_state_options["player_id"]:
                first_player_id = exchanging_players[0]
                first_player = Player.get(id = first_player_id)
                second_player_id = exchanging_players[1]
                second_player = Player.get(id = second_player_id)
                if first_player is None or second_player is None:
                    InvalidDataException()
                if first_player.playing != second_player.playing:
                    rootlog.exception("los jugadores no corresponden a una misma partida")
                    InvalidDataException()
                is_first_player = exchanging_players[0] == player.id
                first_card = card if is_first_player else Card.get(id = room.machine_state_options["card_id"])
                second_card = card if not is_first_player else Card.get(id = room.machine_state_options["card_id"])
                from .cards import CardsService
                cs = CardsService(self.db)
                try:
                    events.extend(cs.exchange_cards(room, first_player, second_player, first_card, second_card))    #falta ver si se esta defendiendo
                    rs = RoomsService(self.db)
                    events.extend(rs.next_turn(sent_sid))
                    return events
                except Exception as e:
                    #volvemos a realizar el intercambio
                    player_A = Player.get(id=room.machine_state_options["ids"][0])  #el que inicia el intercambio es el primer id
                    player_B = Player.get(id=room.machine_state_options["ids"][1])  #el que recive solicitud de intercambio es el segundo id
                    if player_A is None or player_B is None or player_A.playing != player_B.playing:
                        rootlog.exception("los jugadores que estaban intercambiando no eran validos cuando se intento realizar otra vez el intercambio")
                    events.extend(self.begin_exchange(room, player_A, player_B))
                    return events
            else:
                raise InvalidAccionException("No corresponde iniciar un intercambio") 
        except InvalidAccionException as e:
            return e.generate_event(sent_sid)
    
    def begin_exchange(self, room : Room, player_A : Player, player_B : Player):
        """
        setea la maquina de estados para un intercambio entre player_A y player_B
        asume que los checkeos pertinentes se realizaron (ej que esten en la misma sala)
        """
        events = []   
        room.machine_state =  "EXCHANGING"
        room.machine_state_options = {"ids":[player_A.id, player_B.id],
                                    "stage":"STARTING",
                                    }
        events = [{
                    "name":"on_game_begin_exchange",
                    "body":{"players":[player_A.name, player_B.name]},
                    "broadcast":True
        }]
        return events
    
    def begin_end_of_turn_exchange(self, room : Room):
        in_turn_player = list(room.players.select(lambda player : player.position == room.turn and player.status == "VIVO"))[0]
        if in_turn_player is None:
            rootlog.exception(f"el jugador con posicion {room.turn} no esta en la partida")
            raise Exception()
        rs = RoomsService(self.db)
        return self.begin_exchange(room, in_turn_player, rs.next_player(room))