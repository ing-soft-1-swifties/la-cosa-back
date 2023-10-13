from ast import List
from pony.orm import count, db_session, Set
from app.models import Player, Room, Card
from app.services.exceptions import *
from app.services.mixins import DBSessionMixin
from app.services.players import PlayersService

class GamesService(DBSessionMixin):

    def card_to_JSON(self, card: Card):
        return {
            'id': card.id,
            'name': card.name,
            'description': card.description,
            'deck': card.deck,
            'type': card.type,
            'sub_type': card.sub_type
        }

    @db_session
    def game_state(self, room : Room):
        # TODO: exporta en json el estado de la partida, para enviar al frontend
        def player_state(player):
            return{
                "name" : player.name,
                "status" : player.status,
                "position" : player.position,
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
            {"personalInformation": {
                "rol" : player.rol,
                "cards" : [self.card_to_JSON(card) for card in player.hand]
            }}
        )
        return player_in_game_state

    @db_session
    def play_card(self, sent_sid : str, cid : int):
        player = Player.get(sid = sent_sid)
        card = Card.get(id = cid)
        if player is None:
            raise InvalidSidException
        if card is None:
            raise InvalidCidException
        room = player.playing
        ps = PlayersService(self.db)
        if ps.has_card(player, card) == False:
            raise InvalidCardException
        
        #se juega una carta, notar que van a ocurrir eventos (ej:alguien muere), debemos llevar registro
        #para luego notificar al frontend (una propuesta es devolve una lista de eventos con sus especificaciones)
        #a todos los afectados por el evento se les reenvia el game_state
        self.next_turn(room)
        #el metodo anterior retorna la carta que recibio alguna la siguiente persona
        #falta implementar la muestra de eventos
        pass
        
    @db_session
    def next_turn(self, room:Room):
        if room.turn is None:
            print("partida inicializada incorrectamente, turno no pre-seteado")
            raise Exception
        room.turn = (room.turn + 1) % (len(room.players.select(lambda player : player.status != 1)))    #cantidad de jugadores que siguen jugando
        expected_player = Player.get(position = room.turn)
        if expected_player is None:
            print(f"el jugador con turno {room.turn} no esta en la partida")
            raise Exception
        return self.give_card(expected_player, room)
        
    @db_session
    def give_card(self, player:Player, room:Room):
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
