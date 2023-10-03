from ast import List
from pony.orm import count, db_session, Set
from app.models import Player, Room, Card
#from app.services.exceptions import DuplicatePlayerNameException, InvalidRoomException
from app.services.exceptions import *
from app.services.mixins import DBSessionMixin
#from app.services.exceptions import DuplicatePlayerNameException, InvalidRoomException
import random

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
    def personal_game_state(self, player : Player):
        #devuelve un diccionario que representa el estado del juego desde la vision de un jugador
        player_in_game_state = self.game_state(player.playing)
        player_in_game_state.update()
        return player_in_game_state
        #falta un poco de informacion, completar

    def play_card(self, player:Player, card:Card):
        #se juega una carta, notar que van a ocurrir eventos (ej:alguien muere), debemos llevar registro
        #para luego notificar al frontend (una propuesta es devolve una lista de eventos con sus especificaciones)
        #a todos los afectados por el evento se les reenvia el game_state
        pass
    
    @db_session
    def get_card(self, player:Player, room:Room):
        # se entrega una carta del mazo de disponibles al usuario
        # se borra la carta de room.available, se asigna la carta al usuario y se retorna el objeto carta

        card_to_deal = room.available_cards.random(1)
        player.hand.add(card_to_deal)
        room.available_cards.remove(card_to_deal)


        return self.card_to_JSON(card_to_deal) 

    def discard_card(self, player:Player, room:Room):
        #hay que verificar que pueda, si es asi se agrega al mazo de descartes y se quita del jugador
        pass
        return 


    @db_session
    def initialize_deck(self, room : Room):
        """
        Se cargan las cartas que se van a usar en la partida dependiendo de la cantidad de players.
        """
        player_count = count(room.players)

        card = list(Card.select(lambda c : c.deck <= player_count))
        
        room.available_cards = card.copy()
        
        return 


    @db_session
    def initial_deal(self, room : Room):
        """
        Repartir las cartas iniciales.
        """
        # cantidad de cartas a repartir
        qty_cards_to_deal = count(room.players)*4

        # obtenemos todas todas las cartas menos la cosa
        cards_to_deal = room.available_cards.select(lambda c : c.name is not 'La cosa' and c.type is 'ACCION')

        # obtiene de forma random qty_cards_to_deal-1 cartas
        cards_to_deal = random.sample(cards_to_deal, qty_cards_to_deal-1)

        # agrega a las cartas a repartir la carta LA COSA
        cards_to_deal.append(room.available_cards.get(name='La cosa'))

        random.shuffle(cards_to_deal)


        # eliminamos todas las cartas a repartir del mazo de cartas disponibles
        for card in list(cards_to_deal):
            room.available_cards.remove(card)

        # room.available_cards.remove(cards_to_deal)
        # repartimos
        players_dealed = 0
        for player in list(room.players):
            for card_index in range(4):
                player.hand.add(cards_to_deal[players_dealed*4 + card_index])
            
            players_dealed += 1

        return
        
        
    

        
           