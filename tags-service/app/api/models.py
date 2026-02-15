from pydantic import BaseModel
from typing import List, Optional

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