from fastapi import APIRouter, Query, HTTPException
from typing import List
from app.schemas.location import (
    PlaceResult,
    LocationSearchResponse,
    LocationSearchRequest,
    LocationResolveRequest,
    CoordTimezoneRequest,
    CoordTimezoneResponse
)
from app.services.location.location_service import LocationService

router = APIRouter()
_location_service = LocationService()

@router.get("/search", response_model=LocationSearchResponse)
async def search_locations_get(q: str = Query(..., min_length=2)):
    """Place autocomplete search endpoint (GET)."""
    results = await _location_service.search_locations(q)
    return LocationSearchResponse(results=results)

@router.post("/search", response_model=LocationSearchResponse)
async def search_locations_post(req: LocationSearchRequest):
    """Place autocomplete search endpoint (POST)."""
    results = await _location_service.search_locations(req.query)
    return LocationSearchResponse(results=results)

@router.post("/resolve", response_model=PlaceResult)
async def resolve_location(req: LocationResolveRequest):
    """Resolves a query string to a canonical PlaceResult."""
    results = await _location_service.search_locations(req.query)
    if results:
        return results[0]
    raise HTTPException(status_code=404, detail=f"No matching place found for query '{req.query}'")

@router.post("/resolve-coords", response_model=CoordTimezoneResponse)
async def resolve_coordinates_timezone(req: CoordTimezoneRequest):
    """Resolves IANA timezone ID from latitude and longitude."""
    tz_id = _location_service.resolve_timezone_from_coords(req.latitude, req.longitude)
    return CoordTimezoneResponse(
        latitude=req.latitude,
        longitude=req.longitude,
        timezone_id=tz_id
    )
