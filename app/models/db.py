from pony.orm import Database

from .entities import db

db.bind(provider='sqlite', filename=f'la_cosa.sqlite', create_db=True)
db.generate_mapping(create_tables=True)
