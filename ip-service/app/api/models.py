from pydantic import BaseModel, Field


class GeoOut(BaseModel):
    ip: str = ""
    city: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    error: str = ""
