from fastapi import FastAPI
from app.api.tags import tags
from app.api.db import metadata, database, engine
from fastapi.middleware.cors import CORSMiddleware

metadata.create_all(engine)

app = FastAPI(openapi_url="/api/v1/tags/openapi.json", docs_url="/api/v1/tags/docs")

origins = [
    "http://localhost:3000",
    "https://example.com",
    "http://192.168.31.18:3000",
    "http://192.168.31.18:8003",
    "http://192.168.31.18:5000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


app.include_router(tags, prefix='/api/v1/tags', tags=['tags'])
# app.include_router(tags, prefix='/api/v1/tags/group', tags=['tags'])