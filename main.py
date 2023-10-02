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

# Conecciones de routers
app.include_router(router=rooms.router)

# conexiones persistentes
app.mount("/socket", sio_app)


if __name__ == '__main__':
    uvicorn.run('main:app', reload=True)
