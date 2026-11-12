from peewee import DatabaseProxy, Model, SqliteDatabase, TextField

DEFAULT_DB = ":memory:"

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
    database.create_tables([SearchState, FetchState])
