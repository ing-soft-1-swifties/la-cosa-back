from enum import Enum
from pony.orm import (Database, PrimaryKey, Required, Set, Optional, Json)
from app.services.exceptions import *
from ..logger import rootlog
db = Database()

class MachineState(str, Enum):
    PLAYING = "PLAYING"
    DEFENDING = "DEFENDING"
    EXCHANGING = "EXCHANGING"
    PANICKING = "PANICKING"

class PlayerState(str, Enum):
    RECEIVING_EXCHANGE = "RECEIVING_EXCHANGE"
    OFFERING_EXCHANGE = "OFFERING_EXCHANGE"
    WAITING = "WAITING"
    PLAYING = "PLAYING"
    PANICKING = "PANICKING"
    DEFENDING = "DEFENDING"

class Obstacle(db.Entity):
    id = PrimaryKey(int, auto=True)
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
    ignore_quarantine = Optional(bool, default=False)
    ignore_locked_door = Optional(bool, default=False)
    suspended_in = Set('Room', reverse="suspended_card")

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
    quarantine = Optional(int, default=0)
    playing = Required('Room', reverse='players')
    is_host = Required(bool, default=False)
    sid = Optional(str, default="")             # socket id
    token = Required(str)
    hand = Set('Card', reverse='player_hand')
    target_in = Set("Room", reverse="suspended_card_target")

    def json(self):
        
        room: Room = self.playing;

        state: PlayerState = PlayerState.WAITING
        card_picking_amount = 0
        selectable_players = []

        if room.machine_state == MachineState.PLAYING and room.turn == self.position:
            state = PlayerState.PLAYING
        elif room.machine_state == MachineState.PANICKING and room.turn == self.position:
            state = PlayerState.PANICKING
            card_picking_amount = room.machine_state_options.get("card_picking_amount", None)
            selectable_players = room.machine_state_options.get("selectable_players", None)
            assert card_picking_amount is not None
            # assert selectable_players is not None
        elif room.machine_state == MachineState.DEFENDING and room.suspended_card_target == self:
            state = PlayerState.DEFENDING
        elif room.machine_state == MachineState.EXCHANGING:
            if room.turn == self.position:
                state = PlayerState.OFFERING_EXCHANGE
            else:
                state = PlayerState.RECEIVING_EXCHANGE

        return {
                "name" : self.name,
                "playerID": self.id,
                "role" : self.rol,
                "cards" : [card.json() for card in self.hand],
                "position":self.position,
                #estos son agregados para notificar estado al front, asi deciden como renderizar ciertas cosas
                "on_turn": self.status == "VIVO" and self.position == self.playing.turn,
                "on_exchange": self.playing.machine_state == "EXCHANGING" and (self.id in self.playing.machine_state_options.get("ids")),
                "state": state,
                "card_picking_amount": card_picking_amount,
                "selectable_players": selectable_players
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

    def serialize_hand(self, exclude: list[int]=None) -> list[dict]:
        """
        Retorna una lista de diccionarios de cartas, excluyendo las cartas pasadas por parametros.
        - exclude: list[card_id], es una lista de ids de cartas, no tiene en cuenta un id invalido
        """
        if exclude is None:
            exclude = []

        res = []
        for card in self.hand:
            if not card.id in exclude:
                res.append(card.json())

        return res

    def is_alive(self) -> bool:
        return self.status == "VIVO"

    def is_in_quarantine(self) -> bool:
        return self.quarantine > 0

    def set_quarantine(self, amount: int):
        self.quarantine = amount

    def decrease_quarantine(self):
        if self.quarantine > 0:
            self.quarantine -= 1

    def quarantine_turns_left(self):
        return self.quarantine


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
    suspended_card = Optional(Card, reverse = "suspended_in")
    suspended_card_target = Optional(Player, reverse = "target_in")

    def qty_alive_players(self)->int:
        return len(list(self.players.select(lambda player:player.status=='VIVO')))

    def qty_players(self)->int:
        return len(list(self.players.select()))

    def get_host(self) -> Player:
        for player in self.players:
            if player.is_host:
                return player
        raise Exception()   #muerte

    def get_player_by_pos(self, pos) -> Player | None:
        """
        Retorna el player que se encuentra en la posicion <pos>,
            en caso de que <pos> sea una posicion invalida, retorna None
        """
        return self.players.select(lambda p: p.position == pos and p.status == 'VIVO').first()

    def json(self):
        return {
            'id': self.id,
            'name': self.name,
            'max_players' : self.max_players,
            'min_players' : self.min_players,
            'players_count' : len(self.players),
            'is_private' : self.is_private
        }

    def get_current_player(self) -> Player:
        """ Retorna el jugador vivo que esta actualmente en su turno
        """
        return self.players.select(lambda p: p.position == self.turn).first()

    def next_player_from_player(self, player : Player) -> Player:
        """ Retorna el jugador vivo que sigue al player enviado
        """
        if player.status != 'VIVO':
            rootlog.exception("Se quiere calcular quien es el siguiente jugador de un jugador muerto")
            raise Exception()
        position = player.position
        next_turn_position = (position + 1 if self.direction else position - 1) % self.qty_alive_players()
        return self.players.select(lambda p: p.position == next_turn_position and p.status == 'VIVO').first()

    def next_player(self) -> Player:
        """ Retorna el jugador vivo que sigue segun el orden de la ronda
        """
        next_turn_position = (self.turn + 1 if self.direction else self.turn - 1) % self.qty_alive_players()
        return self.players.select(lambda p: p.position == next_turn_position and p.status == 'VIVO').first()

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
        """
            Comportamiento:
                - Se descarta la carta seleccionada
            Checks:
                - Se intenta descartar cartas que no estan en las manos de los players

        """
        if not player.has_card(card.id):
            raise InvalidAccionException(msg='Carta para descartar no esta en la mano')
        else:
            player.remove_card(card.id)

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

        # Devolver sus cartas al mazo
        room.discarted_cards.add(player.hand)
        player.hand.remove(player.hand)

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
        # si es nuestro turno nos lo llevamos
        room = player1.playing
        if room.turn == player1.position:
            room.turn = player2.position

        elif room.turn == player2.position:
            room.turn = player1.position

        player1.position, player2.position = player2.position, player1.position

    def get_quarantine_players(self) -> list[Player]:
        response = []
        for player in self.players:
            player : Player
            if player.is_in_quarantine():
                response.append(player)

        return response

    def add_locked_door(self, obstacle_position):
        obstacle = Obstacle(
            position=obstacle_position,
            room=self
        )
        self.obstacles.add(obstacle)

    def remove_locked_door(self, obstacle_position: int):

        obstacle: Obstacle = self.obstacles.select(position=obstacle_position).first()
        self.obstacles.remove(obstacle)

    def get_obstacles_positions(self) -> list[int]:
        positions = []
        for obstacle in self.obstacles:
            obstacle: Obstacle
            positions.append(obstacle.position)

        return positions
