from typing import List
from warnings import simplefilter
from app.api_models import NamedEntity, Sentence
import os, json, logging, tempfile, re
import requests
from pprint import pprint

from fuzzywuzzy import fuzz


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

        headers = {}
        url = (
            f"{self._azure_ta4h_endpoint}/text/analytics/v3.1-preview.4/entities/health"
        )

        chunk_size = 5120
        chunks = [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]
        doc_array = [
            {"id": idx, "language": language, "text": chunk}
            for idx, chunk in enumerate(chunks)
        ]

        json_doc = {"documents": doc_array}
        log.info("Calling Azure Text Analytics for Health (TA4H)...")
        resp = requests.post(
            url,
            headers=headers,
            json=json_doc,
        )
        resp.raise_for_status()
        log.info("done.")

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
    # Test URL: https://www.bcpp.org/resource/african-american-women-and-breast-cancer/
    #
    def top_sentences(
        self, sentences: List[Sentence], num_sentences: int = 5, useLemma: bool = True
    ) -> List[Sentence]:

        text_sents = [s.text for s in sentences]
        lemma_sents = [l.lemmatized_text for l in sentences]

        ranked_sentences = []

        # pprint(sentences)

        summarizer = Summarizer()

        if not useLemma:
            doc = "\n".join(text_sents)

            # TODO custom sumy DocumentParser ?
            parser = PlaintextParser.from_string(doc, Tokenizer(self.language))

            summary = summarizer(parser.document, num_sentences)

            for summary_sentence in summary:
                for original in sentences:
                    if str(summary_sentence).strip() == original.text.strip():
                        ranked_sentences.append(original)
                        break
        else:
            #  spaCy and Sumy use different tokenizers, so they may do sentencizing slightly differently.
            #  When we compare "lemmatized" versions, they may not match 1:1 because of that,
            #  so unless we do a Sumy Parser implementation using the spaCy token/sentences
            # we may need to do a "fuzzy" match to find the original sentence with the "lemma" matching the summary sentence
            # "lemma"
            #

            doc = "\n".join(lemma_sents)
            parser = PlaintextParser.from_string(doc, Tokenizer(self.language))
            summary = summarizer(parser.document, num_sentences)

            for lemma_sentence in summary:
                for original in sentences:
                    summary_lemma = str(lemma_sentence).strip()
                    original_lemma = original.lemmatized_text.strip()
                    similarity = fuzz.ratio(summary_lemma, original_lemma)
                    # pprint(similarity)
                    if similarity >= 80:
                        ranked_sentences.append(original)
                        break

        if len(ranked_sentences) < num_sentences:
            log.warn(
                f"Only {len(ranked_sentences)} of {num_sentences} sentences ranked."
                "Text too short, or mismatching sentencizer (sumy/spaCy)"
            )

        return ranked_sentences
