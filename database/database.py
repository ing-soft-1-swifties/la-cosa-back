

from pony.orm import *

db = Database ()

db.bind(provider='sqlite', filename='la_cosa.sqlite', create_db=True)
db.generate_mapping(create_tables=True)
