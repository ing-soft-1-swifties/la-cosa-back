from pony.orm import db_session
from app.models import Player, Card
from app.services.exceptions import *
from app.services.mixins import DBSessionMixin
from app.services.games import GamesService

class CardsService(DBSessionMixin):
    pass
    @db_session
    def get_card_json(self, card_id : int):
        gs = GamesService(self.db)
        card = Card.get(id = card_id)
        if card is None:
            raise InvalidCardException()
        return gs.card_to_JSON(card)

    