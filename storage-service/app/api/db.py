import os

from sqlalchemy import (Column, Integer, String, Text, Table, MetaData,
                        create_engine)
from databases import Database

DATABASE_URI = os.getenv('DATABASE_URI')

engine = create_engine(DATABASE_URI)
metadata = MetaData()

steps = Table(
    'steps',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('number', String(50), index=True),
    Column('url', Text),
    Column('src', Text),
    Column('ip', String(50)),
    Column('status_code', String(10)),
    Column('timestamp', String(50)),
    Column('text', Text),
    Column('city', String(100)),
    Column('latitude', String(50)),
    Column('longitude', String(50)),
    Column('error', Text),
    Column('tags', Text),
    Column('words', Text),
    Column('hrases', Text),
    Column('entities', Text),
    Column('text_length', String(20)),
    Column('semantic', Text),
    Column('semantic_words', Text),
    Column('semantic_hrases', Text),
    Column('screenshot_url', Text),
    Column('s3_key', Text),
)

database = Database(DATABASE_URI)
