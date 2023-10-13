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

        room.status = 'IN_GAME' 
        rs.initialize_deck(room)
        rs.initial_deal(room)
        rs.assign_turns(room)

        return room


    @db_session
    def test_give_card_without_shuffle(self):

        room = self.create_valid_room(roomname='test_give_card_without_shuffle', qty_players=12)
        player = list(room.players.random(1))[0]

        self.gs.give_card(player, room)
        assert len(player.hand) == 5
        
    @db_session
    def test_discard_card_successful(self):
        # room del jugador
        room = self.create_valid_room(roomname='test_discard_card_successful', qty_players=4)

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
        room = self.create_valid_room(roomname='test_discard_card_invalid_turn', qty_players=4)

        # seleccionamos un jugador al azar
        player = list(room.players.random(1))[0]

        # asignamos el turno
        room.turn = player.position + 1
        
        # conseguimos una carta
        card = list(Card.select(lambda c: c.name == 'Sospecha').random(1))[0]
        player.hand.add(card)

        with self.assertRaises(PlayerNotInTurn):
            self.gs.discard_card(player, card)

    @db_session
    def test_discard_card_invalid_not_in_hand(self):
        # room del jugador
        room = self.create_valid_room(roomname='test_discard_card_invalid_not_in_hand', qty_players=4)

        # seleccionamos un jugador al azar
        player = list(room.players.random(1))[0]

        # asignamos el turno
        room.turn = player.position

        # conseguimos una carta
        card = list(Card.select(lambda c: c.name == 'Sospecha').random(1))[0]
        player.hand.remove(card)
        
        with self.assertRaises(CardNotInPlayerHandExeption):
            self.gs.discard_card(player, card)

    @db_session
    def test_discard_card_invalid_room(self):
        # room del jugador
        room = self.create_valid_room(roomname='test_discard_card_invalid_room', qty_players=4)

        room.status = 'LOBBY'

        # seleccionamos un jugador al azar
        player = list(room.players.random(1))[0]

        # asignamos el turno
        room.turn = player.position

        # conseguimos una carta
        card = list(Card.select(lambda c: c.name == 'Sospecha').random(1))[0]
        player.hand.remove(card)
        
        with self.assertRaises(InvalidRoomException):
            self.gs.discard_card(player, card)

    @db_session
    def test_give_card_with_invalid_card(self):
        # creamos una room con 4 jugadores
        room = self.create_valid_room(roomname='test_give_card_with_invalid_card', qty_players=4)

        # seleccionamos un jugador al azar
        player = list(room.players.random(1))[0]

        # asignamos el turno
        room.turn = player.position

        # eliminamos las cartas de infeccion del jugador
        infected_player_cards = list(player.hand.select(lambda c: c.name == 'Infectado'))
        player.hand.remove(infected_player_cards)

        # conseguimos una carta de infeccion y se la agregamos al jugador
        card = list(Card.select(lambda c: c.name == 'Infectado').random(1))[0]
        player.hand.add(card)

        # cambiamos el rol del jugador
        player.rol = 'INFECTADO'

        # intentamos descartar la carta de infeccion
        with self.assertRaises(InvalidCardException):
            self.gs.discard_card(player, card)

        # Test: el jugador con rol "la cosa" intenta descartar la cosa
        
        # conseguimos la carta y se la damos al jugador
        card = list(Card.select(lambda c: c.name == 'La cosa').random(1))[0]
        player.hand.add(card)
        #intentamos descartar la carta "la cosa" (no se puede descartar en ningun caso)
        with self.assertRaises(InvalidCardException):
            self.gs.discard_card(player, card)


    @db_session 
    def test_end_game_condition(self):
        
        room:Room = self.create_valid_room(roomname='test_end_game_condition', qty_players=4)
        
        for player in room.players.select():
            player.rol = 'HUMANO'
            player.status = 'VIVO'
        list(room.players.select())[0].rol = 'LA_COSA'
        
        assert self.gs.end_game_condition(room) == 'GAME_IN_PROGRESS'
        
        list(room.players.select(lambda p: p.rol == 'LA_COSA'))[0].status = 'MUERTO'
        
        assert self.gs.end_game_condition(room) == 'HUMANS_WON' 
        
        for player in room.players.select():
            player.rol = 'INFECTADO'
            player.status = 'VIVO'
        list(room.players.select())[0].rol = 'LA_COSA'
        
        assert self.gs.end_game_condition(room) == 'LA_COSA_WON' 
               
        for player in room.players.select():
            player.rol = 'HUMANO'
            player.status = 'MUERTO'
        list(room.players.select())[0].rol = 'LA_COSA' 
        list(room.players.select(lambda p: p.rol == 'LA_COSA'))[0].status = 'VIVO'

        assert self.gs.end_game_condition(room) == 'LA_COSA_WON'
        

    @classmethod
    @db_session
    def tearDownClass(cls) -> None:
        Room.select().delete()
        Player.select().delete()
        Card.select().delete()