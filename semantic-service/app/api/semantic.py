from typing import List
from fastapi import APIRouter, HTTPException
from app.api.models import TagIn, TagOut

from collections import Counter
import spacy
nlp_lg = spacy.load("en_core_web_lg")

def remove_stopwords(text):
    doc = nlp_lg(text)
    return " ".join([token.text for token in doc if not token.is_stop])

def remove_numbers(text):
    doc = nlp_lg(text)
    return " ".join([token.text for token in doc if not token.like_num])

def remove_punctuation(text):
    doc = nlp_lg(text)
    return " ".join([token.text for token in doc if not token.is_punct])

import re
def clean_text(text):
    text = text.strip()  # Убираем пробелы в начале и конце
    text = re.sub(r'\s+', ' ', text)  # Заменяем множественные пробелы на один
    return text

def preprocess_text(text):
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
    query = nlp_lg("happiness")
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