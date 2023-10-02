from fastapi import HTTPException
from pony.orm import db_session
from pony.orm.dbapiprovider import uuid4
from app.models import Player, Room
from app.schemas import NewRoomSchema
from app.services.exceptions import DuplicatePlayerNameException, InvalidRoomException
from app.services.mixins import DBSessionMixin


class RoomsService(DBSessionMixin):

    @db_session
    def join_player(self, name: str, room_id: int):
        """
        Registra a un jugador en una sala existente.

        Parameters
        ----------
        name : str
            El nombre del jugador que se va a registrar en la sala.
        room_id : int
            El identificador único de la sala a la que se unirá el jugador.

        Returns
        -------
        token : str
            Un token único generado para el jugador recién registrado.

        Raises
        ------
        InvalidRoomException
            Se lanza si no se encuentra una sala con el ID proporcionado.
        DuplicatePlayerNameException
            Se lanza si ya existe un jugador con el mismo nombre en la sala.
        """
        expected_room = Room.get(id=room_id)

        if expected_room is None:
            raise InvalidRoomException()

        token = str(uuid4())

        if expected_room.players.select(lambda player : player.name == name).count() > 0:
            raise DuplicatePlayerNameException()
            

        new_player = Player(name = name, token=token)

        expected_room.players.add(new_player)

        return token

    @db_session
    def create_room(self, room: NewRoomSchema) -> str:
        # crear instancia de jugador y partida nueva que lo referencie
        """
        Crea una nueva sala de juego con el anfitrión especificado.

        Parameters
        ----------
        room : NewRoomSchema
            Un objeto que contiene la información necesaria para crear la sala.

        Returns
        -------
        token : str 
            Un token único generado para el anfitrion de la sala.
        """
        token = str(uuid4())

        host = Player(name=room.host_name, token=token, is_host=True)
        
        new_room = Room(
            min_players = room.min_players, 
            max_players = room.max_players, 
            status=0, 
            is_private=room.is_private,
            name = room.room_name
        )

        new_room.players.add(host)

        return token

    @db_session
    def start_game(self, actual_sid : str):
        #si el jugador es propietario de una partida y esta no esta iniciada
        #dadas las condiciones para que se pueda iniciar una partida, esta se inicia

        expected_player = Player.get(sid = actual_sid)
        if expected_player is None:
            raise InvalidSidException()
        if expected_player.hosting is None:
            raise NotOwnerExeption()
        
        expected_room = Room.get(id = expected_player.hosting)
        if expected_room is None:
            raise InvalidRoomException()
        if (len(expected_room.playes) < expected_room.min_players or 
            len(expected_room.players) > expected_room.max_players):

        

        

        Room(
                min_players = room.min_players, 
                max_players = room.max_players, 
                host = host,
                status=0, 
                is_private=room.is_private,
                name = room.room_name
        )

        self.db.commit()

        return token