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
        # room del jugador
        room = self.create_valid_room(roomname='test_give_card', qty_players=4)

        # seleccionamos un jugador al azar
        player = list(room.players.random(1))[0]

        # asignamos el turno
        room.turn = player.position

        # conseguimos una carta
        card = list(Card.select(lambda c: c.name == 'Sospecha').random(1))[0]
        player.hand.add(card)

        cards_in_hand_before = len(player.hand)
        self.gs.discard_card(player, card)

        assert card not in player.hand
        assert card in room.discarted_cards
        assert len(player.hand) == cards_in_hand_before - 1 

    @db_session
    def test_discard_card_invalid_turn(self):
        # room del jugador
        room = self.create_valid_room(roomname='test_give_card', qty_players=4)

        # seleccionamos un jugador al azar
        player = list(room.players.random(1))[0]

        # asignamos el turno
        room.turn = player.position + 1
        
        # conseguimos una carta
        card = list(Card.select(lambda c: c.name == 'Sospecha').random(1))[0]
        player.hand.add(card)

        with self.assertRaises(PlayerNotInTurn):
            self.gs.discard_card(player, card)

    @classmethod
    @db_session
    def tearDownClass(cls) -> None:
        Room.select().delete()
        Player.select().delete()
        Card.select().delete()