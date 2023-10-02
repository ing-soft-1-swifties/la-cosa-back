import uvicorn

# fastAPI entry
from fastapi import FastAPI

# todos los endpoints distintos
from app.endpoints import rooms

from app.sockets import sio_app

app = FastAPI()

# Conecciones de routers
app.include_router(router=rooms.router)

# conexiones persistentes
app.mount("/socket", sio_app)


if __name__ == '__main__':
    uvicorn.run('main:app', reload=True)
