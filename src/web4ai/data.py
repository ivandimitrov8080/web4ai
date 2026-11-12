from peewee import DatabaseProxy, Model, SqliteDatabase, TextField

from os.path import expanduser

DEFAULT_DB = expanduser("~/.local/state/web4ai.sqlite")

db = DatabaseProxy()

class BaseModel(Model):
    class Meta:
        database = db

class SearchState(BaseModel):
    query = TextField(unique=True)
    result = TextField()

class FetchState(BaseModel):
    url = TextField(unique=True)
    result = TextField()

def init_db():
    database = SqliteDatabase(DEFAULT_DB)
    db.initialize(database)
    database.connect()
    database.drop_tables([SearchState, FetchState])
    database.create_tables([SearchState, FetchState])
