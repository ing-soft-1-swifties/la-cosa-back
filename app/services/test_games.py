import unittest
from pony.orm import Database, db_session
from app.models.entities import Player, Room, Card
from app.models.populate_cards import populate
from app.services.games import GamesService
from app.services.rooms import RoomsService
from app.schemas import NewRoomSchema

from app.services.exceptions import *

unittest.TestLoader.sortTestMethodsUsing = None

class TestRoomsService(unittest.TestCase):

    db: Database
    gs: GamesService

    @classmethod
    def setUpClass(cls) -> None:
        from app.models.testing_db import db
        cls.db = db
        cls.gs = GamesService(db = cls.db) 
        with db_session:
            Room.select().delete()
            Player.select().delete()
            Card.select().delete()
        populate()
        
    @db_session
    def create_valid_room(self, roomname:str='newroom', qty_players:int=12) -> Room:
        
        Room.select().delete()
        Player.select().delete()

        rs = RoomsService(self.db)

        newroom = NewRoomSchema(
            room_name   = roomname,
            host_name   = "hostName",
            min_players =  4,
            max_players =  12,
            is_private  =  False
        )
        rs.create_room(newroom)
        room = Room.get(name=roomname)

        for i in range(qty_players-1):
            rs.join_player(f"player-{i}", room.id)

        rs.initialize_deck(room)
        rs.initial_deal(room)
        rs.assign_turns(room)

        return room


    @db_session
    def test_give_card_without_shuffle(self):

        room = self.create_valid_room(roomname='test_give_card', qty_players=12)
        player = list(room.players.random(1))[0]

        self.gs.give_card(player, room)
        assert len(player.hand) == 5

    def test_give_card_with_shuffle(self):
        # TODO: no se puede hacer hasta que este implementado y testeado `discard_card` 
        pass


    @db_session
    def test_discard_card_successful(self):
        pass


    @classmethod
    @db_session
    def tearDownClass(cls) -> None:
        Room.select().delete()
        Player.select().delete()
        Card.select().delete()