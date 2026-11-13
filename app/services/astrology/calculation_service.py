"""Calculation Service.

Orchestrates birth details resolution, real Swiss Ephemeris calculations,
Rashi/Nakshatra/Pada/SubLord mappings, and builds CanonicalAstrologyResult.
"""
import datetime
import hashlib
import uuid
import pytz
import swisseph as swe
from typing import Dict, Any

from app.core.errors import AppException
from app.services.astrology.swiss_provider import SwissEphemerisProvider
from app.services.astrology.astrology_constants import (
    get_rashi_info,
    get_nakshatra_info
)
from app.schemas.canonical_astrology import (
    CanonicalAstrologyResult,
    IdentitySection,
    BirthSection,
    ProviderSection,
    PlanetDetail,
    AngleDetail,
    AnglesSection,
    VedicSection,
    BhavaCuspDetail,
    BhavaSection,
    KPSection,
    ProvenanceSection
)

PLANET_BODIES = [
    ("Sun", swe.SUN),
    ("Moon", swe.MOON),
    ("Mars", swe.MARS),
    ("Mercury", swe.MERCURY),
    ("Jupiter", swe.JUPITER),
    ("Venus", swe.VENUS),
    ("Saturn", swe.SATURN),
    ("Rahu", swe.MEAN_NODE)
]

class CalculationService:
    def __init__(self, provider: SwissEphemerisProvider | None = None):
        self.provider = provider or SwissEphemerisProvider()

    def calculate_natal(
        self,
        profile_id: str,
        name: str,
        birth_date: str,  # YYYY-MM-DD
        birth_time: str,  # HH:MM:SS
        place_label: str,
        latitude: float,
        longitude: float,
        timezone_id: str
    ) -> CanonicalAstrologyResult:
        # 1. Parse local datetime and convert to UTC using IANA timezone
        try:
            tz = pytz.timezone(timezone_id)
            # Support both HH:mm and HH:mm:ss
            if len(birth_time) == 5:
                dt_str = f"{birth_date} {birth_time}:00"
            else:
                dt_str = f"{birth_date} {birth_time}"
            naive_dt = datetime.datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            local_dt = tz.localize(naive_dt)
            utc_dt = local_dt.astimezone(pytz.utc)
        except Exception as e:
            raise AppException(f"Invalid birth datetime or timezone '{timezone_id}': {str(e)}", code="INVALID_INPUT")

        # 2. Calculate Julian Day UT
        hour_decimal = utc_dt.hour + (utc_dt.minute / 60.0) + (utc_dt.second / 3600.0) + (utc_dt.microsecond / 3600000000.0)
        jd_ut = self.provider.get_julian_day_ut(utc_dt.year, utc_dt.month, utc_dt.day, hour_decimal)

        # 3. Calculate Ayanamsha
        ayanamsha_val = self.provider.get_ayanamsha_ut(jd_ut)

        # 4. Calculate Planets & Rahu
        planets_list = []
        rahu_sid_lon = 0.0

        for body_name, body_id in PLANET_BODIES:
            raw = self.provider.calculate_planet(jd_ut, body_id, body_name)
            if body_name == "Rahu":
                rahu_sid_lon = raw.sidereal_longitude

            r_idx, r_name, sign_lord, deg_in_rashi = get_rashi_info(raw.sidereal_longitude)
            n_idx, n_name, star_lord, pada, sub_lord = get_nakshatra_info(raw.sidereal_longitude)

            p_detail = PlanetDetail(
                body=body_name,
                tropical_longitude=raw.tropical_longitude,
                sidereal_longitude=raw.sidereal_longitude,
                speed=raw.speed_longitude,
                retrograde=raw.retrograde,
                rashi=r_idx,
                rashi_name=r_name,
                degree_in_rashi=deg_in_rashi,
                nakshatra=n_idx,
                nakshatra_name=n_name,
                pada=pada,
                sign_lord=sign_lord,
                star_lord=star_lord,
                sub_lord=sub_lord
            )
            planets_list.append(p_detail)

        # 5. Ketu = exactly (Rahu + 180) % 360
        ketu_sid_lon = (rahu_sid_lon + 180.0) % 360.0
        ketu_trop_lon = (ketu_sid_lon + ayanamsha_val) % 360.0
        r_idx, r_name, sign_lord, deg_in_rashi = get_rashi_info(ketu_sid_lon)
        n_idx, n_name, star_lord, pada, sub_lord = get_nakshatra_info(ketu_sid_lon)

        ketu_detail = PlanetDetail(
            body="Ketu",
            tropical_longitude=ketu_trop_lon,
            sidereal_longitude=ketu_sid_lon,
            speed=-0.05,  # Mean node speed approximation
            retrograde=True,
            rashi=r_idx,
            rashi_name=r_name,
            degree_in_rashi=deg_in_rashi,
            nakshatra=n_idx,
            nakshatra_name=n_name,
            pada=pada,
            sign_lord=sign_lord,
            star_lord=star_lord,
            sub_lord=sub_lord
        )
        planets_list.append(ketu_detail)

        # 6. Calculate Angles (Ascendant & MC) and Placidus Cusps
        houses_raw = self.provider.calculate_placidus_houses(jd_ut, latitude, longitude)

        # Ascendant Angle
        asc_lon = houses_raw.ascendant_sidereal
        r_idx, r_name, sign_lord, deg_in_rashi = get_rashi_info(asc_lon)
        n_idx, n_name, star_lord, pada, sub_lord = get_nakshatra_info(asc_lon)
        asc_angle = AngleDetail(
            name="Ascendant",
            sidereal_longitude=asc_lon,
            rashi=r_idx,
            rashi_name=r_name,
            degree_in_rashi=deg_in_rashi,
            nakshatra=n_idx,
            nakshatra_name=n_name,
            pada=pada,
            sign_lord=sign_lord,
            star_lord=star_lord,
            sub_lord=sub_lord
        )

        # MC Angle
        mc_lon = houses_raw.mc_sidereal
        r_idx, r_name, sign_lord, deg_in_rashi = get_rashi_info(mc_lon)
        n_idx, n_name, star_lord, pada, sub_lord = get_nakshatra_info(mc_lon)
        mc_angle = AngleDetail(
            name="MC",
            sidereal_longitude=mc_lon,
            rashi=r_idx,
            rashi_name=r_name,
            degree_in_rashi=deg_in_rashi,
            nakshatra=n_idx,
            nakshatra_name=n_name,
            pada=pada,
            sign_lord=sign_lord,
            star_lord=star_lord,
            sub_lord=sub_lord
        )

        # 7. Whole Sign Houses (Vedic) mapping
        asc_rashi = asc_angle.rashi
        whole_sign = {house_num: (asc_rashi + house_num - 1) % 12 for house_num in range(1, 13)}

        # 8. KP / Placidus House Cusps
        kp_cusps = []
        for i, cusp_lon in enumerate(houses_raw.cusps_sidereal):
            h_num = i + 1
            r_idx, r_name, sign_lord, deg_in_rashi = get_rashi_info(cusp_lon)
            n_idx, n_name, star_lord, pada, sub_lord = get_nakshatra_info(cusp_lon)
            c_detail = BhavaCuspDetail(
                house_number=h_num,
                sidereal_longitude=cusp_lon,
                rashi=r_idx,
                rashi_name=r_name,
                degree_in_rashi=deg_in_rashi,
                sign_lord=sign_lord,
                star_lord=star_lord,
                sub_lord=sub_lord
            )
            kp_cusps.append(c_detail)

        # 9. Compute Hashes & Provenance
        calc_id = f"calc_{uuid.uuid4().hex[:12]}"
        input_str = f"{profile_id}:{birth_date}:{birth_time}:{latitude}:{longitude}:{timezone_id}"
        input_hash = hashlib.sha256(input_str.encode('utf-8')).hexdigest()
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()

        checksum_str = f"{calc_id}:{input_hash}:{jd_ut}:{ayanamsha_val}"
        checksum = hashlib.sha256(checksum_str.encode('utf-8')).hexdigest()

        return CanonicalAstrologyResult(
            identity=IdentitySection(
                calculation_id=calc_id,
                profile_id=profile_id,
                input_hash=input_hash,
                calculation_version="2.0.0"
            ),
            birth=BirthSection(
                local_date=birth_date,
                local_time=birth_time,
                timezone_id=timezone_id,
                utc_instant=utc_dt.isoformat(),
                latitude=latitude,
                longitude=longitude,
                place_label=place_label,
                julian_day_ut=jd_ut
            ),
            provider=ProviderSection(
                swiss_version=self.provider.version,
                ephemeris_mode="SWIEPH",
                sidereal_mode="LAHIRI",
                ayanamsha_name="CHITRAPAKSHA_LAHIRI",
                ayanamsha_value=ayanamsha_val,
                node_mode="MEAN_NODE"
            ),
            planets=planets_list,
            angles=AnglesSection(ascendant=asc_angle, mc=mc_angle),
            vedic=VedicSection(whole_sign_houses=whole_sign),
            bhava=BhavaSection(method="PLACIDUS", cusps=kp_cusps),
            kp=KPSection(cusps=kp_cusps),
            provenance=ProvenanceSection(
                calculated_at_utc=now_utc,
                engine_build="pyswisseph-production-2.0",
                checksum=checksum
            )
        )
