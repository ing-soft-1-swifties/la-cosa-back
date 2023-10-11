
# class Card(db.Entity):
#     id = PrimaryKey(int, auto=True)
#     name = Required(str)
#     description = Optional(str)
#     deck = Required(int)
#     type = Required(int)            # {ALEJATE, PANICO}
#     sub_type = Optional(int)        # {CONTAGIO, ACCION, DEFENSA, OBSTACULO}
from .entities import Card
from pony.orm import db_session

cardsJSON = [
    {
        'name': 'La cosa',
        'amounts' : [1,0,0,0,0,0,0,0],
        'type' : 'ALEJATE',
        'sub-type' : 'CONTAGIO'
    },
    {
        'name' : 'Infectado',
        'amounts' : [8,0,2,2,1,2,2,3],
        'type' : 'ALEJATE',
        'sub-type' : 'CONTAGIO'
    },
    {
        'name' : 'Sospecha',
        'amounts' : [4,0,0,1,1,1,1,0],
        'type' : 'ALEJATE',
        'sub-type' : 'ACCION'
    },
    {
        'name' : 'Seducción',
        'amounts' : [2,0,1,1,1,0,1,1],
        'type' : 'ALEJATE',
        'sub-type' : 'ACCION'
    },
    {
        'name' : '¡Más vale que corras!',
        'amounts' : [2,0,0,1,0,1,0,1],
        'type' : 'ALEJATE',
        'sub-type' : 'ACCION'
    },
    {
        'name' : '¡Cambio de lugar!',
        'amounts' : [2,0,0,1,0,1,0,1],
        'type' : 'ALEJATE',
        'sub-type' : 'ACCION'
    },
    {
        'name' : 'Lanzallamas',
        'amounts' : [2,0,1,0,0,1,0,1],
        'type' : 'ALEJATE',
        'sub-type' : 'ACCION'
    },
    {
        'name' : 'Determinacion',
        'amounts' : [2,0,1,0,0,1,1,0],
        'type' : 'ALEJATE',
        'sub-type' : 'ACCION'
    },
    {
        'name' : 'Analisis',
        'amounts' : [0,1,1,0,0,0,0,0],
        'type' : 'ALEJATE',
        'sub-type' : 'ACCION'
    },
    {
        'name' : 'Whisky',
        'amounts' : [1,0,1,0,0,0,1,0],
        'type' : 'ALEJATE',
        'sub-type' : 'ACCION'
    },
    {
        'name' : 'Vigila tus espaldas',
        'amounts' : [1,0,0,0,0,1,0,0],
        'type' : 'ALEJATE',
        'sub-type' : 'ACCION'
    },
    {
        'name' : 'Hacha',
        'amounts' : [1,0,0,0,0,1,0,0],
        'type' : 'ALEJATE',
        'sub-type' : 'ACCION'
    },
    {
        'name' : '¡No, gracias!',
        'amounts' : [1,0,1,0,1,0,0,1],
        'type' : 'ALEJATE',
        'sub-type' : 'DEFENSA'
    },
    {
        'name' : 'Aterrador',
        'amounts' : [0,1,1,0,1,0,0,1],
        'type' : 'ALEJATE',
        'sub-type' : 'DEFENSA'
    },
    {
        'name' : '¡Fallaste!',
        'amounts' : [1,0,1,0,0,0,0,1],
        'type' : 'ALEJATE',
        'sub-type' : 'DEFENSA'
    },
    {
        'name' : '¡Nada de barbacoas!',
        'amounts' : [1,0,0,0,0,0,0,1],
        'type' : 'ALEJATE',
        'sub-type' : 'DEFENSA'
    },
    {
        'name' : 'Aquí estoy bien',
        'amounts' : [1,0,1,0,0,0,0,1],
        'type' : 'ALEJATE',
        'sub-type' : 'DEFENSA'
    },
    {
        'name' : 'Puerta atrancada',
        'amounts' : [1,0,0,1,0,0,0,1],
        'type' : 'ALEJATE',
        'sub-type' : 'OBSTACULO'
    },
    {
        'name' : 'Cuarentena',
        'amounts' : [0,1,0,0,0,1,0,0],
        'type' : 'ALEJATE',
        'sub-type' : 'OBSTACULO'
    },
    {
        'name' : 'Vuelta y vuelta',
        'amounts' : [1,0,0,0,0,1,0,0],
        'type' : 'PANICO',
        'sub-type' : ''
    },
    {
        'name' : '¿No podemos ser amigos?',
        'amounts' : [0,0,0,1,0,1,0,0],
        'type' : 'PANICO',
        'sub-type' : ''
    },    {
        'name' : 'Cita a ciegas',
        'amounts' : [1,0,0,0,0,1,0,0],
        'type' : 'PANICO',
        'sub-type' : ''
    },    {
        'name' : 'Que quede entre nosotros...',
        'amounts' : [0,0,0,1,0,1,0,0],
        'type' : 'PANICO',
        'sub-type' : ''
    },    {
        'name' : 'Cuerdas podridas',
        'amounts' : [0,0,1,0,0,1,0,0],
        'type' : 'PANICO',
        'sub-type' : ''
    },    
    {
        'name' : '¿Es aqui la fiesta?',
        'amounts' : [0,1,0,0,0,1,0,0],
        'type' : 'PANICO',
        'sub-type' : ''
    },
    {
        'name' : 'Uno, dos...',
        'amounts' : [0,1,0,0,0,1,0,0],
        'type' : 'PANICO',
        'sub-type' : ''
    },
    {
        'name' : 'Tres, cuatro...',
        'amounts' : [1,0,0,0,0,1,0,0],
        'type' : 'PANICO',
        'sub-type' : ''
    },
    {
        'name' : '¡Ups!',
        'amounts' : [0,0,0,0,0,0,1,0],
        'type' : 'PANICO',
        'sub-type' : ''
    },
    {
        'name' : 'Olvidadizo',
        'amounts' : [1,0,0,0,0,0,0,0],
        'type' : 'PANICO',
        'sub-type' : ''
    },
    {
        'name' : 'Revelaciones',
        'amounts' : [0,0,0,0,1,0,0,0],
        'type' : 'PANICO',
        'sub-type' : ''
    },
    {
        'name' : '¡Sal de aqui!',
        'amounts' : [0,1,0,0,0,0,0,0],
        'type' : 'PANICO',
        'sub-type' : ''
    }
]


def populate():
    with db_session:
        for i in range(len(cardsJSON)):
            for j in range(len(cardsJSON[i]['amounts'])):
                for k in range(cardsJSON[i]['amounts'][j]):
                    Card(name=cardsJSON[i]['name'], deck=j+4, type=cardsJSON[i]['type'], sub_type=cardsJSON[i]['sub-type'])


if __name__ == '__main__':
    from .db import db

    populate()
    with db_session:
        print(f"Total de cartas en la db: {len(Card.select())}")
