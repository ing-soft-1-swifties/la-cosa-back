
# class Card(db.Entity):
#     id = PrimaryKey(int, auto=True)
#     name = Required(str)
#     description = Optional(str)
#     deck = Required(int)
#     type = Required(int)            # {Alejate, Panico}
#     sub_type = Optional(int)        # {Contagio, Accion, Defensa, Obstaculo}
#     roomsA = Set('Room', reverse='available_cards')
#     roomsD = Set('Room', reverse='discarted_cards')

from pony.orm import db_session
from __init__ import Card

cardsJSON = [
    {
        'name': 'La cosa',
        'amounts' : [1,0,0,0,0,0,0,0]
    },
    {
        'name' : 'Infectado',
        'amounts' : [8,0,2,2,1,2,2,3]
    },
    {
        'name' : 'Sospecha',
        'amounts' : [4,0,0,1,1,1,1,0]
    },
    {
        'name' : 'Seducción',
        'amounts' : [2,0,1,1,1,0,1,1]
    },
    {
        'name' : '¡Más vale que corras!',
        'amounts' : [2,0,0,1,0,1,0,1]
    },
    {
        'name' : '¡Cambio de lugar!',
        'amounts' : [2,0,0,1,0,1,0,1]
    },
    {
        'name' : 'Lanzallamas',
        'amounts' : [2,0,1,0,0,1,0,1]
    },
    {
        'name' : 'Determinacion',
        'amounts' : [2,0,1,0,0,1,1,0]
    },
    {
        'name' : 'Analisis',
        'amounts' : [0,1,1,0,0,0,0,0]
    },
    {
        'name' : 'Whisky',
        'amounts' : [1,0,1,0,0,0,1,0]
    },
    {
        'name' : 'Vigila tus espaldas',
        'amounts' : [1,0,0,0,0,1,0,0]
    },
    {
        'name' : 'Hacha',
        'amounts' : [1,0,0,0,0,1,0,0]
    },
    {
        'name' : '¡No, gracias!',
        'amounts' : [1,0,1,0,1,0,0,1]
    },
    {
        'name' : 'Aterrador',
        'amounts' : [0,1,1,0,1,0,0,1]
    },
    {
        'name' : '¡Fallaste!',
        'amounts' : [1,0,1,0,0,0,0,1]
    },
    {
        'name' : '¡Nada de barbacoas!',
        'amounts' : [1,0,0,0,0,0,0,1]
    },
    {
        'name' : 'Aquí estoy bien',
        'amounts' : [1,0,1,0,0,0,0,1]
    },
    {
        'name' : 'Puerta atrancada',
        'amounts' : [1,0,0,1,0,0,0,1]
    },
    {
        'name' : 'Cuarentena',
        'amounts' : [0,1,0,0,0,1,0,0]
    },
    {
        'name' : 'Vuelta y vuelta',
        'amounts' : [1,0,0,0,0,1,0,0]
    },
    {
        'name' : '¿No podemos ser amigos?',
        'amounts' : [0,0,0,1,0,1,0,0]
    },    {
        'name' : 'Cita a ciegas',
        'amounts' : [1,0,0,0,0,1,0,0]
    },    {
        'name' : 'Que quede entre nosotros...',
        'amounts' : [0,0,0,1,0,1,0,0]
    },    {
        'name' : 'Cuerdas podridas',
        'amounts' : [0,0,1,0,0,1,0,0]
    },    
    {
        'name' : '¿Es aqui la fiesta?',
        'amounts' : [0,1,0,0,0,1,0,0]
    },
    {
        'name' : 'Uno, dos...',
        'amounts' : [0,1,0,0,0,1,0,0]
    },
    {
        'name' : 'Tres, cuatro...',
        'amounts' : [1,0,0,0,0,1,0,0]
    },
    {
        'name' : '¡Ups!',
        'amounts' : [0,0,0,0,0,0,1,0]
    },
    {
        'name' : 'Olvidadizo',
        'amounts' : [1,0,0,0,0,0,0,0]
    },
    {
        'name' : 'Revelaciones',
        'amounts' : [0,0,0,0,1,0,0,0]
    },
    {
        'name' : '¡Sal de aqui!',
        'amounts' : [0,1,0,0,0,0,0,0]
    }
]

# with db_session:
#     for i in range(len(cardsJSON)):
#         for j in range(len(cardsJSON[i]['amounts'])):
#             for k in range(cardsJSON[i]['amounts'][j]):
#                 Card(name=cardsJSON[i]['name'], deck=j+4, type=0)

with db_session:
    cards = list(Card.select(lambda card: card.name=='Hacha'))
    for card in cards:
        print(f'{card.name}, {card.deck}')



