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
    description = Optional(str)
    deck = Required(int)
    type = Required(int)            # {Alejate, Panico}
    sub_type = Optional(int)        # {Contagio, Accion, Defensa, Obstaculo}
    roomsA = Set('Room', reverse='available_cards')
    roomsD = Set('Room', reverse='discarted_cards')
    playerhand = Set('Player', reverse='hand')
    


class Player(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(str)
    position = Optional(int)
    rol = Optional(int)             # {Humano, LaCosa, Infectado}
    status = Optional(int)          # {Vivo, Muerto, Cuarentena}
    playing = Required('Room', reverse='players')
    is_host = Required(bool, default=False)
    sid = Optional(str)             # socket id
    token = Required(str)
    hand = Optional(Set('Card', reverse='player_hand'))


class Room(db.Entity):
    id = PrimaryKey(int, auto=True)
    obstacles = Set(Obstacle)
    name = Required(str)
    min_players = Required(int)
    max_players = Optional(int)
    is_private = Required(bool) 
    password = Optional(str)
    status = Required(int)          # {lobby, in_game, finished}
    turn = Optional(int)
    direction = Optional(bool)
    players = Set(Player, reverse='playing')
    available_cards = Set(Card, reverse='roomsA')
    discarted_cards = Set(Card, reverse='roomsD')


db.bind(provider='sqlite', filename=f'la_cosa.sqlite', create_db=True)
db.generate_mapping(create_tables=True)
