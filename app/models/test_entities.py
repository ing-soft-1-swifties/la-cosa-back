import unittest
from pony.orm import Database, db_session
from app.models.populate_cards import populate
from app.models.entities import Player, Room, Card

unittest.TestLoader.sortTestMethodsUsing = None  # type: ignore

class TestPlayCardsService(unittest.TestCase):
    db: Database

    @classmethod
    def setUpClass(cls) -> None:
        from app.models.testing_db import db
        cls.db = db

        with db_session:
            Room.select().delete()
            Player.select().delete()
            Card.select().delete()
        populate()



    @classmethod
    @db_session
    def tearDownClass(cls) -> None:
        Room.select().delete()
        Player.select().delete()
        Card.select().delete()