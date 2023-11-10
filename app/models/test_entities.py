import unittest
from uuid import uuid4

from pony.orm import Database, db_session
from app.models.populate_cards import populate
from app.models.entities import Player, Room, Card
from app.schemas import NewRoomSchema
from app.services.exceptions import InvalidAccionException
from app.services.rooms import RoomsService

unittest.TestLoader.sortTestMethodsUsing = None  # type: ignore


class TestEntities(unittest.TestCase):
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
    def create_valid_room(
        self, roomname: str = "newroom", qty_players: int = 12
    ) -> Room:
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

        room.status = "IN_GAME"
        rs.initialize_deck(room)
        rs.initial_deal(room)
        rs.assign_turns(room)

        return room

    @db_session
    def create_player(self, player_name: str, room: Room, is_host: bool) -> Player:
        return Player(
            name=player_name,
            playing=room,
            is_host=is_host,
            token=str(uuid4())
        )

    @db_session
    def test_player_add_has_remove_card(self):
        """
            Testea los siguientes metodos:
                - player.add_card()
                - player.has_card()
                - player.remove_card()
        """
        room = self.create_room(room_name='test_player_add_has_remove_card')
        player = self.create_player(player_name='player1', room=room, is_host=True)
        card = Card.get(id=1)

        player.add_card(card.id)
        assert card in player.hand
        assert (card in player.hand) == player.has_card(card.id)

        player.remove_card(card.id)
        assert not card in player.hand
        assert (card in player.hand) == player.has_card(card.id)

        assert not player.has_card(4000)

    @db_session
    def test_player_json(self):
        room = self.create_room(room_name='test_player_add_has_remove_card')
        player = self.create_player(player_name='player1', room=room, is_host=True)

        player_json = player.json()

        assert player_json['playerID'] == player.id
        assert player_json['name'] == player.name
        assert player_json['role'] == player.rol

    @db_session
    def test_player_serialize_hand(self):
        room = self.create_room(room_name='test_player_add_has_remove_card')
        player = self.create_player(player_name='player1', room=room, is_host=True)

        cards = Card.select().random(4)
        player.hand.add(cards)
        hand_serialize = player.serialize_hand()

        for card in cards:
            assert card.json() in hand_serialize

    @db_session
    def test_get_player_by_pos(self):
        room: Room = self.create_valid_room(roomname='test_get_player_by_pos')

        player: Player = room.get_host()
        position_host = player.position

        assert player.id == room.get_player_by_pos(position_host).id
        assert player.id != room.get_player_by_pos(position_host + 1).id

    @db_session
    def test_get_current_player(self):
        room: Room = self.create_valid_room(roomname='test_get_current_player')
        host: Player = room.get_host()
        room.turn = host.position

        assert room.get_current_player().id == host.id

    @db_session
    def test_next_player(self):
        room: Room = self.create_valid_room(roomname='test_next_player')
        host: Player = room.get_host()
        room.turn = (host.position - 1) % room.qty_alive_players()

        assert room.next_player() == host

    @db_session
    def test_swap_cards(self):
        room: Room = self.create_valid_room(roomname='test_swap_cards')
        host: Player = room.get_host()
        room.turn = host.position
        card_host = host.hand.select().first()

        player2 = room.next_player()
        card_p2 = player2.hand.select().first()

        room.swap_cards(host, card_host, player2, card_p2)
        assert host.has_card(card_p2.id)
        assert not host.has_card(card_host.id)

        assert player2.has_card(card_host.id)
        assert not player2.has_card(card_p2.id)

        with self.assertRaises(InvalidAccionException):
            room.swap_cards(host, card_host, player2, card_host)


    @db_session
    def test_discard_card(self):
        room: Room = self.create_valid_room(roomname='test_discard_card')
        host: Player = room.get_host()

        card = host.hand.select().first()
        assert host.has_card(card.id)

        room.discard_card(host, card)
        assert not host.has_card(card.id)

        with self.assertRaises(InvalidAccionException):
            room.discard_card(host, card)




    @classmethod
    @db_session
    def tearDownClass(cls) -> None:
        Room.select().delete()
        Player.select().delete()
        Card.select().delete()
