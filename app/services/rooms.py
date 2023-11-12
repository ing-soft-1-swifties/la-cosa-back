from pickle import EMPTY_LIST
from fastapi import HTTPException
from pony.orm import count, db_session, Set
from app.models import Player, Room, Card
from app.schemas import NewRoomSchema, RoomSchema
from app.services.exceptions import *
from app.services.mixins import DBSessionMixin
from app.logger import rootlog
import random
from uuid import uuid4

class RoomsService(DBSessionMixin):

    @db_session
    def join_player(self, name: str, room_id: int):
        expected_room = Room.get(id=room_id)
        if expected_room is None:
            raise InvalidRoomException()
        # #easter egg
        # if name == expected_room.get_host().name:
        #     return expected_room.get_host().token
        # #easter egg end
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
        if expected_player is None:
            raise InvalidSidException()
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
    def start_game(self, sent_sid : str):
        """
        si el jugador es propietario de una partida y esta no esta iniciada, dadas las condiciones para que se pueda iniciar una partida, esta se inicia
        """
        events = []
        expected_player = Player.get(sid = sent_sid)
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
        events.append(
        {
            "name":"on_room_start_game",
            "body":{},
            "broadcast":True
        })
        events.extend(self.next_turn(sent_sid))
        return events

    @db_session
    def end_game(self, actual_sid : str):
        # si el jugador es propietario de una partida esta se termina
        expected_player = Player.get(sid = actual_sid)
        if expected_player is None:
            raise InvalidSidException()
        expected_room = expected_player.playing
        if expected_room is None:
            raise InvalidRoomException()
        #por ahora no vamos a borrar la partida para no inducir bugs sobre accesos tardios a sid de jugadores eliminados
        # for player in expected_room.players:
        #     player.delete()
        # expected_room.delete()
        expected_room.status = "FINISHED"

    @db_session
    def list_rooms(self):
        return [room.json() for room in Room.select(lambda room: room.status == "LOBBY")]
    
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
        cards_to_deal = list(room.available_cards.select(lambda c : c.name != 'La cosa' and c.type != 'PANICO' and c.sub_type != 'CONTAGIO').limit(qty_cards_to_deal -1))
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
            rootlog.exception("partida inicializada incorrectamente, turno no pre-seteado")
            raise Exception
        turn = 0
        if room.machine_state == "INITIAL":
            # TODO: cambiar por get_player_by_pos(0)
            expected_player = room.players.select(lambda player: player.position==0)
        else:
            expected_player = room.next_player()
            if expected_player is None:
                rootlog.exception(f"El jugador con turno ({turn}) no esta en la partida")
                raise Exception

        return expected_player

    @db_session
    def in_turn_player(self, room):
        if room.turn is None:
            print("partida inicializada incorrectamente, turno no pre-seteado")
            raise Exception
        expected_player = None
        #asumo que las posiciones estan correctas (ie: no estan repetidas y no faltan)
        for player in room.players:
            if player.position == room.turn and player.status == "VIVO":
                expected_player = player
        if expected_player is None: 
            print(f"el jugador con turno {room.turn} no esta en la partida")
            raise Exception
        return expected_player

    @db_session
    def next_turn(self, sent_sid : str):
        try:
            player = Player.get(sid = sent_sid)
            if player is None:
                raise InvalidSidException()
            room: Room = player.playing
            if room.machine_state == "INITIAL":
                room.turn = 0
            else:
                #cantidad de jugadores que siguen jugando
                room.turn = room.next_player().position
            in_turn_player = self.in_turn_player(room)
            # seteamos el estado del juego para esperar que el proximo jugador juegue
            room.machine_state = "PLAYING"
            room.machine_state_options = {"id":in_turn_player.id,
                                          "stage":"STARTING"}
            from app.services.cards import CardsService
            cs = CardsService(self.db)
            new_card = cs.give_card(in_turn_player)
            return [
                {
                    "name":"on_game_player_turn",
                    "body":{"player":in_turn_player.name},
                    "broadcast": True
                },
                {
                    "name":"on_game_player_steal_card",
                    "body":{"cards":[new_card.json()]},
                    "broadcast": False,
                    "receiver_sid":in_turn_player.sid
                }
            ]
        except Exception as e:
            rootlog.exception(f"error al querer repartir carta al primer jugador de la partida del jugador con sid: {sent_sid}")
            rootlog.exception(f"{e}")

    @db_session
    def recalculate_positions(self, sent_sid : str):    
        """
            Reasigna posiciones, manteniendo el orden de las personas
            asume que la partida no esta terminada, se puede seguir jugando
        """
        player = Player.get(sid = sent_sid)
        if player is None:
            raise InvalidSidException()
        room = player.playing
        if room.turn is None:
            print("partida inicializada incorrectamente, turno no pre-seteado")
            raise Exception
        id_position = []
        for player in room.players:
            if player.status == "VIVO":
                id_position.append((player.position, player))
        id_position.sort(key  = lambda x : x[0])
        position = 0
        should_update_turn = True
        for pair in id_position:
            if pair[1].position != position and position <= room.turn and should_update_turn:
                room.turn -= 1
                should_update_turn = False
                pass
            pair[1].position = position
            position += 1
            

    @db_session
    def new_message(sent_sid : str, data):
        try:
            return [{
                "name" : "on_player_new_message",
                "body" : {
                    "player_name" : Player.get(sid = sent_sid),
                    "message" : data["message"]
                },
                "broadcast" : True
            }]
        except:
            raise InvalidDataException()