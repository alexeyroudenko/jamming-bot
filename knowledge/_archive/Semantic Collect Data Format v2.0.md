---
title: Semantic Collect Data Format v2.0
note_type: ref
tags:
  - ref
  - semantic
  - data
  - format
research_notes: "[[GROK Semantic Collect Data Format v2.0]]"
---

```json
{
  "original_text": "Jammingbot is a fantasy about a post-apocalyptic future, when the main functions of the Internet and assistant bots are defeated and only one self-replicating bot remains, aimlessly plowing the Internet. This is a bot that has no goal, only a path.",
  "num_sentences": 2,
  "sentences": [
    {
      "sentence_id": 0,
      "text": "Jammingbot is a fantasy about a post-apocalyptic future, when the main functions of the Internet and assistant bots are defeated and only one self-replicating bot remains, aimlessly plowing the Internet.",
      "noun_phrases": [
        "Jammingbot",
        "a fantasy",
        "a post-apocalyptic future",
        "the main functions",
        "the Internet",
        "assistant bots",
        "only one self-replicating bot",
        "the Internet"
      ],
      "verbs": ["be", "defeat", "remain", "plow"],
      "entities": [
        {"text": "Jammingbot", "label": "PERSON"},
        {"text": "Internet", "label": "PRODUCT"},
        {"text": "Internet", "label": "PRODUCT"}
      ],
      "svo_triples": [
        {"subject": "Jammingbot", "verb": "be", "object": "a fantasy"},
        {"subject": "functions", "verb": "defeat", "object": null},
        {"subject": "bot", "verb": "remain", "object": null},
        {"subject": "bot", "verb": "plow", "object": "Internet"}
      ],
      "dependencies": [ ... ]   // список из ~45 зависимостей с lemma, pos, dep, head
    },
    {
      "sentence_id": 1,
      "text": "This is a bot that has no goal, only a path.",
      "noun_phrases": [
        "a bot",
        "no goal",
        "only a path"
      ],
      "verbs": ["be", "have"],
      "entities": [],
      "svo_triples": [
        {"subject": "This", "verb": "be", "object": "a bot"},
        {"subject": "bot", "verb": "have", "object": "goal"}
      ],
      "dependencies": [ ... ]
    }
  ],
  "global": {
    "all_noun_phrases": [
      "Jammingbot",
      "a fantasy",
      "a post-apocalyptic future",
      "the main functions",
      "the Internet",
      "assistant bots",
      "only one self-replicating bot",
      "a bot",
      "no goal",
      "only a path"
    ],
    "all_verbs": ["be", "defeat", "remain", "plow", "have"],
    "main_subjects": ["Jammingbot", "bot", "This", "functions"],
    "key_phrases": [
      "Jammingbot",
      "a fantasy",
      "a post-apocalyptic future",
      "the Internet",
      "only one self-replicating bot",
      "no goal",
      "only a path"
    ]
  },
  "mood": "melancholic-philosophical",
  "self_referential_score": 0.75,
  "themes": [
    "post-apocalypse",
    "last_remaining_bot",
    "path_without_goal",
    "digital_ruins"
  ]
}
```