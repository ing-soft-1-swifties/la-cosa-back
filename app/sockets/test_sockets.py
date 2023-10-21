#no son tests formales, se corren con python3 test_sockets.py
#simula casos de usos simples, 
import requests

# URL de la API
url = 'http://localhost:8000/create'

# Datos que se enviarán en el cuerpo de la solicitud
data={
  "room_name": "string",
  "host_name": "string",
  "min_players": 4,
  "max_players": 5,
  "is_private": False
}

# Realizar una solicitud POST a la API REST
response = requests.post(url, json=data)
token = None
# Verificar la respuesta de la API
if response.status_code == 200:
    print('Solicitud exitosa')
    print('Respuesta del servidor:', response.json())
    token = response.json().get("token")
    
else:
    print('La solicitud falló con el código de estado:', response.status_code)
    print('Respuesta del servidor:', response.text)
    quit()
import socketio

# Crea una instancia del cliente Socket.io
sio = socketio.Client()

# # Define funciones para manejar eventos del servidor
# @sio.on('connect')
# def on_connect():
#     print('Conexión establecida')

# @sio.on('message')
# def on_message(data):
#     print('Mensaje recibido:', data)

# @sio.on('disconnect')
# def on_disconnect():
#     print('Desconexión')

# Conéctate al servidor Socket.io
sio.connect('http://localhost:8000', auth={
    "token":token
})
print("conexion establecioda")

# Espera a que la conexión se establezca
sio.wait()

# Simula el envío de un mensaje al servidor
sio.emit('message', 'Hola desde el cliente')

# Puedes emitir más eventos y trabajar con lógica adicional aquí
