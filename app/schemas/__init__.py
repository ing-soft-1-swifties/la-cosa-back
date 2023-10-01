from pydantic import BaseModel, field_validator, model_validator
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

class RoomJoiningInfo(BaseModel):
    name: str
    room_id: int

class ConnectionCredentials(BaseModel):
    token: str

class NewRoomSchema(BaseModel):
    room_name: str
    host_name: str
    min_players: int
    max_players: int

    @field_validator("min_players", "max_players", mode="after")
    @classmethod
    def check_range(cls, v: int):
        if v < 4 or v > 12:
            raise ValueError("should be between 4 and 12, including these bounds.")

    @model_validator(mode="after")
    def check_player_range(self) -> 'NewRoomSchema':

        # no deberian poder ser None, pero al iniciar el server da error si no checkeamos esto :)
        if self.max_players is not None and self.min_players is not None and self.max_players < self.min_players:
            raise ValueError("`min_players` should be lesser or equal than `max_players`")
        return self


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
