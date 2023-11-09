from pony.orm import (Database, PrimaryKey, Required, Set, Optional, Json)
from app.services.exceptions import *
db = Database()

class Obstacle(db.Entity):
    id = PrimaryKey(int, auto=True)
    duration = Required(int)
    position = Required(int)
    room = Required('Room')

class Card(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(str)
    description = Optional(str, default="")
    deck = Required(int)
    type = Required(str)            # {ALEJATE, PANICO}
    sub_type = Optional(str)        # {CONTAGIO, ACCION, DEFENSA, OBSTACULO}
    roomsA = Set('Room', reverse='available_cards')
    roomsD = Set('Room', reverse='discarted_cards')
    player_hand = Set('Player', reverse='hand')
    need_target = Optional(bool, default=False)
    target_adjacent_only = Optional(bool, default=False)

    def json(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'type': self.type,
            'subType': self.sub_type,
            'needTarget' : self.need_target,
            'targetAdjacentOnly': self.target_adjacent_only
        }

class Player(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(str)
    position = Optional(int, default=0)
    rol = Optional(str, default="HUMANO")             # {HUMANO, LA_COSA, INFECTADO}
    status = Optional(str, default="VIVO")          # {VIVO, MUERTO}
    in_quarantine = Optional(bool, default = False)
    playing = Required('Room', reverse='players')
    is_host = Required(bool, default=False)
    sid = Optional(str, default="")             # socket id
    token = Required(str)
    hand = Set('Card', reverse='player_hand')

    def json(self):
        return {
                "name" : self.name,
                "playerID": self.id,
                "role" : self.rol,
                "cards" : [card.json() for card in self.hand],
                "position":self.position,
                #estos son agregados para notificar estado al front, asi deciden como renderizar ciertas cosas
                "on_turn": self.status == "VIVO" and self.position == self.playing.turn,
                "on_exchange": self.playing.machine_state == "EXCHANGING" and (self.id in self.playing.machine_state_options.get("ids"))
                }

    def add_card(self, card_id: int):
        self.hand.add(Card.get(id=card_id))

    def remove_card(self, card_id: int):
        self.hand.remove(Card.get(id=card_id))

    def has_card(self, card_id: int) -> bool :
        card = Card.get(id=card_id)
        if card is None:
            return False

        return card in self.hand

    def serialize_hand(self) -> list[Card]:
        cards_JSON = []
        for card in self.hand:
            cards_JSON.append(card.json())
        return cards_JSON

    def is_alive(self) -> bool:
        return self.status == "VIVO"



class Room(db.Entity):
    id = PrimaryKey(int, auto=True)
    obstacles = Set(Obstacle)
    name = Required(str)
    min_players = Required(int)
    max_players = Required(int)
    is_private = Required(bool) 
    password = Optional(str, default="")
    status = Required(str)          # {LOBBY, IN_GAME, FINISHED}
    turn = Required(int, default=0)
    direction = Required(bool, default=True)
    players = Set(Player, reverse='playing')
    available_cards = Set(Card, reverse='roomsA')
    discarted_cards = Set(Card, reverse='roomsD')
    machine_state = Optional(str)
    machine_state_options = Optional(Json)
    
    def qty_alive_players(self)->int:
        return len(list(self.players.select(lambda player:player.status=='VIVO')))

    def qty_players(self)->int:
        return len(list(self.players.select()))

    def get_host(self):
        for player in self.players:
            if player.is_host:
                return player
        raise Exception()   #muerte

    def json(self):
        return { 
            'id': self.id,
            'name': self.name,
            'max_players' : self.max_players,
            'min_players' : self.min_players,
            'players_count' : len(self.players),
            'is_private' : self.is_private
        }

    def get_current_player(self):
        """ Retorna el jugador vivo que esta actualmente en su turno
        """

        return self.players.select(lambda p: p.position == self.turn).first()

    def next_player(self):
        """ Retorna el jugador vivo que sigue segun el orden de la ronda
        """
        next_turn_position = (self.turn + 1 if self.direction else self.turn - 1) % self.qty_alive_players()
        return self.players.select(lambda p: p.position == next_turn_position and p.status == 'VIVO')

    def swap_cards(self, player1: Player, card1: Card, player2: Player, card2: Card):
        """
        Comportamiento:
            - Le saca la carta 2 al player 2 y se la da al player 1
            - Le saca la carta 1 al player 1 y se la da al player 2
        Checks:
            - Se intenta intercambiar cartas que no estan en las manos de los players

        :param player1: Player
        :param card1: Card
        :param player2: Player
        :param card2: Card
        """

        if not (player1.has_card(card1.id) and player2.has_card(card2.id)):
            raise InvalidAccionException(msg="Se quiso intercambiar cartas que no estaban en la mano del jugador")

        player1.remove_card(card1.id)
        player1.add_card(card2.id)
        player2.remove_card(card2.id)
        player2.add_card(card1.id)

    def discard_card(self, player: Player, card: Card):
        count = player.hand.count()
        for c in player.hand.__iter__():
            if c == card:
                player.hand.remove(card)
        if count == player.hand.count():
            # error
            pass


    def are_players_adjacent(self, player1: Player, player2: Player):

        if player1 not in self.players or player2 not in self.players:
            raise Exception("Players not in this Room")
        if not (player1.is_alive and player2.is_alive):
            raise Exception("Players aren't alive")
        if None in [player1.position, player2.position]:
            raise Exception("Players positions not set")

        # si son adyacentes entonces estaran a uno de distancia
        # Ó estarán a una vuelta de distancia
        return abs(player1.position - player2.position) == 1 or \
               abs(player1.position - player2.position) ==  self.qty_alive_players() - 1

    def kill_player(self, player: Player):
        """
        Mata a un jugador, quitándolo de la mesa y reordenando al resto de jugadores.
        """

        # Matar al jugador
        player.status = "MUERTO"  

        # Reordenar al resto de los jugadores.
        # Las posiciones se mantienen de 0 a cantidad de jugadores - 1

        room = self

        if room.turn is None:
            raise Exception("partida inicializada incorrectamente, turno no pre-seteado")

        # lista de tuplas
        # [(posicion, jugador)]
        id_position = []
        for player in room.players: #type:ignore
            if player.is_alive():
                id_position.append((player.position, player))

        # Ordenar las posiciones
        id_position.sort(key = lambda x : x[0])
        position = 0

        # Actualizar posiciones de los jugadores 
        # y la posición en turno en caso de que el que está en turno 
        # tenga ahora una nueva posicion
        should_update_turn = True
        for pair in id_position:

            # Actualiza el turno de ser necesario
            if pair[1].position != position and position <= room.turn and should_update_turn:
                room.turn -= 1
                should_update_turn = False

            # Actualizamos la posicion
            pair[1].position = position
            position += 1

    def change_direction(self):
        """
        Cambia la direccion del juego
        """
        self.direction = not self.direction

    def swap_players_positions(self, player1: Player, player2: Player):
        """
        Intercambia las posiciones de dos jugadores
        """
        player1.position, player2.position = player2.position, player1.position
