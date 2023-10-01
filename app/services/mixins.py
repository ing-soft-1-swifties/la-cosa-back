from pony.orm import Database


# Mixin para usar en servicios
class DBSessionMixin:
    """
    Mixin providing a database session.
    """
    def __init__(self, db: Database):
        self.db = db
