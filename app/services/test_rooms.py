from pony.orm import Database, db_session
import unittest
from app.models.constants import CardName
from app.models.populate_cards import populate
from app.models.entities import MachineState, Player, Room, Card
from app.schemas import NewRoomSchema
from app.services.rooms import RoomsService
from app.services.exceptions import *

unittest.TestLoader.sortTestMethodsUsing = None

class TestRoomsService(unittest.TestCase):
    db: Database
    rs: RoomsService

    @classmethod
    def setUpClass(cls) -> None:
        from app.models.testing_db import db
        cls.db = db
        cls.rs = RoomsService(db = cls.db)
        with db_session:
            Room.select().delete()
            Player.select().delete()
            Card.select().delete()
        populate()

    @db_session
    def create_valid_room(self, roomname:str='newroom', qty_players:int=12) -> Room:
        rs = RoomsService(self.db)

        Room.select().delete()
        Player.select().delete()
        newroom = NewRoomSchema(
            room_name   = roomname,
            host_name   = "hostName",
            min_players =  4,
            max_players =  12,
            is_private  =  False
        )
        self.rs.create_room(newroom)
        room = Room.get(name=roomname)
        for i in range(qty_players-1):
            self.rs.join_player(f"player-{i}", room.id)

        return room

    @db_session
    def test_next_turn_is_uno_dos(self):

        rs = RoomsService(self.db)

        room: Room = self.create_valid_room(
            qty_players = 3,
            roomname="test_next_turn_is_uno_dos"
        )

        rs.assign_turns(room)

        # La unica carta disponible va a ser 'Uno, dos'
        panic_card = Card(type="PANICO", name=CardName.UNO_DOS, deck = 1)

        assert panic_card is not None
        room.available_cards.add(panic_card) #type:ignore

        player = room.players.select(position = room.turn).first() #type:ignore
        player.sid = "test_next_turn_is_uno_dos"

        assert player is not None

        player: Player

        assert len(room.available_cards) != 0

        assert panic_card.type == "PANICO"

        # Le damos la carta de panico al jugador en turno
        rs.next_turn(player.sid)

        assert room.machine_state == MachineState.PANICKING

        assert room.machine_state_options.get("card_picking_amount", None) is not None

        selectable_players = room.machine_state_options.get("selectable_players", None)

        assert selectable_players is not None and isinstance(selectable_players, list)

        assert player.name not in selectable_players



    @db_session
    def test_next_turn_is_panic(self):

        rs = RoomsService(self.db)

        room: Room = self.create_valid_room(
            roomname="test_play_panic_card"
        )

        rs.assign_turns(room)

        # La unica carta disponible va a ser de panico
        panic_card = Card.select(type="PANICO").first()
        assert panic_card is not None
        room.available_cards.add(panic_card) #type:ignore

        player = room.players.select(position = room.turn).first() #type:ignore
        player.sid = "test_next_turn_is_panic"

        assert player is not None

        player: Player

        assert len(room.available_cards) != 0

        assert panic_card.type == "PANICO"

        # Le damos la carta de panico al jugador en turno
        rs.next_turn(player.sid)

        assert room.machine_state == MachineState.PANICKING

        assert room.machine_state_options.get("card_picking_amount", None) is not None

    @db_session
    def test_next_turn_is_alejate(self):

        rs = RoomsService(self.db)

        room: Room = self.create_valid_room(
            roomname="test_play_alejate_card"
        )

        rs.assign_turns(room)

        # La unica carta disponible va a ser de panico
        alejate_card = Card.select(type="ALEJATE").first()
        assert alejate_card is not None
        room.available_cards.add(alejate_card) #type:ignore

        player = room.players.select(position = room.turn).first() #type:ignore
        player.sid = "test_next_turn_is_alejate"

        assert player is not None

        player: Player

        assert len(room.available_cards) != 0

        assert alejate_card.type == "ALEJATE"

        # Le damos la carta de alejate al jugador en turno
        rs.next_turn(player.sid)

        assert room.machine_state == MachineState.PLAYING


    @db_session
    def test_create_room_succesful(self):
        """
        Deberia poder crear esta Room sin errores
        """
        roomname = "newroom"
        hostname = "hostname"
        newroom = NewRoomSchema(
            room_name   =  roomname,
            host_name   = hostname,
            min_players =  4,
            max_players =  12,
            is_private  =  False
        )
        self.rs.create_room(newroom)
        rooms = Room.select()
        assert rooms.count() == 1
        room = rooms.first()
        assert room is not None
        assert room.name == roomname 

        host = room.get_host() 
        assert host.name == hostname

    @db_session
    def test_join_room(self):
        """
        Deberia unir un jugador a una partida
        """
        # borramos todas las rooms y jugadores
        
        Room.select().delete()
        Player.select().delete()

        # creamos una partida
        roomname = f"test_join_room"
        hostname = "hostname"
        newroom = NewRoomSchema(
            room_name   =  roomname,
            host_name   = hostname,
            min_players =  4,
            max_players =  12,
            is_private  =  False
        )
        self.rs.create_room(newroom)
        room = Room.get(name=roomname)
        self.rs.join_player(name='player_in_room', room_id=room.id)

        players_in_room = list(room.players.select())
        player_in_room = Player.get(name='player_in_room')

        assert player_in_room is not None
        assert player_in_room in players_in_room
        
    @db_session
    def test_join_invalid_room(self):
        # borramos todas las rooms y jugadores
        Room.select().delete()
        Player.select().delete()
    
        with self.assertRaises(InvalidRoomException):
            self.rs.join_player(name='player_in_room', room_id=17128371)

    @db_session
    def test_join_room_duplicate_user(self):
        # borramos todas las rooms y jugadores
        Room.select().delete()
        Player.select().delete()

        # creamos una partida
        roomname = f"test_join_room"
        hostname = "hostname"
        newroom = NewRoomSchema(
            room_name   =  roomname,
            host_name   = hostname,
            min_players =  4,
            max_players =  12,
            is_private  =  False
        )
        self.rs.create_room(newroom)

        room = Room.get(name=roomname)
        
        self.rs.join_player(name='player_in_room', room_id=room.id)
        with self.assertRaises(DuplicatePlayerNameException):
            self.rs.join_player(name='player_in_room', room_id=room.id)

    @db_session
    def test_initialize_deck(self):
        """
        Deberia popular el set available_cards con la cantidad de cartas correspondientes
        """
        Room.select().delete()
        Player.select().delete()
        for i in range(4, 12):
            # eliminamos todas las partidas y jugadores de la db
            # creamos una room
            roomname = f"test_initialize_deck-{i}"
            hostname = "hostname"
            newroom = NewRoomSchema(
                room_name   =  roomname,
                host_name   = hostname,
                min_players =  4,
                max_players =  12,
                is_private  =  False
            )
            self.rs.create_room(newroom)
            
            # obtenemos la entidad room, como es la unica tiene id=1
            room = Room.get(name=roomname)

            # creamos y unimos los jugadores
            for j in range(i-1):
                self.rs.join_player(name=f'player{j}', room_id=room.id)            

            # inicializamos las cartas
            self.rs.initialize_deck(room)

            # probamos que esten las cartas correspondientes        
            for card in list(room.available_cards):
                assert card.deck <= i

            assert len(room.available_cards) != 0 

        
    @db_session
    def test_initial_deal_succesful(self):
        """
        Deberia poder repartir sin errores (popular room.available_cards y las manos de cada player)
        """
        Room.select().delete()
        Player.select().delete()

        roomname = "newroom"
        hostname = "p0"
        newroom = NewRoomSchema(
            room_name   =  roomname,
            host_name   = hostname,
            min_players =  4,
            max_players =  12,
            is_private  =  False
        )
        self.rs.create_room(newroom)
        room = Room.select().first()    
    
        self.rs.join_player(name="p1", room_id=room.id)
        self.rs.join_player(name="p2", room_id=room.id)
        self.rs.join_player(name="p3", room_id=room.id)
        
        self.rs.initialize_deck(room)
        self.rs.initial_deal(room)

        for player in room.players:
            assert len(player.hand) == 4

        for player in room.players: 
            for card in player.hand: 
                assert card.type == 'ALEJATE'

        for card in room.available_cards:
            assert card.name != 'La cosa'
            
        qty_la_cosa = 0    
        for player in room.players:
            for card in player.hand:
                if card.name == 'La cosa':
                    assert player.rol == 'LA_COSA'
                    qty_la_cosa += 1

        assert qty_la_cosa == 1

    @db_session
    def test_list_rooms(self):
        Room.select().delete()
        Player.select().delete()

        assert self.rs.list_rooms() == []

        room = self.create_valid_room(roomname='test_list_rooms',qty_players=7)
        response = self.rs.list_rooms()

        assert len(response) == 1
        assert response[0]['id'] == room.id
        assert response[0]['name'] == room.name
        assert response[0]['max_players'] == room.max_players
        assert response[0]['min_players'] == room.min_players
        assert response[0]['players_count'] == len(room.players)
        assert response[0]['is_private'] == room.is_private
    
    @db_session
    def test_next_player_from_player(self):
        Room.select().delete()
        Player.select().delete()

        newroom = NewRoomSchema(
            room_name   = "test_next_player_from_player",
            host_name   = "hostName",
            min_players =  4,
            max_players =  12,
            is_private  =  False
        )
        self.rs.create_room(newroom)
        room = Room.get(name="test_next_player_from_player")
        for i in range(3):
            self.rs.join_player(f"player-{i}", room.id)
        i = 0
        for player in room.players:
            player.position = i
            i += 1
        next_player = room.next_player_from_player(room.players.select(lambda x:x.position==2).first())
        assert next_player.position == 3
        return room

    @db_session
    def test_start_game(self):
        """
        Deberia popular el set available_cards con la cantidad de cartas correspondientes
        """
        Room.select().delete()
        Player.select().delete()
        for i in range(4, 12):
            # eliminamos todas las partidas y jugadores de la db
            # creamos una room
            roomname = f"test_initialize_game-{i}"
            hostname = "hostname"
            newroom = NewRoomSchema(
                room_name   =  roomname,
                host_name   = hostname,
                min_players =  4,
                max_players =  12,
                is_private  =  False
            )
            self.rs.create_room(newroom)
            
            # obtenemos la entidad room, como es la unica tiene id=1
            room = Room.get(name=roomname)

            # creamos y unimos los jugadores
            for j in range(i-1):
                self.rs.join_player(name=f'player{j}', room_id=room.id)            

            # obtenemos el host de la partida y le asignamos sid = 1
            room.get_host().sid = f"{i}"
            #el jugador con sid = i (host) inicia la partida
            self.rs.start_game(f"{i}")

            # probamos que esten las cartas correspondientes        
            for card in list(room.available_cards):
                assert card.deck <= i

            assert len(room.available_cards) != 0 
            assert room.status == "IN_GAME"
            assert len(room.players) == i
            assigned_positions = []
            for player in room.players:
                assert player.position not in assigned_positions 
                assert player.position >= 0 and player.position < i
                assigned_positions.append(player.position)
            assert room.turn == 0
        pass

    @classmethod
    @db_session
    def tearDownClass(cls) -> None:
        Room.select().delete()
        Player.select().delete()
        Card.select().delete()
