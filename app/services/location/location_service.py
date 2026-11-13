import math
import httpx
from typing import List, Optional
from app.schemas.location import PlaceResult

# Built-in dataset for fast, deterministic, offline-capable place search and exact timezones
BUILTIN_CITIES: List[dict] = [
    {"display_name": "Jaipur, Rajasthan, India", "city": "Jaipur", "state": "Rajasthan", "country": "India", "latitude": 26.9124, "longitude": 75.7873, "timezone_id": "Asia/Kolkata"},
    {"display_name": "New Delhi, Delhi, India", "city": "New Delhi", "state": "Delhi", "country": "India", "latitude": 28.6139, "longitude": 77.2090, "timezone_id": "Asia/Kolkata"},
    {"display_name": "Mumbai, Maharashtra, India", "city": "Mumbai", "state": "Maharashtra", "country": "India", "latitude": 19.0760, "longitude": 72.8777, "timezone_id": "Asia/Kolkata"},
    {"display_name": "Varanasi, Uttar Pradesh, India", "city": "Varanasi", "state": "Uttar Pradesh", "country": "India", "latitude": 25.3176, "longitude": 82.9739, "timezone_id": "Asia/Kolkata"},
    {"display_name": "Bengaluru, Karnataka, India", "city": "Bengaluru", "state": "Karnataka", "country": "India", "latitude": 12.9716, "longitude": 77.5946, "timezone_id": "Asia/Kolkata"},
    {"display_name": "Kolkata, West Bengal, India", "city": "Kolkata", "state": "West Bengal", "country": "India", "latitude": 22.5726, "longitude": 88.3639, "timezone_id": "Asia/Kolkata"},
    {"display_name": "Chennai, Tamil Nadu, India", "city": "Chennai", "state": "Tamil Nadu", "country": "India", "latitude": 13.0827, "longitude": 80.2707, "timezone_id": "Asia/Kolkata"},
    {"display_name": "Hyderabad, Telangana, India", "city": "Hyderabad", "state": "Telangana", "country": "India", "latitude": 17.3850, "longitude": 78.4867, "timezone_id": "Asia/Kolkata"},
    {"display_name": "Ahmedabad, Gujarat, India", "city": "Ahmedabad", "state": "Gujarat", "country": "India", "latitude": 23.0225, "longitude": 72.5714, "timezone_id": "Asia/Kolkata"},
    {"display_name": "Pune, Maharashtra, India", "city": "Pune", "state": "Maharashtra", "country": "India", "latitude": 18.5204, "longitude": 73.8567, "timezone_id": "Asia/Kolkata"},
    {"display_name": "Lucknow, Uttar Pradesh, India", "city": "Lucknow", "state": "Uttar Pradesh", "country": "India", "latitude": 26.8467, "longitude": 80.9462, "timezone_id": "Asia/Kolkata"},
    {"display_name": "Patna, Bihar, India", "city": "Patna", "state": "Bihar", "country": "India", "latitude": 25.5941, "longitude": 85.1376, "timezone_id": "Asia/Kolkata"},
    {"display_name": "Ujjain, Madhya Pradesh, India", "city": "Ujjain", "state": "Madhya Pradesh", "country": "India", "latitude": 23.1765, "longitude": 75.7885, "timezone_id": "Asia/Kolkata"},
    {"display_name": "Haridwar, Uttarakhand, India", "city": "Haridwar", "state": "Uttarakhand", "country": "India", "latitude": 29.9457, "longitude": 78.1642, "timezone_id": "Asia/Kolkata"},
    {"display_name": "Ayodhya, Uttar Pradesh, India", "city": "Ayodhya", "state": "Uttar Pradesh", "country": "India", "latitude": 26.7922, "longitude": 82.1998, "timezone_id": "Asia/Kolkata"},
    {"display_name": "New York, NY, USA", "city": "New York", "state": "New York", "country": "United States", "latitude": 40.7128, "longitude": -74.0060, "timezone_id": "America/New_York"},
    {"display_name": "San Francisco, CA, USA", "city": "San Francisco", "state": "California", "country": "United States", "latitude": 37.7749, "longitude": -122.4194, "timezone_id": "America/Los_Angeles"},
    {"display_name": "Los Angeles, CA, USA", "city": "Los Angeles", "state": "California", "country": "United States", "latitude": 34.0522, "longitude": -118.2437, "timezone_id": "America/Los_Angeles"},
    {"display_name": "Chicago, IL, USA", "city": "Chicago", "state": "Illinois", "country": "United States", "latitude": 41.8781, "longitude": -87.6298, "timezone_id": "America/Chicago"},
    {"display_name": "Houston, TX, USA", "city": "Houston", "state": "Texas", "country": "United States", "latitude": 29.7604, "longitude": -95.3698, "timezone_id": "America/Chicago"},
    {"display_name": "London, Greater London, UK", "city": "London", "state": "England", "country": "United Kingdom", "latitude": 51.5074, "longitude": -0.1278, "timezone_id": "Europe/London"},
    {"display_name": "Paris, Île-de-France, France", "city": "Paris", "state": "Île-de-France", "country": "France", "latitude": 48.8566, "longitude": 2.3522, "timezone_id": "Europe/Paris"},
    {"display_name": "Berlin, Berlin, Germany", "city": "Berlin", "state": "Berlin", "country": "Germany", "latitude": 52.5200, "longitude": 13.4050, "timezone_id": "Europe/Berlin"},
    {"display_name": "Tokyo, Kanto, Japan", "city": "Tokyo", "state": "Tokyo", "country": "Japan", "latitude": 35.6762, "longitude": 139.6503, "timezone_id": "Asia/Tokyo"},
    {"display_name": "Sydney, NSW, Australia", "city": "Sydney", "state": "New South Wales", "country": "Australia", "latitude": -33.8688, "longitude": 151.2093, "timezone_id": "Australia/Sydney"},
    {"display_name": "Toronto, ON, Canada", "city": "Toronto", "state": "Ontario", "country": "Canada", "latitude": 43.6532, "longitude": -79.3832, "timezone_id": "America/Toronto"},
    {"display_name": "Dubai, Dubai, UAE", "city": "Dubai", "state": "Dubai", "country": "United Arab Emirates", "latitude": 25.2048, "longitude": 55.2708, "timezone_id": "Asia/Dubai"},
    {"display_name": "Singapore, Singapore", "city": "Singapore", "state": "Singapore", "country": "Singapore", "latitude": 1.3521, "longitude": 103.8198, "timezone_id": "Asia/Singapore"}
]

class LocationService:
    """Service for geocoding, place autocomplete, and IANA timezone resolution."""

    def resolve_timezone_from_coords(self, lat: float, lon: float, country_code: Optional[str] = None) -> str:
        """Determines IANA timezone ID from latitude and longitude using spatial region mapping."""
        # Check nearest builtin city within 200 km
        min_dist = float("inf")
        best_tz = None

        for item in BUILTIN_CITIES:
            d_lat = math.radians(item["latitude"] - lat)
            d_lon = math.radians(item["longitude"] - lon)
            a = math.sin(d_lat/2)**2 + math.cos(math.radians(lat)) * math.cos(math.radians(item["latitude"])) * math.sin(d_lon/2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            dist_km = 6371 * c
            if dist_km < min_dist:
                min_dist = dist_km
                best_tz = item["timezone_id"]

        if min_dist < 300 and best_tz:
            return best_tz

        # Spatial region bounding box fallbacks
        # India & Indian subcontinent
        if 6.0 <= lat <= 36.0 and 68.0 <= lon <= 97.0:
            return "Asia/Kolkata"
        # US East
        if 24.0 <= lat <= 50.0 and -85.0 <= lon <= -65.0:
            return "America/New_York"
        # US Central
        if 25.0 <= lat <= 50.0 and -105.0 <= lon <= -85.0:
            return "America/Chicago"
        # US Mountain
        if 30.0 <= lat <= 50.0 and -115.0 <= lon <= -105.0:
            return "America/Denver"
        # US Pacific
        if 30.0 <= lat <= 50.0 and -125.0 <= lon <= -115.0:
            return "America/Los_Angeles"
        # UK / Ireland
        if 50.0 <= lat <= 60.0 and -10.0 <= lon <= 2.0:
            return "Europe/London"
        # Central Europe
        if 35.0 <= lat <= 60.0 and 2.0 <= lon <= 25.0:
            return "Europe/Paris"
        # Japan
        if 24.0 <= lat <= 46.0 and 122.0 <= lon <= 150.0:
            return "Asia/Tokyo"
        # Australia East
        if -44.0 <= lat <= -10.0 and 140.0 <= lon <= 155.0:
            return "Australia/Sydney"

        return "UTC"

    async def search_locations(self, query: str) -> List[PlaceResult]:
        query_stripped = query.strip()
        if len(query_stripped) < 2:
            return []

        results: List[PlaceResult] = []
        seen_names = set()

        # 1. First check matching builtin cities
        q_lower = query_stripped.lower()
        for item in BUILTIN_CITIES:
            if (q_lower in item["display_name"].lower() or 
                q_lower in item["city"].lower() or 
                q_lower in item["state"].lower()):
                p = PlaceResult(**item)
                results.append(p)
                seen_names.add(p.display_name.lower())

        # 2. Try online Nominatim geocoding provider
        try:
            url = f"https://nominatim.openstreetmap.org/search?q={query_stripped}&format=json&addressdetails=1&limit=8"
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(url, headers={"User-Agent": "MahadevJyotishAI/1.0"})
                if resp.status_code == 200:
                    items = resp.json()
                    for item in items:
                        display_name = item.get("display_name", "")
                        if display_name.lower() in seen_names:
                            continue

                        address = item.get("address", {})
                        city = (address.get("city") or address.get("town") or 
                                address.get("village") or address.get("county") or "")
                        state = address.get("state", "")
                        country = address.get("country", "")

                        lat = float(item["lat"])
                        lon = float(item["lon"])
                        tz_id = self.resolve_timezone_from_coords(lat, lon, country_code=address.get("country_code"))

                        place_res = PlaceResult(
                            display_name=display_name,
                            city=city if city else None,
                            state=state if state else None,
                            country=country if country else None,
                            latitude=lat,
                            longitude=lon,
                            timezone_id=tz_id
                        )
                        results.append(place_res)
                        seen_names.add(display_name.lower())
        except Exception:
            # Fallback gracefully to built-in matches if external network request fails or times out
            pass

        return results
