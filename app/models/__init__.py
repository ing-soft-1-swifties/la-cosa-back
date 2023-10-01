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
    type = Required(int)            # {Alejate, Panico}
    sub_type = Optional(int)        # {Contagio, Accion, Defensa, Obstaculo}
    roomsA = Set('Room', reverse='available_cards')
    roomsD = Set('Room', reverse='discarted_cards')


class Player(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(str)
    position = Required(int)
    rol = Required(int)             # {Humano, LaCosa, Infectado}
    status = Required(int)          # {Vivo, Muerto, Cuarentena}
    hosting = Optional('Room', reverse='host')
    playing = Optional('Room', reverse='players')
    sid = Optional(str)


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
    host = Required(Player, reverse='hosting')
    players = Set(Player, reverse='playing')
    available_cards = Set(Card, reverse='roomsA')
    discarted_cards = Set(Card, reverse='roomsD')


db.bind(provider='sqlite', filename='../../database/la_cosa.sqlite', create_db=True)
db.generate_mapping(create_tables=True)


