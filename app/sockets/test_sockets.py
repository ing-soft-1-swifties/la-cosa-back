#no son tests formales, se corren con python3 test_sockets.py
#simula casos de usos simples, para este caso simula una creacion y lanzamiento de una partida
#seguido de un descarte y un intercambio exitoso de cartas. No se realizan checkeos automaticos por ahora 

import socketio
import threading
import time

class player():
    def __init__(self, name, room_id):
        self.name = name
        self.room_id = room_id
        self.token = self.join_room()
        self.sio = self.connect_socket()
        self.position = 0
        self.cards = []
        threading.Thread(target=self.listen_events).start()
    def join_room(self):
        import requests
        url = 'http://localhost:8000/join'
        data={
        "room_id": self.room_id,
        "name": self.name,
        }
        response = requests.post(url, json=data)
        token = None
        if response.status_code == 200:
            # print('Solicitud exitosa')
            token = response.json().get("token")
        else:
            print('La solicitud falló con el código de estado:', response.status_code)
            print('Respuesta del servidor:', response.text)
            quit()
        return token
    def connect_socket(self):
        sio = socketio.Client()
        sio.connect('http://localhost:8000', auth={"token":self.token})
        # print(f"conexion establecioda para token {self.token}")
        return sio
    def listen_events(self):
        @self.sio.on('*')
        def on_any_event(event, data):
            self.cards = []
            for carta in data["gameState"]["playerData"]["cards"]:
                self.cards.append({"id":carta["id"],
                                   "name":carta["name"]})
            self.position = data["gameState"]["playerData"]["position"]

        self.sio.wait()
    def emit(self, event, body):
        if body == {}:
            self.sio.emit(event)
        else:
            self.sio.emit(event, body)
    def discard_random_card(self):
        for card in self.cards:
            if card["name"] != "La cosa" \
            or card["name"] != "Infección":
                self.emit("game_discard_card",{"card":card["id"]})
                return
    def exchange_random_card(self):
        for card in self.cards:
            if card["name"] != "La cosa" \
            or card["name"] != "Infección":
                self.emit("game_exchange_card",{"card":card["id"], "on_defense":False, "target":0})
                return
    def show_cards(self):
        print(self.cards)
class host(player):
    def __init__(self, name, room_name):
        self.room_name = room_name
        self.name = name
        self.position = 0
        self.cards = []
        self.token = self.create_room("test")
        self.sio = self.connect_socket()
        threading.Thread(target=self.listen_events).start()
    def create_room(self,room_name):
        import requests
        url = 'http://localhost:8000/create'
        data={
        "room_name": room_name,
        "host_name": self.name,
        "min_players": 4,
        "max_players": 5,
        "is_private": False
        }
        response = requests.post(url, json=data)
        token = None
        if response.status_code == 200:
            # print('Solicitud exitosa')
            # print('Respuesta del servidor:', response.json())
            token = response.json().get("token")
        else:
            print('La solicitud falló con el código de estado:', response.status_code)
            print('Respuesta del servidor:', response.text)
        return token
    def listen_events(self):
        @self.sio.on('*')
        def on_any_event(event, data):
            self.cards = []
            for carta in data["gameState"]["playerData"]["cards"]:
                self.cards.append({"id":carta["id"],
                                   "name":carta["name"]})
            self.position = data["gameState"]["playerData"]["position"]
            # print(" ")
            print("Host escucho el siguiente evento: ", event)
            # print(" ")
            # import json
            # print(json.dumps(data, indent=2))
            # print(f"jugador {self.name} tiene estas cartas: ", data["gameState"]["playerData"]["cards"])

class game():
    def __init__(self, people_amount):
        self.players = []
        self.hoster = host("111", f"test")
        print("Partida creada con exito")
        print("Jugador 1 se unio correctamente")
        self.room_id = self.last_room_id()
        self.players.append(self.hoster)
        for i in range(2,people_amount+1):
            self.players.append(player(f"{i}{i}{i}", self.room_id))
            print(f"Jugador {i} se unio correctamente")
        # self.start()
        # print("Partida iniciada con exito")
    def start(self):
        self.hoster.emit("room_start_game", {})
    def last_room_id(self):
        import requests
        url = 'http://localhost:8000/list'
        response = requests.get(url)
        if response.status_code == 200:
            # print('Solicitud exitosa')
            # print('Respuesta del servidor:', response.json())
            return int(list(response.json())[-1]["id"])
            # token = response.json().get("token")
        else:
            print('La solicitud falló con el código de estado:', response.status_code)
            print('Respuesta del servidor:', response.text)
            quit()
    def player_in_turn(self):
        for i, player in enumerate(self.players):
            if len(player.cards) == 5:
                return player
    def discard_card(self):
        self.player_in_turn = self.player_in_turn()
        self.player_in_turn.discard_random_card()
    def exchange_card(self):
        self.player_in_turn.exchange_random_card()
        time.sleep(1)
        next_player = None
        for player in self.players:
            #notar que no anda para el caso borde de el ultimo jugador
            if player.position == self.player_in_turn.position+1:
                next_player = player
                break
        print("cartas de el primer jugador antes del intercambio: ")
        self.player_in_turn.show_cards()
        print("cartas de el segundo jugador antes del intercambio: ")
        next_player.show_cards()
        next_player.exchange_random_card()
        time.sleep(1)
        print("luego del intercambio: ")
        print("cartas de el primer jugador: ")
        self.player_in_turn.show_cards()
        print("cartas de el segundo jugador: ")
        next_player.show_cards()
        
    

current_game = game(4)  #creamos una partida con 4 personas
current_game.start()    #lanzamos la partida
print("se inició la partida")
time.sleep(1)
current_game.discard_card() #descarta una carta aleatoria la persona que esta en turno
print("se descarto una carta")
time.sleep(1)
current_game.exchange_card()    #realizan intercambios los que deben hacerlo
print("se intercambiaron las cartas")
