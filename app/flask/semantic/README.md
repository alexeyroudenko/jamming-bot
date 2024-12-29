# Semantic
```
pip install -U spacy &
python -m spacy download en_core_web_sm &
python -m spacy download en_core_web_lg
```

## API
Feature | Type | Route | Access
------------ | ------------- | ------------- | -------------
Get all        | POST | http://localhost:5000/spacy/ | Public
Get POST Vars | POST | http://localhost:5000/semantic/vars/ | Public
Add a new article | POST | http://localhost:5000/semantic/ent/ | Public
Update an article | POST | http://localhost:5000/semantic/keywords/ | Public
Delete an article | POST | http://localhost:5000/semantic/phrases_verbs/ | Public
Get Similarities | POST | http://localhost:5000/semantic/similarities/ | Public

### Data art
https://huggingface.co/datasets/jtatman/orca_mini_uncensored_squad_format_train/viewer
