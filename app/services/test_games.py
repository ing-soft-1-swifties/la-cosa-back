import unittest
from pony.orm import Database, db_session
from app.models.entities import Player, Room
from app.models.populate_cards import populate
from app.services.games import GamesService
from app.services.rooms import RoomsService
from app.schemas import NewRoomSchema

from app.services.exceptions import *

unittest.TestLoader.sortTestMethodsUsing = None

class TestRoomsService(unittest.TestCase):

    db: Database
    gs: GamesService

    @db_session
    def create_valid_room(self) -> Room:
        
        Room.select().delete()
        Player.select().delete()

        rs = RoomsService(self.db)

        newroom = NewRoomSchema(
            room_name   = "roomName",
            host_name   = "hostName",
            min_players =  4,
            max_players =  12,
            is_private  =  False
        )
        rs.create_room(newroom)
        room = Room.get(name="roomName")

        for i in range(10):
            rs.join_player(f"player-{i}", room.id)

        rs.initialize_deck(room)
        rs.initial_deal(room)
        rs.assign_turns(room)

        return room

    @classmethod
    def setUpClass(cls) -> None:
        from app.models.testing_db import db
        cls.db = db
        cls.gs = GamesService(db = cls.db) 
        populate()

    def test_give_card(self):
        room = self.create_valid_room()

        print(list(room.players))


        # pytest -v app/services/test_games.py

        assert True


    @classmethod
    @db_session
    def tearDownClass(cls) -> None:
        Room.select().delete()
        Player.select().delete()
        pass