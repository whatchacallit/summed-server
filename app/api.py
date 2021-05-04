# Basic imports
import os, json, logging, tempfile
from typing import List, Text
from dotenv import load_dotenv, find_dotenv
import requests
from urllib.parse import urlencode


# Init logging
import logging

log = logging.getLogger(__name__)


# FastAPI, Starlette, Pydantic etc...
import fastapi
from fastapi import FastAPI
from fastapi.datastructures import UploadFile
from fastapi.params import File
from fastapi.exceptions import HTTPException
from starlette.responses import RedirectResponse

# Spacy and lang models
import spacy


from app.textanalyzer import TextAnalyzer


#
# Import the API models (request / response models for API calls)
#
from app.api_models import (
    BaseResponse,
    Lemma,
    AnalzyeRequest,
    AnalyzeResponse,
    DefinitionResponse,
    NamedEntity,
    NounChunk,
    Sentence,
)


# If running in an (AKS) cluster...
prefix = os.getenv("CLUSTER_ROUTE_PREFIX", "").rstrip("/")


#
# Based on a text, language and model name, construct the name of the loadable spacy Language (e.g. "en_core_web_sm")
#


api = FastAPI(
    title="SumMed API",
    version="v1",
    description="SumMed is an open-source solution to make medical documents easier to understand for patients, healthcare workers and others. \
        Based on FastAPI, spaCy, Azure Cloud services and best-of-breed open source NLP components and models.",
    openapi_prefix=prefix,
)

#
# / gets redirected to API docs
#
@api.get("/", include_in_schema=False)
async def docs_redirect():
    log.info("Redirecting / to openAPI /docs ")
    return RedirectResponse(f"docs")


@api.post(
    "/entities",
    description="Extract the named entities from a input text",
    response_model=AnalyzeResponse,
)
async def get_entities(request: AnalzyeRequest) -> AnalyzeResponse:
    language, text, model, num_sentences = map(
        dict(request).get, ("language", "text", "model", "num_sentences")
    )

    analyzer = TextAnalyzer(text, language, model)
    nlp = analyzer()

    analyzed_text = text.strip().replace("\n", " ")

    # Calls the spaCy NLP pipeline
    doc = nlp(analyzed_text)

    #
    # Named entities identify "things", like organisations, quantities
    #
    entities = [
        NamedEntity(
            text=entity.text,
            start=entity.start_char,
            end=entity.end_char,
            label=entity.label_,
        )
        for entity in doc.ents
    ]
    entities_text = [entity.text for entity in doc.ents]
    entities_text.sort()

    #
    # Named Entities found from Azure Text Analytics for Health (if configured)
    #
    entities_medical = analyzer.get_health_entities(analyzed_text)
    entities = entities_medical

    # Noun chunks with their position in the original text.
    # These are usually good keywords e.g. for a custom web search.
    noun_chunks = [
        NounChunk(text=chunk.text, start=chunk.start_char, end=chunk.end_char)
        for chunk in doc.noun_chunks
    ]
    noun_chunks_text = [chunk.text for chunk in doc.noun_chunks]
    noun_chunks_text.sort()

    lemma = [Lemma(text=token.lemma_, is_stopword=token.is_stop) for token in doc]
    lemma_text = " ".join([token.lemma_ for token in doc if not token.is_stop])

    # Sentences detected by the sentencizer.
    # We will use the "lemmatized" sentence without stopwords for the ranking
    #
    sentences: List[Sentence] = [
        Sentence(
            text=sentence.text,
            lemmatized_text=" ".join(
                [token.lemma_ for token in sentence if not token.is_stop]
            ),
            start=sentence.start_char,
            end=sentence.end_char,
        )
        for sentence in doc.sents
    ]

    # Get the top-n sentences (the "summary")
    top_sentences = analyzer.top_sentences(sentences, num_sentences=num_sentences)

    response = AnalyzeResponse(
        language=analyzer.language or None,
        model=analyzer.model or None,
        text=analyzed_text,
        # lemmatized_text=lemma_text or None,
        entities=entities or None,
        # entities_text=entities_text or None,
        # noun_chunks=noun_chunks or None,
        # noun_chunks_text=noun_chunks_text or None,
        # sentences=sentences or None,
        top_sentences=top_sentences or None
        # lemma=lemma or None,
    )

    return response


#
# Get a defiition for a medical term, using a medical dictionary
#
@api.get(
    "/definition",
    description="Lookup a medical term in the Merriam-Webster medical dictionary. ",
    response_model=DefinitionResponse,
)
async def get_definition(term: str) -> DefinitionResponse:

    apiKey = os.environ.get("MW_API_KEY", None)
    if not apiKey:
        raise HTTPException(
            500,
            "Server configuration error: please configure a valid API key for querying dictionary",
        )

    sanitized_term = urlencode(term.strip())
    url = f"https://www.dictionaryapi.com/api/v3/references/medical/json/{sanitized_term}?key={apiKey}"

    try:

        resp = requests.get(url)
        if resp.ok:
            jsonResp = resp.json()
            if jsonResp:
                definitions = jsonResp
                if definitions:
                    return DefinitionResponse(term=term, definitions=definitions)

        # Something went wrong
        return DefinitionResponse(
            term=term, definitions=[], error=f"Error looking up term: {resp.text}"
        )

    except Exception as e:
        log.error(str(e))
        message = f"Error querying dictionary for '{term}'"
        return DefinitionResponse(term=term, error=message)


# Export
API_V1 = api