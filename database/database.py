from pony.orm import Database
from app.models import db

def get_db(file_basename: str = "la_cosa"):
    db.bind(provider='sqlite', filename=f'{file_basename}.sqlite', create_db=True)
    db.generate_mapping(create_tables=True)

    return db

