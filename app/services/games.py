from ast import List
from pony.orm import count, db_session, Set
from app.models import Player, Room, Card
from app.services.exceptions import *
from app.services.mixins import DBSessionMixin
from app.services.players import PlayersService
from app.logger import rootlog

class GamesService(DBSessionMixin):

    def card_to_JSON(self, card: Card):
        return {
            'id': card.id,
            'name': card.name,
            'description': card.description,
            'type': card.type,
            'subType': card.sub_type
        }

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
                "playerID": player.id,
                "role" : player.rol,
                "cards" : [self.card_to_JSON(card) for card in player.hand]
            }}
        )
        return player_in_game_state

    @db_session
    def play_card(self, sent_sid : str, payload):
        player = Player.get(sid = sent_sid)
        #card = Card.get(id = payload["card_id"])
        card = Card.get(id = payload["card"])   #dejemos esto hasta que el front lo repare
        if player is None:
            raise InvalidSidException()
        if card is None:
            raise InvalidCidException()
        room = player.playing
        ps = PlayersService(self.db)
        if ps.has_card(player, card) == False:
            raise InvalidCardException()
        if room.machine_state != "PLAYING":
            rootlog.exception("no correspondia jugar una carta")
            raise InvalidAccionException()
        if room.machine_state_options["id"] != player.id:
            rootlog.exception(f"no era el turno de la persona que intento jugar {room.machine_state_options['id']} {player.id}")
            raise InvalidAccionException()

        #caso: la carta jugada es lanzallamas ¡ruido de asadoo!
        if card.name == "Lanzallamas":
            print("se jugo una carta de lanzallamas")
            pass
           

        #se juega una carta, notar que van a ocurrir eventos (ej:alguien muere), debemos llevar registro
        #para luego notificar al frontend (una propuesta es devolve una lista de eventos con sus especificaciones)
        #a todos los afectados por el evento se les reenvia el game_state
        events = []
        #el metodo anterior retorna la carta que recibio alguna la siguiente persona
        #falta implementar la muestra de eventos
        return events
        
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
            room.turn = (room.turn + 1) % (len(room.players.select(lambda player : player.status != 1)))    #cantidad de jugadores que siguen jugando
        expected_player = None
        #asumo que las posiciones estan correctas (ie: no estan repetidas y no faltan)
        for player in room.players:
            if player.position == room.turn:
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
        return self.card_to_JSON(card_to_deal)
    
    @db_session
    def end_game_condition(self, room:Room) -> str:
        """Chequea si se finalizo la partida.

        Args: room (Room): current valid room

        Returns: str: {'GAME_IN_PROGRESS', 'LA_COSA_WON', 'HUMANS_WON'}
        """
        
        ret = 'GAME_IN_PROGRESS'
        # Si queda solo un sobreviviente     
        if len(room.players.select(lambda p : p.status != 'MUERTO')) == 1:
            survivor : Player = list(room.players.select(lambda p : p.status != 'MUERTO'))[0]
            # Chequeo si es la cosa
            if survivor.rol == 'LA_COSA':
                ret='LA_COSA_WON'
            else: 
                ret='HUMANS_WON'
        
        # Chequeo el estado de la cosa
        la_cosa : Player = list(room.players.select(lambda p : p.rol == 'LA_COSA'))[0]
        if la_cosa.status == 'MUERTO':
            ret='HUMANS_WON'
        
        qty_alive_players = len(room.players.select(lambda p : p.status != 'MUERTO'))
        qty_alive_non_human_players = len(room.players.select(lambda p : p.status != 'MUERTO' and p.rol != 'HUMANO'))
        if qty_alive_non_human_players == qty_alive_players: 
            ret='LA_COSA_WON'
                
        return ret
    
    @db_session
    def discard_card(self, player: Player, card: Card):
        """
        Descarta una carta del jugador en la sala actual.

        Parámetros:
            player (Player): El jugador que desea descartar una carta.
            card (Card): La carta que el jugador desea descartar.

        Excepciones:
            PlayerNotInRoom: Si el jugador no se encuentra en ninguna sala.
            CardNotInPlayerHandException: Si la carta no pertenece a las cartas del jugador.
            PlayerNotInTurn: Si el jugador no se encuentra en su turno.
            InvalidCardException: Si se intenta descartar una carta inválida, como "Infectado" cuando el jugador es un "INFECTADO"
                y solo tiene una carta "Infectado" en su mano, o una carta "La cosa".

        Retorna:
            None
        """
        # room que esta jugando el jugador
        room = player.playing
        
        # Jugador no esta en la sala
        if room is None or room.status != 'IN_GAME':
            raise InvalidRoomException()

        # La carta no pertenece a las cartas del jugador
        if card not in player.hand:
            raise CardNotInPlayerHandExeption()        

        # Jugador no esta en su turno
        if player.position != room.turn:
            raise PlayerNotInTurn()

        # Carta invalida
        infected_count = len(player.hand.select(name='Infectado'))
        invalid_discard_infected = card.name == 'Infectado' and player.rol == 'INFECTADO' and infected_count == 1
        invalid_discard_la_cosa = card.name == 'La cosa'
        if invalid_discard_infected or invalid_discard_la_cosa:
            raise InvalidCardException() 

        player.hand.remove(card)
        room.discarted_cards.add(card)

        return
    
    @db_session
    def exchange_cards(self, room: Room, sender : Player, reciever : Player, card_s : Card, card_r:Card):
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
        valid_player_position = (sender.position == (reciever.position -1)%qty_players and room.direction) or (sender.position == (reciever.position +1)%qty_players and not room.direction)
        if not valid_player_position:
            raise InvalidExchangeParticipants()
        
        sender_not_in_turn = sender.position != room.turn
        if sender_not_in_turn:
            raise PlayerNotInTurn()
        
        card_not_in_hand_sender = len(sender.hand.select(name=card_s.name)) == 0
        card_not_in_hand_reciever = len(reciever.hand.select(name=card_r.name)) == 0
        if card_not_in_hand_reciever or card_not_in_hand_sender:
            raise CardNotInPlayerHandExeption()
        
        lacosa_exchange = (card_s.name == 'La cosa') or (card_r.name == 'La cosa')
        if lacosa_exchange:
            raise RoleCardExchange()
        
        # intercambio invalido de cartas 'Infectado': 
        # - un humano intercambia infectado
        invalid_infected_exchange = (sender.rol == 'HUMANO' and card_s.name == 'Infectado') or (reciever.rol=='HUMANO' and card_r.name=='Infectado')
        if invalid_infected_exchange:
            raise InvalidCardExchange()
        
        # - un infectado intercambia su ultima infeccion
        invalid_infected_exchange = False
        invalid_infected_exchange = sender.rol == 'INFECTADO' and card_s.name == 'Infectado' and len(sender.hand.select(name='Infectado')) == 1
        invalid_infected_exchange = invalid_infected_exchange or (reciever.rol == 'INFECTADO' and card_r.name == 'Infectado' and len(reciever.hand.select(name='Infectado')) == 1)
        if invalid_infected_exchange:
            raise RoleCardExchange()
        
        # - un infectado intercambia una carta infectado con un humano
        invalid_infected_exchange = False
        invalid_infected_exchange = sender.rol=='INFECTADO' and reciever.rol=='HUMANO' and card_s.name=='Infectado'
        invalid_infected_exchange = invalid_infected_exchange or (reciever.rol=='INFECTADO' and sender.rol=='HUMANO' and card_r.name=='Infectado')
        if invalid_infected_exchange:
            raise InvalidCardExchange()
        
        
        
        if card_s.name == 'Infectado' and sender.rol == 'LA_COSA':
            reciever.rol = 'INFECTADO'
        
        if card_r.name == 'Infectado' and reciever.rol == 'LA_COSA': 
            sender.rol = 'INFECTADO'
            
        sender.hand.remove(card_s)
        sender.hand.add(card_r)
        reciever.hand.remove(card_r)
        reciever.hand.add(card_s)
        
        return