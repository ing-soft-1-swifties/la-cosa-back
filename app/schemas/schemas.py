from pydantic import BaseModel
from typing import List

class ObstacleSchema(BaseModel):
    duration: int
    position: int
    room_id: int

    class Config:
        from_attributes = True

class CardSchema(BaseModel):
    name: str
    description: str = None
    type: int
    sub_type: int = None
    roomsA: List[int] = []
    roomsD: List[int] = []

    class Config:
        from_attributes = True

class PlayerSchema(BaseModel):
    name: str
    position: int
    rol: int
    status: int
    hosting: int = None
    playing: int = None

    class Config:
        from_attributes = True

class RoomSchema(BaseModel):
    name: str
    min_players: int
    max_players: int = None
    is_private: bool
    password: str = None
    status: int
    turn: int = None
    direction: bool = None
    host: int
    players: List[int] = []
    available_cards: List[int] = []
    discarted_cards: List[int] = []
    obstacles: List[int] = []

    class Config:
        from_attributes = True