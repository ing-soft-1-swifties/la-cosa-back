import unittest
from pony.orm import Database, db_session
from app.models.entities import Player, Room, Card
from app.models.populate_cards import populate
from app.services.games import GamesService
from app.services.cards import CardsService
from app.services.rooms import RoomsService
from app.schemas import NewRoomSchema
from uuid import uuid4 

from app.services.exceptions import *

unittest.TestLoader.sortTestMethodsUsing = None


class TestGamesService(unittest.TestCase):
    db: Database
    gs: GamesService
    cs: CardsService
    rs: RoomsService

    @classmethod
    def setUpClass(cls) -> None:
        from app.models.testing_db import db

        cls.db = db
        cls.gs = GamesService(db=cls.db)
        cls.rs = RoomsService(db=cls.db)
        with db_session:
            Room.select().delete()
            Player.select().delete()
            Card.select().delete()
        populate()

    @db_session
    def create_valid_room(
        self, roomname: str = "newroom", qty_players: int = 12
    ) -> Room:
        Room.select().delete()
        Player.select().delete()

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
    def test_end_game_condition(self):
        # room valido
        room: Room = self.create_valid_room(
            roomname="test_end_game_condition", qty_players=4
        )

        for player in room.players.select():
            player.rol = "HUMANO"
            player.status = "VIVO"
        list(room.players.select())[0].rol = "LA_COSA"

        # seteamos el sid del host para poder enviarlo a la funcion
        room.get_host().sid = "1234"

        # tan todos los players vivos
        assert self.gs.end_game_condition("1234")[0] == "GAME_IN_PROGRESS"

        list(room.players.select(lambda p: p.rol == "LA_COSA"))[0].status = "MUERTO"
        # esta la cosa muerta
        assert self.gs.end_game_condition("1234")[0] == "HUMANS_WON"

        for player in room.players.select():
            player.rol = "INFECTADO"
            player.status = "VIVO"
        list(room.players.select())[0].rol = "LA_COSA"
        # todos lod players estan infectados
        assert self.gs.end_game_condition("1234")[0] == "LA_COSA_WON"

        for player in room.players.select():
            player.rol = "HUMANO"
            player.status = "MUERTO"
        list(room.players.select())[0].rol = "LA_COSA"
        list(room.players.select(lambda p: p.rol == "LA_COSA"))[0].status = "VIVO"
        # solo queda la cosa viva
        assert self.gs.end_game_condition("1234")[0] == "LA_COSA_WON"

        list(room.players.select(lambda p: p.rol == "LA_COSA"))[0].status = "MUERTO"
        list(room.players.select(lambda p: p.rol != "LA_COSA"))[0].status = "VIVO"
        # esta la cosa muerta, y un humano vivo
        assert self.gs.end_game_condition("1234")[0] == "HUMANS_WON"

    @db_session
    def test_play_card(self):
        room: Room = self.create_valid_room(roomname="test_play_card", qty_players=4)

        card = list(Card.select(lambda x: x.name == "Sospecha"))[0]

        host = room.get_host()
        host.hand.add(card)
        host.sid = "1234"

        room.status = "IN_GAME"
        room.machine_state = "PLAYING"
        room.machine_state_options = {"id": host.id}

        room.turn = host.position
        last_hand_size = len(host.hand)
        self.gs.play_card_manager(
            "1234", {"card": card.id, "card_options": {"target": None}}
        )
        assert last_hand_size == len(host.hand) + 1

    @db_session
    def test_play_card_invalid_turn(self):
        room: Room = self.create_valid_room(
            roomname="test_play_card_invalid_turn", qty_players=4
        )
        sender: Player = list(room.players.select(rol="LA_COSA"))[0]

        card = list(Card.select(lambda x: x.name == "Lanzallamas"))[0]

        host = room.get_host()
        host.hand.add(card)
        host.sid = "1234"

        room.status = "IN_GAME"
        room.machine_state = "PLAYING"
        room.machine_state_options = {"id": host.id}
        position = 1
        next_player = None
        for player in room.players:
            if player.id != host.id:
                if position == 1:
                    next_player = player
                player.position = position
                position += 1

        card2 = list(Card.select(lambda x: x.name == "Lanzallamas"))[1]
        next_player.hand.add(card2)
        next_player.sid = "999"

        room.turn = host.position

        ret = self.gs.play_card_manager(
            "999", {"card": card2.id, "card_options": {"target": host.id}}
        )
        assert ret[0]["name"] == "on_game_invalid_action"
        assert ret[0]["broadcast"] == False

    @db_session
    def test_exchange_manager_happy(self):
        # primeras excepciones
        room: Room = self.create_valid_room(roomname="test_exchange_manager_happy", qty_players=4)
        host: Player = room.get_host()
        host.sid = "host"
        room.turn = host.position
        next_p: Player = self.rs.next_player(room)
        next_p.sid = "next_p"
        card_host: Card = list(
            host.hand.select(lambda c: c.name != "La cosa" and c.name != "Infectado")
        )[0]
        card_next_p: Card = list(
            next_p.hand.select(lambda c: c.name != "La cosa" and c.name != "Infectado")
        )[0]

        # setting maquina de estados
        machine_state_options = {"ids": [host.id, next_p.id], "stage": "STARTING"}
        room.machine_state = "EXCHANGING"
        room.machine_state_options = machine_state_options

        # payload setting primera llamada a intercambio
        payload = {"card": card_host.id, "on_defense": False}

        events = self.gs.exchange_card_manager(host.sid, payload)

        # chequeos
        assert room.machine_state == "EXCHANGING"
        assert room.machine_state_options["stage"] == "FINISHING"
        assert room.machine_state_options["card_id"] == card_host.id
        assert room.machine_state_options["player_id"] == host.id
        assert events == []

        # payload setting segunda llamada a intercambio
        payload = {"card": card_next_p.id, "on_defense": False}

        events = self.gs.exchange_card_manager(next_p.sid, payload)

        expected_events = [
            {
                "name": "on_game_finish_exchange",
                "body": {"players": [host.name, next_p.name]},
                "broadcast": True,
            },
            {
                "name": "on_game_exchange_result",
                "body": {"card_in": card_next_p.id, "card_out": card_host.id},
                "broadcast": False,
                "receiver_sid": host.sid,
            },
            {
                "name": "on_game_exchange_result",
                "body": {"card_in": card_host.id, "card_out": card_next_p.id},
                "broadcast": False,
                "receiver_sid": next_p.sid,
            }
        ]
        assert room.machine_state == "PLAYING"
        for event in expected_events:
            assert event in events

    @db_session
    def test_exchange_manager_success_defense(self):
        # primeras excepciones
        room: Room = self.create_valid_room(roomname="test_exchange_manager_success_defense", qty_players=4)
        host: Player = room.get_host()
        host.sid = uuid4()
        room.turn = host.position
        next_p: Player = self.rs.next_player(room)
        next_p.sid = uuid4()
        card_host: Card = list(
            host.hand.select(lambda c: c.name != "La cosa" and c.name != "Infectado")
        )[0]
        card_next_p_old: Card = list(
            next_p.hand.select(lambda c: c.name != "La cosa" and c.name != "Infectado")
        )[0]        
        card_next_p: Card = Card.select(lambda c:c.name == "¡No, gracias!")
        
        next_p.hand.remove(card_next_p_old)
        next_p.hand.add(card_next_p)

        # setting maquina de estados
        machine_state_options = {"ids": [host.id, next_p.id], "stage": "STARTING"}
        room.machine_state = "EXCHANGING"
        room.machine_state_options = machine_state_options

        # payload setting primera llamada a intercambio
        payload = {"card": card_host.id, "on_defense": False}

        events = self.gs.exchange_card_manager(host.sid, payload)

        # chequeos
        assert room.machine_state == "EXCHANGING"
        assert room.machine_state_options["stage"] == "FINISHING"
        assert room.machine_state_options["card_id"] == card_host.id
        assert room.machine_state_options["player_id"] == host.id
        assert events == []

        # payload setting segunda llamada a intercambio
        payload = {"card": card_next_p.id, "on_defense": True}

        events = self.gs.exchange_card_manager(next_p.sid, payload)

        expected_events = [
            {
                "name": "on_game_finish_exchange",
                "body": {"players": [host.name, next_p.name]},
                "broadcast": True,
            },
            {
                "name": "on_game_exchange_result",
                "body": {"card_in": card_next_p.id, "card_out": card_host.id},
                "broadcast": False,
                "receiver_sid": host.sid,
            },
            {
                "name": "on_game_exchange_result",
                "body": {"card_in": card_host.id, "card_out": card_next_p.id},
                "broadcast": False,
                "receiver_sid": next_p.sid,
            }
        ]
        assert room.machine_state == "PLAYING"
        for event in expected_events:
            assert event in events

    @classmethod
    @db_session
    def tearDownClass(cls) -> None:
        Room.select().delete()
        Player.select().delete()
        Card.select().delete()
