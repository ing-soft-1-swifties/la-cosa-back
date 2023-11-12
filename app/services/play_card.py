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

    def play_lanzallamas(self, player : Player, room : Room, card : Card, card_options) -> list[dict]:
        """
            Elimina de la partida a un jugador adyacente
        """
        #lista de eventos que vamos a retornar
        events = []
        target_id = card_options.get("target")
        if target_id is None:
            raise InvalidAccionException("Objetivo invalido")
        target_player = Player.get(id = target_id)
        if target_player is None or target_player.status != "VIVO":
            raise InvalidAccionException("Objetivo Invalido")

        events.append({
            'name': 'on_game_player_play_card',
            'body': {
                'card_id': card.id,
                'card_name': card.name,
                'card_options': card_options,
                'player_name': player.name,
            },
            'broadcast': True
        })

        room.kill_player(target_player)

        events.append({
            "name": "on_game_player_death",
            "body": {
                "player": target_player.name,
                "reason": "LANZALLAMAS",
                "killer": room.get_current_player()
            },
            "broadcast": True
        })

        return events

    def play_nada_de_barbacoas(self, player: Player, room: Room, card: Card, card_options):
        """
            Cancela una carta LANZALLAMAS que te tenga como objetivo. Roba
            una carta ALEJATE en sustitucion de esta
        """
        return [
            {
                "name": "on_game_player_play_defense_card",
                "body": {
                    "player_name": player.name,
                    "card_name": card.name,
                    "card_options": card_options,
                    "card_id": card.id
                    },
                "broadcast": True
            }
        ]

    def play_whisky(self, player: Player, room: Room, card: Card, card_options) -> list[dict]:
        """
            Muestra todas tus cartas a todos los jugadores.
            Solo puedes jugar esta carta sobre ti mismo.
        """
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

    def play_sospecha(self, player: Player, room: Room, card: Card, card_options) -> list[dict]:
        """
            Mira una carta aleatoria de la mano de un jugador adjacente
        """
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

    def play_ups(self, player: Player, room: Room, card: Card, card_options) -> list[dict]:
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

    def play_que_quede_entre_nosotros(self, player: Player, room: Room, card: Card, card_options) -> list[dict]:
        """
            Muestrale todas las cartas de tu mano a un jugador
            adjacente de tu eleccion
        """
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

    def play_analisis(self, player: Player, room: Room, card: Card, card_options) -> list[dict]:
        """
            Mira la mano de un jugador adjacente
        """
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

    def play_cambio_de_lugar(self, player: Player, room: Room, card: Card, card_options) -> list[dict]:
        """
            Cambiate de sitio con un jugador adyacente que no este en cuarentena o tras una puerta atrancada
        """

        # validamos el input
        target_id = card_options.get("target")
        if target_id is None:
            raise InvalidAccionException("Objetivo invalido")

        target_player: Player = Player.get(id=target_id)
        if target_player is None or target_player.status != "VIVO" or target_player.playing != room:
            raise InvalidAccionException("Objetivo Invalido")

        if not self.valid_adyacent_player(player, target_player, room):
            raise InvalidAccionException("El objetivo no esta al lado tuyo")

        if target_player.is_in_quarantine():
            raise InvalidAccionException("El objetivo esta en cuarentena")

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

    def play_vigila_tus_espaldas(self, player: Player, room: Room, card: Card, card_options) -> list[dict]:
        """
            Invierte el orden de juego.
            Ahora, tanto el orden de turnos como los intercambios de cartas van en elsentido contrario
        """
        room.change_direction()

        return [
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

    def play_mas_vale_que_corras(self, player: Player, room: Room, card: Card, card_options) -> list[dict]:
        """
            Cambiate de sitio con cualquier jugador de tu eleccion que no este en cuarentena,
            ignorando cualquier puerta atrancada
        """
        target_id = card_options.get("target")
        if target_id is None:
            raise InvalidAccionException("Objetivo invalido")

        target_player: Player = Player.get(id=target_id)
        if target_player is None or target_player.status != "VIVO" or target_player.playing != room:
            raise InvalidAccionException("Objetivo Invalido")

        if target_player.is_in_quarantine():
            raise InvalidAccionException("El objetivo esta en cuarentena")

        # cambiamos las posiciones de los jugadores
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

    def play_seduccion(self, player: Player, room: Room, card: Card, card_options) -> list[dict]:
        """
            Intercambia una carta con cualquier jugador de tu eleccion
            que no este en cuarentena.
            Tu turno termina.
        """
        return []

    def play_aterrador(self, player: Player, room: Room, card: Card, card_options) -> list[dict]:
        """
            Niegate a un ofrecimiento de intercambio de cartas y mira
            la carta que te has negado a recibir.
            Roba una carta ALEJATE en sustitucion de esta.
        """
        return []

    def play_aqui_estoy_bien(self, player: Player, room: Room, card: Card, card_options) -> list[dict]:
        """
            Cancela una carta CAMBIO DE LUGAR o MAS VALE QUE CORRAS de la
            que seas objetivo. Roba una carta ALEJATE en sustitucion de esta.
        """
        return []

    def play_no_gracias(self, player: Player, room: Room, card: Card, card_options) -> list[dict]:
        """
            Niegate a un ofrecimiento de intercambio de cartas. Roba
            una carta ALEJATE en sustitucion de esta.
        """
        return []

    def play_fallaste(self, player: Player, room: Room, card: Card, card_options) -> list[dict]:
        """
            El siguiente jugador despues de ti realiza el intercambio de
            cartas en lugar de hacerlo tu. No queda infectado si recibe una carta
            INFECTADO. Roba una carta ALEJATE en sustitucion de esta
        """
        return []

    def play_revelaciones(self, player: Player, room: Room, card: Card, card_options) -> list[dict]:
        """
            empezando por ti y siguiendo en el orden de juego, cada jugador
            elige si revela o no su mano.
            La ronda de revelaciones termina cuando un jugador muestre una carta
            INFECTADO, sin que tenga que revelar el resto de su mano.
        """
        return []

    def play_cita_a_ciegas(self, player: Player, room: Room, card: Card, card_options) -> list[dict]:
        """
            Intercambia una carta de tu mano con la primera carta del mazo,
            descartando cualquier carta de PANICO robada.
            Tu turno termina
        """
        return []

    def play_cuarentena(self, player: Player, room: Room, card: Card, card_options) -> list[dict]:
        """
            Durante dos rondas, un jugador adyacente debe robar, descartar e intercambiar
            cartas boca arriba. No puede eliminar jugadores ni cambiar de sitio
        """
        target_id = card_options.get("target")
        if target_id is None:
            raise InvalidAccionException("Objetivo invalido")

        target_player: Player = Player.get(id=target_id)
        if target_player is None or target_player.status != "VIVO" or target_player.playing != room:
            raise InvalidAccionException("Objetivo Invalido")

        if not self.valid_adyacent_player(player, target_player, room):
            raise InvalidAccionException("El objetivo no esta al lado tuyo")

        target_player.set_quarantine(2)

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
            },
        ]

    def play_puerta_atrancada(self, player: Player, room: Room, card: Card, card_options) -> list[dict]:
        """
            Coloca esta carta entre un jugador adyacente y tu. No
            se permiten acciones entre este jugdor y tu.
        """
        return []

    def play_hacha(self, player: Player, room: Room, card: Card, card_options) -> list[dict]:
        """
            Retira una carta PUERTA ATRANCADA o CUARENTENA de ti mismo
            o de un jugador adyacente
        """
        return []

    def play_cuerdas_podridas(self, player: Player, room: Room, card: Card, card_options):
        """
            Las viejas cuerdas que usaste son faciles de romper!
            Todas las cartas CUARENTENA que haya en juego son descartadas
        """
        return []

    def play_es_aqui_la_fiesta(self, player: Player, room: Room, card: Card, card_options):
        """
            Descarta todas las cartas CUARENTENA y PUERTA ATRANCADA que haya en el juego.
            A continuacion, empezando por ti, todos los jugadores cambian de sitio
            por parejas, en el sentido pde las agujas del reloj.
            Si hay un numero impar de jugadores, el ultimo jugador no se mueve.
        """
        return []

    def play_vuelta_y_vuelta(self, player: Player, room: Room, card: Card, card_options):
        """
            Tods los jugadores deben darle una carta al siguiente jugador que tengan
            al lado, simultaneamente y en el sentido de juego actual, ignorando cualquier carta
            PUERTA ATRANCADA y CUARENTENA que haya en el juego.
            No puedes usar ninguna carta para evitar este intercambio.
            LA COSA puede infectar a otro jugador de esta forma.
            Tu turno termina.
        """
        return []

    def play_no_podemos_ser_amigos(self, player: Player, room: Room, card: Card, card_options):
        """
            Intercambia una carta con cualquier jugador de tu eleccion que no este en cuarentena
        """
        return []

    def play_olvidadizo(self, player: Player, room: Room, card: Card, card_options):
        """
            Descarta 3 cartas de tu mano y roba 3 nuevas cartas ALEJATE descartando
            cualquier carta de PANICO robada.
        """
        return []

    def play_sal_de_aqui(self, player: Player, room: Room, card: Card, card_options):
        """
            Cambiate de sitio con cualquier jugador de tu eleccion que no este en cuarentena
        """
        return []

    def play_uno_dos(self, player: Player, room: Room, card: Card, card_options):
        """
            cambiate de sitio con el tercer jugador que tengas a tu izquierda o a tu derecha (tu eleccion),
            ignorando cualquier carta PUERTA ATRANCADA que haya en juego.
            Si tu o ese jugador estais en CUARENTENA, el cambio no se realiza.

        """
        return []

    def play_tres_cuatro(self, player: Player, room: Room, card: Card, card_options):
        """
            Todas las cartas PURTA ATRANCADA que haya en juego son descartadas
        """
        return []

"""
P0 
    Ataque:
        [x] Vigila tus espaldas
        [x] Cambio de lugar
        [x] Más vale que corras
        [ ] Seducción
        [x] Análisis
        [x] Sospecha
        [x] Whisky
    Defensa:
        [ ] Aterrador
        [ ] Aquí estoy bien
        [ ] No, gracias
        [ ] Fallaste
        [x] Nada de Barbacoas
P1
    Pánico:
        [ ] Solo entre nosotros
        [ ] Revelaciones
        [ ] Cita a ciegas
        [x] Oops!
    Otras cartas
        [ ] Cuarentena ----------------
        [ ] Puerta Atrancada
        [ ] Hacha
P2 
    Pánico:
        [ ] Cuerdas podridas ----------------
        [ ] Esta es la fiesta? -----------------
        [x] Oops!
        [ ] Ronda y ronda
        [ ] Podemos ser Amigos?
        [ ] Olvidadizo
        [ ] Carta 1, 2 ... (movimiento) ------------------
        [ ] Carta 3, 4 ... (movimiento)
"""