from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from app.api.semantic import semantic
from app.api.tag_embeddings import tag_embeddings_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="semantic-service",
    docs_url=None,
    openapi_url="/openapi.json",
)


@app.get("/docs", include_in_schema=False)
async def swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="openapi.json",
        title=f"{app.title} - Swagger UI",
    )

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
app.include_router(tag_embeddings_router, prefix='/api/v1/semantic')