
class DuplicatePlayerNameException(Exception):
    """
    Excepción lanzada cuando se intenta registrar un jugador con un nombre que ya está en uso en una sala.
    """
    pass

class InvalidRoomException(Exception):
    """
    Excepción lanzada cuando se intenta acceder a una sala que no existe o no es válida.
    """
    pass


