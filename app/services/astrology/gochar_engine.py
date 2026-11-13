"""Target-date Gochar (Transits) Engine.

Computes exact target-date planetary snapshot via real Swiss Ephemeris and maps
transit positions against the natal D1 Lagna and Chandra Rashi.
"""

from datetime import datetime, timezone
from typing import List, Optional
import uuid

from app.schemas.canonical_astrology import CanonicalAstrologyResult
from app.schemas.dasha_gochar_yoga import TransitPlanetFact, GocharResult
from app.services.astrology.calculation_service import CalculationService

class GocharEngine:
    """Deterministic Gochar (Transit) Engine using Swiss Ephemeris via CalculationService."""

    def __init__(self, calc_service: Optional[CalculationService] = None):
        self.calc_service = calc_service or CalculationService()

    def calculate_gochar_snapshot(
        self,
        natal_canonical: CanonicalAstrologyResult,
        target_datetime_utc: datetime,
        latitude: float = 26.9124,
        longitude: float = 75.7873,
        profile_id: str = "prof_default"
    ) -> GocharResult:
        """Calculates transit snapshot for target_datetime_utc against natal chart."""
        if target_datetime_utc.tzinfo is None:
            target_datetime_utc = target_datetime_utc.replace(tzinfo=timezone.utc)

        target_date_str = target_datetime_utc.strftime("%Y-%m-%d")
        target_time_str = target_datetime_utc.strftime("%H:%M:%S")

        # 1. Fetch real Swiss Ephemeris snapshot for target date/time via CalculationService
        target_canonical = self.calc_service.calculate_natal(
            profile_id=profile_id,
            name="Transit Event",
            birth_date=target_date_str,
            birth_time=target_time_str,
            place_label="Transit Location",
            latitude=latitude,
            longitude=longitude,
            timezone_id="UTC"
        )

        natal_lagna_rashi = natal_canonical.angles.ascendant.rashi
        natal_moon_planet = next(p for p in natal_canonical.planets if p.body == "Moon")
        natal_moon_rashi = natal_moon_planet.rashi

        transits: List[TransitPlanetFact] = []
        aspects_conjunctions: List[str] = []

        for tp in target_canonical.planets:
            # House relative to Natal D1 Lagna
            house_d1 = ((tp.rashi - natal_lagna_rashi) % 12) + 1
            # House relative to Natal Moon (Chandra Rashi)
            house_moon = ((tp.rashi - natal_moon_rashi) % 12) + 1

            t_fact = TransitPlanetFact(
                body=tp.body,
                sidereal_longitude=tp.sidereal_longitude,
                rashi=tp.rashi,
                rashi_name=tp.rashi_name,
                degree_in_rashi=tp.degree_in_rashi,
                speed=tp.speed,
                retrograde=tp.retrograde,
                nakshatra=tp.nakshatra,
                nakshatra_name=tp.nakshatra_name,
                star_lord=tp.star_lord,
                house_from_d1_lagna=house_d1,
                house_from_moon=house_moon
            )
            transits.append(t_fact)

            # Special Transit Analysis
            if tp.body == "Saturn":
                if house_moon == 12:
                    aspects_conjunctions.append("Saturn Transit in 12th from Moon (Sade Sati 1st Phase)")
                elif house_moon == 1:
                    aspects_conjunctions.append("Saturn Transit over Natal Moon (Sade Sati Peak/2nd Phase)")
                elif house_moon == 2:
                    aspects_conjunctions.append("Saturn Transit in 2nd from Moon (Sade Sati 3rd Phase)")
                elif house_moon in [4, 8]:
                    aspects_conjunctions.append(f"Saturn Dhaiya (Transit in House {house_moon} from Moon)")

            if tp.body == "Jupiter":
                if house_moon in [2, 5, 7, 9, 11]:
                    aspects_conjunctions.append(f"Auspicious Jupiter Transit in House {house_moon} from Moon")

            if tp.body in ["Rahu", "Ketu"]:
                if house_moon in [3, 6, 11]:
                    aspects_conjunctions.append(f"Favorable {tp.body} Transit in House {house_moon} from Moon")

        calc_id = f"gochar_{uuid.uuid4().hex[:12]}"
        
        return GocharResult(
            calculation_id=calc_id,
            profile_id=profile_id,
            natal_input_hash=natal_canonical.identity.input_hash,
            target_datetime_utc=target_datetime_utc.isoformat(),
            transits=transits,
            key_aspects_and_conjunctions=aspects_conjunctions
        )

