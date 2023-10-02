import uvicorn

# fastAPI entry
from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

# todos los endpoints distintos
from app.endpoints import rooms

from app.sockets import sio_app

app = FastAPI()



app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conecciones de routers
app.include_router(router=rooms.router)

# conexiones persistentes
app.mount("/sockets", sio_app)


if __name__ == '__main__':
    uvicorn.run('main:app', reload=True)
