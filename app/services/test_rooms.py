from pony.orm import Database, db_session
import unittest
from app.models.populate_cards import populate
from app.models.entities import Player, Room, Card
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
        populate()

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
        assert rooms.count() == 1;
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


        pass
    
    def test_join_invalid_room(self):
        pass

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


    
    db_session
    def test_initial_deal_succesful(self):
        """
        Deberia poder repartir sin errores (popular room.available_cards y las manos de cada player)
        """
        rooms = Room.select()
        room = rooms.first()
        
        
        if rooms.count() == 0:
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
        else:     
            room = rooms.first()
            
    
        self.rs.join_player(self.rs, "p1", room.id)
        self.rs.join_player(self.rs, "p2", room.id)
        self.rs.join_player(self.rs, "p3", room.id)
        assert room.players.count() == 4
        self.rs.initial_deal(room)
        assert room.discarted_cards.count() == 0
        assert room.available_cards.count() != 0
        are_from_deck = True
        for card in room.available_cards:
                are_from_deck = are_from_deck && card.deck
        
        
        

    @classmethod
    @db_session
    def tearDownClass(cls) -> None:
        Room.select().delete()
        Player.select().delete()
