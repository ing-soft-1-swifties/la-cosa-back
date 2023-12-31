import unittest
from pony.orm import Database, db_session
from app.models.entities import Player, Room, Card
from app.models.populate_cards import populate
from app.services.games import GamesService
from app.services.cards import CardsService
from app.services.play_card import PlayCardsService
from app.services.rooms import RoomsService
from app.schemas import NewRoomSchema
from app.models.constants import CardName as cards

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
    def create_valid_room(self, roomname: str = 'newroom', qty_players: int = 12) -> Room:
        rs = RoomsService(self.db)

        newroom = NewRoomSchema(
            room_name=roomname,
            host_name='hostName',
            min_players=4,
            max_players=12,
            is_private=False,
        )
        rs.create_room(newroom)
        room = Room.get(name=roomname)

        for i in range(qty_players - 1):
            rs.join_player(f'player-{i}', room.id)

        room.status = 'IN_GAME'
        
        rs.initialize_deck(room)
        rs.initial_deal(room)
        rs.assign_turns(room)

        return room

    @db_session
    def test_play_card_lanzallamas(self):
        room: Room = self.create_valid_room(roomname='test_play_card_lanzallamas', qty_players=4)
        
        card = list(Card.select(lambda x : x.name == cards.LANZALLAMAS))[0]

        host = room.get_host()
        #agregamos lazallamas a la mano de host
        host.hand.add(card)
        #setemos el sid del host para poder invacar play_card desde host
        host.sid = 'test_play_card_lanzallamas'

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
        nada_de_barbacoas = Card.select(name = cards.NADA_DE_BARBACOAS)
        next_player.hand.remove(nada_de_barbacoas)

        #seetamos el room para que le toque a host
        room.status = 'IN_GAME'
        room.machine_state = 'PLAYING'
        room.machine_state_options = {'id' : host.id}
        room.turn = host.position
        
        #far_player sera un jugador que no esta al lado de host
        far_player = list(room.players.select(lambda player: player.position == 2))[0]
        
        json =  {'card': card.id, 'card_options': {'target': far_player.id}}
        with self.assertRaises(InvalidAccionException):
            self.gs.play_card_manager('test_play_card_lanzallamas', json)

        
        #veamos que si la jugamos correctamente se muere el objetivo
        last_hand_size = len(host.hand)
        self.gs.play_card_manager('test_play_card_lanzallamas', {'card': card.id, 'card_options': {'target': next_player.id}})
        assert next_player.status == 'MUERTO'
        assert len(host.hand) == last_hand_size-1

    @db_session
    def test_play_card_whisky(self):
        TEST_NAME = 'test_play_card_whisky'
        # creamos una room valida
        room = self.create_valid_room(roomname=TEST_NAME, qty_players=12)

        # obtenemos un jugador y le damos la carta whisky
        player: Player = room.players.random(1)[0]
        whisky = Card.select(lambda c: c.name== cards.WHISKY).first()
        player.hand.add(whisky)


        response = self.pcs.play_whisky(player, room, whisky, {'arg': []})

        assert len(response) == 1

        response = response[0]

        assert response['name'] == 'on_game_player_play_card'
        assert whisky.id == response['body']['card_id']
        assert player.serialize_hand(exclude=[whisky.id]) == response['body']['effects']['cards']

    @db_session
    def test_play_card_aterrador(self):
        TEST_NAME = 'test_play_card_aterrador'
        # creamos una room valida
        room = self.create_valid_room(roomname=TEST_NAME, qty_players=12)

        # obtenemos un jugador y le damos la carta whisky
        player: Player = room.players.select(lambda x:x.position == 1).first()
        aterrador = Card.select(lambda c: c.name== cards.ATERRADOR).first()
        player.hand.add(aterrador)
        # obtenemos el jugador anterior y le damos un no gracias (podria haber sido cualquiera)
        last_player: Player = room.players.select(lambda x:x.position == 0).first()
        no_gracias = Card.select(lambda c: c.name== cards.NO_GRACIAS).first()
        last_player.hand.add(no_gracias)


        response = self.pcs.play_aterrador(player, room, aterrador, {
            "starter_card_id":no_gracias.id,
            "starter_name": last_player.name})

        assert len(response) == 1

        response = response[0]

        assert response['name'] == 'on_game_defend_with_aterrador'
        assert no_gracias.id == response['body']['card_id']

    @db_session
    def test_play_card_sospecha(self):
        TEST_NAME = 'test_play_card_sospecha'
        # creamos una room valida
        room = self.create_valid_room(roomname=TEST_NAME, qty_players=12)

        # obtenemos un jugador y le damos la carta sospecha
        player = room.players.select(lambda p: p.position==0).first()
        adyacent_player = room.players.select(lambda p: p.position==1).first()

        sospecha = Card.select(lambda c: c.name== cards.SOSPECHA).first()
        player.hand.add(sospecha)
        # jugamos la carta sospecha
        response = self.pcs.play_sospecha(player, room, sospecha, card_options={'target': adyacent_player.id})

        assert len(response) == 2

        assert response[0]['name'] == 'on_game_player_play_card'
        assert response[1]['name'] == 'on_game_player_play_card'
        
        assert sospecha.id == response[0]['body']['card_id']
        assert sospecha.id == response[1]['body']['card_id']

        # print(response[0])
        # print(response[1])
        response = response[1]

        cards_id = []
        for card in adyacent_player.hand:
            cards_id.append(card.id)

        for cardJSON in response['body']['effects']['cards']:
            assert cardJSON['id'] in cards_id


    @db_session
    def test_play_card_ups(self):
        TEST_NAME = 'test_play_card_ups'
        # creamos una room valida
        room = self.create_valid_room(roomname=TEST_NAME, qty_players=12)

        player: Player = room.players.random(1)[0]
        ups = Card.select(lambda c: c.name == cards.UPS).first()
        player.add_card(ups.id)

        response = self.pcs.play_ups(
            player=player,
            room=room,
            card=ups,
            card_options={'arg': []}
        )[0]
        assert response['body']['card_id'] == ups.id
        assert  player.serialize_hand(exclude=[ups.id]) == response['body']['effects']['cards']

    @db_session
    def test_play_card_que_quede_entre_nosotros(self):
        TEST_NAME = 'test_play_card_que_quede_entre_nosotros'
        # creamos una room valida
        room = self.create_valid_room(roomname=TEST_NAME, qty_players=12)

        # seleccionamos un jugador al azar y le damos la carta
        player: Player = room.players.select(lambda p: p.position==1).first()
        between_us = Card.select(lambda c: c.name == cards.QUE_QUEDE_ENTRE_NOSOTROS).first()
        player.add_card(between_us.id)

        # seleccionamos un jugador adjacente
        adyacent_player: Player = room.players.select(lambda p: p.position==2).first()

        response = self.pcs.play_que_quede_entre_nosotros(
            player=player,
            room=room,
            card=between_us,
            card_options={'target': adyacent_player.id}
        )
        assert len(response) == 2

        assert response[0]['name'] == 'on_game_player_play_card'
        assert response[0]['body']['card_id'] == between_us.id
        assert response[0]['receiver_sid'] == adyacent_player.sid
        assert response[0]['body']['effects']['player'] == player.name
        assert response[0]['body']['effects']['cards'] == player.serialize_hand(exclude=[between_us.id])

        assert response[1]['name'] == 'on_game_player_play_card'
        assert response[1]['body']['card_id'] == between_us.id

        assert response[1]['body']['card_id'] == between_us.id
        assert player.serialize_hand(exclude=[between_us.id]) == response[0]['body']['effects']['cards']


    @db_session
    def test_play_card_analisis(self):
        TEST_NAME = 'test_play_card_analisis'
        # creamos una room valida
        room = self.create_valid_room(roomname=TEST_NAME, qty_players=12)

        # seleccionamos un jugador al azar y le damos la carta
        player: Player = room.players.select(lambda p: p.position==1).first()
        analisis = Card.select(lambda c: c.name == cards.ANALISIS).first()
        player.add_card(analisis.id)

        # seleccionamos un jugador adjacente
        adyacent_player: Player = room.players.select(lambda p: p.position==2).first()

        response = self.pcs.play_analisis(
            player=player,
            room=room,
            card=analisis,
            card_options={'target': adyacent_player.id}
        )
        assert len(response) == 2

        # broadcast
        assert response[0]['name'] == 'on_game_player_play_card'
        assert response[0]['body']['card_id'] == analisis.id
        assert response[0]['body']['card_name'] == analisis.name
        assert response[0]['body']['player_name'] == player.name
        assert response[0]['broadcast']

        # objectivo
        assert response[1]['name'] == 'on_game_player_play_card'
        assert response[1]['body']['card_id'] == analisis.id
        assert response[1]['body']['card_name'] == analisis.name
        assert response[1]['body']['player_name'] == player.name
        assert response[1]['body']['effects']['player'] == adyacent_player.name
        assert response[1]['body']['effects']['cards'] == adyacent_player.serialize_hand()
        assert not response[1]['broadcast']

    @db_session
    def test_play_cambio_de_lugar(self):
        TEST_NAME = 'test_play_cambio_de_lugar'
        # creamos una room valida
        room = self.create_valid_room(roomname=TEST_NAME, qty_players=12)

        # seleccionamos un jugador al azar y le damos la carta
        player: Player = room.players.select(lambda p: p.position == 0).first()
        room.turn = player.position
        cambio_de_lugar = Card.select(lambda c: c.name == cards.CAMBIO_DE_LUGAR).first()
        player.add_card(cambio_de_lugar.id)

        # seleccionamos un jugador no adjacente
        adyacent_player: Player = room.players.select(lambda p: p.position == 1).first()

        player_position = player.position
        adyacent_player_position = adyacent_player.position

        # seleccionamos un jugador adjacente
        response = self.pcs.play_cambio_de_lugar(
            player=player,
            room=room,
            card=cambio_de_lugar,
            card_options={'target': adyacent_player.id}  # INTVALID
        )

        # comportamiento esperado de rooms
        assert player.position == adyacent_player_position
        assert adyacent_player.position == player_position

        # evento on_game_swap_positions
        assert len(response) == 2
        assert response[0]['name'] == 'on_game_swap_positions'
        assert player.name in response[0]['body']['players']
        assert adyacent_player.name in response[0]['body']['players']
        assert response[0]['broadcast']

        # evento on_game_player_play_card
        assert response[1]['name'] == 'on_game_player_play_card'
        assert response[1]['broadcast']
        assert response[1]['body']['card_id'] == cambio_de_lugar.id
        assert response[1]['body']['card_name'] == cambio_de_lugar.name
        assert response[1]['body']['player_name'] == player.name

    @db_session
    def test_play_vigila_tus_espaldas(self):
        TEST_NAME = 'test_play_vigila_tus_espaldas'
        # creamos una room valida
        room = self.create_valid_room(roomname=TEST_NAME, qty_players=12)

        # seleccionamos un jugador al azar y le damos la carta
        player: Player = room.players.select(lambda p: p.position == 0).first()
        room.turn = player.position
        card = Card.select(lambda c: c.name == cards.VIGILA_TUS_ESPALDAS).first()
        player.add_card(card.id)

        # guardamos la direccion vieja
        old_direction = room.direction

        response = self.pcs.play_vigila_tus_espaldas(
            player=player,
            room=room,
            card=card,
            card_options={}  # INTVALID
        )

        # comportamiento esperado
        assert room.direction != old_direction
        assert len(response) == 1
        assert response[0]['name'] == 'on_game_player_play_card'
        assert response[0]['body']['card_id'] == card.id
        assert response[0]['body']['card_name'] == card.name
        assert response[0]['body']['player_name'] == player.name
        assert response[0]['broadcast']

    @db_session
    def test_play_cuarentena(self):
        TEST_NAME = 'test_play_cuarentena'
        # creamos una room valida
        room = self.create_valid_room(roomname=TEST_NAME, qty_players=12)

        # seleccionamos un jugador al azar y le damos la carta
        player: Player = room.players.select(lambda p: p.position == 0).first()
        room.turn = player.position
        card = Card.select(lambda c: c.name == cards.CUARENTENA).first()
        player.add_card(card.id)

        # seleccionamos un jugador no adjacente
        other_player: Player = room.players.select(lambda p: p.position == 1).first()

        # seleccionamos un jugador adjacente
        response = self.pcs.play_cuarentena(
            player=player,
            room=room,
            card=card,
            card_options={'target': other_player.id}
        )

        # comportamiento esperado
        assert other_player.is_in_quarantine()

        # evento on_game_swap_positions
        assert len(response) == 1
        assert response[0]['name'] == 'on_game_player_play_card'
        assert response[0]['body']['card_id'] == card.id
        assert response[0]['body']['card_name'] == card.name
        assert response[0]['body']['player_name'] == player.name
        assert response[0]['broadcast']

    @db_session
    def test_play_cuerdas_podridas(self):
        TEST_NAME = 'test_play_cuerdas_podridas'
        # creamos una room valida
        room = self.create_valid_room(roomname=TEST_NAME, qty_players=12)

        # seleccionamos un jugador al azar y le damos la carta
        player: Player = room.players.select(lambda p: p.position == 0).first()
        room.turn = player.position
        card = Card.select(lambda c: c.name == cards.CUERDAS_PODRIDAS).first()
        player.add_card(card.id)

        # seleccionamos otro jugador y lo ponemos en cuarentena
        other_player: Player = room.players.select(lambda p: p.position == 1).first()
        other_player.set_quarantine(2)

        # seleccionamos un jugador adjacente
        response = self.pcs.play_cuerdas_podridas(
            player=player,
            room=room,
            card=card,
            card_options={}
        )
        assert not other_player.is_in_quarantine()

        assert len(response) == 1
        assert response[0]['name'] == 'on_game_player_play_card'
        assert response[0]['body']['card_id'] == card.id
        assert response[0]['body']['card_name'] == card.name
        assert response[0]['body']['player_name'] == player.name
        assert response[0]['broadcast']

    @db_session
    def test_play_puerta_atrancada(self):
        TEST_NAME = 'test_play_puerta_atrancada'
        # creamos una room valida
        room = self.create_valid_room(roomname=TEST_NAME, qty_players=12)

        # seleccionamos un jugador al azar y le damos la carta
        player: Player = room.players.select(lambda p: p.position == 0).first()
        room.turn = player.position
        card = Card.select(lambda c: c.name == cards.PUERTA_ATRANCADA).first()
        player.add_card(card.id)

        # seleccionamos a un jugador adjacente
        other_player: Player = room.players.select(lambda p: p.position == 1).first()
        response = self.pcs.play_puerta_atrancada(
            player=player,
            room=room,
            card=card,
            card_options={'target': player.id}
        )
        assert player.position in room.get_obstacles_positions()

        assert len(response) == 1
        assert response[0]['name'] == 'on_game_player_play_card'
        assert response[0]['body']['card_id'] == card.id
        assert response[0]['body']['card_name'] == card.name
        assert response[0]['body']['player_name'] == player.name
        assert response[0]['broadcast']

    @db_session
    def test_play_hacha(self):
        TEST_NAME = 'test_play_hacha'
        # creamos una room valida
        room = self.create_valid_room(roomname=TEST_NAME, qty_players=12)

        # seleccionamos un jugador al azar y le damos la carta
        player: Player = room.players.select(lambda p: p.position == 0).first()
        room.turn = player.position
        card = Card.select(lambda c: c.name == cards.HACHA).first()
        player.add_card(card.id)


        # seleccionamos a un jugador adjacente
        other_player: Player = room.players.select(lambda p: p.position == 1).first()

        other_player.set_quarantine(2)

        # jugamos hacha sobre una CUARENTENA
        response = self.pcs.play_hacha(
            player=player,
            room=room,
            card=card,
            card_options={
                'is_quarantine': True,
                'target': other_player.id
            }
        )
        assert not other_player.is_in_quarantine()

        # agregamos una PUERTA ATRANCADA
        room.add_locked_door(other_player.position)

        # jugamos hacha sobre la PUERTA ATRANCADA
        response = self.pcs.play_hacha(
            player=player,
            room=room,
            card=card,
            card_options={
                'is_quarantine': False,
                'target': other_player.id
            }
        )

        assert not other_player.position in room.get_obstacles_positions()

        assert len(response) == 1
        assert response[0]['name'] == 'on_game_player_play_card'
        assert response[0]['body']['card_id'] == card.id
        assert response[0]['body']['card_name'] == card.name
        assert response[0]['body']['player_name'] == player.name
        assert response[0]['broadcast']

    @db_session
    def test_play_hacha_invalid(self):
        TEST_NAME = 'test_play_hacha_invalid'
        # creamos una room valida
        room = self.create_valid_room(roomname=TEST_NAME, qty_players=12)

        # seleccionamos un jugador al azar y le damos la carta
        player: Player = room.players.select(lambda p: p.position == 0).first()
        room.turn = player.position
        card = Card.select(lambda c: c.name == cards.HACHA).first()
        player.add_card(card.id)

        # seleccionamos a un jugador adjacente
        other_player: Player = room.players.select(lambda p: p.position == 1).first()

        with self.assertRaises(InvalidAccionException):
            self.pcs.play_hacha(
                player=player,
                room=room,
                card=card,
                card_options={}
            )

        with self.assertRaises(InvalidAccionException):
            self.pcs.play_hacha(
                player=player,
                room=room,
                card=card,
                card_options={
                    'is_quarantine': False,
                    'target': other_player.id
                }
            )

    @db_session
    def test_play_tres_cuatro(self):
        TEST_NAME = 'test_play_tres_cuatro'
        # creamos una room valida
        room = self.create_valid_room(roomname=TEST_NAME, qty_players=12)

        # seleccionamos un jugador al azar y le damos la carta
        player: Player = room.players.select(lambda p: p.position == 0).first()
        room.turn = player.position
        card = Card.select(lambda c: c.name == cards.TRES_CUATRO).first()
        player.add_card(card.id)

        # seleccionamos a un jugador adjacente
        other_player: Player = room.players.select(lambda p: p.position == 1).first()

        room.add_locked_door(other_player.position)
        # jugamos hacha sobre una CUARENTENA
        response = self.pcs.play_tres_cuatro(
            player=player,
            room=room,
            card=card,
            card_options={}
        )
        assert not other_player.position in room.get_obstacles_positions()
        assert len(response) == 1
        assert response[0]['name'] == 'on_game_player_play_card'
        assert response[0]['body']['card_id'] == card.id
        assert response[0]['body']['card_name'] == card.name
        assert response[0]['body']['player_name'] == player.name
        assert response[0]['broadcast']

    @db_session
    def test_play_seduccion(self):
        TEST_NAME = 'test_play_seduccion'
        # creamos una room valida
        room = self.create_valid_room(roomname=TEST_NAME, qty_players=12)

        # seleccionamos un jugador al azar y le damos la carta
        player: Player = room.players.select(lambda p: p.position == 0).first()
        room.turn = player.position
        card = Card.select(lambda c: c.name == cards.SEDUCCION).first()
        player.add_card(card.id)

        # seleccionamos a un jugador adjacente
        other_player: Player = room.players.select(lambda p: p.position == 1).first()

        # jugamos hacha sobre una CUARENTENA
        response = self.pcs.play_seduccion(
            player=player,
            room=room,
            card=card,
            card_options={'target': other_player.id}
        )

        assert len(response) == 1
        assert response[0]['name'] == 'on_game_player_play_card'
        assert response[0]['body']['card_id'] == card.id
        assert response[0]['body']['card_name'] == card.name
        assert response[0]['body']['player_name'] == player.name
        assert response[0]['broadcast']

    @db_session
    def test_play_mas_vale_que_corras(self):
        TEST_NAME = 'test_play_mas_vale_que_corras'
        # creamos una room valida
        room = self.create_valid_room(roomname=TEST_NAME, qty_players=12)

        # seleccionamos un jugador al azar y le damos la carta
        player: Player = room.players.select(lambda p: p.position == 0).first()
        room.turn = player.position
        card = Card.select(lambda c: c.name == cards.MAS_VALES_QUE_CORRAS).first()
        player.add_card(card.id)
        old_player_position = player.position

        # seleccionamos a un jugador adjacente
        other_player: Player = room.players.select(lambda p: p.position == 1).first()
        old_other_player_position = other_player.position


        # jugamos hacha sobre una CUARENTENA
        response = self.pcs.play_mas_vale_que_corras(
            player=player,
            room=room,
            card=card,
            card_options={'target': other_player.id}
        )

        assert player.position == old_other_player_position
        assert other_player.position == old_player_position

        assert len(response) == 2
        assert response[1]['name'] == 'on_game_player_play_card'
        assert response[1]['body']['card_id'] == card.id
        assert response[1]['body']['card_name'] == card.name
        assert response[1]['body']['player_name'] == player.name
        assert response[1]['broadcast']

    @db_session
    def test_play_nada_de_barbacoas(self):
        TEST_NAME = 'test_play_nada_de_barbacoas'
        # creamos una room valida
        room = self.create_valid_room(roomname=TEST_NAME, qty_players=12)

        # seleccionamos un jugador al azar y le damos la carta
        player: Player = room.players.select(lambda p: p.position == 0).first()
        room.turn = player.position
        card = Card.select(lambda c: c.name == cards.NADA_DE_BARBACOAS).first()
        player.add_card(card.id)
        old_player_position = player.position

        # seleccionamos a un jugador adjacente
        other_player: Player = room.players.select(lambda p: p.position == 1).first()
        old_other_player_position = other_player.position

        # jugamos hacha sobre una CUARENTENA
        response = self.pcs.play_nada_de_barbacoas(
            player=player,
            room=room,
            card=card,
            card_options={'target': other_player.id}
        )

        assert len(response) == 1
        assert response[0]['name'] == 'on_game_player_play_defense_card'
        assert response[0]['body']['player_name'] == player.name
        assert response[0]['body']['card_name'] == card.name
        assert response[0]['body']['card_id'] == card.id
        assert response[0]['broadcast']

    @db_session
    def test_play_fallaste(self):
        TEST_NAME = 'test_play_fallaste'
        # creamos una room valida
        room = self.create_valid_room(roomname=TEST_NAME, qty_players=12)

        # seleccionamos un jugador al azar y le damos la carta
        player: Player = room.players.select(lambda p: p.position == 0).first()
        room.turn = player.position

        card = Card.select(lambda c: c.name == cards.FALLASTE).first()
        player.add_card(card.id)

        # seleccionamos a un jugador adjacente
        other_player: Player = room.players.select(lambda p: p.position == 1).first()

        # jugamos hacha sobre una CUARENTENA
        response = self.pcs.play_fallaste(
            player=player,
            room=room,
            card=card,
            card_options={
                'starter_player_id': other_player.id,
            }
        )

        assert len(response) == 1
        assert response[0]['name'] == 'on_game_begin_exchange'
        assert response[0]['broadcast']

    @db_session
    def test_play_aqui_estoy_bien(self):
        TEST_NAME = 'test_play_aqui_estoy_bien'
        # creamos una room valida
        room = self.create_valid_room(roomname=TEST_NAME, qty_players=12)

        # seleccionamos un jugador al azar y le damos la carta
        player: Player = room.players.select(lambda p: p.position == 0).first()
        room.turn = player.position
        card = Card.select(lambda c: c.name == cards.AQUI_ESTOY_BIEN).first()
        player.add_card(card.id)

        # seleccionamos a un jugador adjacente
        other_player: Player = room.players.select(lambda p: p.position == 1).first()

        # jugamos hacha sobre una CUARENTENA
        response = self.pcs.play_aqui_estoy_bien(
            player=player,
            room=room,
            card=card,
            card_options={'target': other_player.id}
        )

        assert len(response) == 1
        assert response[0]['name'] == 'on_game_player_play_defense_card'
        assert response[0]['body']['player_name'] == player.name
        assert response[0]['body']['card_name'] == card.name
        assert response[0]['body']['card_id'] == card.id
        assert response[0]['broadcast']

    @classmethod
    @db_session
    def tearDownClass(cls) -> None:
        Room.select().delete()
        Player.select().delete()
        Card.select().delete()
