from pony.orm import (Database, PrimaryKey, Required, Set, Optional)

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
    sub_type = Optional(str, default="")        # {CONTAGIO, ACCION, DEFENSA, OBSTACULO}
    roomsA = Set('Room', reverse='available_cards')
    roomsD = Set('Room', reverse='discarted_cards')
    player_hand = Set('Player', reverse='hand')
    


class Player(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(str)
    position = Optional(int, default=0)
    rol = Optional(str, default="HUMANO")             # {HUMANO, LA_COSA, INFECTADO}
    status = Optional(str, default="VIVO")          # {VIVO, MUERTO, CUARENTENA}
    playing = Required('Room', reverse='players')
    is_host = Required(bool, default=False)
    sid = Optional(str, default="")             # socket id
    token = Required(str)
    hand = Set('Card', reverse='player_hand')


class Room(db.Entity):
    id = PrimaryKey(int, auto=True)
    obstacles = Set(Obstacle)
    name = Required(str)
    min_players = Required(int)
    max_players = Required(int)
    is_private = Required(bool) 
    password = Optional(str, default="")
    status = Required(str)          # {LOBBY, IN_GAME, FINISH}
    turn =  Optional(int, default=0)
    direction = Optional(bool, default=True)
    players = Set(Player, reverse='playing')
    available_cards = Set(Card, reverse='roomsA')
    discarted_cards = Set(Card, reverse='roomsD')

    def get_host(self):
        for player in self.players:
            if player.is_host:
                return player
        raise Exception()   #muerte