from pydantic import BaseModel, Field
from typing import Optional


class SourceItem(BaseModel):
    document: str
    chunk_id: int
    page:     int
    text:     str
    score:    float


class AgentResponse(BaseModel):
    success:             bool
    action:              str
    answer:              str
    sources:             list[SourceItem] = []
    confidence:          str
    needs_clarification: bool
    message:             Optional[str]    = None
    session_id:          Optional[str]    = None


class UploadResponse(BaseModel):
    success:        bool
    filename:       str
    chunks_created: int
    pages_parsed:   int
    message:        str
    warnings:       list[str] = []
