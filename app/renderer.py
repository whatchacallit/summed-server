from typing import List
from app.api_models import AnalyzeResponse, NamedEntity, Sentence
import os, json, logging, tempfile
import requests

from jinja2 import Template

# Init logging
import logging

log = logging.getLogger(__name__)

# Spacy and lang models
import spacy


class HTMLRenderer(object):
    def __call__(self, analysis: AnalyzeResponse) -> str:

        # with open('renderer.html.jinja') as f:
        #    template = Template(f.read())
        entities = analysis.entities
        tagged_text = analysis.text

        already_replaced = []
        for e in entities:

            if not e.text in already_replaced:
                tagged_text = tagged_text.replace(
                    e.text, f"<span alt='{e.label}' class='{e.label}'>{e.text}</span>"
                )
                already_replaced.append(e.text)
        log.info(tagged_text)
        template = Template(
            f"""
            <div id='myId' class='summed_text_container'>
            {tagged_text}
            </div>
        """
        )
        html = template.render(analysis)
        return html  # super().__call__(*args, **kwds)
