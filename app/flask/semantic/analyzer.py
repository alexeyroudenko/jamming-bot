#
#
#

# import spacy

# def analyze_text(text):
#     words = []
#     hrases = []
#     import spacy
#     nlp = spacy.load("en_core_web_sm")
#     doc = nlp(text)
#     query = nlp("Jammingbot")
#     similarities = {}
#     for token in doc:
#         if token.has_vector and query.has_vector:
#             similarity = query.similarity(token)
#             if similarity > 0:  # Фильтрация значений, близких к нулю
#                 similarities[token.text] = similarity
    
#     sorted_similarities = sorted(similarities.items(), 
#                                 key=lambda x: x[1], 
#                                 reverse=True)   
                
#     # self_job.meta['sorted_similarities'] = sorted_similarities
#     # print(f"similarity сwith'{query.text}':")
#     for word, similarity in sorted_similarities[0:13]:
#         #print(f"{word}: {similarity:.2f}")
#         words.append(word)        

#     #
#     # Analyze noun hrases
#     #
#     import spacy
#     nlp = spacy.load("en_core_web_lg")
#     doc = nlp(text)
#     noun_hrases =  [chunk.text for chunk in doc.noun_chunks]            
#     for i in noun_hrases[0:13]:
#         hrases.append(i)
            
#     return words, hrases




# def analyze_sorted_similarity_app(text):
#     words = []
#     import spacy
#     nlp = spacy.load("en_core_web_sm")
#     doc = nlp(text)
#     query = nlp("Jammingbot")
#     similarities = {}
#     for token in doc:
#         if token.has_vector and query.has_vector:
#             similarity = query.similarity(token)
#             if similarity > 0:  # Фильтрация значений, близких к нулю
#                 similarities[token.text] = similarity
    
#     sorted_similarities = sorted(similarities.items(), 
#                                 key=lambda x: x[1], 
#                                 reverse=True)   
                
#     # self_job.meta['sorted_similarities'] = sorted_similarities
#     # print(f"similarity сwith'{query.text}':")
#     for word, similarity in sorted_similarities[0:13]:
#         #print(f"{word}: {similarity:.2f}")
#         words.append(word)
#     return words
