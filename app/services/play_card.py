from pony.orm import db_session
from app.models import Player, Card, Room
from app.services.exceptions import *
from app.services.mixins import DBSessionMixin

class PlayCardsService(DBSessionMixin):

    def valid_adyacent_player(self, player_1: Player, player_2: Player, room: Room) -> bool:

        if player_1.position is None or player_2.position is None:
            return False

        if  abs(player_1.position - player_2.position) != 1 and \
            abs(player_1.position - player_2.position) != room.qty_alive_players() - 1:
            return False

        return True

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
        # Enséñales todas tus cartas a los demás jugadores.
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

    @db_session
    def play_analisis(self, player: Player, room: Room, card: Card, card_options):
        # Agarra 1 carta aleatoria de un jugador adyacente, mirala y devuélvesela
        
        events = []

        # validamos el input
        target_id = card_options.get("target")
        if target_id is None:
            raise InvalidAccionException("Objetivo invalido")
        
        target_player: Player = Player.get(id = target_id)
        if target_player is None or target_player.status != "VIVO" or target_player.playing != room :
            raise InvalidAccionException("Objetivo Invalido")

        if not self.valid_adyacent_player(player, target_player, room):
            raise InvalidAccionException("El objetivo no esta al lado tuyo")

        # obtenemos las cartas en formato JSON
        cardsJSON = []
        for card_i in target_player.hand:
            cardsJSON.append(card_i.json())

        events.append({
            'name': 'on_game_player_play_card',
            'body': {
                'card': card.id,
                'card_options': card_options,
            },
            'broadcast': True,
            'except_sid': player.sid
        })

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
            'broadcast': False,
            'receiver_sid': player.sid
        })

        return events

    def play_ups(self, player: Player, room: Room, card: Card, card_options):
        # muestrele todas las cartas de tu mano a todos los jugadores
        cards_json = player.serialize_hand()
        events = [{
            'name': 'on_game_player_play_card',
            'body': {
                'card': card.id,
                'card_options': card_options,
                'effects': {
                    'player': player.name,
                    'cards': cards_json
                }
            },
            'broadcast': True
        }]
        return events

    def play_que_quede_entre_nosotros(self, player: Player, room: Room, card: Card, card_options):
        # muestrale todas las cartas de tu mano a un jugador adjacente de tu eleccion
        # validamos el input
        target_id = card_options.get("target")
        if target_id is None:
            raise InvalidAccionException("Objetivo invalido")

        target_player: Player = Player.get(id=target_id)
        if target_player is None or target_player.status != "VIVO" or target_player.playing != room:
            raise InvalidAccionException("Objetivo Invalido")

        if not self.valid_adyacent_player(player, target_player, room):
            raise InvalidAccionException("El objetivo no esta al lado tuyo")

        card_json = player.serialize_hand()

        events = [
            {
                'name': 'on_game_player_play_card',
                'body': {
                    'card': card.id,
                    'card_options': card_options,
                    'effects': {
                        'player': player.name,
                        'cards': card_json
                    }
                },
                'broadcast': False,
                'receiver_sid': target_player.sid
            }, {
                'name': 'on_game_player_play_card',
                'body': {
                    'card': card.id,
                    'card_options': card_options,
                },
                'broadcast': True,
                'except_sid': player.sid
            }
        ]

        return events
