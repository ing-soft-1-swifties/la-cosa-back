from typing import List
from pony.orm import db_session
from app.models import Player, Room, Card
from app.models.entities import MachineState
from app.services.exceptions import *
from app.services.mixins import DBSessionMixin
from app.services.play_card import PlayCardsService
from app.services.players import PlayersService
from app.services.rooms import RoomsService
from app.services.cards import CardsService
from app.logger import rootlog
from app.models.constants import CardName

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
                "quarantine" : player.quarantine_turns_left(),
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
            "doors_positions": room.get_obstacles_positions(),
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
            ps = PlayersService(self.db)
            cs = CardsService(self.db)

            # lista de eventos a informar a los jugadores
            events = []     

            # verificamos inputs correctos            
            sent_card_id = payload.get("card")
            on_defense: bool = payload.get("on_defense")

            # obtenemos y verificamos el jugador
            player = Player.get(sid = sent_sid)
            if player is None:
                raise InvalidSidException()

            if on_defense is None or not isinstance(on_defense, bool):
                raise InvalidDataException()

            room: Room = player.playing
            played_card = room.suspended_card

            if room.machine_state != MachineState.DEFENDING:
                rootlog.exception("No correspondia defenderse de una carta")
                raise InvalidAccionException("No corresponde defenderse")

            if room.suspended_card_target != player:
                rootlog.exception(f"No correspondia que esta persona se defienda")
                raise InvalidAccionException("No estan jugando una carta sobre vos")

            # Early return, ejecutamos el efecto de la carta suspendida
            if not on_defense:
                #obtenemos el jugador que jugo la carta inicialmente
                player_in_turn = Player.get(position = room.turn, playing = room)
                played_card_options = room.machine_state_options.get("card_options", {})

                if played_card is None:
                    raise InvalidCidException()

                if player_in_turn is None:
                    rootlog.exception("deberia estar el jugador que jugo la carta en machine_state_options y no lo esta")
                    raise Exception()


                events.extend(self.dispatch_card_effect(player_in_turn.sid, player_in_turn, room, played_card, played_card_options))

                return events

            defense_card = Card.get(id = sent_card_id) 

            if sent_card_id is None:
                raise InvalidDataException()

            if not ps.has_card(player, defense_card):
                raise InvalidCardException()

            assert room.machine_state is not None

            if defense_card.name not in self.defense_for_card(played_card.name):
                raise InvalidAccionException(f"No se puede defender {played_card.name} con {defense_card.name}")

            assert room.machine_state_options is not None

            events.extend(self.dispatch_card_effect(sent_sid, player, room, defense_card, {}))

            # Descartar la carta
            player.hand.remove(defense_card)
            room.discarted_cards.add(defense_card)

            # Dar carta "Alejate" al jugador que se defendio
            cs.give_alejate_card(player)
            
            return events
        except InvalidAccionException as e:
            return e.generate_event(sent_sid)

    def dispatch_exchange_defense_card_effect(self, sent_sid, player, room, card, card_options):
        pcs = PlayCardsService(self.db)
        rs = RoomsService(self.db)
        events = []

        if card.name == CardName.FALLASTE:
            events.extend(pcs.play_fallaste(player, room, card, card_options))
        elif card.name == CardName.NO_GRACIAS:
            events.extend(pcs.play_no_gracias(player, room, card, card_options))
            events.extend(rs.next_turn(sent_sid))
        elif card.name == CardName.ATERRADOR:
            events.extend(pcs.play_aterrador(player, room, card, card_options))
            print(events)
            events.extend(rs.next_turn(sent_sid))

        room.discard_card(player, card)
        return events


    def dispatch_card_effect(self, sent_sid, player, room, card, card_options):
        pcs = PlayCardsService(self.db)
        rs = RoomsService(self.db)
        events = []

        rootlog.exception(f"El jugador <{player.name}> jugo la carta <{card.name}>")

        if card.name == CardName.LANZALLAMAS:
            events.extend(pcs.play_lanzallamas(player, room, card, card_options))

        elif card.name == CardName.WHISKY:
            events.extend(pcs.play_whisky(player, room, card, card_options))

        elif card.name == CardName.NADA_DE_BARBACOAS:
            events.extend(pcs.play_nada_de_barbacoas(player, room, card, card_options))

        elif card.name == CardName.AQUI_ESTOY_BIEN:
            events.extend(pcs.play_aqui_estoy_bien(player, room, card, card_options))

        elif card.name == CardName.SOSPECHA:
            events.extend(pcs.play_sospecha(player, room, card, card_options))

        elif card.name == CardName.SEDUCCION:
            events.extend(pcs.play_seduccion(player, room, card, card_options))
            return events

        elif card.name == CardName.UPS:
            events.extend(pcs.play_ups(player, room, card, card_options))

        elif card.name == CardName.QUE_QUEDE_ENTRE_NOSOTROS:
            events.extend(pcs.play_que_quede_entre_nosotros(player, room, card, card_options))

        elif card.name == CardName.ANALISIS:
            events.extend(pcs.play_analisis(player, room, card, card_options))

        elif card.name == CardName.CAMBIO_DE_LUGAR:
            events.extend(pcs.play_cambio_de_lugar(player, room, card, card_options))

        elif card.name == CardName.VIGILA_TUS_ESPALDAS:
            events.extend(pcs.play_vigila_tus_espaldas(player, room, card, card_options))

        elif card.name == CardName.MAS_VALES_QUE_CORRAS:
            events.extend(pcs.play_mas_vale_que_corras(player, room, card, card_options))

        elif card.name == CardName.OLVIDADIZO:
            events.extend(pcs.play_olvidadizo(player, room, card, card_options))

        elif card.name == CardName.CITA_A_CIEGAS:
            events.extend(pcs.play_cita_a_ciegas(player, room, card, card_options))

        elif card.name == CardName.CUARENTENA:
            events.extend(pcs.play_cuarentena(player, room, card, card_options))

        elif card.name == CardName.CUERDAS_PODRIDAS:
            events.extend(pcs.play_cuerdas_podridas(player, room, card, card_options))

        elif card.name == CardName.PUERTA_ATRANCADA:
            events.extend(pcs.play_puerta_atrancada(player, room, card, card_options))

        elif card.name == CardName.HACHA:
            events.extend(pcs.play_hacha(player, room, card, card_options))

        elif card.name == CardName.UNO_DOS:
            events.extend(pcs.play_uno_dos(player, room, card, card_options))

        elif card.name == CardName.TRES_CUATRO:
            events.extend(pcs.play_tres_cuatro(player, room, card, card_options))

        elif card.name == CardName.ES_AQUI_LA_FIESTA:
            events.extend(pcs.play_es_aqui_la_fiesta(player, room, card, card_options))

        else:
            rootlog.exception(f"Esta carta ({card.name}) no esta implementada")
            events.append(
                {
                    'name': 'on_game_player_play_card',
                    'body': {
                        'card_id': card.id,
                        'card_name': card.name,
                        'card_options': card_options,
                        'player_name': player.name
                    },
                    'broadcast': True,
                },
            )

        rs.recalculate_positions(sent_sid)
        player.hand.remove(card)
        room.discarted_cards.add(card)

        result, json = self.end_game_condition_one_player(sent_sid)

        if result != "GAME_IN_PROGRESS":
            events.append({
                "name": "on_game_end",
                "body": json,
                "broadcast": True
            })
        else:
            events.extend(self.begin_end_of_turn_exchange(room))
        return events

    @staticmethod
    def defense_for_card(card_name: str) -> list[str]:
        defense_dict = {
            "Lanzallamas": ["¡Nada de barbacoas!"],
            "¡Cambio de lugar!": ["Aquí estoy bien"],
            "¡Más vale que corras!": ["Aquí estoy bien"]
        }

        return defense_dict.get(card_name, [])


    @db_session
    def play_card_manager(self, sent_sid : str, payload):

        # definimos las cartas que no se pueden jugar
        unplayable_cards = ["La cosa", "Infectado"]
        
        # inicializamos los servicios
        ps = PlayersService(self.db)

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
        
        if not ps.has_card(player, card):
            rootlog.exception("Un jugador quiso jugar una carta la cual no era de su pertenencia")
            raise InvalidCardException()

        if card.type not in ["PANICO", "ALEJATE"]:
            raise InvalidDataException()

        # obtenemos y verificamos la room
        room: Room = player.playing
        assert room is not None
        assert room.machine_state_options is not None
        if room.machine_state not in [MachineState.PLAYING, MachineState.PANICKING]:
            rootlog.exception("No correspondia jugar una carta")
            raise InvalidAccionException("No corresponde jugar")

        if room.turn != player.position: #type:ignore
            rootlog.exception(f"No era el turno de la persona que intento jugar {room.machine_state_options['id']} - {player.id}") # type:ignore
            raise InvalidAccionException("No es tu turno")

        defense = False

        # veamos si es una carta que se juega sobre alguien
        # vemos tambien si es posible que el jugador objetivo se defienda
        # en cuyo caso agregamos un evento para avisarle que debe defenderse
        if card.need_target:
            target_id = card_options.get("target", None)
            if target_id is None:
                raise InvalidAccionException("Objetivo invalido")
            target = Player.get(id = target_id)
            if target is None or not target.is_alive():
                raise InvalidAccionException("Objetivo invalido")


            if not card.name in [CardName.HACHA, CardName.PUERTA_ATRANCADA] and (card.target_adjacent_only and not room.are_players_adjacent(player, target)):
                raise InvalidAccionException("El jugador no esta a tu lado")

            if not card.ignore_quarantine and target.is_in_quarantine():
                raise InvalidAccionException("El jugador objetivo esta en cuarentena")

            are_players_blocked = room.are_players_blocked(player, target)

            if not card.ignore_locked_door and are_players_blocked:
                raise InvalidAccionException("No puede jugar debido a la puerta atrancada.")

            #veamos si la persona sobre la que se esta jugando la carta tiene la posibilidad de defenderse
            defense = any([defense_card in target.hand.name for defense_card in self.defense_for_card(card.name)])

            # Si se puede defender, dejamos asentada la info necesaria para ejecutar su efecto luego
            if defense:
                room.suspended_card = card
                room.suspended_card_target = target
                room.machine_state = MachineState.DEFENDING
                room.machine_state_options = {
                    "card_options": card_options
                }

        # Validaciones propias de cuando la carta es de panico
        if room.machine_state == MachineState.PANICKING and card.type != "PANICO":
            raise InvalidAccionException("Debes jugar la carta de pánico en tu mano.")
        if room.machine_state == MachineState.PANICKING:

            card_picking_amount = room.machine_state_options.get("card_picking_amount", None)

            assert card_picking_amount is not None

            if(card_picking_amount > 0):
                cards = card_options.get("cards")
                assert cards is not None and isinstance(cards, list)
                if len(player.hand.select(lambda c : c.id in cards)) != card_picking_amount:
                    raise InvalidAccionException(f"Debes elegir {card_picking_amount} cartas para jugar la carta.")

        # si no es posible defenderse, llamamos al efecto de la carta de una
        if not defense:
            events.extend(self.dispatch_card_effect(sent_sid, player, room, card, card_options))
        else:
            events.append({
                    'name': 'on_game_player_play_card',
                    'body': {
                        'card_id': card.id,
                        'card_name': card.name,
                        'card_options': card_options,
                        'player_name': player.name
                    },
                    'broadcast': True,
                })

        player.hand.remove(card)
        room.discarted_cards.add(card)
        

        return events

    @db_session
    def discard_card_manager(self, sent_sid : str, payload):
        cs = CardsService(self.db)
        events = cs.discard_card(sent_sid, payload)
        return events

    @db_session
    def end_game_condition_one_player(self, sent_sid: str):
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
        if room.players.select(lambda p:p.rol == 'LA_COSA').first().status == 'MUERTO':
            ret = 'HUMANS_WON'
            info = {
                "winner_team": "HUMANOS",
                "winner": list(map(lambda x: x.name, list(room.players.select(rol='HUMANO')))),
                "roles": roles
            }

        # Si queda solo un sobreviviente
        if len(room.players.select(lambda p: p.status != 'MUERTO')) == 1:
            survivor: Player = list(room.players.select(lambda p: p.status != 'MUERTO'))[0] # type: ignore
            # Chequeo si es la cosa
            if survivor.rol == 'LA_COSA':
                ret = 'LA_COSA_WON'
                info = {
                    "winner_team": "LA_COSA",
                    "winner": list(map(lambda x: x.name, list(room.players.select(rol='LA_COSA')))),
                    "roles": roles
                }
            else:
                ret = 'HUMANS_WON'
                info = {
                    "winner_team": "HUMANOS",
                    "winner": list(map(lambda x: x.name, list(room.players.select(rol='HUMANO')))),
                    "roles": roles
                }
        return ret, info

    @db_session
    def end_game_condition_la_cosa(self, sent_sid: str):
        """La cosa chequea si se finalizo la partida.

        Args: room (Room): current valid room

        Returns: event: on_game_end
        """


        player = Player.get(sid=sent_sid)

        if player is None:
            raise InvalidSidException()

        if player.rol != 'LA_COSA':
            raise InvalidAccionException(msg="Alguien quiso finalizar la partida y nos es la cosa")

        # inputs
        room: Room = player.playing

        roles = []
        for player in room.players:
            roles.append((player.name, player.rol))

        if len(room.players.select(lambda p: p.status != 'MUERTO' and p.rol == 'HUMANO')) == 0:

            info = {
                    "winner_team": "LA_COSA",
                    "winner": list(map(lambda x: x.name, list(room.players.select(rol='LA_COSA')))),
                    "roles": roles
                }
        else:

            info = {
                "winner_team": "HUMANOS",
                "winner": list(map(lambda x: x.name, list(room.players.select(rol='HUMANO')))),
                "roles": roles
            }

        event = [{
            "name": "on_game_end",
            "body": info,
            "broadcast": True
        }]

        return event

    @db_session
    def exchange_card_manager(self, sent_sid: str, payload):
        try:
            #lista de eventos a enviar al front
            events = []
            #obtenemos el jugador 
            player = Player.get(sid=sent_sid)
            if player is None:
                raise InvalidSidException()
            #obtenemos la carta y la intension de defensa
            sent_card_id = payload.get("card")
            on_defense = payload.get("on_defense")
            if sent_card_id is None or on_defense is None:
                raise InvalidDataException()
            card = Card.get(id = sent_card_id)
            if card is None:
                raise InvalidCidException()
            #checkeamos que la carta sea cambiable
            unchangable_cards = ["La cosa"]
            if card.name in unchangable_cards:
                raise InvalidAccionException(f"No se puede intercambiar {card.name}")
            room: Room = player.playing
            #checkeamos que la presiona tenga la carta que quiere cambiar
            ps = PlayersService(self.db)
            if ps.has_card(player, card) == False:
                raise InvalidCardException()
            #checkeamos maquina de estados en intercambio
            room = player.playing
            if room.machine_state != "EXCHANGING":
                rootlog.exception("no correspondia intercambiar una carta")
                raise InvalidAccionException("No corresponde intercambiar")
            #obtenemos la lista de ids de jugadores que les corresponde intercambiar
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
                    defense_cards = [CardName.NO_GRACIAS, CardName.FALLASTE, CardName.ATERRADOR]
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
                                            "on_defense": on_defense if not first_player else False, #si es la segunda persona del intercambio, guarda si se esta defendiendo
                                            "compute_infection": room.machine_state_options.get("compute_infection")
                                            }
                #habria que ver si notificamos al primer jugador en seleccionar carta de intercambio de que se acepto su eleccion
                #por ahora luego de que los dos seleccionan se realiza el intercambio y se notifica
                return events
            #esif es la ultima persona que faltaba en decidir
            elif room.machine_state_options["stage"] == "FINISHING" and player.id != room.machine_state_options["player_id"]:
                #obtengo los datos de que jugadores van a intercambiar y que cartas
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
                #obtenemos las cartas segun quien fue el primer jugador en llamar a el exchange_manager
                first_card = card if is_first_player else Card.get(id = room.machine_state_options["card_id"])
                second_card = card if not is_first_player else Card.get(id = room.machine_state_options["card_id"])
                from .cards import CardsService
                cs = CardsService(self.db)
                
                # CUARENTENA
                room.get_current_player().decrease_quarantine()
                if room.machine_state_options["on_defense"] or (on_defense and not is_first_player):  #si se esta defendiendo
                    #second_player.hand.remove(second_card)
                    cs.give_alejate_card(second_player)
                    events.extend([{
                        "name":"on_game_player_play_defense_card",
                        "body":{"player_name":second_player.name, "card_name":second_card.name},
                        "broadcast": True
                    }])
                    #ahora veamos los efectos que induce la defensa para la carta jugada
                    card_options = {}
                    if(second_card.name == CardName.FALLASTE):
                        card_options = {
                            "starter_player_id" : first_player.id
                        }
                    elif(second_card.name == CardName.ATERRADOR):
                        card_options = {
                            "starter_card_id" : first_card.id,
                            "starter_name" : first_player.name
                        }

                    events.extend(self.dispatch_exchange_defense_card_effect(sent_sid, second_player, room, second_card, card_options))

                #si la persona que no inicio el intercambio no se esta defendiendo
                else:
                    try:
                        #realizamos el intercambio si no se estaba defendiendo
                        compute_infection_actual = room.machine_state_options.get("compute_infection")
                        events.extend(cs.exchange_cards(room, first_player,
                                                        second_player,
                                                        first_card,
                                                        second_card,
                                                        room.machine_state_options["compute_infection"]))   
                        events.extend(rs.next_turn(sent_sid))
                    except Exception as e:
                        #ante algun error que no provocó cambios, volvemos a comenzar el intercambio
                        print("El intercambio no fue exitoso, volvemso a intentar")
                        player_A = Player.get(id=room.machine_state_options["ids"][0])  #el que inicia el intercambio es el primer id
                        player_B = Player.get(id=room.machine_state_options["ids"][1])  #el que recive solicitud de intercambio es el segundo id
                        if player_A is None or player_B is None or player_A.playing != player_B.playing:
                            rootlog.exception("los jugadores que estaban intercambiando no eran validos cuando se intento realizar otra vez el intercambio")
                        compute_infection_actual = room.machine_state_options.get("compute_infection")
                        e = InvalidAccionException("Error al intercambiar, seleccione nuevamente")
                        events.extend(e.generate_event(player_A.sid))
                        events.extend(e.generate_event(player_B.sid))
                        events.extend(self.begin_exchange(room, player_A, player_B, compute_infection=compute_infection_actual))
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


    def begin_exchange(self, room: Room, player_A: Player, player_B: Player, compute_infection = True, blockable = True)-> list[dict]:
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

        if is_player_a_superinfected or is_player_b_superinfected or (room.are_players_blocked(player_A, player_B) and blockable):
            events.extend(rs.next_turn(player_A.sid))
            return events
        else:
            room.machine_state = "EXCHANGING"
            room.machine_state_options = {"ids": [player_A.id, player_B.id],
                                          "stage": "STARTING",
                                          "compute_infection": compute_infection}
            events.append({
                "name": "on_game_begin_exchange",
                "body": {"players": [player_A.name, player_B.name]},
                "broadcast": True
            })
        return events

    def begin_end_of_turn_exchange(self, room : Room):
        in_turn_player = room.get_player_by_pos(room.turn)
        if in_turn_player is None:
            rootlog.exception(f"el jugador con posicion {room.turn} no esta en la partida")
            raise Exception()
        rs = RoomsService(self.db)
        return self.begin_exchange(room, in_turn_player, rs.next_player(room))
