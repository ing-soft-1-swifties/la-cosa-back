
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
        'sub_type' : 'CONTAGIO',
        'need_target': False,
        'target_adjacent_only': False
    },
    {
        'name' : 'Infectado',
        'amounts' : [8,0,2,2,1,2,2,3],
        'type' : 'ALEJATE',
        'sub_type' : 'CONTAGIO',
        'need_target': False,
        'target_adjacent_only': False
    },
    {
        'name' : 'Sospecha',
        'amounts' : [4,0,0,1,1,1,1,0],
        'type' : 'ALEJATE',
        'sub_type' : 'ACCION',
        'need_target': True,
        'target_adjacent_only': True
    },
    {
        'name' : 'Seducción',
        'amounts' : [2,0,1,1,1,0,1,1],
        'type' : 'ALEJATE',
        'sub_type' : 'ACCION',  
        'need_target': True,
        'target_adjacent_only': False
    },
    {
        'name' : '¡Más vale que corras!',
        'amounts' : [2,0,0,1,0,1,0,1],
        'type' : 'ALEJATE',
        'sub_type' : 'ACCION',
        'need_target': True,
        'target_adjacent_only': False
    },
    {
        'name' : '¡Cambio de lugar!',
        'amounts' : [2,0,0,1,0,1,0,1],
        'type' : 'ALEJATE',
        'sub_type' : 'ACCION',
        'need_target': True,
        'target_adjacent_only': True
    },
    {
        'name' : 'Lanzallamas',
        'amounts' : [2,0,1,0,0,1,0,1],
        'type' : 'ALEJATE',
        'sub_type' : 'ACCION',
        'need_target': True,
        'target_adjacent_only': True
    },
    {
        'name' : 'Determinacion',
        'amounts' : [2,0,1,0,0,1,1,0],
        'type' : 'ALEJATE',
        'sub_type' : 'ACCION',
        'need_target': False,
        'target_adjacent_only': False
    },
    {
        'name' : 'Analisis',
        'amounts' : [0,1,1,0,0,0,0,0],
        'type' : 'ALEJATE',
        'sub_type' : 'ACCION',
        'need_target': True,
        'target_adjacent_only': True
    },
    {
        'name' : 'Whisky',
        'amounts' : [1,0,1,0,0,0,1,0],
        'type' : 'ALEJATE',
        'sub_type' : 'ACCION',
        'need_target': False,
        'target_adjacent_only': False
    },
    {
        'name' : 'Vigila tus espaldas',
        'amounts' : [1,0,0,0,0,1,0,0],
        'type' : 'ALEJATE',
        'sub_type' : 'ACCION',
        'need_target': False,
        'target_adjacent_only': False
    },
    {
        'name' : 'Hacha',
        'amounts' : [1,0,0,0,0,1,0,0],
        'type' : 'ALEJATE',
        'sub_type' : 'ACCION',
        'need_target': True,
        'target_adjacent_only': True
    },
    {
        'name' : '¡No, gracias!',
        'amounts' : [1,0,1,0,1,0,0,1],
        'type' : 'ALEJATE',
        'sub_type' : 'DEFENSA',
        'need_target': False,
        'target_adjacent_only': False
    },
    {
        'name' : 'Aterrador',
        'amounts' : [0,1,1,0,1,0,0,1],
        'type' : 'ALEJATE',
        'sub_type' : 'DEFENSA',
        'need_target': False,
        'target_adjacent_only': False
    },
    {
        'name' : '¡Fallaste!',
        'amounts' : [1,0,1,0,0,0,0,1],
        'type' : 'ALEJATE',
        'sub_type' : 'DEFENSA',
        'need_target': False,
        'target_adjacent_only': False
    },
    {
        'name' : '¡Nada de barbacoas!',
        'amounts' : [1,0,0,0,0,0,0,1],
        'type' : 'ALEJATE',
        'sub_type' : 'DEFENSA',
        'need_target': False,
        'target_adjacent_only': False
    },
    {
        'name' : 'Aquí estoy bien',
        'amounts' : [1,0,1,0,0,0,0,1],
        'type' : 'ALEJATE',
        'sub_type' : 'DEFENSA',
        'need_target': False,
        'target_adjacent_only': False
    },
    {
        'name' : 'Puerta atrancada',
        'amounts' : [1,0,0,1,0,0,0,1],
        'type' : 'ALEJATE',
        'sub_type' : 'OBSTACULO',
        'need_target': True,
        'target_adjacent_only': True
    },
    {
        'name' : 'Cuarentena',
        'amounts' : [0,1,0,0,0,1,0,0],
        'type' : 'ALEJATE',
        'sub_type' : 'OBSTACULO',
        'need_target': True,
        'target_adjacent_only': True
    },
    {
        'name' : 'Vuelta y vuelta',
        'amounts' : [1,0,0,0,0,1,0,0],
        'type' : 'PANICO',
        'sub_type' : '',
        'need_target': False,
        'target_adjacent_only': False
    },
    {
        'name' : '¿No podemos ser amigos?',
        'amounts' : [0,0,0,1,0,1,0,0],
        'type' : 'PANICO',
        'sub_type' : '',
        'need_target': False,
        'target_adjacent_only': False
    },    {
        'name' : 'Cita a ciegas',
        'amounts' : [1,0,0,0,0,1,0,0],
        'type' : 'PANICO',
        'sub_type' : '',
        'need_target': False,
        'target_adjacent_only': False
        
    },    {
        'name' : 'Que quede entre nosotros...',
        'amounts' : [0,0,0,1,0,1,0,0],
        'type' : 'PANICO',
        'sub_type' : '',
        'need_target': False,
        'target_adjacent_only': False
    },    {
        'name' : 'Cuerdas podridas',
        'amounts' : [0,0,1,0,0,1,0,0],
        'type' : 'PANICO',
        'sub_type' : '',
        'need_target': False,
        'target_adjacent_only': False
    },
    {
        'name' : '¿Es aqui la fiesta?',
        'amounts' : [0,1,0,0,0,1,0,0],
        'type' : 'PANICO',
        'sub_type' : '',
        'need_target': False,
        'target_adjacent_only': False
    },
    {
        'name' : 'Uno, dos...',
        'amounts' : [0,1,0,0,0,1,0,0],
        'type' : 'PANICO',
        'sub_type' : '',
        'need_target': False,
        'target_adjacent_only': False
    },
    {
        'name' : 'Tres, cuatro...',
        'amounts' : [1,0,0,0,0,1,0,0],
        'type' : 'PANICO',
        'sub_type' : '',
        'need_target': False,
        'target_adjacent_only': False
    },
    {
        'name' : '¡Ups!',
        'amounts' : [0,0,0,0,0,0,1,0],
        'type' : 'PANICO',
        'sub_type' : '',
        'need_target': False,
        'target_adjacent_only': False
    },
    {
        'name' : 'Olvidadizo',
        'amounts' : [1,0,0,0,0,0,0,0],
        'type' : 'PANICO',
        'sub_type' : '',
        'need_target': False,
        'target_adjacent_only': False
    },
    {
        'name' : 'Revelaciones',
        'amounts' : [0,0,0,0,1,0,0,0],
        'type' : 'PANICO',
        'sub_type' : '',
        'need_target': False,
        'target_adjacent_only': False
    },
    {
        'name' : '¡Sal de aqui!',
        'amounts' : [0,1,0,0,0,0,0,0],
        'type' : 'PANICO',
        'sub_type' : '',
        'need_target': False,
        'target_adjacent_only': False
    }
]


def populate():
    with db_session:
        for i in range(len(cardsJSON)):
            for j in range(len(cardsJSON[i]['amounts'])):
                for k in range(cardsJSON[i]['amounts'][j]):
                    Card(
                        name=cardsJSON[i]['name'], 
                        deck=j+4, type=cardsJSON[i]['type'], 
                        sub_type=cardsJSON[i]['sub_type'],
                        need_target=cardsJSON[i]['need_target'],
                        target_adjacent_only=cardsJSON[i]['target_adjacent_only']
                    )


if __name__ == '__main__':
    from .db import db

    populate()
    with db_session:
        print(f"Total de cartas en la db: {len(Card.select())}")
