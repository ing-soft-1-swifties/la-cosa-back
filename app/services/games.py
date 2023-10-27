from pony.orm import db_session
from app.models import Player, Room, Card
from app.services.exceptions import *
from app.services.mixins import DBSessionMixin
from app.services.play_card import PlayCardsService
from app.services.players import PlayersService
from app.services.rooms import RoomsService
from app.services.cards import CardsService
from app.logger import rootlog
from app.models.constants import CardName as cards

class GamesService(DBSessionMixin):



    @db_session
    def game_state(self, room : Room):
        rs = RoomsService(self.db)
        def player_state(player):
            return {
                "name" : player.name,
                "id" : player.id,
                "status" : player.status,
                "position" : player.position,
                "in_quarantine" : player.in_quarantine,
                #estos son agregados para notificar estado al front, asi deciden como renderizar ciertas cosas
                "on_turn": player.status == "VIVO" and player.position == room.turn,
                "on_exchange": room.machine_state == "EXCHANGING" and (player.id in room.machine_state_options.get("ids"))
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
            "direction": room.direction,
            "player_in_turn" : rs.in_turn_player(room).name,
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
    def play_defense_card_manager(self, sent_sid : str, payload):
        try:
            rs = RoomsService(self.db)
            ps = PlayersService(self.db)
            cs = CardsService(self.db)
            pcs = PlayCardsService(self.db)

            # lista de eventos a informar a los jugadores
            events = []     

            # verificamos inputs correctos            
            sent_card_id = payload.get("card")
            on_defense = payload.get("on_defense")
            if sent_card_id is None or on_defense is None:
                raise InvalidDataException()
            
            # obtenemos y verificamos el jugador
            player = Player.get(sid = sent_sid)
            if player is None:
                raise InvalidSidException()

            # obtenemos y verificamos las cartas
            played_card = Card.get(id = room.machine_state_options["card"])
            card = Card.get(id = sent_card_id) 
            if card is None or played_card is None:
                raise InvalidCidException()

            if ps.has_card(player, card) == False:
                raise InvalidCardException()

            #obtenemos el jugador que jugo la carta inicialmente
            in_turn_player = Player.get(sid = room.machine_state_options["id"])
            if in_turn_player is None:
                rootlog.exception("deberia estar el jugador que jugo la carta en machine_state_options y no lo esta")
                raise Exception()
            # obtenemos y verificamos la maquina de estados
            room = player.playing
            if room.machine_state != "PLAYING" and room.machine_state == "FINISHING":
                rootlog.exception("No correspondia defenderse de una carta")
                raise InvalidAccionException("No corresponde defenderse")

            if room.machine_state_options["target"] != player.id:
                rootlog.exception(f"No correspondia que esta persona se defienda")
                raise InvalidAccionException("No estan jugando una carta sobre vos")
            

            #
            if card not in played_card.defense_cards:
                raise InvalidAccionException(f"No se puede defender {played_card.name} con {card.name}")

            events = []
            if on_defense == False:
                events.extend(self.play_card_manager(in_turn_player.sid, room.machine_state_options))
            else:
                if card.name == "¡Nada de barbacoas!":
                    pass

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
    def play_card_manager(self, sent_sid : str, payload):

        try:
            # definimos las cartas que no se pueden jugar
            unplayable_cards = ["La cosa", "Infectado"]

            # inicializamos los servicios
            rs = RoomsService(self.db)
            ps = PlayersService(self.db)
            cs = CardsService(self.db)
            pcs = PlayCardsService(self.db)

            # lista de eventos a informar a los jugadores
            events = []

            # verificamos inputs correctos
            sent_card_id = payload.get("card")
            card_options = payload.get("card_options")
            if sent_card_id is None or card_options is None:
                raise InvalidDataException()

            # obtenemos y verificamos el jugador
            player = Player.get(sid = sent_sid)
            if player is None:
                raise InvalidSidException()

            # obtenemos y verificamos las cartas
            card = Card.get(id = sent_card_id)
            if card is None:
                raise InvalidCidException()

            if card.name in unplayable_cards:
                raise InvalidAccionException(f"No se puede jugar {card.name}")

            if ps.has_card(player, card) == False:
                raise InvalidCardException()

            # obtenemos y verificamos la room
            room = player.playing
            if room.machine_state != "PLAYING":
                rootlog.exception("No correspondia jugar una carta")
                raise InvalidAccionException("No corresponde jugar")

            if room.machine_state_options["id"] != player.id:
                rootlog.exception(f"No era el turno de la persona que intento jugar {room.machine_state_options['id']} - {player.id}")
                raise InvalidAccionException("No es tu turno")

            # caso: la carta jugada es lanzallamas ¡ruido de asadoo!
            events = []

            if card.name == cards.LANZALLAMAS:
                events.extend(pcs.play_lanzallamas(player, room, card, card_options))

            elif card.name == cards.WHISKY:
                events.extend(pcs.play_whisky(player, room, card, card_options))

            elif card.name == cards.SOSPECHA:
                events.extend(pcs.play_sospecha(player, room, card, card_options))

            elif card.name == cards.UPS:
                events.extend(pcs.play_ups(player, room, card, card_options))

            elif card.name == cards.QUE_QUEDE_ENTRE_NOSOTROS:
                events.extend(pcs.play_que_quede_entre_nosotros(player, room, card, card_options))

            elif card.name == cards.ANALISIS:
                events.extend(pcs.play_analisis(player, room, card, card_options))

            elif card.name == cards.CAMBIO_DE_LUGAR:
                events.extend(pcs.play_cambio_de_lugar(player, room, card, card_options))

            elif card.name == cards.VIGILA_TUS_ESPALDAS:
                events.extend(pcs.play_vigila_tus_espaldas(player, room, card, card_options))

            elif card.name == cards.MAS_VALES_QUE_CORRAS:
                events.extend(pcs.play_mas_vale_que_corras(player, room, card, card_options))


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
                # si hago esto cuando quireo notificar no existen mass los jugadores
                # rs.end_game(sent_sid)
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
    def exchange_card_manager(self, sent_sid: str, payload):
        try:
            events = []
            player = Player.get(sid=sent_sid)
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
            if on_defense:
                if first_player:
                    raise InvalidAccionException("No te podes defender si sos el que inicia el intercambio")
                else:
                    #verifiquemos si se puede defender con la carta que esta planteando
                    defense_cards = ["¡No, gracias!"]
                    if card.name not in defense_cards:
                        raise InvalidAccionException(f"No te podes defender con la carta {card.name}")

            rs = RoomsService(self.db)
            #if es la primera persona en decidir la carta a intercambiar
            if room.machine_state_options["stage"] == "STARTING":
                room.machine_state = "EXCHANGING"
                #seteamos la maquina para la segunda etapa del intercambio (solo falta uno en decidir)
                room.machine_state_options={"ids":room.machine_state_options["ids"],
                                            "stage":"FINISHING",
                                            "card_id" : card.id,    #carta de la primera persona en decidir
                                            "player_id":player.id,  #player_id de la primera persona en decidir
                                            "on_defense": on_defense if not first_player else False #si es la segunda persona del intercambio, guarda si se esta defendiendo
                                            }
                #habria que ver si notificamos al primer jugador en seleccionar carta de intercambio de que se acepto su eleccion
                #por ahora luego de que los dos seleccionan se realiza el intercambio y se notifica
                return events
            #esif es la ultima persona que faltaba en decidir
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
                if room.machine_state_options["on_defense"] or on_defense:  #si se esta defendiendo
                    second_player.hand.remove(second_card)
                    cs.give_alejate_card(second_player)
                    events.extend([{
                        "name":"on_game_player_play_defense_card",
                        "body":{"player":second_player.name, "card":second_card.json()},
                        "broadcast": True
                    }])
                    events.extend(rs.next_turn(sent_sid))
                else:
                    try:
                        #realizamos el intercambio si no se estaba defendiendo
                        events.extend(cs.exchange_cards(room, first_player, second_player, first_card, second_card))    #falta ver si se esta defendiendo
                        events.extend(rs.next_turn(sent_sid))
                    except Exception as e:
                        #ante algun error que no provocó cambios, volvemos a comenzar el intercambio
                        print("El intercambio no fue exitoso, volvemso a intentar")
                        player_A = Player.get(id=room.machine_state_options["ids"][0])  #el que inicia el intercambio es el primer id
                        player_B = Player.get(id=room.machine_state_options["ids"][1])  #el que recive solicitud de intercambio es el segundo id
                        if player_A is None or player_B is None or player_A.playing != player_B.playing:
                            rootlog.exception("los jugadores que estaban intercambiando no eran validos cuando se intento realizar otra vez el intercambio")
                        e = InvalidAccionException("Error al intercambiar, seleccione nuevamente")
                        events.extend(e.generate_event(player_A.sid))
                        events.extend(e.generate_event(player_B.sid))
                        events.extend(self.begin_exchange(room, player_A, player_B))
                        return events
            else:
                raise InvalidAccionException("No corresponde iniciar un intercambio")
            return events
        except InvalidAccionException as e:
            return e.generate_event(sent_sid)

    def superinfection_check(self, player_checked: Player, player_exchanging: Player):
        # Superinfeccion

        # - no sos la cosa
        is_not_la_cosa = player_checked.rol != 'LA_COSA'

        # - solo tenes cartas infectado
        only_infected_cards = True
        for card in player_checked.hand:
            only_infected_cards = only_infected_cards and card.name == 'Infectado'

        # solo podes intercambiar cuando vos sos infectado y le das a la cosa
        exchange_possible = player_checked.rol == 'INFECTADO' and player_exchanging.rol == 'LA_COSA'

        is_superinfected = is_not_la_cosa and only_infected_cards and (not exchange_possible)

        return is_superinfected

    def begin_exchange(self, room: Room, player_A: Player, player_B: Player):
        """
        setea la maquina de estados para un intercambio entre player_A y player_B
        asume que los checkeos pertinentes se realizaron (ej que esten en la misma sala)
        """
        events = []
        rs = RoomsService(self.db)

        is_player_a_superinfected = self.superinfection_check(player_A, player_B)
        is_player_b_superinfected = self.superinfection_check(player_B, player_A)
        if is_player_a_superinfected:
            room: Room = player_A.playing
            room.kill_player(player_A)
            events.append({
                "name": "on_game_player_death",
                "body": {"player": player_A.name, "reason": "SUPERINFECCION"},
                "broadcast": True
            })

        if is_player_b_superinfected:
            room: Room = player_B.playing
            room.kill_player(player_B)
            events.append({
                "name": "on_game_player_death",
                "body": {"player": player_B.name, "reason": "SUPERINFECCION"},
                "broadcast": True
            })

        if is_player_a_superinfected or is_player_b_superinfected:
            events.extend(rs.next_turn(player_A.sid))
            return events
        else:
            room.machine_state = "EXCHANGING"
            room.machine_state_options = {"ids": [player_A.id, player_B.id],
                                          "stage": "STARTING"}
            events.append({
                "name": "on_game_begin_exchange",
                "body": {"players": [player_A.name, player_B.name]},
                "broadcast": True
            })
        return events

    def begin_end_of_turn_exchange(self, room : Room):
        in_turn_player = list(room.players.select(lambda player : player.position == room.turn and player.status == "VIVO"))[0]
        if in_turn_player is None:
            rootlog.exception(f"el jugador con posicion {room.turn} no esta en la partida")
            raise Exception()
        rs = RoomsService(self.db)
        return self.begin_exchange(room, in_turn_player, rs.next_player(room))
