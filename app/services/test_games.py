from pony.orm import Database, db_session
import unittest
from app.models.entities import Player, Room
from app.services.games import GamesService
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

    
    def test_give_card(self):
        assert True

    @classmethod
    @db_session
    def tearDownClass(cls) -> None:
        # Room.select().delete()
        # Player.select().delete()
        pass