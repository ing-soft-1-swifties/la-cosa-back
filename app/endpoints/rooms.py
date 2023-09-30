from fastapi import APIRouter
from app.models import Room
from app.schemas import RoomSchema

from pony.orm import db_session

from database.database import db


router = APIRouter()




@router.post("/create")
def crear_partida(raw_room: RoomSchema):
    with db_session:
        room = Room(raw_room.model_dump())
        db.commit()

    return {"guardado": f"id: {room.id}"}


@router.get("/all")
def listar_partida():
    with db_session:
        raw_room = Room.select()
        rooms = [RoomSchema.model_validate(room, from_attributes=True) for room in raw_room]

    return rooms;
