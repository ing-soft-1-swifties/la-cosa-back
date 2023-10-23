import unittest
from pony.orm import Database, db_session
from app.models.entities import Player, Room, Card
from app.models.populate_cards import populate
from app.services.games import GamesService
from app.services.cards import CardsService
from app.services.play_card import PlayCardsService
from app.services.rooms import RoomsService
from app.schemas import NewRoomSchema

from app.services.exceptions import *

unittest.TestLoader.sortTestMethodsUsing = None # type: ignore 

class TestPlayCardsService(unittest.TestCase):

    db: Database
    gs: GamesService
    cs: CardsService

    @classmethod
    def setUpClass(cls) -> None:
        from app.models.testing_db import db
        cls.db = db
        cls.gs = GamesService(db = cls.db) 
        cls.cs = CardsService(db = cls.db)
        cls.pcs = PlayCardsService(db = cls.db)

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

        room.status = "IN_GAME"
        
        rs.initialize_deck(room)
        rs.initial_deal(room)
        rs.assign_turns(room)

        return room

    @db_session
    def test_play_card_lanzallamas(self):
        room: Room = self.create_valid_room(roomname='test_play_card_lanzallamas', qty_players=4)
        
        card = list(Card.select(lambda x : x.name == "Lanzallamas"))[0]

        host = room.get_host()
        #agregamos lazallamas a la mano de host
        host.hand.add(card)
        #setemos el sid del host para poder invacar play_card desde host
        host.sid = "test_play_card_lanzallamas"

        #host en la posicion 0
        host.position = 0

        #asignamos desde la posicion 1 en adelante a los demas jugadores
        position = 1
        for player in room.players:
            if player.id != host.id:    
                player.position = position
                position += 1
        
        #next_player sera el jugador que sigue de host
        next_player = list(room.players.select(lambda player: player.position == 1))[0]

        #seetamos el room para que le toque a host
        room.status = "IN_GAME"
        room.machine_state = "PLAYING"
        room.machine_state_options = {"id" : host.id}
        room.turn = host.position
        
        #far_player sera un jugador que no esta al lado de host
        far_player = list(room.players.select(lambda player: player.position == 2))[0]
        
        json =  {"card": card.id, "card_options": {"target": far_player.id}}
        ret = self.gs.play_card_manager("test_play_card_lanzallamas", json)
        assert ret[0]["name"] == "on_game_invalid_action"
        assert ret[0]["broadcast"] == False

        
        #veamos que si la jugamos correctamente se muere el objetivo
        last_hand_size = len(host.hand)
        ret = self.gs.play_card_manager("test_play_card_lanzallamas", {"card": card.id, "card_options": {"target": next_player.id}})
        assert ret[0]["name"] !=  "on_game_invalid_action"
        assert next_player.status == "MUERTO"
        assert len(host.hand) == last_hand_size-1

    @classmethod
    @db_session
    def tearDownClass(cls) -> None:
        Room.select().delete()
        Player.select().delete()
        Card.select().delete()