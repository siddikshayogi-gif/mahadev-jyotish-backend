from pydantic import BaseModel, Field
from typing import Optional, List

class PlaceResult(BaseModel):
    display_name: str
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    latitude: float
    longitude: float
    timezone_id: str

class LocationSearchRequest(BaseModel):
    query: str

class LocationResolveRequest(BaseModel):
    query: str

class LocationSearchResponse(BaseModel):
    results: List[PlaceResult]

class CoordTimezoneRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)

class CoordTimezoneResponse(BaseModel):
    latitude: float
    longitude: float
    timezone_id: str
