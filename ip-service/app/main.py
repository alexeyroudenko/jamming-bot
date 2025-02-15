from fastapi import FastAPI
from app.api.ip import ip
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(openapi_url="/api/v1/ip/openapi.json", docs_url="/api/v1/ip/docs")

origins = [
    "http://localhost:3000",
    "https://example.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ip, prefix='/api/v1/ip')