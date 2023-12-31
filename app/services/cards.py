from pony.orm import db_session
from app.models import Player, Card, Room
from app.services.exceptions import *
from app.services.mixins import DBSessionMixin
from app.logger import rootlog

class CardsService(DBSessionMixin):
    pass

    @db_session
    def card_to_JSON_from_cid(self, card_id : int):
        card = Card.get(id = card_id)
        if card is None:
            raise InvalidCardException()
        return card.json()

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
        return card_to_deal

    @db_session
    def give_alejate_card(self, player:Player) -> Card:
        """ Toma un jugador y le entrega la primera carta de alejate disponible, no hace shuffle de ser necesario, solo obtiene la carta del maso de descartes
        Returns:
            Carta que se entregó
        """
        room = player.playing
        alejate_available_cards = room.available_cards.select(type = "ALEJATE")
        alejate_discarted_cards = room.discarted_cards.select(type = "ALEJATE")
        card_to_deal = None
        if len(list(alejate_available_cards)) == 0:
            if(len(list(alejate_discarted_cards)) == 0):
                rootlog.exception("no hay cartas de tipo Alejate en ninguno de los dos masos")
                raise Exception()
            card_to_deal = list(alejate_discarted_cards.random(1))[0]
            room.discarted_cards.remove(card_to_deal)
        else:
            card_to_deal = list(alejate_available_cards.random(1))[0]
            room.available_cards.remove(card_to_deal)

        # agregamos la carta al jugador
        player.hand.add(card_to_deal)
        return card_to_deal

    @db_session
    def exchange_cards(self, room: Room, player_A : Player, player_B : Player, card_A : Card, card_B:Card, compute_infection = True):
        """ Realiza el intercambio de cartas.
        
        Args:
            room (Room): Room valida en la que ambos players estan jugando.
            sender (Player): el jugador que al final de su turno comienza a intercambiar una carta
            reciever (Player): el jugador siguiente en la orden de turno
            card_s (Card): carta que selecciona el jugador "sender" para intercambiar
            card_r (_type_): carta que selecciona el jugador "reciever" para intercambiar

        Returns:
            Events   
        """       
        #lista de eventos a retornar
        events = []
        # qty_players = len(room.players.select())
        # valid_player_position = player_A.position == (player_B.position -1)% qty_players and room.direction
        # if not valid_player_position:
        #     raise InvalidExchangeParticipants()
        
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
        
        if compute_infection == True:
            if card_A.name == 'Infectado' and player_A.rol == 'LA_COSA':
                player_B.rol = 'INFECTADO'
            
            if card_B.name == 'Infectado' and player_B.rol == 'LA_COSA': 
                player_A.rol = 'INFECTADO'

        quarantine = []
        if player_A.is_in_quarantine():
            quarantine.append(
                {
                    'player_name': player_A.name,
                    'card': card_A.json()
                }
            )

        if player_B.is_in_quarantine():
            quarantine.append(
                {
                    'player_name': player_B.name,
                    'card': card_B.json()
                }
            )

        
            
        player_A.hand.remove(card_A)
        player_A.hand.add(card_B)
        player_B.hand.remove(card_B)
        player_B.hand.add(card_A)

        return [
            {
                "name": "on_game_finish_exchange",
                "body": {
                    "players": [player_A.name, player_B.name],
                    "quarantine": None if quarantine == [] else quarantine
                },
                "broadcast": True,
                "except_sid": [player_A.sid, player_B.sid]
            },
            {
                "name": "on_game_finish_exchange",
                "body": {
                    "players": [player_A.name, player_B.name],
                    "quarantine": None if quarantine == [] else quarantine,
                    "card_in": card_B.json(),
                    "card_out": card_A.json()
                },
                "broadcast": False,
                "receiver_sid": player_A.sid
            },
            {
                "name": "on_game_finish_exchange",
                "body": {
                    "players": [player_A.name, player_B.name],
                    "quarantine": None if quarantine == [] else quarantine,
                    "card_in": card_A.json(),
                    "card_out":card_B.json()
                },
                "broadcast": False,
                "receiver_sid": player_B.sid
            }
        ]



    @db_session
    def discard_card(self, sent_sid : str, payload):
        try:
            #eventos que vamos a retornar para ser enviados a los jugdores
            events = []
            player = Player.get(sid = sent_sid)
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

            events.extend(self.discard_card_with_validation(player, card))

            # events.extend(rs.next_turn(sent_sid))
            # return events
            from .games import GamesService
            gs = GamesService(self.db)
            events.extend(gs.begin_end_of_turn_exchange(room))
            return events
        except InvalidAccionException as e:
            return e.generate_event(sent_sid)

    def discard_card_with_validation(self, player: Player, card: Card):
        events = []
        room: Room = player.playing
        # Carta invalida
        infected_count = len(player.hand.select(name='Infectado'))
        invalid_discard_infected = card.name == 'Infectado' and player.rol == 'INFECTADO' and infected_count == 1
        invalid_discard_la_cosa = card.name == 'La cosa'
        if invalid_discard_infected or invalid_discard_la_cosa:
            raise InvalidCardException() 

        player.hand.remove(card)
        room.discarted_cards.add(card)
        from .rooms import RoomsService
        rs = RoomsService(self.db)

        quarantine = []
        if player.is_in_quarantine():
            quarantine.append(
                {
                    'player_name': player.name,
                    'card': card.json()
                }
            )

        events.append(
            {
                "name": "on_game_player_discard_card",
                "body": {
                    "player": player.name,
                    "quarantine": None if quarantine == [] else quarantine
                },
                "broadcast": True
            }
        )

        return events
