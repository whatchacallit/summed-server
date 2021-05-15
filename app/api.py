# Basic imports
from app import bing_search, cognitive_services, dictionary
from app.renderer import HTMLRenderer
import os, logging, tempfile
from typing import List, Text
from dotenv import load_dotenv, find_dotenv
import requests
from urllib.parse import urlencode


# Init logging
import logging


# FastAPI, Starlette, Pydantic etc...
import fastapi
from fastapi import FastAPI
from fastapi.datastructures import UploadFile
from fastapi.params import File
from fastapi.exceptions import HTTPException
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse

# Spacy and lang models
import spacy


from app.textanalyzer import TextAnalyzer
from app.utils import init_api

from app.bing_search import bing_search


#
# Import the API models (request / response models for API calls)
#
from app.api_models import (
    ImmersiveReaderTokenResponse,
    Lemma,
    AnalyzeRequest,
    AnalyzeResponse,
    DefinitionResponse,
    NamedEntity,
    NounChunk,
    RenderRequest,
    SearchResponse,
    Sentence,
    TranslateResponse,
)


log = logging.getLogger(__name__)


# If running in an (AKS) cluster...
prefix = os.getenv("CLUSTER_ROUTE_PREFIX", "").rstrip("/")


#
# Based on a text, language and model name, construct the name of the loadable spacy Language (e.g. "en_core_web_sm")
#


api = FastAPI(
    title="SumMed API Server",
    version="v1",
    description="SumMed is an open-source solution to make medical documents easier to understand for patients, healthcare workers and others. \
        Using FastAPI, spaCy, Azure Cloud services and selected open source NLP components and models.",
    openapi_prefix=prefix,
)

# Configure CORS, logging etc.
init_api(api, log)


#
# / gets redirected to API docs
#
@api.get("/", include_in_schema=False)
async def docs_redirect():
    log.info("Redirecting / to openAPI /docs ")
    return RedirectResponse(f"docs")


@api.get(
    "/translate",
    description="Translate text into a target language.",
    response_model=TranslateResponse,
    tags=["text_analysis"],
)
async def get_translate(text: str, to: str = "de") -> TranslateResponse:
    result = await cognitive_services.translate(text=text, to=to)

    return result


@api.get(
    "/immersive_reader_token",
    description="Retrieve an authorization token for the Microsoft Immersive Reader UI component.",
    response_model=ImmersiveReaderTokenResponse,
    tags=["frontend"],
)
async def get_ir_token() -> ImmersiveReaderTokenResponse:
    result = await cognitive_services.getIRToken()

    return result


@api.post(
    "/render",
    description="Render an Analysis response into HTML",
    response_class=HTMLResponse,
    tags=["frontend"],
)
async def post_render(request: RenderRequest) -> HTMLResponse:
    renderer = HTMLRenderer()
    return renderer(request)


@api.post(
    "/analyze",
    description="Extract the named entities from a input text",
    response_model=AnalyzeResponse,
    tags=["text_analysis"],
)
async def post_analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    language, text, model, num_sentences = map(
        dict(request).get, ("language", "text", "model", "num_sentences")
    )

    analyzer = TextAnalyzer(text, language, model)
    nlp = analyzer()

    analyzed_text = text.strip()  # .replace("\n", " ")

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
        for sentence in doc.sents  # TODO check if we can improve the default spaCy sentencizer
    ]

    # Get the top-n sentences (the "summary")
    top_sentences = analyzer.top_sentences(sentences, num_sentences=num_sentences)

    response = AnalyzeResponse(
        language=analyzer.language or None,
        model=analyzer.model or None,
        text=analyzed_text,
        entities=entities or None,
        # lemmatized_text=lemma_text or None,
        # entities_text=entities_text or None,
        # noun_chunks=noun_chunks or None,
        # noun_chunks_text=noun_chunks_text or None,
        # sentences=sentences or None,
        top_sentences=top_sentences or None
        # lemma=lemma or None,
    )

    return response


@api.get(
    "/search",
    response_model=SearchResponse,
    summary="Search for related medical documents",
    description="Search for medical documents related to a search query string. May find webpages, images and videos.",
    response_description="The search results",
    tags=["search"],
)
async def get_search(q: str) -> SearchResponse:
    try:
        response = bing_search.search(q)
    except Exception as e:
        log.error(str(e))
        message = f"Error calling search services for '{q}'"
        raise HTTPException(500, message)

    return response


#
# Get a definition for a medical term, using a medical dictionary
#
@api.get(
    "/definition",
    description="Lookup a medical term in the Merriam-Webster medical dictionary. ",
    response_model=DefinitionResponse,
    tags=["search"],
)
async def get_definition(term: str) -> DefinitionResponse:

    try:
        response = dictionary.lookup_term(term)
        return response

    except Exception as e:
        log.error(e)
        message = f"Error querying dictionary for '{term}'"
        raise HTTPException(500, message)


# Export
API_V1 = api