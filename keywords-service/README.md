# Keyword-Based Text Classification API

This is a FastAPI application that classifies English text into topics (e.g., Technology, Literature, History) based on keyword matching. The application uses a JSON dictionary with 50 keywords per topic and is containerized using Docker.

## Setup

1. Build the Docker image:
   ```bash
   docker build -t keyword-classifier .
   ```

2. Run the container:
   ```bash
   docker run -d -p 8000:8000 keyword-classifier
   ```

3. Access the API at `http://localhost:8000/docs` for Swagger UI.

## Usage

Send a POST request to `/classify` with JSON:
```json
{
    "text": "Artificial intelligence is transforming the world of programming and technology."
}
```

Example response:
```json
[
    {"topic": "Technology"}
]
```

## Dependencies
- FastAPI
- Uvicorn
- Pydantic