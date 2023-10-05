from .entities import db

db.bind(provider='sqlite', filename=f':sharedmemory:', create_db=True)
db.generate_mapping(create_tables=True)
