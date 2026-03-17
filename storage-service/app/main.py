from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from starlette.status import HTTP_400_BAD_REQUEST
import json
import os

app = FastAPI()

DATA_DIR = "/usr/src/app/data"
DATA_FILE = os.path.join(DATA_DIR, "data.tsv")
STEPS_DIR = os.path.join(DATA_DIR, "steps")

STEP_FIELDS = [
    'number', 'url', 'src', 'ip', 'status_code', 'timestamp', 'text',
    'city', 'latitude', 'longitude', 'error',
    'tags', 'words', 'hrases', 'entities', 'text_length',
    'semantic', 'semantic_words', 'semantic_hrases',
    'screenshot_url', 's3_key',
]


def _ensure_data_file():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.isfile(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            f.write("\t".join(STEP_FIELDS) + "\n")


def _ensure_steps_dir():
    os.makedirs(STEPS_DIR, exist_ok=True)


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
    _ensure_data_file()

    values = [str(data.get(f, '')) for f in STEP_FIELDS]
    tsv_line = "\t".join(values) + "\n"
    with open(DATA_FILE, "a", encoding="utf-8") as f:
        f.write(tsv_line)

    step_num = data.get("number", data.get("step"))
    if step_num is not None:
        _ensure_steps_dir()
        step_path = os.path.join(STEPS_DIR, f"{step_num}.json")
        with open(step_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    return {"msg": "ok"}


@app.get("/get/step/{number}")
async def get_step(number: str):
    _ensure_steps_dir()
    step_path = os.path.join(STEPS_DIR, f"{number}.json")
    if not os.path.isfile(step_path):
        raise HTTPException(status_code=404, detail="Step not found")
    with open(step_path, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/get/latest")
async def get_latest():
    """Return the latest 3000 steps as objects with named fields."""
    try:
        _ensure_data_file()
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()

        parsed_data = []
        for line in lines[-3000:]:
            line = line.strip()
            if not line:
                continue
            values = line.split('\t')
            if values == STEP_FIELDS:
                continue
            row = {}
            for i, field in enumerate(STEP_FIELDS):
                val = values[i] if i < len(values) else ''
                row[field] = val
            parsed_data.append(row)

        return {
            "fields": STEP_FIELDS,
            "total_lines": max(len(lines) - 1, 0),
            "returned_lines": len(parsed_data),
            "data": parsed_data,
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Data file not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")
