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


@app.get("/get/latest")
async def get_latest():
    """
    Returns the latest 3000 lines from the stored TSV file as JSON array
    """
    try:
        with open("/usr/src/app/data/data.tsv", "r", encoding="utf-8") as f:
            # Read all lines and get the last 3000
            lines = f.readlines()
            latest_lines = lines[-3000:] if len(lines) > 3000 else lines
            
            # Parse TSV lines into JSON array
            parsed_data = []
            for line in latest_lines:
                line = line.strip()
                if line:  # Skip empty lines
                    # Split by tab and create array of values
                    values = line.split('\t')
                    parsed_data.append(values)
            
            return {
                "total_lines": len(lines),
                "returned_lines": len(parsed_data),
                "data": parsed_data
            }
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Data file not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading file: {str(e)}"
        )
