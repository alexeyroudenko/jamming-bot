


from bs4 import BeautifulSoup, NavigableString, Tag
def get_text_from_html(html):    
    soup = BeautifulSoup(html)
    header = soup.find('header')
    if header:
        header.decompose()
    footer = soup.find('footer')
    if footer:
        footer.decompose()
    text_out = ""
    for header in soup.find_all('h2'):
        nextNode = header
        while True:
            nextNode = nextNode.nextSibling
            if nextNode is None:
                break
            if isinstance(nextNode, NavigableString):
                text_out += nextNode.strip().replace("\n","").replace("\r","")
                break
            if isinstance(nextNode, Tag):
                if nextNode.name in {'h1', 'h2', 'h3', 'h4', 'h5'}:
                    break
                txt = nextNode.get_text(strip=True).strip().replace("\n","").replace("\r","")
                if len(txt) > 0:
                    text_out += nextNode.get_text(strip=True).strip().replace("\n","").replace("\r","")
                    break
                    # return text_out
                    
    if text_out == "":
        paragraphs = [p.get_text() for p in soup.find_all('p')]
        if len(paragraphs) > 0:
            text_out = paragraphs[0]
                            
    return text_out


import spacy

def analyze_text(text):
    words = []
    hrases = []
    import spacy
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(text)
    query = nlp("Jammingbot")
    similarities = {}
    for token in doc:
        if token.has_vector and query.has_vector:
            similarity = query.similarity(token)
            if similarity > 0:  # Фильтрация значений, близких к нулю
                similarities[token.text] = similarity
    
    sorted_similarities = sorted(similarities.items(), 
                                key=lambda x: x[1], 
                                reverse=True)   
                
    # self_job.meta['sorted_similarities'] = sorted_similarities
    # print(f"similarity сwith'{query.text}':")
    for word, similarity in sorted_similarities[0:13]:
        #print(f"{word}: {similarity:.2f}")
        words.append(word)        

    #
    # Analyze noun hrases
    #
    import spacy
    nlp = spacy.load("en_core_web_lg")
    doc = nlp(text)
    noun_hrases =  [chunk.text for chunk in doc.noun_chunks]            
    for i in noun_hrases[0:13]:
        hrases.append(i)
            
    return words, hrases




def analyze_sorted_similarity_app(text):
    words = []
    import spacy
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(text)
    query = nlp("Jammingbot")
    similarities = {}
    for token in doc:
        if token.has_vector and query.has_vector:
            similarity = query.similarity(token)
            if similarity > 0:  # Фильтрация значений, близких к нулю
                similarities[token.text] = similarity
    
    sorted_similarities = sorted(similarities.items(), 
                                key=lambda x: x[1], 
                                reverse=True)   
                
    # self_job.meta['sorted_similarities'] = sorted_similarities
    # print(f"similarity сwith'{query.text}':")
    for word, similarity in sorted_similarities[0:13]:
        #print(f"{word}: {similarity:.2f}")
        words.append(word)
    return words
