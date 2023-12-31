from pony.orm import db_session
from app.models import Player, Card, Room
from app.services.exceptions import *
from app.services.mixins import DBSessionMixin
import random

class PlayCardsService(DBSessionMixin):

    def play_lanzallamas(self, player : Player, room : Room, card : Card, card_options) -> list[dict]:
        """
            Elimina de la partida a un jugador adyacente
        """
        # lista de eventos que vamos a retornar
        target_id = card_options.get("target")
        target_player = Player.get(id = target_id)

        if player.is_in_quarantine():
            raise InvalidAccionException("Un jugador en cuarentena no puede jugar un lanzallamas")

        room.kill_player(target_player)

        return [
            {
                'name': 'on_game_player_play_card',
                'body': {
                    'card_id': card.id,
                    'card_name': card.name,
                    'card_options': card_options,
                    'player_name': player.name,
                },
                'broadcast': True
            },
            {
                "name": "on_game_player_death",
                "body": {
                    "player": target_player.name,
                    "killer": player.name,
                    "reason": "LANZALLAMAS"
                },
                "broadcast": True
           }
        ]

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
        return [
            {
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
            }
        ]

    def play_sospecha(self, player: Player, room: Room, card: Card, card_options) -> list[dict]:
        """
            Mira una carta aleatoria de la mano de un jugador adjacente
        """
        # validamos el input
        target_id = card_options.get("target")
        target_player: Player = Player.get(id = target_id)

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
                'except_sid': [player.sid]
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
        target_player: Player = Player.get(id=target_id)

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
                'except_sid': [player.sid]
            }
        ]

    def play_analisis(self, player: Player, room: Room, card: Card, card_options) -> list[dict]:
        """
            Mira la mano de un jugador adjacente
        """
        target_id = card_options.get("target")
        target_player: Player = Player.get(id=target_id)

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
                'except_sid': [player.sid]
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
        target_player: Player = Player.get(id=target_id)

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
        target_player: Player = Player.get(id=target_id)

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

        target_id = card_options.get("target", None)

        assert target_id is not None

        target_player: Player = Player.get(id=target_id)

        assert target_player is not None

        assert target_player.is_alive()

        # seteamos la maquina de estados para que comience el intercambio
        from app.services.games import GamesService
        gs = GamesService(self.db)
        gs.begin_exchange(
            room=room,
            player_A=player,
            player_B=target_player,
            blockable=False
        )

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

    def play_aterrador(self, player: Player, room: Room, card: Card, card_options) -> list[dict]:
        """
            Niegate a un ofrecimiento de intercambio de cartas y mira
            la carta que te has negado a recibir.
            Roba una carta ALEJATE en sustitucion de esta.
        """
        card = Card.get(id = card_options["starter_card_id"])
        starter_player = room.players.select(lambda x: x.name == card_options["starter_name"]).first()
        events = [
            {
                'name': 'on_game_defend_with_aterrador',
                'body': {
                    'card_id': card.id,
                    'card_name': card.name,
                    'card_options': card_options,
                    'player_name': player.name,
                    'effects': {
                        "card" : card.json(),
                        "name" : starter_player.name
                    }
                },
                'broadcast': False,
                'receiver_sid': player.sid
        }]
        return events

    def play_aqui_estoy_bien(self, player: Player, room: Room, card: Card, card_options) -> list[dict]:
        """
            Cancela una carta CAMBIO DE LUGAR o MAS VALE QUE CORRAS de la
            que seas objetivo. Roba una carta ALEJATE en sustitucion de esta.
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
        #lista de eventos a comunicar al front-end
        events = []
        #obtengo el siguiente jugador a defending_player
        defending_player = player
        starter_player = room.players.select(lambda x: x.id == card_options["starter_player_id"]).first()
        next_player = room.next_player_from_player(defending_player)
        #si el siguiente a la persona que se defendio es la persona que inicio el intercambio
        #buscamos a la persona que le sigue al que inicio el intercambio
        if next_player == starter_player:
            next_player = room.next_player_from_player(starter_player)

        from .games import GamesService
        gs = GamesService(self.db)
        #comenzamos el nuevo intercambio
        #TODO! la persona no se infecta!!
        print(starter_player.name + " " + next_player.name)
        events.extend(gs.begin_exchange(room, starter_player, next_player, compute_infection=False))
        return events

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

        events = []

        cards_ids = card_options.get("cards", None)
        
        assert cards_ids is not None
        
        cards = player.hand.select(lambda c : c.id in cards_ids)

        assert len(cards) == 1

        from app.services.cards import CardsService

        cs =  CardsService(self.db)


        quarantine = []
        new_cards = []
        for card in cards:
            events.extend(cs.discard_card_with_validation(player, card))
            new_card = cs.give_alejate_card(player)
            new_cards.append(new_card)


            if player.is_in_quarantine():
                quarantine.append(
                    {
                        'player_name': player.name,
                        'card': new_card.json()
                    }
                )

        # Evento privado
        events.append({
            "name": "on_game_player_steal_card",
            "body": {
                "cards": [c.json() for c in new_cards],
                "card_type": "Alejate",
                "player": player.name
            },
            "broadcast": False,
            "receiver_sid": player.sid
        })

        # Evento publico
        events.append(
            {
                "name": "on_game_player_steal_card",
                "body": {
                    "player": player.name,
                    "card_type": "ALEJATE",
                    "quarantine": None if quarantine == [] else quarantine,
                },
                "broadcast": True,
                "except_sid": [player.sid]
            }
        )

        return events

    def play_cuarentena(self, player: Player, room: Room, card: Card, card_options) -> list[dict]:
        """
            Durante dos rondas, un jugador adyacente debe robar, descartar e intercambiar
            cartas boca arriba. No puede eliminar jugadores ni cambiar de sitio
        """
        target_id = card_options.get("target")
        target_player: Player = Player.get(id=target_id)

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

        # Representamos un obstaculo entre el jugador 3 y 4 como un obstaculo en la posicion
        # 3, por ende, al obstaculo lo creamos con la posicion tal que sea la minima entre
        # las posiciones de los jugadores
        target_id = card_options.get("target")
        target_player: Player = Player.get(id=target_id)


        valid_positions = [player.position]
        if player.position == 0:
            valid_positions.append(room.qty_alive_players()-1)
        else:
            valid_positions.append(player.position-1)

        if not target_player.position in valid_positions:
            raise InvalidAccionException("El jugador no esta al lado tuyo")

        room.add_locked_door(target_player.position)

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
            }
        ]

    def play_hacha(self, player: Player, room: Room, card: Card, card_options) -> list[dict]:
        """
            Retira una carta PUERTA ATRANCADA o CUARENTENA de ti mismo
            o de un jugador adyacente.
        """
        is_quarantine = card_options.get("is_quarantine")
        if is_quarantine is None:
            raise InvalidAccionException("El campo is_quarantine es obligatorio")

        target = card_options.get("target")
        target_player: Player = Player.get(id=target)

        if is_quarantine:
            # tomamos target_id como una id de un JUGADOR
            target_player.set_quarantine(0)

        else:
            # tomamos target_id como una id de jugador que a su derecha tiene una PUERTA ATRANCADA
            if not target_player.position in room.get_obstacles_positions():
                raise InvalidAccionException("No existe un obstaculo en esa posicion")
            room.remove_locked_door(target_player.position)

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
            }
        ]

    def play_cuerdas_podridas(self, player: Player, room: Room, card: Card, card_options):
        """
            Las viejas cuerdas que usaste son faciles de romper!
            Todas las cartas CUARENTENA que haya en juego son descartadas
        """
        for player_i in room.get_quarantine_players():
            player_i.set_quarantine(0)

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

    def play_es_aqui_la_fiesta(self, player: Player, room: Room, card: Card, card_options):
        """
            Descarta todas las cartas CUARENTENA y PUERTA ATRANCADA que haya en el juego.
            A continuacion, empezando por ti, todos los jugadores cambian de sitio
            por parejas, en el sentido de las agujas del reloj.
            Si hay un numero impar de jugadores, el ultimo jugador no se mueve.
        """

        # Eliminamos todas las PUERTAS ATRANCADAS
        for obstacle_position in room.get_obstacles_positions():
            room.remove_locked_door(obstacle_position)

        # Eliminamos todas las CUARENTENAS
        for player in room.get_quarantine_players():
            player.set_quarantine(0)

        events = []

        players = room.get_alive_players()
        last_player_read = player
        while len(players) > 1:
            next_player = room.next_player_from_player(last_player_read)
            next_next_player = room.next_player_from_player(next_player)
            room.swap_players_positions(last_player_read, next_player)
            events.append(
                {
                    'name': 'on_game_swap_positions',
                    'body': {
                        'players': [last_player_read.name, next_player.name],
                    },
                    'broadcast': True,
                }
            )
            players.remove(next_player)
            players.remove(last_player_read)
            last_player_read = next_next_player

        events.append({
            'name': 'on_game_player_play_card',
            'body': {
                'card_id': card.id,
                'card_name': card.name,
                'card_options': card_options,
                'player_name': player.name
            },
            'broadcast': True
        })

        return events


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
        return self.play_seduccion(
            player=player,
            room=room,
            card=card,
            card_options=card_options
        )

    def play_olvidadizo(self, player: Player, room: Room, card: Card, card_options):
        """
            Descarta 3 cartas de tu mano y roba 3 nuevas cartas ALEJATE descartando
            cualquier carta de PANICO robada.
        """

        events = []

        cards_ids = card_options.get("cards", None)
        
        assert cards_ids is not None
        
        cards = player.hand.select(lambda c : c.id in cards_ids)

        assert len(cards) == 3

        from app.services.cards import CardsService

        cs =  CardsService(self.db)


        quarantine = []
        new_cards = []
        for card in cards:
            events.extend(cs.discard_card_with_validation(player, card))
            new_card = cs.give_alejate_card(player)
            new_cards.append(new_card)


            if player.is_in_quarantine():
                quarantine.append(
                    {
                        'player_name': player.name,
                        'card': new_card.json()
                    }
                )

        # Evento privado
        events.append({
            "name": "on_game_player_steal_card",
            "body": {
                "cards": [c.json() for c in new_cards],
                "card_type": "Alejate",
                "player": player.name
            },
            "broadcast": False,
            "receiver_sid": player.sid
        })

        # Evento publico
        events.append(
            {
                "name": "on_game_player_steal_card",
                "body": {
                    "player": player.name,
                    "card_type": "ALEJATE",
                    "quarantine": None if quarantine == [] else quarantine,
                },
                "broadcast": True,
                "except_sid": [player.sid]
            }
        )

        return events

    def play_sal_de_aqui(self, player: Player, room: Room, card: Card, card_options):
        """
            Cambiate de sitio con cualquier jugador de tu eleccion que no este en cuarentena
        """
        return self.play_mas_vale_que_corras(
            player=player,
            room=room,
            card=card,
            card_options=card_options
        )

    def play_uno_dos(self, player: Player, room: Room, card: Card, card_options):
        """
            cambiate de sitio con el tercer jugador que tengas a tu izquierda o a tu derecha (tu eleccion),
            ignorando cualquier carta PUERTA ATRANCADA que haya en juego.
            Si tu o ese jugador estais en CUARENTENA, el cambio no se realiza.
            SI EL OBJETIVO ESTA EN CUARENTENA NO TIENE EFECTO PERO SI SE PUEDE JUGAR
        """

        events = []
        target_id = card_options.get("target")
        target_player = Player.get(id = target_id)

        assert target_player is not None

        if not target_player.is_in_quarantine():
            room.swap_players_positions(player, target_player)
            events.append(
                {
                    'name': 'on_game_swap_positions',
                    'body': {
                        'players': [player.name, target_player.name],
                    },
                    'broadcast': True,
                }
            )
        events.append({
            'name': 'on_game_player_play_card',
            'body': {
                'card_id': card.id,
                'card_name': card.name,
                'card_options': card_options,
                'player_name': player.name
            },
            'broadcast': True
        })

        return events

    def play_tres_cuatro(self, player: Player, room: Room, card: Card, card_options):
        """
            Todas las cartas PURTA ATRANCADA que haya en juego son descartadas
        """
        for position in room.get_obstacles_positions():
            room.remove_locked_door(position)

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
            }
        ]

"""
P0 
    Ataque:
        [x] Vigila tus espaldas
        [x] Cambio de lugar
        [x] Más vale que corras
        [x] Seducción
        [x] AnálisisP
        [x] Sospecha
        [x] Whisky
    Defensa:
        [x] Aterrador
        [x] Aquí estoy bien
        [x] No, gracias
        [x] Fallaste
        [x] Nada de Barbacoas
P1
    Pánico:
        [x] Que quede entre nosotros
        [ ] Revelaciones
        [x] Cita a ciegas
        [x] Oops!
    Otras cartas
        [x] Cuarentena
        [x] Puerta Atrancada
        [x] Hacha
P2 
    Pánico:
        [x] Cuerdas podridas
        [x] Esta es la fiesta?
        [x] Oops!
        [ ] Vuelta y vuelta
        [x] No podemos ser amigos
        [x] Olvidadizo
        [x] Carta 1, 2 ... (movimiento)
        [x] Carta 3, 4 ... (movimiento)
        [x] Sal de aqui
"""
