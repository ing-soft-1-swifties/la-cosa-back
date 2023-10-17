from pony.orm import db_session
from app.models import Player, Card
from app.services.exceptions import *
from app.services.mixins import DBSessionMixin

class CardsService(DBSessionMixin):
    pass
    # @db_session
    # def get_json(self, card_id : int):
    #     Card.get(id = card_id)
    
    # @db_session
    # def disconnect_player(self, actual_sid : str):

    # @db_session
    # def is_host(self, actual_sid : str):

    # @db_session
    # def has_card(self, player : Player, card : Card):

    # def get_name(self, sent_sid : str):