from pony.orm import db_session
from app.models import Player, Card, Room
from app.services.exceptions import *
from app.services.mixins import DBSessionMixin
import random

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
        return [{
            'name': 'on_game_player_play_card',
            'body': {
                'card_id': card.id,
                'card_name': card.name,
                'card_options': card_options,
                'player_name': player.name,
                'effects' : {
                    'player': player.name, 
                    'cards': player.serialize_hand(exclude=[card.id])
                }
            },
            'broadcast': True
        }]

    def play_sospecha(self, player: Player, room: Room, card: Card, card_options):
        # mira una carta aleatoria de la mano de un jugador adjacente

        # validamos el input
        target_id = card_options.get("target")
        if target_id is None:
            raise InvalidAccionException("Objetivo invalido")
        
        target_player: Player = Player.get(id = target_id)
        if target_player is None or target_player.status != "VIVO" or target_player.playing != room :
            raise InvalidAccionException("Objetivo Invalido")

        if not self.valid_adyacent_player(player, target_player, room):
            raise InvalidAccionException("El objetivo no esta al lado tuyo")
        return [
            {
                'name': 'on_game_player_play_card',
                'body': {
                    'card_id': card.id,
                    'card_name': card.name,
                    'card_options': card_options,
                    'player_name': player.name
                },
                'broadcast': True,
                'except_sid': player.sid
            },
            {
                'name': 'on_game_player_play_card',
                'body': {
                    'card_id': card.id,
                    'card_name': card.name,
                    'card_options': card_options,
                    'player_name': player.name,
                    'effects' : {
                        'player': target_player.name,
                        'cards': [random.choice(target_player.serialize_hand())]
                    }
                },
                'broadcast': False,
                'receiver_sid': player.sid
            }
        ]

    def play_ups(self, player: Player, room: Room, card: Card, card_options):
        # muestrele todas las cartas de tu mano a todos los jugadores
        return [{
            'name': 'on_game_player_play_card',
            'body': {
                'card_id': card.id,
                'card_name': card.name,
                'card_options': card_options,
                'player_name': player.name,
                'effects': {
                    'player': player.name,
                    'cards': player.serialize_hand(exclude=[card.id])
                }
            },
            'broadcast': True
        }]

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

        return [
            {   # este se lo mandamos solo al target
                'name': 'on_game_player_play_card',
                'body': {
                    'card_id': card.id,
                    'card_name': card.name,
                    'card_options': card_options,
                    'player_name': player.name,
                    'effects': {
                        'player': player.name,
                        'cards': player.serialize_hand(exclude=[card.id])
                    }
                },
                'broadcast': False,
                'receiver_sid': target_player.sid
            },
            {   # este se lo mandamos solo a todos
                'name': 'on_game_player_play_card',
                'body': {
                    'card_id': card.id,
                    'card_name': card.name,
                    'card_options': card_options,
                    'player_name': player.name,
                },
                'broadcast': True,
                'except_sid': player.sid
            }
        ]

    def play_analisis(self, player: Player, room: Room, card: Card, card_options):
        # mira la mano de un jugador adjacente
        target_id = card_options.get("target")
        if target_id is None:
            raise InvalidAccionException("Objetivo invalido")

        target_player: Player = Player.get(id=target_id)
        if target_player is None or target_player.status != "VIVO" or target_player.playing != room:
            raise InvalidAccionException("Objetivo Invalido")

        if not self.valid_adyacent_player(player, target_player, room):
            raise InvalidAccionException("El objetivo no esta al lado tuyo")

        return [
            {
                'name': 'on_game_player_play_card',
                'body': {
                    'card_id': card.id,
                    'card_name': card.name,
                    'card_options': card_options,
                    'player_name': player.name
                },
                'broadcast': True,
                'except_sid': player.sid
            },
            {
                'name': 'on_game_player_play_card',
                'body': {
                    'card_id': card.id,
                    'card_name': card.name,
                    'card_options': card_options,
                    'player_name': player.name,
                    'effects': {
                        'player': target_player.name,
                        'cards': target_player.serialize_hand()
                    }
                },
                'broadcast': False,
                'receiver_sid': player.sid
            }
        ]

    def play_cambio_de_lugar(self, player: Player, room: Room, card: Card, card_options):
        # cambiate de sitio con un jugador adyacente que no este en cuarentena o tras una puerta atrancada
        # validamos el input
        target_id = card_options.get("target")
        if target_id is None:
            raise InvalidAccionException("Objetivo invalido")

        target_player: Player = Player.get(id=target_id)
        if target_player is None or target_player.status != "VIVO" or target_player.playing != room:
            raise InvalidAccionException("Objetivo Invalido")

        if not self.valid_adyacent_player(player, target_player, room):
            raise InvalidAccionException("El objetivo no esta al lado tuyo")

        # cambia las posiciones de los jugadores
        room.swap_players_positions(player, target_player)

        return [
            {
                'name': 'on_game_swap_positions',
                'body': {
                    'players': [player.name, target_player.name],
                },
                'broadcast': True,
            },
            {
                'name': 'on_game_player_play_card',
                'body': {
                    'card_id': card.id,
                    'card_name': card.name,
                    'card_options': card_options,
                    'player_name': player.name
                },
                'broadcast': True
            }
        ]

"""
    TODO:
    - P0:
        - Ataque:
            [x] Análisis
            [x] Sospecha
            [x] Whisky
            [ ] Cambio de lugar
            [ ] Vigila tus espaldas
            [ ] Más vale que corras
            [ ] Seducción
        - Defensa:
            [ ] Aterrador
            [ ] Aquí estoy bien
            [ ] No, gracias
            [ ] Fallaste
            [ ] Nada de Barbacoas
    - P1:
        - Panico:
            [ ] Solo entre nosotros
            [ ] Revelaciones
            [ ] Cita a ciegas
            [x] Oops!
        [ ] Cuarentena
        [ ] Puerta Atrancada
        [ ] Hacha
"""