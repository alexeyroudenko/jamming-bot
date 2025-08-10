



import spacy

def _try_load(model_name):
    try:
        return spacy.load(model_name)
    except Exception:
        return None

nlp_sm = _try_load("en_core_web_sm")
if nlp_sm is None:
    # As a last resort, load any available English model name
    nlp_sm = _try_load("en_core_web_md") or _try_load("en_core_web_lg")
    if nlp_sm is None:
        # Fallback to blank English if no model is present (to avoid hard crash)
        nlp_sm = spacy.blank("en")

# Prefer lg, otherwise md, otherwise reuse sm
nlp_lg = _try_load("en_core_web_lg") or _try_load("en_core_web_md") or nlp_sm

def analyze_text(text):
    words = []
    hrases = []
    
    doc = nlp_sm(text)
    query = nlp_sm("Jammingbot")
    similarities = {}
    for token in doc:
        if token.has_vector and query.has_vector:
            similarity = query.similarity(token)
            if similarity > 0:  # Фильтрация значений, близких к нулю
                similarities[token.text] = similarity
    
    sorted_similarities = sorted(similarities.items(), 
                                key=lambda x: x[1], 
                                reverse=True)   
            
    for word, similarity in sorted_similarities[0:13]:
        words.append(word)        

    #
    # Analyze noun hrases
    #
    doc = nlp_lg(text)
    noun_hrases =  [chunk.text for chunk in doc.noun_chunks]            
    for i in noun_hrases[0:13]:
        hrases.append(i)
            
    return words, hrases



def analyze_sorted_similarity_app(text):
    words = []    
    doc = nlp_sm(text)
    query = nlp_sm("Jammingbot")
    similarities = {}
    for token in doc:
        if token.has_vector and query.has_vector:
            similarity = query.similarity(token)
            if similarity > 0:  # Фильтрация значений, близких к нулю
                similarities[token.text] = similarity
    
    sorted_similarities = sorted(similarities.items(), 
                                key=lambda x: x[1], 
                                reverse=True)   
                
    for word, similarity in sorted_similarities[0:13]:
        words.append(word)
    return words
