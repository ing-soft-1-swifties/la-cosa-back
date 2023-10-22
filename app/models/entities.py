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
                "position":self.position
                }

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

