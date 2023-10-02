from fastapi import HTTPException
from pony.orm import db_session
from app.models import Player, Room, Card
#from app.services.exceptions import DuplicatePlayerNameException, InvalidRoomException
from app.services.exceptions import *
from app.services.mixins import DBSessionMixin

class GamesService(DBSessionMixin):

    @db_session
    def game_state(self, room : Room):
        # TODO: exporta en json el estado de la partida, para enviar al frontend
        def player_state(player):
            return{
                "name" : player.name,
                "state" : player.status,
                "position" : player.position,
            }
        game_state = {
            "game_status" : room.status,
            "turn" : room.turn,
            "players_state" : [player_state(player) for player in room.players]
        }
        return game_state

    @db_session
    def personal_game_state(self, player : Player):
        #devuelve un diccionario que representa el estado del juego desde la vision de un jugador
        player_in_game_state = self.game_state(player.playing)
        player_in_game_state.update(
        )
        return player_in_game_state
        #falta un poco de informacion, completar

    def play_card(self, player:Player, card:Card):
        #se juega una carta, notar que van a ocurrir eventos (ej:alguien muere), debemos llevar registro
        #para luego notificar al frontend (una propuesta es devolve una lista de eventos con sus especificaciones)
        #a todos los afectados por el evento se les reenvia el game_state
        pass

    def get_card(self, player:Player, room:Room):
        #se entrega una carta del mazo de disponibles al usuario
        pass

    def discard_card(self, player:Player, room:Room):
        #hay que verificar que pueda, si es asi se agrega al mazo de descartes y se quita del jugador
        pass
