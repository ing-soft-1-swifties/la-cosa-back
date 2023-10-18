from pony.orm import db_session
from app.models import Player, Card, Room
from app.services.exceptions import *
from app.services.mixins import DBSessionMixin

class CardsService(DBSessionMixin):
    pass
    @db_session
    def card_to_JSON_from_cid(self, card_id : int):
        card = Card.get(id = card_id)
        if card is None:
            raise InvalidCardException()
        return card.json()

    def play_lanzallamas(self, player : Player, room : Room, card : Card, card_options):
        """Juega una carta lanzallamas.

        Args: player, card, card_options

        Returns: list(tuples(event_name, event_body))
        """
        target_id = card_options.get("target")
        if target_id is None:
            raise InvalidAccionException("Objetivo invalido")
        target_player = Player.get(id = target_id)
        if target_player is None or target_player.status != "VIVO":
            raise InvalidAccionException("Objetivo Invalido")

        #veamos que esten al lado
        if player.position is None or target_player.position is None:
            #seleccionar una buena excepcion
            raise Exception()
        
        # Vemos que los jugadores esten adyacentes:
        if abs(player.position - target_player.position) != 1 and \
            abs(player.position - target_player.position) !=  len(room.players.select(status = "VIVO"))-1:
            #falta enriquecer con info a este excepcion
            raise InvalidAccionException("El objetivo no esta al lado tuyo")

        target_player.status = "MUERTO"  
        return[("on_game_player_death",{"player":target_player.name})]