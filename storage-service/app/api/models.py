from pydantic import BaseModel
from typing import Optional


class StepIn(BaseModel):
    number: Optional[str] = ''
    url: Optional[str] = ''
    src: Optional[str] = ''
    ip: Optional[str] = ''
    status_code: Optional[str] = ''
    timestamp: Optional[str] = ''
    text: Optional[str] = ''
    city: Optional[str] = ''
    latitude: Optional[str] = ''
    longitude: Optional[str] = ''
    error: Optional[str] = ''
    tags: Optional[str] = ''
    words: Optional[str] = ''
    hrases: Optional[str] = ''
    entities: Optional[str] = ''
    text_length: Optional[str] = ''
    semantic: Optional[str] = ''
    semantic_words: Optional[str] = ''
    semantic_hrases: Optional[str] = ''
    screenshot_url: Optional[str] = ''
    s3_key: Optional[str] = ''


class StepOut(StepIn):
    id: int
