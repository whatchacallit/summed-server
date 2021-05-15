from requests.models import Response
from app.api_models import ExtractResponse
import requests
import newspaper, re

# simple language detector
from langdetect import detect as detect_language


class Extractor(object):
    """
    Class for extracting text etc (ExtractResponse) for URLs.
    """

    def __init__(self) -> None:
        super().__init__()

    def __call__(self, url: str, options: dict = {}) -> ExtractResponse:
        # TODO split up how to load the resource behinf the url.
        # right now, only HTML webpages are supported.
        # should be possible to point to any target media type (pdf etc.).
        # Try to download first, if required
        response = self.extract_webpage(url, options)

        return response

    def extract_webpage(self, url: str, options: dict = {}) -> ExtractResponse:
        """
        Extracts text + metadata from a url pointing to a HTML
        """
        # session = requests.Session()
        # TODO support auth/login through  options {}
        # response = session.get(url)

        # https://newspaper.readthedocs.io/en/latest/

        article = newspaper.Article(url=url)
        article.download()
        article.parse()
        text = article.text

        meta = {}
        language = detect_language(text) or "en"
        doc_class = "article"
        mediatype = "text/html"

        response = ExtractResponse(
            **{
                "sourceUrl": url,
                "language": language,
                "text": text,
                "document_class": doc_class,
                "mediatype": mediatype,
                "metadata": meta,
            }
        )

        return response

    def extract_file_storage(url: str, options: dict = {}) -> ExtractResponse:
        """
        Extract from a file that exists in internal (file) storage,
        e.g has been uploaded there first.
        """
        pass
