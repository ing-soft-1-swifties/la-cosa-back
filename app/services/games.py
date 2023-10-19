from pony.orm import db_session
from app.models import Player, Room, Card
from app.services.exceptions import *
from app.services.mixins import DBSessionMixin
from app.services.players import PlayersService
from app.services.rooms import RoomsService
from app.services.cards import CardsService
from app.logger import rootlog

class GamesService(DBSessionMixin):


    @db_session
    def game_state(self, room : Room):
        # TODO: exporta en json el estado de la partida, para enviar al frontend
        def player_state(player):
            return{
                "name" : player.name,
                "id" : player.id,
                "status" : player.status,
                "position" : player.position,
                "in_quarantine" : player.in_quarantine
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
    def get_personal_game_status_by_sid(self, sent_sid : str):
        player = Player.get(sid = sent_sid)
        #devuelve un diccionario que representa el estado del juego desde la vision de un jugador
        player_in_game_state = self.game_state(player.playing)
        #agreguemos que cartas tiene esta persona y su estado
        player_in_game_state.update({"playerData": player.json()})
        return player_in_game_state

    @db_session
    def play_card(self, sent_sid : str, payload):
        cs = CardsService(self.db)
        events = []     #lista de eventos a informar a los jugadores
        player = Player.get(sid = sent_sid)
        if player is None:
            raise InvalidSidException()
        sent_card_id = payload.get("card")
        card_options = payload.get("card_options")
        if sent_card_id is None or card_options is None:
            raise InvalidDataException()
        card = Card.get(id = sent_card_id) 
        if card is None:
            raise InvalidCidException()
        unplayable_cards = ["La cosa", "Infectado"]
        if card.name in unplayable_cards:
            raise InvalidAccionException(f"No se puede jugar {card.name}")
        room = player.playing
        ps = PlayersService(self.db)
        if ps.has_card(player, card) == False:
            raise InvalidCardException()
        if room.machine_state != "PLAYING":
            rootlog.exception("no correspondia jugar una carta")
            raise InvalidAccionException("No corresponde jugar")
        if room.machine_state_options["id"] != player.id:
            rootlog.exception(f"no era el turno de la persona que intento jugar {room.machine_state_options['id']} {player.id}")
            raise InvalidAccionException("No es tu turno")

        #caso: la carta jugada es lanzallamas ¡ruido de asadoo!
        events = []
        if card.name == "Lanzallamas":
            events.extend(cs.play_lanzallamas(player, room, card, card_options))
        
        rs = RoomsService(self.db)
        rs.recalculate_positions(sent_sid)
        #deberiamos ver si termino el juego
        #aca deberiamos llamar al servicio de cartas descartar cuando este listo
        #cs.discard_card(player, card)
        player.hand.remove(card)
        room.discarted_cards.add(card)
        return events

    @db_session
    def discard_card(self, sent_sid : str, payload):
        cs = CardsService(self.db)
        return cs.discard_card(sent_sid, payload)

    @db_session
    def end_game_condition(self, sent_sid : str) -> str:
        """Chequea si se finalizo la partida.

        Args: room (Room): current valid room

        Returns: str: {'GAME_IN_PROGRESS', 'LA_COSA_WON', 'HUMANS_WON'}
        """
        player = Player.get(sid = sent_sid)
        info = {}
        # inputs validos
        if player is None:
            raise InvalidSidException()
        room: Room = player.playing
        
        roles = []
        for player in room.players:
            roles.append((player.name, player.rol))
        
        ret = 'GAME_IN_PROGRESS'
        # Si queda solo un sobreviviente     
        if len(room.players.select(lambda p: p.status != 'MUERTO')) == 1:
            survivor: Player = list(room.players.select(lambda p: p.status != 'MUERTO'))[0] # type: ignore
            # Chequeo si es la cosa
            if survivor.rol == 'LA_COSA':
                ret = 'LA_COSA_WON'
                info = {
                    "winner_team": "LA_COSA",
                    "winner": list(map(lambda x: x.name, list(room.players.select(rol='LA_COSA')))),
                    "roles":roles
                }                
            else: 
                ret = 'HUMANS_WON'
                info = {
                    "winner_team": "HUMANOS",
                    "winner": list(map(lambda x: x.name, list(room.players.select(rol='HUMANO')))),
                    "roles":roles
                }
        
        # Chequeo el estado de la cosa
        la_cosa: Player = list(room.players.select(lambda p: p.rol == 'LA_COSA'))[0] # type: ignore
        # la_cosa: Player = room.players.get(rol = 'LA_COSA') # type: ignore
        
        if la_cosa.status == 'MUERTO':
            ret = 'HUMANS_WON'
            info = {
                "winner_team": "HUMANOS",
                "winner": list(map(lambda x: x.name, list(room.players.select(rol='HUMANO')))),
                "roles": roles
            }
    
        qty_alive_players = len(room.players.select(lambda p : p.status != 'MUERTO'))
        qty_alive_non_human_players = len(room.players.select(lambda p : p.status != 'MUERTO' and p.rol != 'HUMANO'))
        if qty_alive_non_human_players == qty_alive_players: 
            ret='LA_COSA_WON'
            info = {"winner_team":"LA_COSA",
                        "winner": list(map(lambda x: x.name, list(room.players.select(rol='LA_COSA')))),
                        "roles":roles}   
                
        return ret, info
    
    @db_session
    def exchange_card_manager(self, sent_sid : str, payload):
        player = Player.get(sid = sent_sid)
        if player is None:
            raise InvalidSidException()
        sent_card_id = payload.get("card")
        on_defense = payload.get("on_defense")
        if sent_card_id is None or on_defense is None:
            raise InvalidDataException()
        card = Card.get(id = sent_card_id)
        if card is None:
            raise InvalidCidException()
        unchangable_cards = ["La cosa"]
        if card.name in unchangable_cards:
            raise InvalidAccionException(f"No se puede intercambiar {card.name}")
        room = player.playing
        ps = PlayersService(self.db)
        if ps.has_card(player, card) == False:
            raise InvalidCardException()
        #maquina de estados
        if room.machine_state != "EXCHANGING":
            rootlog.exception("no correspondia intercambiar una carta")
            raise InvalidAccionException("No corresponde intercambiar")

        print(room.machine_state_options["ids"])
        exchanging_players = room.machine_state_options.get("ids")
        if exchanging_players is None:
            rootlog.exception("deberia existir campo ids en estado intercambio")
            raise Exception()
        if room.machine_state_options["id"] not in room.machine_state_options["ids"]:
            rootlog.exception(f"no corresponde que la persona intercambie{room.machine_state_options['id']} {player.id}")
            raise InvalidAccionException("No corresponde iniciar un intercambio")
        first_player = exchanging_players[0] == player.id
        if first_player:
            if on_defense:
                raise InvalidAccionException("No te podes defender si sos el que inicia el intercambio")
        if room.machine_state_options["state"] == "STARTING":
            room.machine_state = "EXCHANGING"
            room.machine_state_options = {"id":player.id, 
                                         "stage":"FINISHING",
                                         "card_id" : card.id,
                                         "player_id":player.id,
                                         "on_defense": on_defense if not first_player else False}
            return False    #temporal, indicamos que no vaya al siguiente turno
        elif room.machine_state_options["state"] == "FINISHING" and player.id != room.machine_state_options["player_id"]:
            first_player_id = exchanging_players[0]
            first_player = Player.get(id = first_player_id)
            second_player_id = exchanging_players[1]
            second_player = Player.get(id = second_player_id)
            if first_player is None or second_player is None:
                InvalidDataException()
            if first_player.playing != second_player.playing:
                rootlog.exception("los jugadores no corresponden a una misma partida")
                InvalidDataException()
            is_first_player = exchanging_players[0] == player.id
            first_card = card if is_first_player else Card.get(id = room.machine_state_options["card_id"])
            second_card = card if not is_first_player else Card.get(id = room.machine_state_options["card_id"])
            from .cards import CardsService
            cs = CardsService(self.db)
            events = cs.exchange_cards(room, first_player, second_player, first_card, second_card)
            print(f"intercambio entre {first_player.name} y {second_player.name} finalizado exitosamente")
            return events
        else:
            raise InvalidAccionException("No corresponde iniciar un intercambio") 
        
        