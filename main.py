# fastAPI entry
from fastapi import FastAPI

# modelos de base de datos
from app.models import models

# todos los endpoints distintos
from app.endpoints import submodule

#importamos los esquemas
from app.schemas import schemas

from pony.orm import *

app = FastAPI()

db = Database()

db.bind(provider='sqlite', filename='database/database.sqlite', create_db=True)
db.generate_mapping(create_tables=True)



@app.get("/")   
def read_root():

    with db_session:
        obstacles = models.Card.select()

        asd = list(obstacles)
        
        print(type(asd[0]))

    return {"Hello": asd[0].name}


@app.get("/save")
def add_obstacle():

    with db_session:
        card = models.Card(name="Alejo", description="gordito lindo", type=2, sub_type=5)
        commit()
        return {"Hello": "ya guarde"}




app.include_router(submodule.router)

