from pony.orm import db_session
from app.models import Player, Room, Card
from app.services.exceptions import *
from app.services.mixins import DBSessionMixin
from app.services.players import PlayersService
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
        player_in_game_state.update(
            {"playerData": {
                "name" : player.name,
                "playerID": player.id,
                "role" : player.rol,
                "cards" : [card.json() for card in player.hand]
            }}
        )
        return player_in_game_state

    @db_session
    def play_card(self, sent_sid : str, payload):
        cs = CardsService(self.db)
        events = []
        player = Player.get(sid = sent_sid)
        #card = Card.get(id = payload["card_id"])
        sent_card_id = payload.get("card")
        card_options = payload.get("card_options")
        if sent_card_id is None or card_options is None:
            raise InvalidDataException()
        card = Card.get(id = sent_card_id)   #dejemos esto hasta que el front lo repare
        if player is None:
            raise InvalidSidException()
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
        if card.name == "Lanzallamas":
            print("se jugo una carta de lanzallamas")
            events.extend(cs.play_lanzallamas(player, room, card, card_options))
            #veamos si es uno del lado
        
        self.recalculate_positions(sent_sid)
        player.hand.remove(card)
        room.discarted_cards.add(card)
        return events
        
    @db_session
    def recalculate_positions(self, sent_sid : str):    
        """
            Reasigna posiciones, manteniendo el orden de las personas
            asume que la partida no esta terminada, se puede seguir jugando
        """
        player = Player.get(sid = sent_sid)
        if player is None:
            raise InvalidSidException()
        room = player.playing
        if room.turn is None:
            print("partida inicializada incorrectamente, turno no pre-seteado")
            raise Exception
        id_position = []
        for player in room.players:
            if player.status == "VIVO":
                id_position.append((player.position, player))
        id_position.sort(key  = lambda x : x[0])
        position = 0
        should_update_turn = True
        for pair in id_position:
            if pair[1].position != position and position <= room.turn and should_update_turn:
                room.turn -= 1
                should_update_turn = False
                pass
            pair[1].position = position
            position += 1
        
    @db_session
    def next_turn(self, sent_sid : str):    
        player = Player.get(sid = sent_sid)
        if player is None:
            raise InvalidSidException()
        room = player.playing
        if room.turn is None:
            print("partida inicializada incorrectamente, turno no pre-seteado")
            raise Exception
        if room.machine_state == "INITIAL":
            room.turn = 0
        else:
            room.turn = (room.turn + 1) % (len(room.players.select(lambda player : player.status == "VIVO")))    #cantidad de jugadores que siguen jugando
        expected_player = None
        #asumo que las posiciones estan correctas (ie: no estan repetidas y no faltan)
        for player in room.players:
            if player.position == room.turn and player.status == "VIVO":
                expected_player = player
        if expected_player is None: 
            print(f"el jugador con turno {room.turn} no esta en la partida")
            raise Exception
        room.machine_state = "PLAYING"
        room.machine_state_options = {"id":expected_player.id}
        return self.give_card(expected_player), expected_player.sid
        

    @db_session
    def give_card(self, player:Player):
        room = player.playing
        # se entrega una carta del mazo de disponibles al usuario
        # se borra la carta de room.available, se asigna la carta al usuario y se retorna el objeto carta

        shuffle = len(room.available_cards) == 0
            
        if shuffle:
            # deck temporal que contiene las cartas descartadas
            temp_deck = list(room.discarted_cards)
            # eliminamos todas las cartas descartadas
            room.discarted_cards.clear()
            room.available_cards.clear()
            # asignamos el deck temporal a las cartas disponibles 
            room.available_cards.add(temp_deck)
        
        # obtenemos una carta y la eliminamos
        card_to_deal = list(room.available_cards.random(1))[0]
        room.available_cards.remove(card_to_deal)
        
        # agregamos la carta al jugador
        player.hand.add(card_to_deal)

        # computamos el JSON con la info de la carta y retornamos.
        return card_to_deal.json()
        
    
    @db_session
    def end_game_condition(self, sent_sid : str) -> str:
        """Chequea si se finalizo la partida.

        Args: room (Room): current valid room

        Returns: str: {'GAME_IN_PROGRESS', 'LA_COSA_WON', 'HUMANS_WON'}
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
    def discard_card(self, sent_sid : str, payload):
        # import ipdb
        # ipdb.set_trace()

        # room que esta jugando el jugador
        player = Player.get(sid = sent_sid)
        # carta enviada
        sent_card_id = payload.get("card")
        
        # invalid inputs
        if sent_card_id is None:
            raise InvalidDataException()
        if player is None:
            raise InvalidSidException()
        card = Card.get(id = sent_card_id)  
        if card is None:
            raise InvalidCidException()

        # room actual
        room = player.playing
        # Jugador no esta en la sala
        if room is None or room.status != 'IN_GAME':
            raise InvalidRoomException()
        
        # La carta no pertenece a las cartas del jugador
        if card not in player.hand:
            raise InvalidCardException()
        
        # Estado incorrecto
        if room.machine_state != "PLAYING":
            rootlog.exception("No correspondia descartar una carta")
            raise InvalidAccionException("No corresponde descartar")

        # esta el turno incorrecto
        if room.machine_state_options["id"] != player.id:
            rootlog.exception(f"no era el turno de la persona que intento descartar {room.machine_state_options['id']} {player.id}")
            raise InvalidAccionException(msg="No es tu turno")
        

        # Carta invalida
        infected_count = len(player.hand.select(name='Infectado'))
        invalid_discard_infected = card.name == 'Infectado' and player.rol == 'INFECTADO' and infected_count == 1
        invalid_discard_la_cosa = card.name == 'La cosa'
        if invalid_discard_infected or invalid_discard_la_cosa:
            raise InvalidCardException() 

        player.hand.remove(card)
        room.discarted_cards.add(card)
        return card.id

    @db_session
    def exchange_cards(self, room: Room, player_A : Player, player_B : Player, card_A : Card, card_B:Card):
        """ Realiza el intercambio de cartas.
        
        Args:
            room (Room): Room valida en la que ambos players estan jugando.
            sender (Player): el jugador que al final de su turno comienza a intercambiar una carta
            reciever (Player): el jugador siguiente en la orden de turno
            card_s (Card): carta que selecciona el jugador "sender" para intercambiar
            card_r (_type_): carta que selecciona el jugador "reciever" para intercambiar

        Returns:
            None    
        """       
        qty_players = len(room.players.select())
        valid_player_position = player_A.position == (player_B.position -1)%qty_players and room.direction
        if not valid_player_position:
            raise InvalidExchangeParticipants()
        
        sender_not_in_turn = player_A.position != room.turn
        if sender_not_in_turn:
            raise PlayerNotInTurn()
        
        card_not_in_hand_sender = len(player_A.hand.select(name=card_A.name)) == 0
        card_not_in_hand_reciever = len(player_B.hand.select(name=card_B.name)) == 0
        if card_not_in_hand_reciever or card_not_in_hand_sender:
            raise CardNotInPlayerHandExeption()
        
        lacosa_exchange = (card_A.name == 'La cosa') or (card_B.name == 'La cosa')
        if lacosa_exchange:
            raise RoleCardExchange()
        
        # intercambio invalido de cartas 'Infectado': 
        # - un humano intercambia infectado
        invalid_infected_exchange = (player_A.rol == 'HUMANO' and card_A.name == 'Infectado') or (player_B.rol=='HUMANO' and card_B.name=='Infectado')
        if invalid_infected_exchange:
            raise InvalidCardExchange()
        
        # - un infectado intercambia su ultima infeccion
        invalid_infected_exchange = player_A.rol == 'INFECTADO' and card_A.name == 'Infectado' and len(player_A.hand.select(name='Infectado')) == 1
        invalid_infected_exchange = invalid_infected_exchange or (player_B.rol == 'INFECTADO' and card_B.name == 'Infectado' and len(player_B.hand.select(name='Infectado')) == 1)
        if invalid_infected_exchange:
            raise RoleCardExchange()
        
        # - un infectado intercambia una carta infectado con un humano
        invalid_infected_exchange = player_A.rol=='INFECTADO' and player_B.rol=='HUMANO' and card_A.name=='Infectado'
        invalid_infected_exchange = invalid_infected_exchange or (player_B.rol=='INFECTADO' and player_A.rol=='HUMANO' and card_B.name=='Infectado')
        if invalid_infected_exchange:
            raise InvalidCardExchange()
        
        
        
        if card_A.name == 'Infectado' and player_A.rol == 'LA_COSA':
            player_B.rol = 'INFECTADO'
        
        if card_B.name == 'Infectado' and player_B.rol == 'LA_COSA': 
            player_A.rol = 'INFECTADO'
            
        player_A.hand.remove(card_A)
        player_A.hand.add(card_B)
        player_B.hand.remove(card_B)
        player_B.hand.add(card_A)
        
        return

    @db_session
    def exchange_card_manager(self, sent_sid : str, payload):
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

        print(room.machine_state_options["ids"])
        exchanging_players = room.machine_state_options.get("ids")
        if exchanging_players is None:
            rootlog.exception("deberia existir campo ids en estado intercambio")
            raise Exception()
        if room.machine_state_options["id"] not in room.machine_state_options["ids"]:
            rootlog.exception(f"no corresponde que la persona intercambie{room.machine_state_options['id']} {player.id}")
            raise InvalidAccionException("No corresponde iniciar un intercambio")
            first_player = exchanging_players[0] == player.id
        if room.machine_state_options["state"] == "STARTING":
            room.machine_state = "EXCHANGING"
            room.machine_state_options = {"id":player.id, 
                                         "stage":"FINISHING",
                                         "card_id" : card.id,
                                         "player_id":player.id,
                                         "on_defense": on_defense if not first_player else None}
        if room.machine_state_options["state"] == "FINISHING" and player.id != room.machine_state_options["player_id"]:
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
            self.exchange_cards(room, first_player, second_player, first_card, second_card)
            print(f"intercambio entre {first_player.name} y {second_player.name} finalizado exitosamente")
        else:
            raise InvalidAccionException("No corresponde iniciar un intercambio") 
        
        