#no son tests formales, se corren con python3 test_sockets.py
#simula casos de usos simples, 

def create_room(host_name, room_name):
    import requests
    url = 'http://localhost:8000/create'
    data={
    "room_name": room_name,
    "host_name": host_name,
    "min_players": 4,
    "max_players": 5,
    "is_private": False
    }
    response = requests.post(url, json=data)
    token = None
    if response.status_code == 200:
        print('Solicitud exitosa')
        print('Respuesta del servidor:', response.json())
        token = response.json().get("token")
    else:
        print('La solicitud falló con el código de estado:', response.status_code)
        print('Respuesta del servidor:', response.text)
    return token

def join_room(player_name, room_id):
    import requests
    url = 'http://localhost:8000/join'
    data={
    "room_id": room_id,
    "name": player_name,
    }
    response = requests.post(url, json=data)
    token = None
    if response.status_code == 200:
        print('Solicitud exitosa')
        print('Respuesta del servidor:', response.json())
        token = response.json().get("token")
    else:
        print('La solicitud falló con el código de estado:', response.status_code)
        print('Respuesta del servidor:', response.text)
    return token


import socketio
def connect_socket(token):
    import requests
    sio = socketio.Client()

    sio.connect('http://localhost:8000', auth={"token":token})
    # Espera a que la conexión se establezca
    print(f"conexion establecioda para token {token}")
    # Simula el envío de un mensaje al servidor
    # sio.emit('message', 'Hola desde el cliente')
    return sio

def listen_events(sio):
    def on_any_event(sid, data):
        print(data)
    sio.on("*", on_any_event) 
    sio.wait()

import threading

host_token = create_room("111", "test")
players_sockets = []
players_sockets.append(connect_socket(host_token))
for i in range(2,5):
    player_token = join_room(f"{i}{i}{i}", 1)
    players_sockets.append(connect_socket(player_token))
listening_thread = threading.Thread(target=listen_events, args=(players_sockets[0],))
listening_thread.start()
players_sockets[0].emit("room_start_game") 
