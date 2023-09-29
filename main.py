# fastAPI entry
from fastapi import FastAPI

# todos los endpoints distintos
from app.endpoints import submodule

# modelos de base de datos -> Base de datos
from app.models import * 

# importamos los esquemas -> Fastapi
from app.schemas import *

# imports ponyORM
from pony.orm import *

app = FastAPI()


db = Database()
db.bind(provider='sqlite', filename='database/database.sqlite', create_db=True)
db.generate_mapping(create_tables=True)


@app.get("/")
def read_root():

    with db_session:

        raw_cards = Card.select()

        print(type(raw_cards))
        cards = [CardSchema.model_validate(card, from_attributes=True) for card in raw_cards]

    return {"Hello": cards}


@app.get("/save")
def add_obstacle():

    with db_session:
        card = Card(name="nombreCarta", description="descripcionCarta", type=0, sub_type=0)
        commit()
        return {"Hello": "Guardado!"}



# Conecciones de routers
app.include_router(router=submodule.router)

