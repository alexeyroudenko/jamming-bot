---
title: Scene 2. Dependency Parsing
note_type: scene
project: "[[jamming-bot/Jamming Bot]]"
order: 2
tags:
  - scene
  - jamming-bot
  - nlp
---

# Scene 2. Dependency Parsing

Связанный формат данных: [[Semantic Collect Data Format]]

Анализ зависимостей раскрывает грамматическую структуру предложения и помогает находить связанные слова и типы отношений между ними. Для проекта это способ извлекать синтаксический смысл из текстовых фрагментов и превращать случайные страницы в осмысленные следы.

## Пример

```python
# https://spacy.io/api/token#children
import spacy
from spacy import displacy

nlp = spacy.load("en_core_web_lg")
doc = nlp(text)

for token in doc:
    print(f"{token.text}>{token.head}")
```

![[displacy.svg]]

![[01.png|230]] ![[02.png|230]] ![[03.png|230]]

![[00.mp4]]

## Контекст сцены

Создание смыслового слепка из случайных фраз и разрозненных фрагментов текста возможно. К этому процессу можно подходить как к извлечению смысловой сущности из остатков человеческого контента, когда цель не в точности высказываний, а в попытке передать общее настроение, атмосферу и впечатление.

- Применение [[Spacy]] для анализа семантических связей: [[Spacy dep]], [[Spacy ent]]

![[jamming bot - 2024-12-26.mp4]]

## English note

Dependency parsing is the process of analyzing grammatical structure in a sentence and identifying related words together with the type of their relationship. It helps reveal syntactic dependencies and is useful for information extraction, machine translation, and sentiment analysis.
