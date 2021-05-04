
# Run it locally

# Build & run the docker container





# Building the project from scratch
We use a virtual python environment (under .env) to install spaCy 3.x

1. Setup and install spaCy
```bash
python -m venv venv
source ./venv/Scripts/activate
pip install -U pip setuptools wheel
pip install -U spacy[transformers,lookups]
python -m spacy download en_core_web_sm
python -m spacy download fr_core_news_sm
python -m spacy download de_core_news_sm
```

2. Install other dependencies
```bash
pip install -U fastapi pytest python-dotenv uvicorn black requests requests-file
```

3. freeze the requirements
```bash
pip freeze > requirements.txt
```