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
    def exchange_cards(self, room: Room, player_A : Player, player_B : Player, card_A : Card, card_B:Card):
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
        qty_players = len(room.players.select())
        valid_player_position = player_A.position == (player_B.position -1)%qty_players and room.direction
        if not valid_player_position:
            raise InvalidExchangeParticipants()
        
        # sender_not_in_turn = player_A.position != room.turn
        # if sender_not_in_turn:
        #     raise PlayerNotInTurn()
        
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
        
        return[{
                "name":"on_game_finish_exchange",
                "body":{"players":[player_A.name, player_B.name]},
                "broadcast":True
        },{
                "name":"on_game_exchange_result",
                "body":{"card_in":card_B.id, "card_out":card_A.id},
                "broadcast":False,
                "receiver_sid":player_A.sid
        },{
                "name":"on_game_exchange_result",
                "body":{"card_in":card_A.id, "card_out":card_B.id},
                "broadcast":False,
                "receiver_sid":player_B.sid
        }]
        

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

            # Carta invalida
            infected_count = len(player.hand.select(name='Infectado'))
            invalid_discard_infected = card.name == 'Infectado' and player.rol == 'INFECTADO' and infected_count == 1
            invalid_discard_la_cosa = card.name == 'La cosa'
            if invalid_discard_infected or invalid_discard_la_cosa:
                raise InvalidCardException() 

            player.hand.remove(card)
            room.discarted_cards.add(card)
            #TODO!  Falta agregar un evento de que un jugdor descarto una carta
            from .rooms import RoomsService
            rs = RoomsService(self.db)

            events.extend([{
                "name":"on_game_player_discard_card",
                "body":{"player":player.name},
                "broadcast":True
            }])
            # events.extend(rs.next_turn(sent_sid))
            # return events
            from .games import GamesService
            gs = GamesService(self.db)
            events.extend(gs.begin_end_of_turn_exchange(room))
            return events
        except InvalidAccionException as e:
            return e.generate_event(sent_sid)

    def play_lanzallamas(self, player : Player, room : Room, card : Card, card_options):
        """Juega una carta lanzallamas.

        Args: player, card, card_options

        Returns: list(tuples(event_name, event_body))
        """
        #lista de eventos que vamos a retornar
        events = []
        target_id = card_options.get("target")
        if target_id is None:
            raise InvalidAccionException("Objetivo invalido")
        target_player = Player.get(id = target_id)
        if target_player is None or target_player.status != "VIVO":
            raise InvalidAccionException("Objetivo Invalido")

        #veamos que esten al lado
        if player.position is None or target_player.position is None:
            #seleccionar una buena excepcion
            raise Exception()
        
        # Vemos que los jugadores esten adyacentes:
        if abs(player.position - target_player.position) != 1 and \
            abs(player.position - target_player.position) !=  len(room.players.select(status = "VIVO"))-1:
            #falta enriquecer con info a este excepcion
            raise InvalidAccionException("El objetivo no esta al lado tuyo")

        target_player.status = "MUERTO"  
        events.append({"name":"on_game_player_death",
                       "body":{"player":target_player.name},
                       "broadcast":True
                      })
        return events