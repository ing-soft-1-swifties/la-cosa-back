import uvicorn

# fastAPI entry
from fastapi import FastAPI

# todos los endpoints distintos
from app.endpoints import rooms

# modelos de base de datos -> Base de datos
from app.models import * 

# importamos los esquemas -> Fastapi
from app.schemas import *

# imports ponyORM
from pony.orm import db_session

from database.database import db

from app.sockets import sio_app

app = FastAPI()


@app.get("/")
def read_root():

    with db_session:
        raw_cards = Card.select()
        cards = [CardSchema.model_validate(card, from_attributes=True) for card in raw_cards]

    return {"Hello": cards}


@app.get("/save")
def add_card():

    with db_session:
        card = Card(name="nombreCarta", description="descripcionCarta", type=0, sub_type=0)
        db.commit()
        return {"Hello": "Guardado!"}


# Conecciones de routers
app.include_router(router=rooms.router)

# conexiones persistentes
app.mount("/socket", sio_app)


if __name__ == '__main__':
    uvicorn.run('main:app', reload=True)
