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

        self.gs.give_card(player)
        assert len(player.hand) == 5
    
    @db_session
    def test_give_card_with_shuffle(self):
        # creamos la room y obtenemos un jugador
        room = self.create_valid_room(roomname='test_give_card_without_shuffle', qty_players=12)
        player = list(room.players.random(1))[0]
        
        # eliminamos todas las cartas de la room y de la mano del jugador
        room.available_cards.clear()
        room.discarted_cards.clear()
        player.hand.clear()

        # obtenemos una carta y la agregamos al mazo de descarte
        card = list(Card.select(lambda c: c.name=='Infectado'))[0]
        room.discarted_cards.add(card)
        
        # le damos una carta al jugador, como no hay cartas disponibles, deberia "mezclar" y
        # dar la unica carta que estaba en discarted_cards

        self.gs.give_card(player)
        assert len(player.hand) == 1
        assert card in player.hand


    @db_session
    def test_discard_card_successful(self):
        # room del jugador
        room = self.create_valid_room(roomname='test_discard_card_successful', qty_players=4)

        # seleccionamos un jugador al azar
        player = room.get_host()

        # asignamos el turno
        room.turn = player.position
        room.machine_state = "PLAYING"
        room.machine_state_options = {"id":player.id}

        # conseguimos una carta
        card = list(Card.select(lambda c: c.name == 'Sospecha').random(1))[0]
        player.hand.add(card)
        cards_in_hand_before = len(player.hand)
        
        # seteamos la room
        room.machine_state = 'PLAYING'
        room.machine_state_options = {
            'id': player.id
        }
        player.sid = "27016"
        json = {"card": card.id}
        self.gs.discard_card("27016", json)

        assert card not in player.hand
        assert card in room.discarted_cards
        assert len(player.hand) == cards_in_hand_before - 1 

    @db_session
    def test_discard_card_invalid_turn(self):
        # room del jugador
        room = self.create_valid_room(roomname='test_discard_card_invalid_turn', qty_players=4)

        # seleccionamos un jugador al azar
        player = room.get_host()

        # asignamos el turno
        room.turn = player.position + 1
        
        # conseguimos una carta
        card = list(Card.select(lambda c: c.name == 'Sospecha').random(1))[0]
        player.hand.add(card)

        # seteamos la room
        room.machine_state = 'PLAYING'
        room.machine_state_options = {
            'id': player.id+1
        }
        player.sid = "27016"
        json = {"card": card.id}


        with self.assertRaises(InvalidAccionException):
            self.gs.discard_card("27016", json)

    @db_session
    def test_discard_card_invalid_not_in_hand(self):
        # room del jugador
        room = self.create_valid_room(roomname='test_discard_card_invalid_not_in_hand', qty_players=4)

        # seleccionamos un jugador al azar
        player = room.get_host()

        # asignamos el turno
        room.turn = player.position

        # conseguimos una carta
        card = list(Card.select(lambda c: c.name == 'Sospecha').random(1))[0]
        player.hand.remove(card)
        
        # seteamos la room
        room.machine_state = 'PLAYING'
        room.machine_state_options = {
            'id': player.id
        }
        player.sid = "27016"
        json = {"card": card.id}

        with self.assertRaises(InvalidCardException):
            self.gs.discard_card("27016", json)

    @db_session
    def test_discard_card_invalid_room(self):
        # room del jugador
        room = self.create_valid_room(roomname='test_discard_card_invalid_room', qty_players=4)


        # seleccionamos un jugador al azar
        player = room.get_host()

        # asignamos el turno
        room.turn = player.position

        # conseguimos una carta
        card = list(Card.select(lambda c: c.name == 'Sospecha').random(1))[0]
        player.hand.add(card)
        
        # seteamos la room
        room.status = 'LOBBY'
        room.machine_state = 'PLAYING'
        room.machine_state_options = {
            'id': player.id
        }
        player.sid = "27016"
        json = {"card": card.id}

        with self.assertRaises(InvalidRoomException):
            self.gs.discard_card("27016", json)

    @db_session
    def test_give_card_with_invalid_card(self):
        # creamos una room con 4 jugadores
        room = self.create_valid_room(roomname='test_give_card_with_invalid_card', qty_players=4)

        # seleccionamos un jugador al azar
        player = room.get_host()

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

        # seteamos la room
        room.machine_state = 'PLAYING'
        room.machine_state_options = {
            'id': player.id
        }
        player.sid = "27016"
        json = {"card": card.id}
        
        # intentamos descartar la carta de infeccion
        with self.assertRaises(InvalidCardException):
            self.gs.discard_card("27016", json)

        # Test: el jugador con rol "la cosa" intenta descartar la cosa
        
        # conseguimos la carta y se la damos al jugador
        card = list(Card.select(lambda c: c.name == 'La cosa').random(1))[0]
        player.hand.add(card)
        json = {"card": card.id}
        #intentamos descartar la carta "la cosa" (no se puede descartar en ningun caso)
        with self.assertRaises(InvalidCardException):
            self.gs.discard_card("27016", json)

    @db_session 
    def test_end_game_condition(self):
        # room valido
        room:Room = self.create_valid_room(roomname='test_end_game_condition', qty_players=4)
        
        for player in room.players.select():
            player.rol = 'HUMANO'
            player.status = 'VIVO'
        list(room.players.select())[0].rol = 'LA_COSA'

        #seteamos el sid del host para poder enviarlo a la funcion
        room.get_host().sid = "1234"

        # tan todos los players vivos 
        assert self.gs.end_game_condition("1234")[0] == 'GAME_IN_PROGRESS'

        list(room.players.select(lambda p: p.rol == 'LA_COSA'))[0].status = 'MUERTO'
        # esta la cosa muerta
        assert self.gs.end_game_condition("1234")[0] == 'HUMANS_WON' 
        
        for player in room.players.select():
            player.rol = 'INFECTADO'
            player.status = 'VIVO'
        list(room.players.select())[0].rol = 'LA_COSA'
        # todos lod players estan infectados
        assert self.gs.end_game_condition("1234")[0] == 'LA_COSA_WON' 
               
        for player in room.players.select():
            player.rol = 'HUMANO'
            player.status = 'MUERTO'
        list(room.players.select())[0].rol = 'LA_COSA' 
        list(room.players.select(lambda p: p.rol == 'LA_COSA'))[0].status = 'VIVO'
        # solo queda la cosa viva
        assert self.gs.end_game_condition("1234")[0] == 'LA_COSA_WON'
        
        list(room.players.select(lambda p: p.rol == 'LA_COSA'))[0].status = 'MUERTO'
        list(room.players.select(lambda p: p.rol != 'LA_COSA'))[0].status = 'VIVO'
        # esta la cosa muerta, y un humano vivo
        assert self.gs.end_game_condition("1234")[0] == 'HUMANS_WON'

    @db_session 
    def test_exchange_cards_invalid_position(self):
        
        room:Room = self.create_valid_room(roomname='test_exchange_cards_invalid_position', qty_players=4)
        # room.direction = True
        room.turn= 0
        sender:Player =list(room.players.select(position=0))[0]
        reciever:Player = list(room.players.select(position=3))[0]
        card_s : Card= list(sender.hand.select(lambda c: c.name != 'La cosa' and c.name != 'Infectado'))[0]
        card_r : Card= list(reciever.hand.select(lambda c: c.name != 'La cosa' and c.name != 'Infectado'))[0]
        
        #seteamos el sid del host para poder enviarlo a la funcion
        # room.get_host().sid = "1234"

        with self.assertRaises(InvalidExchangeParticipants):
            self.gs.exchange_cards(room=room,sender=sender,reciever=reciever,card_s=card_s, card_r=card_r)

    @db_session 
    def test_exchange_cards_not_in_turn(self):
        
        room:Room = self.create_valid_room(roomname='test_exchange_cards_not_in_turn', qty_players=4)
        # room.direction = True
        room.turn=0
        sender:Player =list(room.players.select(position=2))[0]
        reciever:Player = list(room.players.select(position=3))[0]
        card_s : Card= list(sender.hand.select(lambda c: c.name != 'La cosa' and c.name != 'Infectado'))[0]
        card_r : Card= list(reciever.hand.select(lambda c: c.name != 'La cosa' and c.name != 'Infectado'))[0]
        
        with self.assertRaises(PlayerNotInTurn):
            self.gs.exchange_cards(room=room,sender=sender,reciever=reciever,card_s=card_s, card_r=card_r)

    @db_session 
    def test_exchange_cards_card_not_in_hand(self):
        room:Room = self.create_valid_room(roomname='test_exchange_cards_card_not_in_hand', qty_players=4)
        # room.direction = True
        sender:Player =list(room.players.select(rol='LA_COSA'))[0]
        room.turn = sender.position
        reciever:Player = list(room.players.select(position=(sender.position+1)%len(room.players.select(status='VIVO'))))[0]
        card_s: Card = list(room.available_cards.select(lambda c: c not in sender.hand))[0]
        card_r : Card= list(reciever.hand.select(lambda c: c.name != 'La cosa' and c.name != 'Infectado'))[0]
        
        with self.assertRaises(CardNotInPlayerHandExeption):
            self.gs.exchange_cards(room=room,sender=sender,reciever=reciever,card_s=card_s, card_r=card_r)
        
    @db_session 
    def test_exchange_cards_la_cosa(self):
        
        room:Room = self.create_valid_room(roomname='test_exchange_cards_la_cosa', qty_players=4)
        room.direction = True
        sender:Player =list(room.players.select(rol='LA_COSA'))[0]
        room.turn=sender.position
        reciever:Player = list(room.players.select(position=(sender.position+1)%len(room.players.select(status='VIVO'))))[0]
        
        card_s: Card = list(sender.hand.select(name='La cosa'))[0]
        card_r : Card= list(reciever.hand.select(lambda c: c.name != 'La cosa' and c.name != 'Infectado'))[0]
        
        with self.assertRaises(RoleCardExchange):
            self.gs.exchange_cards(room=room,sender=sender,reciever=reciever,card_s=card_s, card_r=card_r)
    
    @db_session 
    def test_exchange_cards_invalid_ifection_human_to_anything(self):
        
        room:Room = self.create_valid_room(roomname='test_exchange_cards_invalid_ifection_human_to_anything', qty_players=4)
        room.direction = True
        sender:Player =list(room.players.select(rol='HUMANO'))[0]
        room.turn=sender.position
        reciever:Player = list(room.players.select(position=(sender.position+1)%len(room.players.select(status='VIVO'))))[0]
        card_s: Card = list(room.available_cards.select(name='Infectado'))[0]
        
        temp_c = list(sender.hand.select())[0]
        sender.hand.remove(temp_c)
        sender.hand.add(card_s)
        
        card_r : Card= list(reciever.hand.select(lambda c: c.name != 'La cosa' and c.name != 'Infectado'))[0]
        
        with self.assertRaises(InvalidCardExchange):
            self.gs.exchange_cards(room=room,sender=sender,reciever=reciever,card_s=card_s, card_r=card_r)
    
    @db_session
    def test_exchange_cards_invalid_ifection_last_infection(self):
        room:Room = self.create_valid_room(roomname='test_exchange_cards_invalid_ifection_human_to_anything', qty_players=4)
        room.direction = True
        sender:Player =list(room.players.select(rol='LA_COSA'))[0]
        room.turn=sender.position
        reciever:Player = list(room.players.select(position=(sender.position+1)%len(room.players.select(status='VIVO'))))[0]
        card_s: Card = list(sender.hand.select(lambda c:c.name != 'La cosa'))[0]        
        card_r:Card = list(room.available_cards.select(name='Infectado'))[0]
        temp_c = list(reciever.hand.select())[0]
        reciever.hand.remove(temp_c)
        reciever.hand.add(card_r)
        reciever.rol = 'INFECTADO'
        
        with self.assertRaises(RoleCardExchange):
            self.gs.exchange_cards(room=room,sender=sender,reciever=reciever,card_s=card_s, card_r=card_r)
            
    @db_session
    def test_exchange_cards_invalid_ifection_infected_to_human(self):
        room:Room = self.create_valid_room(roomname='test_exchange_cards_invalid_ifection_infected_to_human', qty_players=4)
        room.direction = True
        sender:Player = list(room.players.select(rol='HUMANO'))[0]
        room.turn=sender.position
        reciever:Player = list(room.players.select(position=(sender.position+1)%len(room.players.select(status='VIVO'))))[0]
        card_s: Card = list(sender.hand.select(lambda c:c.name != 'La cosa'))[0]        
        card_r:Card = list(room.available_cards.select(name='Infectado'))[0]
        reciever.hand.select().delete()
        reciever.hand.add( list(room.available_cards.select(name='Infectado'))[1])
        reciever.hand.add(card_r)
        reciever.hand.add(card_r)
        # inf_count = 0
        # for inf in list(reciever.hand.select(name='Infectado')):
        #     inf_count += 1
        # print(inf_count)
        # print(len(reciever.hand.select(name='Infectado')))
        reciever.rol = 'INFECTADO'
        
        with self.assertRaises(InvalidCardExchange):
            self.gs.exchange_cards(room=room,sender=sender,reciever=reciever,card_s=card_s, card_r=card_r)

    @db_session
    def test_exchange_cards_infection_direction_true(self):
        room:Room = self.create_valid_room(roomname='test_exchange_cards_infection_direction_true', qty_players=4)
        room.direction = True
        sender:Player =list(room.players.select(rol='LA_COSA'))[0]
        room.turn = sender.position
        reciever:Player = list(room.players.select(position=(sender.position+1)%len(room.players.select(status='VIVO'))))[0]
        card_s: Card = list(room.available_cards.select(name='Infectado'))[0]
        
        temp_c = list(sender.hand.select(lambda c: c.name!='La cosa'))[0]
        sender.hand.remove(temp_c)
        sender.hand.add(card_s)
        
        card_r : Card= list(reciever.hand.select(lambda c: c.name != 'La cosa' and c.name != 'Infectado'))[0]
        
        self.gs.exchange_cards(room,sender,reciever,card_s,card_r)
        
        assert reciever.rol == 'INFECTADO'
        

    @db_session
    def test_exchange_cards_infection_direction_true(self):
        room:Room = self.create_valid_room(roomname='test_exchange_cards_infection_direction_true', qty_players=4)
        room.direction = True
        sender:Player =list(room.players.select(rol='LA_COSA'))[0]
        room.turn = sender.position
        reciever:Player = list(room.players.select(position=(sender.position+1)%len(room.players.select(status='VIVO'))))[0]
        card_s: Card = list(room.available_cards.select(name='Infectado'))[0]
        
        temp_c = list(sender.hand.select(lambda c: c.name!='La cosa'))[0]
        sender.hand.remove(temp_c)
        sender.hand.add(card_s)
        
        card_r : Card= list(reciever.hand.select(lambda c: c.name != 'La cosa' and c.name != 'Infectado'))[0]
        
        self.gs.exchange_cards(room,sender,reciever,card_s,card_r)
        assert reciever.rol == 'INFECTADO'


    @db_session
    def test_play_card(self):
        room:Room = self.create_valid_room(roomname='test_play_card', qty_players=4)
        
        card = list(Card.select(lambda x : x.name == "Sospecha"))[0]

        host = room.get_host()
        host.hand.add(card)
        host.sid = "1234"

        room.status = "IN_GAME"
        room.machine_state = "PLAYING"
        room.machine_state_options = {"id" : host.id}

        room.turn = host.position
        last_hand_size = len(host.hand)
        self.gs.play_card("1234", {"card": card.id, "card_options": {"target": None}})
        assert last_hand_size == len(host.hand)+1

    @db_session
    def test_play_card_lanzallamas(self):
        room:Room = self.create_valid_room(roomname='test_play_card_lanzallamas', qty_players=4)
        sender:Player =list(room.players.select(rol='LA_COSA'))[0]
        
        card = list(Card.select(lambda x : x.name == "Lanzallamas"))[0]

        host = room.get_host()
        host.hand.add(card)
        host.sid = "1234"

        room.status = "IN_GAME"
        room.machine_state = "PLAYING"
        room.machine_state_options = {"id" : host.id}
        position = 1
        next_player = None
        for player in room.players:
            if player.id != host.id:
                if position  == 1:
                    next_player = player
                player.position = position
                position += 1
        
        room.turn = host.position
        last_hand_size = len(host.hand)
        self.gs.play_card("1234", {"card": card.id, "card_options": {"target": player.id}})
        assert player.status == "MUERTO"
    @classmethod
    @db_session
    def tearDownClass(cls) -> None:
        Room.select().delete()
        Player.select().delete()
        Card.select().delete()