from pydantic import BaseModel, Field
from typing import List, Optional


class TagBulkIn(BaseModel):
    """Массовое добавление тегов с той же семантикой, что POST / (increment count при существующем name)."""
    names: List[str] = Field(default_factory=list, max_length=800)


class TagIn(BaseModel):
    name: str
    count: int    

class TagOut(TagIn):
    id: int

# class TagGetAndUpdate(TagIn):
#     name: Optional[str] = None
#     count: Optional[int] = None
    
class TagUpdate(TagIn):
    name: Optional[str] = None
    count: Optional[int] = None


class TagSyncItem(BaseModel):
    name: str
    count: int = 0


class TagSyncIn(BaseModel):
    items: List[TagSyncItem] = Field(default_factory=list, max_length=2000)