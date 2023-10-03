from ast import List
from pony.orm import count, db_session, Set
from app.models import Player, Room, Card
from app.services.exceptions import *
from app.services.mixins import DBSessionMixin

class GamesService(DBSessionMixin):

    def card_to_JSON(self, card: Card):
        return {
            'id': card.id,
            'name': card.name,
            'description': card.description,
            'deck': card.deck,
            'type': card.type,
            'sub_type': card.sub_type
        }

    @db_session
    def game_state(self, room : Room):
        # TODO: exporta en json el estado de la partida, para enviar al frontend
        def player_state(player):
            return{
                "name" : player.name,
                "status" : player.status,
                "position" : player.position,
            }
        game_state = {
            "config" : {
                "id" : room.id,
                "name" : room.name,
                "host" : room.get_host().name,
                "minPlayers" : room.min_players,
                "maxPlayers" : room.max_players
            },
            "status" : room.status,
            "turn" : room.turn,
            "players" : [player_state(player) for player in room.players]
        }
        return game_state
    
    @db_session
    def get_game_status_by_sid(self, sent_sid : str):
        return self.game_state(Player.get(sid = sent_sid).playing)

    @db_session
    def get_game_status_by_rid(self, sent_rid : int):
        return self.game_state(Room.get(id = sent_rid))

    @db_session
    def personal_game_state_by_sid(self, sent_sid : str):
        player = Player.get(sid = sent_sid)
        #devuelve un diccionario que representa el estado del juego desde la vision de un jugador
        player_in_game_state = self.game_state(player.playing)
        #agreguemos que cartas tiene esta persona y su estado
        player_in_game_state.update(
            {"personalInformation": {
                "rol" : player.rol,
                "cards" : [self.card_to_JSON(card) for card in player.hand]
            }}
        )
        return player_in_game_state

    def play_card(self, player:Player, card:Card):
        #se juega una carta, notar que van a ocurrir eventos (ej:alguien muere), debemos llevar registro
        #para luego notificar al frontend (una propuesta es devolve una lista de eventos con sus especificaciones)
        #a todos los afectados por el evento se les reenvia el game_state
        room = player.playing
        self.next_turn(room)
        #el metodo anterior retorna la carta que recibio alguna la siguiente persona
        #falta implementar la muestra de eventos
        pass
        
    @db_session
    def next_turn(self, room:Room):
        if room.turn is None:
            print("partida inicializada incorrectamente, turno no pre-seteado")
            raise Exception
        room.turn = (room.turn + 1) % (len(room.players.select(lambda player : player.status != 1)))    #cantidad de jugadores que siguen jugando
        expected_player = Player.get(position = room.turn)
        if expected_player is None:
            print(f"el jugador con turno {room.turn} no esta en la partida")
            raise Exception
        return self.give_card(expected_player, room)
        
    @db_session
    def give_card(self, player:Player, room:Room):
        # se entrega una carta del mazo de disponibles al usuario
        # se borra la carta de room.available, se asigna la carta al usuario y se retorna el objeto carta
        if len(room.available_cards) > 0:
            card_to_deal = room.available_cards.random(1)
        else:
            #habria que mezclar el mazo de descartes y que sea el nuevo mazo de disponibles
            raise Exception
            random.shuffle(room.discarted_cards)
            room.available_cards = room.discarted_cards
            rooom.discard_card.clear()
            #lo de arriba es una aproximacion, falta ver que funcione
        player.hand.add(card_to_deal)
        room.available_cards.remove(card_to_deal)
        return self.card_to_JSON(card_to_deal) 

    @db_session
    def discard_card(self, player:Player, room:Room):
        #hay que verificar que pueda, si es asi se agrega al mazo de descartes y se quita del jugador
        pass
        return 