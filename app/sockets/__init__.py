import socketio

sio_server = socketio.AsyncServer(
        async_mode = "asgi",
        cors_allowed_origins= ["*"]
)

sio_app = socketio.ASGIApp(
    socketio_server=sio_server,
    socketio_path="sockets"
)

@sio_server.event
async def connect(sid, environ, auth):
    # autenticar jugador con token
    # guardar en jugador el socket id
    # ack de conexion para el cliente si es que es necesario
    await sio_server.emit('connected', room=sid)
