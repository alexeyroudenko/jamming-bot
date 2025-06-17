import json
import re
from collections import Counter

def load_keywords(file_path):
    """Загружает словарь ключевых слов из JSON-файла."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def classify_text_by_keywords(text, keyword_dict):
    """
    Классифицирует текст по темам на основе подсчёта ключевых слов.
    Возвращает тему с наибольшим количеством совпадений.
    """
    # Нормализация текста: убираем пунктуацию и приводим к нижнему регистру
    text = re.sub(r'[^\w\s]', '', text.lower())
    words = text.split()
    
    # Подсчитываем совпадения для каждой темы
    topic_scores = {topic: 0 for topic in keyword_dict}
    for word in words:
        for topic, keywords in keyword_dict.items():
            if word in keywords:
                topic_scores[topic] += 1
    
    # Находим тему с максимальным счётом
    max_score = max(topic_scores.values())
    if max_score == 0:
        return "Undefined topic"
    
    # Возвращаем тему (или темы, если несколько с одинаковым счётом)
    predicted_topics = [topic for topic, score in topic_scores.items() if score == max_score]
    return predicted_topics[0] if len(predicted_topics) == 1 else predicted_topics[1]