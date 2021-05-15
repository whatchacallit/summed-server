from typing import List, Optional
from fastapi.datastructures import UploadFile
from pydantic.main import BaseModel
from enum import Enum


class TextSpan(BaseModel):
    text: str
    start: int
    end: int


class NamedEntity(TextSpan):
    label: str  # The (predicted) label of the text span
    definition: Optional[str] = None  # A short description


class NounChunk(TextSpan):
    definition: Optional[str] = None


class Lemma(BaseModel):
    text: str
    is_stopword: Optional[bool] = None


class Sentence(TextSpan):
    text: str
    lemmatized_text: Optional[str]
    score: Optional[float] = None


#
# Request Models (= schema for API requests)
#
class BaseRequest(BaseModel):
    verbose: Optional[bool] = None
    metadata: Optional[dict] = None


class NLPBaseRequest(BaseRequest):
    language: Optional[str] = None
    model: Optional[str] = None
    text: str


class SentenceRequest(NLPBaseRequest):
    pass


class AnalyzeRequest(NLPBaseRequest):
    num_sentences: Optional[int] = 3

    class Config:
        schema_extra = {
            "example": {
                "text": "Breast cancer most commonly presents as a lump that feels different from the rest of the breast tissue.\
More than 80% of cases are discovered when a person detects such a lump with the fingertips.",
            }
        }


#
# Response Models (= schema for API responses)
#
class BaseResponse(BaseModel):
    error: Optional[str]


class TranslateResponse(BaseModel):
    """
    Response for a text translation request
    """

    from_language: str
    from_text: str
    to_language: str
    to_text: str


class NLPBaseResponse(BaseResponse):
    language: Optional[str]
    model: Optional[str]
    text: Optional[str]


class AnalyzeResponse(NLPBaseResponse):
    entities: Optional[List[NamedEntity]] = None
    health_entities: Optional[List[NamedEntity]] = None

    # entities_text: Optional[List[str]]
    noun_chunks: Optional[List[NounChunk]] = None
    # noun_chunks_text: Optional[List[str]]
    sentences: Optional[List[Sentence]] = None
    top_sentences: Optional[List[Sentence]] = None

    # lemma: Optional[List[Lemma]]
    # lemmatized_text: Optional[str]

    class Config:
        schema_extra = {
            "example": {
                "language": "en",
                "model": "core_web_sm",
                "text": "Hello again! The quick brown fox jumps over the lazy dog. A second time !",
                "entities": [],
                "health_entities": [{"text": "..."}],
                "sentences": [{"text": "Hello again!"}],
            }
        }


class ImmersiveReaderTokenResponse(BaseResponse):
    token: str
    subdomain: str


class TermDefinition(BaseModel):
    id: str
    term: str
    type: str
    text: str


class DefinitionResponse(BaseResponse):
    term: str
    definitions: Optional[List[TermDefinition]]


class RenderRequest(AnalyzeResponse):
    """
    Request to renders the result a previous "analyze" response  into an output format, such as HTML/...

    """

    format: Optional[str] = "html"


class Page(BaseModel):
    """
    A related webpage

    - **title** Title of the web page
    - **text** Text (usually a summary)
    - **url** The web address
    """

    title: str
    text: str
    url: str


class Image(BaseModel):
    """
    An Image Url

    - **text** Short text/ description of the image
    - **url** The web address
    - **hostPageUrl** The web address of the webpage that hosts the image
    - **webSearchUrl** The web adress to do a Microsoft Bing "similarity" search
    """

    text: str
    url: str
    hostPageUrl: str
    thumbnailUrl: str
    webSearchUrl: str


class Video(BaseModel):
    """
    An Video Url

    - **text** Short text/ description of the video
    - **url** The web address
    - **hostPageUrl** The web address of the webpage that hosts the video
    - **webSearchUrl** The web adress to do a Microsoft Bing "similarity" search
    """

    text: str
    url: str
    hostPageUrl: str
    thumbnailUrl: str
    webSearchUrl: str


class SearchResponse(BaseModel):
    """
    Search responses, contain pages, images and videos

    - **pages** List of (web) pages
    - **images** List of images
    - **videos** List of videos
    """

    pages: Optional[List[Page]]
    images: Optional[List[Image]]
    videos: Optional[List[Video]]
