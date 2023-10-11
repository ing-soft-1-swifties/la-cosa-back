from pony.orm import Database, db_session
import unittest
from app.models.populate_cards import populate
from app.models.entities import Player, Room, Card
from app.schemas import NewRoomSchema
from app.services.rooms import RoomsService

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

    def test_join_room(self):
        pass
        
    def test_join_room_duplicate_user(self):
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


    @classmethod
    @db_session
    def tearDownClass(cls) -> None:
        Room.select().delete()
        Player.select().delete()
