import os

from sqlalchemy import (Column, Date, Integer, MetaData, String, Table,
                        UniqueConstraint, create_engine, Index)

from databases import Database

DATABASE_URI = os.getenv('DATABASE_URI')

engine = create_engine(DATABASE_URI)
metadata = MetaData()

tags = Table(
    'movies',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String(50)),
    Column('count', Integer)
)

tag_daily_stats = Table(
    'tag_daily_stats',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('day', Date, nullable=False),
    Column('tag_name', String(50), nullable=False),
    Column('count', Integer, nullable=False, default=0),
    UniqueConstraint('day', 'tag_name', name='uq_tag_daily_stats_day_tag_name'),
    Index('ix_tag_daily_stats_day', 'day'),
    Index('ix_tag_daily_stats_tag_name', 'tag_name'),
)

database = Database(DATABASE_URI)