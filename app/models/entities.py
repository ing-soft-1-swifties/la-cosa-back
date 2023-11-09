from pony.orm import (Database, PrimaryKey, Required, Set, Optional, Json)

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

    # TODO:
    #   el jugador de la posicion actual
    def get_current_player(self):
        pass

    # TODO:
    #   teniendo en cuenta el sentido de la misma, y que esten vivos
    def next_player(self):
        pass

    # TODO:
    def swap_cards(player1, card1, player2, card2):
        pass

    # TODO:
    def discard_card(self, player, card):
        pass

    # TODO:
    def are_players_adjacent(player1, player2):
        pass

    # TODO:
    def kill_player(self):
        pass

    # TODO:
    def change_direction(self):
        pass

    # TODO
    def swap_players_positions(self, player1, player2):
        pass

