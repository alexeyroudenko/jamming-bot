from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from starlette.status import HTTP_400_BAD_REQUEST
import json

app = FastAPI()

# Модель для входящего запроса
class TextInput(BaseModel):
    text: str

# Эндпоинт для классификации
@app.post("/store")
async def store(request: Request):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Invalid or empty JSON body"
        )
    if not isinstance(data, dict) or not data:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="JSON body must be a non-empty object"
        )
    values = list(data.values())
    tsv_line = "\t".join(map(str, values)) + "\n"
    with open("/usr/src/app/data/data.tsv", "a", encoding="utf-8") as f:
        f.write(tsv_line)
    return {"msg": "ok"}