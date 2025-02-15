from typing import List
from fastapi import APIRouter, HTTPException
from app.api.models import TagIn, TagOut

from collections import Counter
import spacy
nlp_lg = spacy.load("en_core_web_lg")

def analyze_text(text):
    words = []
    hrases = []
    
    doc = nlp_lg(text)
    keywords = [token.text.lower() for token in doc if token.pos_ in ["NOUN", "ADJ"] and not token.is_stop]
    keyword_counts = Counter(keywords)
    words = []
    for item in keyword_counts.most_common(10):
        words.append(item[0])


        
                    
    doc = nlp_lg(text)
    noun_hrases =  [chunk.text for chunk in doc.noun_chunks]            
    for i in noun_hrases[0:10]:
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