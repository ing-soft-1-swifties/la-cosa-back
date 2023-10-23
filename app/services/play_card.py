from pony.orm import db_session
from app.models import Player, Card, Room
from app.services.exceptions import *
from app.services.mixins import DBSessionMixin

class PlayCardsService(DBSessionMixin):

    def play_lanzallamas(self, player : Player, room : Room, card : Card, card_options):
        """Juega una carta lanzallamas.

        Args: player, card, card_options
        """
        #lista de eventos que vamos a retornar
        events = []
        target_id = card_options.get("target")
        if target_id is None:
            raise InvalidAccionException("Objetivo invalido")
        target_player = Player.get(id = target_id)
        if target_player is None or target_player.status != "VIVO":
            raise InvalidAccionException("Objetivo Invalido")

        # veamos que esten al lado
        if player.position is None or target_player.position is None:
            # seleccionar una buena excepcion
            raise Exception()
        
        # Vemos que los jugadores esten adyacentes:
        if abs(player.position - target_player.position) != 1 and \
            abs(player.position - target_player.position) !=  len(room.players.select(status = "VIVO"))-1:
            # falta enriquecer con info a este excepcion
            raise InvalidAccionException("El objetivo no esta al lado tuyo")

        target_player.status = "MUERTO"  
        events.append({
            "name": "on_game_player_death",
            "body": {
                "player": target_player.name
            },
            "broadcast": True
        })

        events.append({
            "name":"on_game_player_play_card",
            "body":{
                "player": player.name,
                "card" : card.json(),
                "card_options" : card_options,
            },
            "broadcast":True
        }) 
        return events

    @db_session
    def play_whisky(self, player: Player, room: Room, card: Card, card_options):
        # Whisky: Enséñales todas tus cartas a los demás jugadores. 
        # Esta carta sólo puedes jugarla sobre ti mismo
        
        events = []

        cardsJSON = []
        for card_i in player.hand:
            cardsJSON.append(card_i.json())

        events.append({
            'name': 'on_game_player_play_card',
            'body': {
                'card': card.id,
                'card_options': card_options,
                'effects' : {
                    'player': player.name, 
                    'cards': cardsJSON
                }
            },
            'broadcast': True
        })

        return events


