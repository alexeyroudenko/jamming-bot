from typing import List

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
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


class SemanticCalculate(BaseModel):
    text: str

@semantic.post('/tags/')
async def get_geo(text_data: SemanticCalculate):
    if not text_data:
        raise HTTPException(status_code=404, detail="text not found")

    text = text_data.text
    entities: List[dict] = []
    if nlp_lg is not None:
        edoc = nlp_lg(text[:100000])
        entities = [{"text": ent.text, "label": ent.label_} for ent in edoc.ents]

    words, hrases, sim = analyze_text(text)
    dependency = []
    for token in edoc:
        dependency.append(f"{token.text}>{token.head}")
    return {
        "text": text,
        "words": words,
        "hrases": hrases,
        "sim": sim,
        "entities": entities,
        "dependency": dependency,
    }


@semantic.get('/analyze_all/')
async def analyze_all_get(text: str = ""):
    if not text:
        raise HTTPException(status_code=400, detail="text parameter is required")
    return _analyze_all(text)


@semantic.post('/analyze_all/')
async def analyze_all_post(text_data: SemanticCalculate):
    if not text_data or not text_data.text:
        raise HTTPException(status_code=400, detail="text is required")
    return _analyze_all(text_data.text)


def _analyze_all(text: str):
    if nlp_lg is None:
        raise HTTPException(status_code=503, detail="SpaCy model not loaded")

    doc = nlp_lg(text)
    noun_phrases = [chunk.text for chunk in doc.noun_chunks]
    verbs = [token.lemma_ for token in doc if token.pos_ == "VERB"]
    entities = [{"text": ent.text, "label": ent.label_} for ent in doc.ents]
    keywords = [token.text.lower() for token in doc if token.pos_ in ["NOUN", "ADJ"] and not token.is_stop]
    subjects = [token.text for token in doc if token.dep_ == "nsubj"]
    objects = [token.text for token in doc if token.dep_ == "dobj"]
    dependency = [{"token": token.text, "dep": token.dep_, "head": token.head.text} for token in doc]

    return {
        "noun_phrases": noun_phrases,
        "verbs": verbs,
        "entities": entities,
        "keywords": keywords,
        "subjects": subjects,
        "objects": objects,
        "dependency": dependency,
    }


class CombineIn(BaseModel):
    words: List[str]
    limit: int = 32
    max_phrases: int = 512


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


from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_vader = SentimentIntensityAnalyzer()


class SentimentPhrasesIn(BaseModel):
    phrases: List[str]
    limit: int = 256


def _sentiment_stats_for_phrases(phrases: List[str], limit: int) -> dict:
    trimmed = [p.strip() for p in phrases if p and p.strip()][: max(0, min(limit, 512))]
    items = []
    for text in trimmed:
        scores = _vader.polarity_scores(text)
        compound = float(scores["compound"])
        neu = float(scores["neu"])
        subjectivity = max(0.0, min(1.0, 1.0 - neu))
        items.append(
            {"text": text, "polarity": compound, "subjectivity": subjectivity}
        )

    n = len(items)
    if n == 0:
        return {
            "items": [],
            "stats": {
                "mean_polarity": 0.0,
                "pct_positive": 0.0,
                "pct_negative": 0.0,
                "pct_neutral": 0.0,
                "count": 0,
            },
        }

    pos = sum(1 for it in items if it["polarity"] > 0.05)
    neg = sum(1 for it in items if it["polarity"] < -0.05)
    neu_c = n - pos - neg
    mean_pol = sum(it["polarity"] for it in items) / n
    return {
        "items": items,
        "stats": {
            "mean_polarity": mean_pol,
            "pct_positive": pos / n,
            "pct_negative": neg / n,
            "pct_neutral": neu_c / n,
            "count": n,
        },
    }


@semantic.post("/sentiment-phrases/")
async def sentiment_phrases(data: SentimentPhrasesIn):
    return _sentiment_stats_for_phrases(data.phrases, data.limit)