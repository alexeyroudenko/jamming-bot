from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict
from classifier import classify_text_by_keywords, load_keywords
import json

app = FastAPI()

# Загружаем словарь ключевых слов при старте
keyword_dict = load_keywords("keywords.json")

# Модель для входящего запроса
class TextInput(BaseModel):
    text: str

# Эндпоинт для классификации
@app.post("/classify", response_model=List[Dict[str, str]])
async def classify(input: TextInput):
    predicted_topic = classify_text_by_keywords(input.text, keyword_dict)
    return [{"topic": predicted_topic}]