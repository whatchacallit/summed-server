from typing import List
from app.api_models import NamedEntity, Sentence
import os, json, logging, tempfile
import requests


# Azure Text Analytics
from azure.core.credentials import AzureKeyCredential
from azure.ai.textanalytics import TextAnalyticsClient

# Sumy summarizer
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer

# from sumy.summarizers.lsa import LsaSummarizer as Summarizer
# from sumy.summarizers.text_rank import TextRankSummarizer as Summarizer
from sumy.summarizers.lex_rank import LexRankSummarizer as Summarizer

# simple language detector
from langdetect import detect as detect_language


# Init logging
import logging

log = logging.getLogger(__name__)

# Spacy and lang models
import spacy

# Languages should be only instatiated once per process, so we keep them here...
SPACY_LANGUAGE_INSTANCES = {}


class TextAnalyzer(object):

    text: str = None
    language: str = None
    model: str = None

    _azure_ta4h_endpoint: str = None
    _azure_ta4h_apikey: str = None

    def __init__(self, text: str, language: str, model: str):
        self.text = text
        self._azure_ta4h_endpoint = os.getenv("AZURE_TEXT_ANALYTICS_ENDPOINT")
        self._azure_ta4h_apikey = os.getenv("AZURE_TEXT_ANALYTICS_KEY")

        self.language = language
        self.model = model

    def __call__(self):
        model_name = self._getSpacyModelName()
        nlp = self._getSpacyLanguage(model_name)

        return nlp

    #
    # manages SPACY_LANGUAGE_INSTANCES (e.g. spacy.Language singletons).
    # This makes sure loaded spacy.Language models are reused
    #
    def _getSpacyLanguage(self, model_name: str) -> spacy.Language:
        if not SPACY_LANGUAGE_INSTANCES.get(model_name):
            log.info(f"Loading languge model: '{model_name}' ...")
            SPACY_LANGUAGE_INSTANCES[model_name] = spacy.load(model_name)

        log.info(f"Using language model: '{model_name}' ...")
        return SPACY_LANGUAGE_INSTANCES[model_name]

    #
    # Construct the correct  spaCy model name to use with spacy.load(...)
    # if language None or "detect": detect&set the language based on 'text. Else: use self.language
    # if model None or "default": use available default models (like 'xx_core_news_sm')  , else use self.model
    #
    def _getSpacyModelName(self):
        if not self.language or self.language.lower() == "detect":
            # Detect most probable laguage code from input text
            self.language = detect_language(self.text)[:2].lower()
        if not self.model or self.model.lower() == "default":
            if self.language == "en":
                self.model = "core_web_sm"
            else:
                self.model = "core_news_sm"

        # At this point we should have a valid, two-char language code, plus a 'model' shortname.
        # For default spaCy languages, just join them together, e.g. "de_core_news_sm"
        # TODO for our specialized languages, we may do something differently here (e.g. resolve to a path)
        name = f"{self.language}_{self.model}"
        return name

    #
    # Calls Azure Text Analytics for health on the input text.
    # Note: This is a poentially longrunning operation
    #
    def _azure_text_analytics_for_health(self, text: str, language: str = "en"):

        # client = TextAnalyticsClient(
        #    self._azure_ta4h_endpoint, AzureKeyCredential(self._azure_ta4h_apikey)
        # )
        # response = client.recognize_entities([text], language=language)
        headers = {}
        url = (
            f"{self._azure_ta4h_endpoint}/text/analytics/v3.1-preview.4/entities/health"
        )
        resp = requests.post(
            url,
            headers=headers,
            json={"documents": [{"id": 0, "language": language, "text": text}]},
        )
        resp.raise_for_status()
        result = []
        if resp.ok:
            docs = resp.json()["documents"]
            result = [doc for doc in docs]  # if not doc.is_error

        return result

    #
    # Identifies the "medical" entities, using Azure Text analytics for Health
    #
    def get_health_entities(self, text: str) -> List[NamedEntity]:
        result = self._azure_text_analytics_for_health(text, self.language)

        medical_entities = []

        for doc in result:
            # log.info(json.dumps(doc, indent=4, sort_keys=True))

            for entity in doc["entities"]:

                ne = NamedEntity(
                    text=entity["text"],
                    definition=entity.get("name", ""),
                    start=entity["offset"],
                    end=entity["offset"] + entity["length"],
                    label=entity["category"],
                )
                medical_entities.append(ne)

        return medical_entities

    #
    # Returns the top-n ranked Sentences from the list.
    # Uses the "lemmatized" version of the text
    # Preserves the relative order from within the original document (e.g. it is *not* sorted by score)
    #
    #
    def top_sentences(self, sentences: List[Sentence], num_sentences: int = 5):

        # Create full text from lemmatized sentences.
        # log.info(sentences)
        fulltext = " ".join([s.lemmatized_text for s in sentences])

        # now rank the (lemmatized) sentences, using Sumy.
        # Any tokenizer should (hopefully) work at this point.
        parser = PlaintextParser.from_string(fulltext, Tokenizer(self.language))
        summarizer = Summarizer()
        ranked_sentences = []
        summary = summarizer(parser.document, num_sentences)

        # go through all the sentences from the original text...
        for original_sentence in sentences:
            # check if the sentence is the summary. If yes, append to
            for summary_sentence in summary:
                if (
                    str(original_sentence.lemmatized_text).strip()
                    == str(summary_sentence).strip()
                ):
                    ranked_sentences.append(original_sentence)
                    break

        return ranked_sentences
