from fastapi import FastAPI
from app.api.semantic import semantic
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(openapi_url="/api/v1/semantic/openapi.json", docs_url="/api/v1/semantic/docs")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

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

app.include_router(semantic, prefix='/api/v1/semantic')