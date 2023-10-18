from pickle import EMPTY_LIST
from fastapi import HTTPException
from pony.orm import count, db_session, Set
from pony.orm.dbapiprovider import uuid4
from app.models import Player, Room, Card
from app.schemas import NewRoomSchema, RoomSchema
#from app.services.exceptions import DuplicatePlayerNameException, InvalidRoomException
from app.services.exceptions import *
from app.services.mixins import DBSessionMixin
from app.logger import rootlog
import random

class RoomsService(DBSessionMixin):

    @db_session
    def join_player(self, name: str, room_id: int):
        # TODO: validar partida y union del jugador
        
        expected_room = Room.get(id=room_id)
        if expected_room is None:
            raise InvalidRoomException()
        # #easter egg
        # if name == expected_room.get_host().name:
        #     return expected_room.get_host().token
        # #easter egg end
        # #ultra easter egg
        # for player in expected_room.players:
        #     if player.name == name:
        #         return player.token
        # #ultra easter egg end
        if expected_room.status != "LOBBY":   #not in lobby
            raise NotInLobbyException()
        if len(expected_room.players) >= expected_room.max_players:
            raise TooManyPlayersException()
        token = str(uuid4())
        
        if len(expected_room.players.select(lambda player : player.name == name)) > 0:
            raise DuplicatePlayerNameException()


        new_player = Player(name = name, token=token, playing=expected_room, is_host = False)

        expected_room.players.add(new_player)

        return token

    @db_session
    def create_room(self, room: NewRoomSchema) -> str:
        # crear instancia de jugador y partida nueva que lo referencie
        token = str(uuid4())
        new_room = Room(
                min_players = room.min_players, 
                max_players = room.max_players, 
                status="LOBBY", 
                is_private=room.is_private,
                name = room.room_name
        )
        Player(name=room.host_name, token=token, playing=new_room, is_host=True, )
        self.db.commit()
        return token

    @db_session
    def get_players_sid(self, actual_sid):
        expected_player = Player.get(sid = actual_sid)
        expected_room = expected_player.playing
        if expected_room is None:
            raise InvalidRoomException()
        return [player.sid for player in list(expected_room.players)]

    @db_session
    def assign_turns(self, room : Room):
        turn = 0
        for player in room.players:
            player.position = turn
            turn += 1 

    @db_session
    def start_game(self, actual_sid : str):
        """
        si el jugador es propietario de una partida y esta no esta iniciada, dadas las condiciones para que se pueda iniciar una partida, esta se inicia
        """
        expected_player = Player.get(sid = actual_sid)
        if expected_player is None:
            raise InvalidSidException()
        if expected_player.is_host == False:
            raise NotOwnerExeption()
        expected_room = expected_player.playing
        if expected_room is None:
            raise InvalidRoomException()
        if expected_room.status != "LOBBY":   #not in lobby
            raise NotInLobbyException()
        if len(expected_room.players) < expected_room.min_players:
            raise NotEnoughPlayersException()
        if len(expected_room.players) > expected_room.max_players:
            raise TooManyPlayersException()
        self.assign_turns(expected_room)
        expected_room.status = "IN_GAME"    #in game
        expected_room.machine_state = "INITIAL"
        try:
            self.initialize_deck(expected_room)
        except Exception as e:
            rootlog.exception("Error al iniciar mazo")
            expected_room.status = "LOBBY"    
            expected_room.available_cards.clear()
            raise e
        try:
            self.initial_deal(expected_room)
        except Exception as e:
            rootlog.exception("Error al repartir cartas")
            expected_room.status = "LOBBY"    
            for player in expected_room.players:
                player.hand.clear()
            raise e


    @db_session
    def end_game(self, actual_sid : str):
        #si el jugador es propietario de una partida esta se termina
        expected_player = Player.get(sid = actual_sid)
        if expected_player is None:
            raise InvalidSidException()
        expected_room = expected_player.playing
        if expected_room is None:
            raise InvalidRoomException()
        for player in expected_room.players:
            player.delete()
        expected_room.delete()


    @db_session
    def list_rooms(self):

        def get_json(room):
            return { 
                'id': room.id,
                'name': room.name,
                'max_players' : room.max_players,
                'min_players' : room.min_players,
                'players_count' : len(room.players),
                'is_private' : room.is_private
            }

        return [get_json(room) for room in Room.select(lambda x: x.status == "LOBBY")]
    
    @db_session
    def initialize_deck(self, room : Room):
        """
        Se cargan las cartas que se van a usar en la partida dependiendo de la cantidad de players.
        """
        # cantidad de jugadores
        player_count = len(room.players)
        # query para conseguir las cartas correspondientes a la cantidad de jugadores
        cards = list(Card.select(lambda c : c.deck <= player_count))
        # limpiamos los sets de relaciones
        room.available_cards.clear()
        room.discarted_cards.clear()
        # agregamos las cartas
        room.available_cards.add(cards)

        return 

    @db_session
    def initial_deal(self, room : Room):
        """
        Repartir las cartas iniciales.
        """
        # cantidad de cartas a repartir
        qty_cards_to_deal = len(room.players)*4
        # obtenemos todas todas las cartas alejate menos las de contagio
        cards_to_deal = list(room.available_cards \
                            .select(lambda c : c.name != 'La cosa' and c.type != 'PANICO' and c.sub_type != 'CONTAGIO')\
                            .limit(qty_cards_to_deal -1))
        #se agrega la cosa a las cartas repartibles 
        cards_to_deal.append(list(room.available_cards.select(lambda lacosa : lacosa.name == 'La cosa') ))
        
        
        # mezclamos las cartas
        random.shuffle(cards_to_deal) 
        # eliminamos todas las cartas a repartir del mazo de cartas disponibles
        for card in cards_to_deal:
            room.available_cards.remove(card)
        
        # room.available_cards.select(lambda c : c in cards_to_deal).delete()

        # repartimos
        for player in list(room.players):
            player.hand.clear()
            for card_index in range(4):
                player.hand.add(cards_to_deal.pop(len(cards_to_deal)-1))
            
            for card in player.hand:
                if card.name == 'La cosa':
                    player.rol = 'LA_COSA'
        return
    
    @db_session
    def next_player(self, room):
        if room.turn is None:
            print("partida inicializada incorrectamente, turno no pre-seteado")
            raise Exception
        if room.machine_state == "INITIAL":
            room.turn = 0
        else:
            room.turn = (room.turn + 1) % (len(room.players.select(lambda player : player.status == "VIVO")))    #cantidad de jugadores que siguen jugando
        expected_player = None
        #asumo que las posiciones estan correctas (ie: no estan repetidas y no faltan)
        for player in room.players:
            if player.position == room.turn and player.status == "VIVO":
                expected_player = player
        if expected_player is None: 
            print(f"el jugador con turno {room.turn} no esta en la partida")
            raise Exception
        return expected_player