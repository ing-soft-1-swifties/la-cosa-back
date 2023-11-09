import unittest
from uuid import uuid4

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

    @db_session
    def create_room(self, room_name: str) -> Room:
        return Room(
            name=room_name,
            min_players=4,
            max_players=12,
            is_private=False,
            status='INITIAL'
        )

    @db_session
    def create_player(self, player_name: str, room: Room, is_host) -> Player:
        return Player(
            name=player_name,
            playing=room,
            is_host=is_host,
            token=str(uuid4())
        )

    # TODO
    def test_player_has_card(self):
        pass

    # TODO
    def test_player_serialize_hand(self):
        pass

    # TODO
    def test_player_json(self):
        pass

    @classmethod
    @db_session
    def tearDownClass(cls) -> None:
        Room.select().delete()
        Player.select().delete()
        Card.select().delete()