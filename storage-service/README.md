## Setup

1. Build the Docker image:
   ```bash
   docker build -t storage-service .
   ```

2. Run the container:
   ```bash
   docker run -d -p 7781:7781 storage-service
   ```

3. Access the API at `http://localhost:7781/docs` for Swagger UI.

## Usage

Send a POST request to `/store` with JSON:
```json
{
    "field1": "Artificial intelligence 1",
    "field2": "Artificial intelligence 2"

}
```

Example response:
```json
[
    {"msg": "ok"}
]
```

## Dependencies
- FastAPI
- Uvicorn
- Pydantic