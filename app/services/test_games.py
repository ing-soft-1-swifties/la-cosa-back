import unittest
from pony.orm import Database, db_session
from app.models.entities import MachineState, Player, Room, Card
from app.models.populate_cards import populate
from app.services.games import GamesService
from app.services.cards import CardsService
from app.services.rooms import RoomsService
from app.schemas import NewRoomSchema
from uuid import uuid4 

from app.services.exceptions import *

unittest.TestLoader.sortTestMethodsUsing = None # type: ignore


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
    def test_end_game_one_player_condition(self):
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
        assert self.gs.end_game_condition_one_player("1234")[0] == "GAME_IN_PROGRESS"
        room.players.select(lambda p: p.rol == "LA_COSA").first().status = "MUERTO"
        # esta la cosa muerta
        assert self.gs.end_game_condition_one_player("1234")[0] == "HUMANS_WON"

        for player in room.players.select():
            player.rol = "HUMANO"
            player.status = "MUERTO"
        list(room.players.select())[0].rol = "LA_COSA"
        list(room.players.select(lambda p: p.rol == "LA_COSA"))[0].status = "VIVO"
        # solo queda la cosa viva
        assert self.gs.end_game_condition_one_player("1234")[0] == "LA_COSA_WON"


    @db_session
    def test_end_game_condition_la_cosa(self):
        # room valido
        room: Room = self.create_valid_room(
            roomname="test_end_game_condition_la_cosa", qty_players=4
        )

        for player in room.players:
            player.rol = "HUMANO"
            player.status = "VIVO"
        room.get_host().rol = "LA_COSA"

        # seteamos el sid del host para poder enviarlo a la funcion
        room.get_host().sid = "test_end_game_condition_la_cosa_host"

        event = self.gs.end_game_condition_la_cosa("test_end_game_condition_la_cosa_host")[0]
        assert event["name"] == 'on_game_end'
        assert event["body"]["winner_team"] == "HUMANOS"

        for player in room.players:
            player.rol = "INFECTADO"

        room.get_host().rol = 'LA_COSA'
        event = self.gs.end_game_condition_la_cosa("test_end_game_condition_la_cosa_host")[0]
        assert event["name"] == 'on_game_end'
        assert event["body"]["winner_team"] == "LA_COSA"

        room.get_host().rol = 'HUMANO'
        with self.assertRaises(InvalidAccionException):
            self.gs.end_game_condition_la_cosa("test_end_game_condition_la_cosa_host")


    @db_session
    def test_play_card(self):
        room: Room = self.create_valid_room(roomname="test_play_card", qty_players=4)

        card = list(Card.select(lambda x: x.name == "Revelaciones"))[0]

        host = room.get_host()
        host.hand.add(card)
        host.sid = "test_play_card"

        room.status = "IN_GAME"
        room.machine_state = "PLAYING"
        room.machine_state_options = {"id": host.id}

        room.turn = host.position
        last_hand_size = len(host.hand)
        self.gs.play_card_manager(
            "test_play_card", {"card": card.id, "card_options": {"target": None}}
        )
        assert last_hand_size == len(host.hand) + 1

    @db_session
    def test_superinfection(self):
        # primeras excepciones
        room: Room = self.create_valid_room(roomname="test_superinfection", qty_players=4)
        host: Player = room.get_host()

        # setting players for exchanging
        host.sid = "host_superinfection"
        room.turn = host.position
        next_p: Player = room.next_player()
        next_p.sid = "next_p_superinfection"

        for c in next_p.hand:
            next_p.hand.remove(c)

        infectado: list[Card] = []
        infectado.extend(list(Card.select(lambda c: c.name == 'Infectado')))

        next_p.add_card(infectado[0].id)
        next_p.add_card(infectado[1].id)
        next_p.add_card(infectado[2].id)
        next_p.add_card(infectado[3].id)
        next_p.rol = 'HUMANO'

        assert len(list(next_p.hand.select())) == 4

        card_host: Card = host.hand.select(lambda c: c.name != "La cosa").first()
        card_next_p: Card = next_p.hand.select(lambda c: c.name != "La cosa").first()

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

        events = self.gs.begin_exchange(room, host, next_p)

        expected_events = [
            {
                "name": "on_game_player_death",
                "body": {"player": next_p.name, "reason": "SUPERINFECCION"},
                "broadcast": True
            }
            # ,{
            #     "name": "on_game_player_turn",
            #     "body": {"player": room.get_current_player().name},
            #     "broadcast": True
            # }
        ]

        print(expected_events[0])
        print(f"\n- {expected_events[0] in events}\n")
        print(events)


        assert room.machine_state in MachineState.PLAYING or MachineState.PANICKING
        for event in expected_events:
            assert event in events

    @db_session
    def test_superinfection_check(self):

        room: Room = self.create_valid_room()
        player1: Player = room.get_host()
        room.turn = player1.position
        player2 = room.next_player()

        for card in list(player2.hand.select()):
            player2.remove_card(card.id)

        infectado: list[Card] = []
        infectado.extend(list(Card.select(lambda c: c.name == 'Infectado')))

        assert len(list(player2.hand.select())) == 0

        player2.add_card(infectado[0].id)
        player2.add_card(infectado[1].id)
        player2.add_card(infectado[2].id)
        player2.add_card(infectado[3].id)

        assert player2.hand.__len__() == 4
        player2.rol = 'HUMANO'

        is_a_superinfected = self.gs.superinfection_check(player_checked=player2, player_exchanging=player1)

        assert is_a_superinfected
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
        assert room.machine_state in [MachineState.PLAYING, MachineState.PANICKING]
        for event in expected_events:
            assert event in events

    @db_session
    def test_exchange_manager_success_defense(self):
        # primeras excepciones
        room: Room = self.create_valid_room(roomname="test_exchange_manager_success_defense", qty_players=4)
        host: Player = room.get_host()
        host.sid = str(uuid4())
        room.turn = host.position
        next_p: Player = self.rs.next_player(room)
        next_p.sid = str(uuid4())
        card_host: Card = list(
            host.hand.select(lambda c: c.name != "La cosa" and c.name != "Infectado")
        )[0]
        card_next_p_old: Card = list(
            next_p.hand.select(lambda c: c.name != "La cosa" and c.name != "Infectado")
        )[0]        
        card_next_p: Card = list(Card.select(lambda c:c.name == "¡No, gracias!"))[0]
        
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
                "name":"on_game_player_play_defense_card",
                "body":{"player_name": next_p.name, "card_name": card_next_p.name},
                "broadcast": True
            }
        ]
        assert room.machine_state in [MachineState.PLAYING, MachineState.PANICKING]
        for event in expected_events:
            assert event in events

    @classmethod
    @db_session
    def tearDownClass(cls) -> None:
        Room.select().delete()
        Player.select().delete()
        Card.select().delete()
