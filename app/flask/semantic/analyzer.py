



import spacy

nlp_sm = spacy.load("en_core_web_sm")
nlp_lg = spacy.load("en_core_web_lg")

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
