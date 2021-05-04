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


class AnalzyeRequest(NLPBaseRequest):
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
                "sentences": [{"text": "Hello again!"}, {"text": "..."}],
            }
        }


class DefinitionResponse(BaseResponse):
    term: str
    definitions: Optional[list]
