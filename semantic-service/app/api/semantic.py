from typing import List
from fastapi import APIRouter, HTTPException
from app.api.models import TagIn, TagOut

from collections import Counter
from itertools import combinations
import spacy

# Initialize spaCy model with error handling
nlp_lg = None
try:
    nlp_lg = spacy.load("en_core_web_lg")
    print("SpaCy model loaded successfully")
except Exception as e:
    print(f"Failed to load SpaCy model: {e}")
    nlp_lg = None

def remove_stopwords(text):
    if nlp_lg is None:
        return text
    doc = nlp_lg(text)
    return " ".join([token.text for token in doc if not token.is_stop])

def remove_numbers(text):
    if nlp_lg is None:
        return text
    doc = nlp_lg(text)
    return " ".join([token.text for token in doc if not token.like_num])

def remove_punctuation(text):
    if nlp_lg is None:
        return text
    doc = nlp_lg(text)
    return " ".join([token.text for token in doc if not token.is_punct])

import re
def clean_text(text):
    text = text.strip()  # Убираем пробелы в начале и конце
    text = re.sub(r'\s+', ' ', text)  # Заменяем множественные пробелы на один
    return text

def preprocess_text(text):
    if nlp_lg is None:
        return text.lower()
    text = clean_text(text)  # Убираем лишние пробелы
    text = text.lower()  # Приводим к нижнему регистру
    doc = nlp_lg(text)
    
    tokens = [
        token.lemma_ for token in doc
        if not token.is_stop and not token.is_punct and not token.like_num
    ]
    
    return " ".join(tokens)

def analyze_text(texts):
    words = []
    hrases = []
    
    if nlp_lg is None:
        return words, hrases, []
    
    text = clean_text(texts)
    text = text.lower()
    text = remove_stopwords(text)
    text = remove_punctuation(text)
    text = remove_numbers(text)
    text = preprocess_text(text)
    

    doc = nlp_lg(text)
    keywords = [token.text.lower() for token in doc if token.pos_ in ["NOUN", "ADJ"] and not token.is_stop]
    keyword_counts = Counter(keywords)
    words = []
    for item in keyword_counts.most_common(10):
        words.append(item[0])

                    
    doc = nlp_lg(text)
    noun_hrases =  [chunk.text for chunk in doc.noun_chunks]            
    for i in noun_hrases[0:64]:
        hrases.append(i.lower())
        
    
    sim = []      
    query = nlp_lg("happiness love life joy bliss delight euphoria serenity contentment")
    similarities = {}
    for token in doc:
        if token.has_vector and query.has_vector:
            similarity = query.similarity(token)
            if similarity > 0:
                similarities[token.text] = similarity


    sorted_similarities = sorted(similarities.items(), key=lambda x: x[1], reverse=True)
    print(f"Similarity w '{query.text}':")
    for word, similarity in sorted_similarities[0:5]:
        print(f"{word}: {similarity:.2f}")
        sim.append(word)
            
    
    
    return words, hrases, sim



semantic = APIRouter()

from pydantic import BaseModel
class SemanticCalculate(BaseModel):
    text: str

@semantic.post('/tags/')
async def get_geo(text_data: SemanticCalculate):
    if not text_data:
        raise HTTPException(status_code=404, detail="text not found")    
    
    text = text_data.text
    out = TagOut()
    out.text = text
    words, hrases, sim = analyze_text(text)    
    out.words = words
    out.hrases = hrases
    out.sim = sim
    return out


class CombineIn(BaseModel):
    words: List[str]
    limit: int = 50
    max_phrases: int = 1024


@semantic.post('/combine/')
async def combine_tags(data: CombineIn):
    if nlp_lg is None:
        raise HTTPException(status_code=503, detail="SpaCy model not loaded")

    words = [w.strip() for w in data.words if w.strip()][:data.limit]
    phrases = []

    for a, b in combinations(words, 2):
        doc = nlp_lg(f"{a} {b}")
        pos_a = doc[0].pos_
        pos_b = doc[-1].pos_

        if pos_a in ("NOUN", "PROPN", "ADJ") and pos_b in ("NOUN", "PROPN"):
            phrases.append(f"the {a} {b}")
        elif pos_a == "VERB":
            phrases.append(f"to {a} {b}")

        if len(phrases) >= data.max_phrases:
            break

    return {"phrases": phrases, "count": len(phrases)}