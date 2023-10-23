import unittest

from uuid import uuid4

from pony.orm import Database, db_session
from app.models.entities import Player, Room, Card
from app.models.populate_cards import populate
from app.services.games import GamesService
from app.services.cards import CardsService
from app.services.players import PlayersService
from app.services.rooms import RoomsService
from app.schemas import NewRoomSchema

from app.services.exceptions import *

unittest.TestLoader.sortTestMethodsUsing = None # type: ignore


class TestPlayerService(unittest.TestCase):
    db: Database
    gs: GamesService
    cs: CardsService
    rs: RoomsService
    ps: PlayersService

    @classmethod
    def setUpClass(cls) -> None:
        from app.models.testing_db import db
        cls.db = db
        cls.gs = GamesService(db=cls.db)
        cls.rs = RoomsService(db=cls.db)
        cls.ps = PlayersService(db=cls.db)

        with db_session:
            Room.select().delete()
            Player.select().delete()
            Card.select().delete()
        populate()

    @db_session
    def create_valid_room(self, roomname: str = "newroom", qty_players: int = 12) -> Room:
        rs = RoomsService(self.db)

        newroom = NewRoomSchema(
            room_name=roomname,
            host_name="hostName",
            min_players=4,
            max_players=12,
            is_private=False,
        )
        rs.create_room(newroom)
        room = Room.get(name=roomname)

        for i in range(qty_players - 1):
            rs.join_player(f"player-{i}", room.id)


        for player in room.players:
            player.sid = str(uuid4())
        
        room.status = "IN_GAME"
        room.direction = True


        rs.initialize_deck(room)
        rs.initial_deal(room)
        rs.assign_turns(room)

        return room


    @db_session
    def test_connect_player_succesfull(self):
        TEST_NAME = 'test_connect_player_succesfull'
        
        # creamos una room valida
        room = self.create_valid_room(roomname=TEST_NAME, qty_players=12)
        
        # obtenemos un jugador y asignamos el token
        player = room.players.random(1)[0]
        player.token = TEST_NAME

        response = self.ps.connect_player(TEST_NAME, player.sid)

        assert response[0]['name'] == 'on_room_new_player'


    @db_session
    def test_connect_player_invalid_token(self):
        TEST_NAME = 'test_connect_player_invalid_token'
        
        # creamos una room valida
        room = self.create_valid_room(roomname=TEST_NAME, qty_players=12)
        
        # obtenemos un jugador y asignamos el token
        player = room.players.random(1)[0]
        player.token = 'token_invaldo'

        with self.assertRaises(InvalidTokenException):        
            self.ps.connect_player(TEST_NAME, player.sid)


    @db_session
    def test_disconnect_player_succesfull(self):
        TEST_NAME = 'test_disconnect_player_succesfull'
        
        # creamos una room valida
        room = self.create_valid_room(roomname=TEST_NAME, qty_players=12)
        
        # obtenemos un jugador y asignamos el token
        player = room.players.random(1)[0]

        response = self.ps.disconnect_player(player.sid)

        assert response[0]['name'] == 'on_room_left_player'


    @db_session
    def test_disconnect_player_invalid_sid(self):
        TEST_NAME = 'test_disconnect_player_invalid_sid'
        
        # creamos una room valida
        room = self.create_valid_room(roomname=TEST_NAME, qty_players=12)
        
        # obtenemos un jugador y asignamos el token
        player = room.players.random(1)[0]
        player.token = TEST_NAME


        with self.assertRaises(InvalidSidException):        
            self.ps.disconnect_player(player.sid + 'invalid')


    @db_session
    def test_has_card(self):

        TEST_NAME = 'test_has_card'
        
        # creamos una room valida
        room = self.create_valid_room(roomname=TEST_NAME, qty_players=12)
        
        # obtenemos un jugador y asignamos el token
        player = room.players.random(1)[0]

        # agregamos una carta random al jugador
        card = Card.select().random(1)[0]
        player.hand.add(card)
        assert self.ps.has_card(player, card)

        # eliminamos la carta
        player.hand.remove(card)
        assert not self.ps.has_card(player, card)


    @db_session
    def test_is_host(self):

        TEST_NAME = 'test_is_host'
        
        # creamos una room valida
        room = self.create_valid_room(roomname=TEST_NAME, qty_players=12)
        
        # obtenemos un jugador y asignamos el token
        host = room.get_host()

        assert self.ps.is_host(host.sid) == True

        player_not_host = room.players.select(lambda p: p.sid != host.sid).random(1)[0]

        assert self.ps.is_host(player_not_host.sid) == False


    @db_session
    def test_is_host_invalid_sid(self):

        TEST_NAME = 'test_is_host_invalid_sid'
        
        # creamos una room valida
        room = self.create_valid_room(roomname=TEST_NAME, qty_players=12)
        
        # obtenemos un jugador y asignamos el token
        host = room.get_host()

        with self.assertRaises(InvalidSidException):
            self.ps.is_host(host.sid + 'invalid')
 
    @db_session
    def test_get_name(self):

        TEST_NAME = 'test_get_name'
        
        # creamos una room valida
        room = self.create_valid_room(roomname=TEST_NAME, qty_players=12)
        
        player = room.players.random(1)[0]

        assert self.ps.get_name(player.sid) == player.name

    @db_session
    def test_get_name_invalid_sid(self):

        TEST_NAME = 'test_get_name_invalid_sid'
        
        # creamos una room valida
        room = self.create_valid_room(roomname=TEST_NAME, qty_players=12)
        
        player = room.players.random(1)[0]

        with self.assertRaises(InvalidSidException):
            self.ps.get_name(player.sid + 'invalid')

    @classmethod
    @db_session
    def tearDownClass(cls) -> None:
        Room.select().delete()
        Player.select().delete()
        Card.select().delete()
