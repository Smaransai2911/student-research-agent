from pydantic import BaseModel, Field
from typing import Optional


class QueryRequest(BaseModel):
    session_id: str           = Field(..., min_length=1, max_length=128)
    query:      str           = Field(..., min_length=1, max_length=2000)
    mode:       Optional[str] = Field(default=None)
    model_config = {"str_strip_whitespace": True}
