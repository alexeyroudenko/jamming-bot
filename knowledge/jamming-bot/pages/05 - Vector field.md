---
title: Vector field
note_type: web_entry
web_type: page
project: "[[jamming-bot/Jamming Bot]]"
parent: "[[pages/_index|Jamming Bot Pages Index]]"
url: https://jamming-bot.arthew0.online/tags/vectorfield/
tags:
  - web
  - page
  - vectorfield
  - tags
  - jamming-bot
---

# Vector field

## URL

https://jamming-bot.arthew0.online/tags/vectorfield/

## Описание

В этом режиме теги и частицы собираются в поле направлений, где данные ведут себя как поток и локальная динамика. Визуализация превращает семантику в почти физическую среду, которую можно деформировать, наблюдать и переживать как движение.

## Алгоритм


Vector field использует не отдельный dataset, а текущий поток тегов проекта. 
Страница берёт теги через
`GET /api/tags/get/`,
затем отправляет их в 
`POST /api/tags/embeddings/`,
 где Flask строит компактное представление на базе spaCy-векторов.

### Как это работает

1. UI загружает список тегов и ограничивает число якорных слов.
2. Backend очищает список: убирает пустые значения, дубликаты и обрезает массив до `max_words`.
3. Для каждого слова Flask вызывает `en_core_web_md` и проверяет, есть ли у токена вектор.
4. Если векторов достаточно, API возвращает:
   - `vectors2d` — первые две нормализованные координаты вектора
   - `vectors3d` — первые три нормализованные координаты
   - `links` — связи между словами с высокой `similarity`
5. На фронте эти слова становятся `anchors`, а поле скорости для частиц считается как смесь:
   - процедурного шума
   - локального влияния anchor points
6. Если векторов мало, включается fallback-режим с синтетическими координатами, чтобы визуализация всё равно жила.

### API-слой

`/tags/vectorfield/` использует тот же embeddings API, что и другие tag-визуализации, но интерпретирует результат не как граф, а как поле направлений.

```python
def build_embeddings_response(words, *, max_words=48, min_sim=0.38, max_links=160):
    # Clean list and keep only unique tags.
    # If spaCy vectors are available, return vectors2d/vectors3d + similarity links.
    # Otherwise, fall back to synthetic coordinates.
```

### Ключевая часть backend

```python
for d in docs:
    v = d.vector
    norm = float(d.vector_norm)
    x = float(v[0]) / norm if norm else 0.0
    y = float(v[1]) / norm if norm else 0.0
    z = float(v[2]) / norm if norm else 0.0
    vectors2d.append([x, y])
    vectors3d.append([x, y, z])
```

Это не UMAP и не t-SNE, а прямой нормализованный срез первых компонент spaCy-вектора. За счёт этого режим работает быстро и может пересобираться почти в реальном времени.

### Ключевая часть frontend

```javascript
function fieldAt(x, y, t) {
  var fx = noise2(y, x * 0.5, t) * 0.55;
  var fy = noise2(x, y + 3, t + 1) * 0.55;
  // Then anchors bend the field locally.
  return { x: fx, y: fy };
}
```

Именно здесь семантические anchors начинают вести себя как источники локального потока. Поэтому visual mode воспринимается не как статичная схема тегов, а как живая среда, где значения дрейфуют и влияют на траектории частиц.


