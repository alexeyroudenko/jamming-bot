---
title: Semantic dev notes
note_type: dev
project: "[[Jamming Bot]]"
dev_area: research
tags:
  - dev
  - nlp
  - spacy
  - jamming-bot
---

# Semantic dev notes

![[jamming bot - 2024-12-26.mp4]]

## Keywords

```python
import spacy
from collections import Counter

nlp = spacy.load("en_core_web_lg")
doc = nlp(text)
keywords = [token.text.lower() for token in doc if token.pos_ in ["NOUN", "ADJ"] and not token.is_stop]
keyword_counts = Counter(keywords)

print("Top-5 Keywords:")
print(keyword_counts.most_common(5))
```

Top-5 Keywords: `[('internet', 6), ('bot', 4), ('bots', 3), ('fantasy', 2), ('post', 2)]`

## Similarities

```python
import spacy

nlp = spacy.load("en_core_web_sm")
doc = nlp(bot_text)
query = nlp("Jammingbot")
similarities = {}

for token in doc:
    if token.has_vector and query.has_vector:
        similarity = query.similarity(token)
        if similarity > 0:
            similarities[token.text] = similarity

sorted_similarities = sorted(similarities.items(), key=lambda x: x[1], reverse=True)

print(f"Similarity with '{query.text}':")
for word, similarity in sorted_similarities[0:30]:
    print(f"{word}: {similarity:.2f}")
```

## Tag grouping

- http://localhost:8080/api/v1/tags/tags/group/

![[Scene03 - Semantic Cloud.png]]

## Phrases and verbs

```python
import spacy

nlp = spacy.load("en_core_web_lg")
doc = nlp(text)
noun_phrases = [chunk.text for chunk in doc.noun_chunks]
noun_phrases_out = []

for phrase in noun_phrases:
    if len(phrase) > 5:
        noun_phrases_out.append(phrase)

print(noun_phrases_out)
print("-------------")
print("Noun phrases:", [chunk.text for chunk in doc.noun_chunks])
print("Verbs:", [token.lemma_ for token in doc if token.pos_ == "VERB"])

for entity in doc.ents:
    print(entity.text, entity.label_)
```

![[jamming_bot_semantic_cloud.png]]

## Spacy dep

```python
import spacy
from spacy import displacy

nlp = spacy.load("en_core_web_sm")
text = "Jammingbot is a concept exploring the remnants of internet functionality in a dystopian future."
doc = nlp(text)
displacy.serve(doc, style="dep")
```

![[jamming_bot_semantic_cloud_spacy_dep.png]]

## Spacy ent

```python
import spacy
from spacy import displacy

nlp = spacy.load("en_core_web_lg")
doc = nlp(bot_text)
displacy.serve(doc, style="ent")
```

![[jamming_bot_semantic_cloud_spacy_ent.png]]
