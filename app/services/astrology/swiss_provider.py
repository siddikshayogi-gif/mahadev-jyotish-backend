"""Authoritative Swiss Ephemeris Astronomy Provider.

Executes real pyswisseph calculations on the secure backend.
Fail-closed: returns explicit exceptions if real swisseph is unavailable.
"""
from dataclasses import dataclass
from typing import Tuple, Dict, Any
import swisseph as swe
from app.core.errors import AppException

class SwissEphemerisUnavailableException(AppException):
    def __init__(self, message: str = "Swiss Ephemeris runtime is unavailable"):
        super().__init__(
            message=message,
            code="SWISS_EPHEMERIS_UNAVAILABLE",
            status_code=503
        )

@dataclass(frozen=True)
class PlanetRawData:
    body_name: str
    tropical_longitude: float
    sidereal_longitude: float
    speed_longitude: float
    retrograde: bool

@dataclass(frozen=True)
class HouseRawData:
    ascendant_sidereal: float
    mc_sidereal: float
    cusps_sidereal: Tuple[float, ...]

class SwissEphemerisProvider:
    def __init__(self, ephe_path: str | None = None):
        try:
            if ephe_path:
                swe.set_ephe_path(ephe_path)
            # Lahiri (Chitrapaksha) Ayanamsha
            swe.set_sid_mode(swe.SIDM_LAHIRI)
        except Exception as e:
            raise SwissEphemerisUnavailableException(f"Failed to initialize Swiss Ephemeris: {str(e)}")

    @property
    def version(self) -> str:
        try:
            return str(swe.version)
        except Exception as e:
            raise SwissEphemerisUnavailableException(f"Failed to read Swiss Ephemeris version: {str(e)}")

    def get_julian_day_ut(self, year: int, month: int, day: int, hour_decimal: float) -> float:
        """Calculate Julian Day UT."""
        try:
            return float(swe.julday(year, month, day, hour_decimal))
        except Exception as e:
            raise AppException(f"Failed to calculate Julian Day: {str(e)}", code="CALCULATION_ERROR")

    def get_ayanamsha_ut(self, jd_ut: float) -> float:
        """Calculate Lahiri Ayanamsha value for Julian Day UT."""
        try:
            return float(swe.get_ayanamsa_ut(jd_ut))
        except Exception as e:
            raise AppException(f"Failed to calculate Ayanamsha: {str(e)}", code="CALCULATION_ERROR")

    def calculate_planet(self, jd_ut: float, body_id: int, body_name: str) -> PlanetRawData:
        """Calculate tropical and sidereal longitudes and speed for a planet or node."""
        try:
            # Tropical calculation
            flags_trop = swe.FLG_SPEED | swe.FLG_SWIEPH
            res_trop, _ = swe.calc_ut(jd_ut, body_id, flags_trop)
            trop_lon = res_trop[0] % 360.0

            # Sidereal calculation (Lahiri)
            flags_sid = swe.FLG_SIDEREAL | swe.FLG_SPEED | swe.FLG_SWIEPH
            res_sid, _ = swe.calc_ut(jd_ut, body_id, flags_sid)
            sid_lon = res_sid[0] % 360.0
            speed_lon = res_sid[3]
            is_retrograde = speed_lon < 0.0

            return PlanetRawData(
                body_name=body_name,
                tropical_longitude=trop_lon,
                sidereal_longitude=sid_lon,
                speed_longitude=speed_lon,
                retrograde=is_retrograde
            )
        except Exception as e:
            raise AppException(f"Failed to calculate planet {body_name}: {str(e)}", code="CALCULATION_ERROR")

    def calculate_placidus_houses(self, jd_ut: float, latitude: float, longitude: float) -> HouseRawData:
        """Calculate Placidus house cusps, Ascendant, and MC in Sidereal Lahiri."""
        try:
            # swe.houses_ex with b'P' for Placidus and FLG_SIDEREAL
            cusps, ascmc = swe.houses_ex(jd_ut, latitude, longitude, b'P', swe.FLG_SIDEREAL)
            
            ascendant_sid = ascmc[0] % 360.0
            mc_sid = ascmc[1] % 360.0
            
            # Extract 12 house cusps normalized 0..360
            cusps_sid = tuple(float(c) % 360.0 for c in cusps[:12])

            return HouseRawData(
                ascendant_sidereal=ascendant_sid,
                mc_sidereal=mc_sid,
                cusps_sidereal=cusps_sid
            )
        except Exception as e:
            raise AppException(f"Failed to calculate Placidus houses: {str(e)}", code="CALCULATION_ERROR")
