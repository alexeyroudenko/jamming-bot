---
title: Semantic Collect Data Format
note_type: ref
tags:
  - ref
  - semantic
  - data
  - format
---

# Semantic Collect Data Format

Рабочая заметка о формате семантических данных и промежуточных структур, используемых при анализе текста.
## Берем за основу:
```
Jammingbot is a fantasy about a post-apocalyptic future, when the main functions of the Internet and assistant bots are defeated and only one self-replicating bot remains, aimlessly plowing the Internet. This is a bot that has no goal, only a path.
```
# Noun phrases, Verbs
```
Noun phrases ['Jammingbot', 'a fantasy', 'the theme', 'a post-apocalyptic future', 'the main functions', 'the Internet', 'assistant bots', 'only one self-replicating bot', 'the Internet', 'no goal', 'only a path'] 
Verbs ['defeat', 'replicate', 'remain', 'plow', 'have'] 
Entities [{'PERSON': 'Jammingbot'}, {'CARDINAL': 'only one'}]
```

## Semantic Collect Data Format 
Обновление структуры: [[Semantic Collect Data Format v2.0]]

```json
{
   "noun_phrases":[
      "Jammingbot",
      "a fantasy",
      "the theme",
      "a post-apocalyptic future",
      "the main functions",
      "the Internet",
      "assistant bots",
      "only one self-replicating bot",
      "the Internet",
      "This",
      "a bot",
      "that",
      "no goal",
      "only a path"
   ],
   "verbs":[
      "defeat",
      "replicate",
      "remain",
      "plow",
      "have"
   ],
   "entities":[
      "(""Jammingbot",
      "PERSON"")",
      "(""only one",
      "CARDINAL"")"
   ],
   "keywords":[
      "fantasy",
      "theme",
      "post",
      "-",
      "apocalyptic",
      "future",
      "main",
      "functions",
      "internet",
      "assistant",
      "bots",
      "self",
      "bot",
      "internet",
      "bot",
      "goal",
      "path"
   ],
   "subjects":[
      "Jammingbot",
      "bot",
      "This",
      "that"
   ],
   "objects":[
      "Internet",
      "goal"
   ],
   "dependency":[
		Jammingbot>is
		is>is
		a>fantasy
		fantasy>is
		on>fantasy
		the>theme
		theme>on
		of>theme
		a>future
		post>future
		->future
		apocalyptic>future
		future>of
		,>future
		when>defeated
		the>functions
		main>functions
		functions>defeated
		of>functions
		the>Internet
		Internet>of
		and>functions
		assistant>bots
		bots>defeated
		will>defeated
		be>defeated
		defeated>is
		and>defeated
		only>one
		one>bot
		self>replicating
		->replicating
		replicating>bot
		bot>remain
		will>remain
		remain>defeated
		,>remain
		aimlessly>plowing
		plowing>remain
		the>Internet
		Internet>plowing
		.>is
		This>is
		is>is
		a>bot
		bot>is
		that>has
		has>bot
		no>goal
		goal>has
		,>is
		but>is
		only>path
		a>path
		path>is
		.>is   
	]
}


```

## 1. В Jamming Bot строим граф

Эта заметка фиксирует пример формата для noun phrases, verbs, entities, keywords и dependency-связей, которые затем могут использоваться в [[jamming-bot/Jamming Bot|Jamming Bot]] как входные данные для визуализации и семантической обработки.
[[Scene 2. Dependency Parsing]]
## Есть такое
```
Jammingbot>is
is>is
a>fantasy
fantasy>is
on>fantasy
the>theme
theme>on
of>theme
a>future
post>future
->future
apocalyptic>future
future>of
,>future
when>defeated
the>functions
main>functions
functions>defeated
of>functions
the>Internet
Internet>of
and>functions
assistant>bots
bots>defeated
will>defeated
be>defeated
defeated>is
and>defeated
only>one
one>bot
self>replicating
->replicating
replicating>bot
bot>remain
will>remain
remain>defeated
,>remain
aimlessly>plowing
plowing>remain
the>Internet
Internet>plowing
.>is
This>is
is>is
a>bot
bot>is
that>has
has>bot
no>goal
goal>has
,>is
but>is
only>path
a>path
path>is
.>is
```

[[Semantic Collect Data Format v2.0]]