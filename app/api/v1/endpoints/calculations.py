from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import pytz
import logging

from app.schemas.canonical_astrology import CanonicalAstrologyResult
from app.schemas.vedic_astrology import VedicChartResult
from app.schemas.kp_astrology import KPChartResult
from app.schemas.dasha_gochar_yoga import (
    DashaHierarchyResult,
    GocharResult,
    YogaResult
)
from app.services.astrology.calculation_service import CalculationService
from app.services.astrology.vedic_engine import VedicEngine
from app.services.astrology.kp_engine import KPEngine
from app.services.astrology.dasha_engine import DashaEngine
from app.services.astrology.gochar_engine import GocharEngine
from app.services.astrology.yoga_engine import YogaEngine
from app.services.astrology.kp_horary_engine import KPHoraryEngine, KPHoraryResult
from app.services.astrology.temporal_scanners import TemporalScanner
from app.services.astrology.smart_muhurat_engine import SmartMuhuratEngine, MuhuratFinderResult
from app.services.astrology.stress_alert_engine import MentalPeaceStressEngine, StressAlertResult
from app.services.astrology.numerology_synergy_engine import NumerologySynergyEngine, NumerologySynergyResult
from app.services.astrology.ashtakoot_compatibility_engine import AshtakootCompatibilityEngine, AshtakootMatchingResult
from app.services.astrology.event_journal_engine import EventJournalEngine, EventJournalEntry, AccuracyStatistics
from app.api.v1.endpoints.profiles import _profiles_db
from app.core.errors import NotFoundException

logger = logging.getLogger(__name__)
router = APIRouter()

class NatalCalculationRequest(BaseModel):
    profile_id: Optional[str] = None
    name: Optional[str] = None
    date_of_birth: Optional[str] = None
    time_of_birth: Optional[str] = None
    place_of_birth: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone_id: Optional[str] = None

class DashaCalculationRequest(NatalCalculationRequest):
    target_date_utc: Optional[str] = None
    max_depth: Optional[int] = 5

class DashaSubPeriodsRequest(BaseModel):
    parent_lord: str
    parent_start_date_utc: str
    parent_end_date_utc: str
    parent_level: int
    target_date_utc: Optional[str] = None
    birth_date_utc: Optional[str] = None

class GocharCalculationRequest(NatalCalculationRequest):
    target_datetime_utc: Optional[str] = None
    target_latitude: Optional[float] = None
    target_longitude: Optional[float] = None

class KPHoraryCalculationRequest(NatalCalculationRequest):
    horary_number: int  # 1 to 249
    category: Optional[str] = "GENERAL"

class TimeTravelScanCalculationRequest(NatalCalculationRequest):
    target_datetime_utc: str
    topic: Optional[str] = "GENERAL"

class SmartMuhuratCalculationRequest(NatalCalculationRequest):
    category: Optional[str] = "GENERAL"
    days_ahead: Optional[int] = 30

class StressAlertCalculationRequest(NatalCalculationRequest):
    target_datetime_utc: Optional[str] = None

class NumerologySynergyCalculationRequest(NatalCalculationRequest):
    target_datetime_utc: Optional[str] = None

class AshtakootMatchingCalculationRequest(BaseModel):
    groom: NatalCalculationRequest
    bride: NatalCalculationRequest
    groom_name: Optional[str] = "Groom"
    bride_name: Optional[str] = "Bride"

class EventJournalFeedbackRequest(BaseModel):
    entry_id: str
    actual_outcome: str  # "CONFIRMED_YES", "CONFIRMED_NO", "PARTIAL"
    actual_event_date: Optional[str] = None
    feedback_notes: Optional[str] = None

_calc_service = CalculationService()
_vedic_engine = VedicEngine()
_kp_engine = KPEngine()
_dasha_engine = DashaEngine()
_gochar_engine = GocharEngine()
_yoga_engine = YogaEngine()
_horary_engine = KPHoraryEngine()
_temporal_scanner = TemporalScanner()
_muhurat_engine = SmartMuhuratEngine()
_stress_engine = MentalPeaceStressEngine()
_numerology_engine = NumerologySynergyEngine()
_ashtakoot_engine = AshtakakootCompatibilityEngine = AshtakootCompatibilityEngine()
_journal_engine = EventJournalEngine()

@router.post("/natal", response_model=CanonicalAstrologyResult)
async def calculate_natal(req: NatalCalculationRequest):
    """Calculates canonical astrology result using real backend Swiss Ephemeris."""
    
    # If profile_id is in profiles_db, load profile details
    if req.profile_id and req.profile_id in _profiles_db:
        p = _profiles_db[req.profile_id]
        name = p.name
        dob = p.date_of_birth
        tob = p.time_of_birth
        place = p.place_of_birth
        lat = p.latitude
        lon = p.longitude
        tz_id = p.timezone_id
    else:
        name = req.name
        dob = req.date_of_birth
        tob = req.time_of_birth
        place = req.place_of_birth
        lat = req.latitude
        lon = req.longitude
        tz_id = req.timezone_id

    if not dob or not tob or lat is None or lon is None:
        raise HTTPException(
            status_code=400,
            detail="Missing birth data (date, time, lat, lon). No profile or birth data provided."
        )

    result = _calc_service.calculate_natal(
        profile_id=req.profile_id or "custom",
        name=name or "User",
        birth_date=dob,
        birth_time=tob,
        place_label=place or "Custom Location",
        latitude=lat,
        longitude=lon,
        timezone_id=tz_id or "UTC"
    )
    return result

@router.post("/vedic", response_model=VedicChartResult)
async def calculate_vedic(req: NatalCalculationRequest):
    """Calculates deterministic Vedic chart facts (D1, D9, D10, Bhava Chalit, Chandra Kundali, Dignities)."""
    canonical_res = await calculate_natal(req)
    vedic_res = _vedic_engine.calculate_vedic_chart(canonical_res)
    return vedic_res

@router.post("/kp", response_model=KPChartResult)
async def calculate_kp(req: NatalCalculationRequest):
    """Calculates deterministic KP astrology facts (Placidus Cusps, Sign/Star/Sub/SSL lords, Significators, Ruling Planets, Events)."""
    canonical_res = await calculate_natal(req)
    kp_res = _kp_engine.calculate_kp(canonical_res)
    return kp_res

@router.post("/dasha", response_model=DashaHierarchyResult)
async def calculate_dasha(req: DashaCalculationRequest):
    """Calculates 5-level Vimshottari Dasha hierarchy and active chain."""
    try:
        canonical_res = await calculate_natal(req)
        moon_p = next(p for p in canonical_res.planets if p.body == "Moon")

        tz = pytz.timezone(canonical_res.birth.timezone_id)
        # Ensure HH:mm:ss for strptime
        local_time = canonical_res.birth.local_time
        if len(local_time) == 5:
            local_time += ":00"
        dt_str = f"{canonical_res.birth.local_date} {local_time}"
        naive_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        birth_dt_utc = tz.localize(naive_dt).astimezone(pytz.utc)

        if req.target_date_utc:
            target_dt = datetime.fromisoformat(req.target_date_utc.replace("Z", "+00:00"))
        else:
            target_dt = datetime.now(timezone.utc)

        dasha_res = _dasha_engine.calculate_dasha_hierarchy(
            moon_longitude=moon_p.sidereal_longitude,
            birth_datetime_utc=birth_dt_utc,
            target_datetime_utc=target_dt,
            max_depth=req.max_depth or 5,
            profile_id=req.profile_id or "prof_default"
        )
        return dasha_res
    except Exception as e:
        logger.exception("Dasha calculation failed")
        raise HTTPException(status_code=500, detail=f"Dasha calculation failed: {str(e)}")

@router.post("/dasha/sub-periods")
async def get_dasha_sub_periods(req: DashaSubPeriodsRequest):
    """Returns 9 sub-periods for a given parent Dasha interval."""
    try:
        if req.parent_level >= 5:
            raise HTTPException(status_code=400, detail="Cannot subdivide beyond level 5 (Prana)")

        periods = _dasha_engine.get_sub_periods(
            parent_lord=req.parent_lord,
            parent_start_iso=req.parent_start_date_utc,
            parent_end_iso=req.parent_end_date_utc,
            parent_level=req.parent_level,
            target_date_iso=req.target_date_utc,
            birth_date_iso=req.birth_date_utc
        )

        return {
            "parent_level": req.parent_level,
            "child_level": req.parent_level + 1,
            "periods": periods
        }
    except Exception as e:
        logger.exception("Sub-period calculation failed")
        raise HTTPException(status_code=500, detail=f"Failed to get sub-periods: {str(e)}")

@router.post("/gochar", response_model=GocharResult)
async def calculate_gochar(req: GocharCalculationRequest):
    """Calculates target-date Gochar (Transits) snapshot via Swiss Ephemeris."""
    try:
        canonical_res = await calculate_natal(req)
        if req.target_datetime_utc:
            target_dt = datetime.fromisoformat(req.target_datetime_utc.replace("Z", "+00:00"))
        else:
            target_dt = datetime.now(timezone.utc)

        lat = req.target_latitude if req.target_latitude is not None else canonical_res.birth.latitude
        lon = req.target_longitude if req.target_longitude is not None else canonical_res.birth.longitude

        gochar_res = _gochar_engine.calculate_gochar_snapshot(
            natal_canonical=canonical_res,
            target_datetime_utc=target_dt,
            latitude=lat,
            longitude=lon,
            profile_id=req.profile_id or "prof_default"
        )
        return gochar_res
    except Exception as e:
        logger.exception("Gochar calculation failed")
        raise HTTPException(status_code=500, detail=f"Gochar calculation failed: {str(e)}")

@router.post("/yogas", response_model=YogaResult)
async def calculate_yogas(req: NatalCalculationRequest):
    """Evaluates catalogued classical Vedic Yogas with source references."""
    vedic_res = await calculate_vedic(req)
    yoga_res = _yoga_engine.evaluate_yogas(
        vedic_chart=vedic_res,
        profile_id=req.profile_id or "prof_default"
    )
    return yoga_res

@router.post("/audit/internal")
async def astrology_audit(req: DashaCalculationRequest):
    """DEBUG-only astrology calculation audit. Returns all layers for verification."""
    # This should be disabled in production in a real scenario
    canonical = await calculate_natal(req)
    vedic = _vedic_engine.calculate_vedic_chart(canonical)
    kp = _kp_engine.calculate_kp(canonical)

    # Resolve birth date for dasha
    moon_p = next(p for p in canonical.planets if p.body == "Moon")
    tz = pytz.timezone(canonical.birth.timezone_id)
    local_time = canonical.birth.local_time
    if len(local_time) == 5: local_time += ":00"
    dt_str = f"{canonical.birth.local_date} {local_time}"
    naive_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    birth_dt_utc = tz.localize(naive_dt).astimezone(pytz.utc)

    target_dt = datetime.fromisoformat(req.target_date_utc.replace("Z", "+00:00")) if req.target_date_utc else datetime.now(timezone.utc)

    dasha = _dasha_engine.calculate_dasha_hierarchy(
        moon_longitude=moon_p.sidereal_longitude,
        birth_datetime_utc=birth_dt_utc,
        target_datetime_utc=target_dt
    )

    gochar = _gochar_engine.calculate_gochar_snapshot(canonical, target_dt)

    return {
        "profile": req.profile_id,
        "target_date": target_dt.isoformat(),
        "canonical": canonical.model_dump(),
        "vedic_summary": {
            "d1_lagna": vedic.d1_lagna.rashi_name,
            "d9_lagna": vedic.d9_lagna.rashi_name,
            "d10_lagna": vedic.d10_lagna.rashi_name,
            "moon_sign": moon_p.rashi_name,
            "planets": [{p.body: p.rashi_name} for p in vedic.planets]
        },
        "kp_summary": {
            "asc_sub": kp.cusps[0].sub_lord,
            "cusps": [{f"H{c.house_number}": c.sidereal_longitude} for c in kp.cusps]
        },
        "dasha_active": [f"{d.level_name}: {d.lord}" for d in dasha.active_chain],
        "gochar_moon_house": next(t.house_from_d1_lagna for t in gochar.transits if t.body == "Moon")
    }

@router.post("/kp/horary", response_model=KPHoraryResult)
async def calculate_kp_horary(req: KPHoraryCalculationRequest):
    """Calculates KP Horary (1-249) Prashna result."""
    canonical = await calculate_natal(req)
    res = _horary_engine.evaluate_horary(
        horary_number=req.horary_number,
        canonical_natal=canonical,
        category=req.category or "GENERAL"
    )
    return res

@router.post("/time-travel")
async def time_travel_scan(req: TimeTravelScanCalculationRequest):
    """Scans arbitrary past/future date for 5-level Dasha + Transit snapshot & event activation score."""
    canonical = await calculate_natal(req)
    target_dt = datetime.fromisoformat(req.target_datetime_utc.replace("Z", "+00:00"))
    res = await _temporal_scanner.time_travel_scan(
        canonical_natal=canonical,
        target_datetime_utc=target_dt,
        topic=req.topic or "GENERAL"
    )
    return res

@router.post("/muhurat", response_model=MuhuratFinderResult)
async def find_smart_muhurats(req: SmartMuhuratCalculationRequest):
    """Calculates top auspicious Muhurats over 7-30 days based on Chandra/Tara Bala and Rahu Kaal avoidance."""
    canonical = await calculate_natal(req)
    res = _muhurat_engine.find_muhurats(
        canonical_natal=canonical,
        category=req.category or "GENERAL",
        days_ahead=req.days_ahead or 30
    )
    return res

@router.post("/stress-alert", response_model=StressAlertResult)
async def evaluate_stress_alert(req: StressAlertCalculationRequest):
    """Calculates real-time Mental Peace score (0-100) and detects Ashtama/Dwadasha Moon stress transits."""
    canonical = await calculate_natal(req)
    target_dt = datetime.fromisoformat(req.target_datetime_utc.replace("Z", "+00:00")) if req.target_datetime_utc else None
    res = _stress_engine.evaluate_mental_peace(
        canonical_natal=canonical,
        target_datetime_utc=target_dt
    )
    return res

@router.post("/numerology-synergy", response_model=NumerologySynergyResult)
async def evaluate_numerology_synergy(req: NumerologySynergyCalculationRequest):
    """Computes Moolank, Bhagyank, Namank, and Daily Energy Score synergy with active Dasha lord."""
    canonical = await calculate_natal(req)
    target_dt = datetime.fromisoformat(req.target_datetime_utc.replace("Z", "+00:00")) if req.target_datetime_utc else None
    res = _numerology_engine.evaluate_synergy(
        canonical_natal=canonical,
        target_datetime_utc=target_dt
    )
    return res

@router.post("/ashtakoot-matching", response_model=AshtakootMatchingResult)
async def calculate_ashtakoot_matching(req: AshtakootMatchingCalculationRequest):
    """Calculates 36-Gun Ashtakoot matching, Dosh Parihar rules, and Manglik cancellation."""
    groom_canonical = await calculate_natal(req.groom)
    bride_canonical = await calculate_natal(req.bride)
    res = _ashtakoot_engine.evaluate_matching(
        groom_canonical=groom_canonical,
        bride_canonical=bride_canonical,
        groom_name=req.groom_name or req.groom.name or "Groom",
        bride_name=req.bride_name or req.bride.name or "Bride"
    )
    return res

@router.post("/event-journal/feedback")
async def record_prediction_feedback(req: EventJournalFeedbackRequest):
    """Records user confirmation feedback on prediction accuracy (Rule 22 Blind Testing)."""
    res = _journal_engine.record_feedback(
        entry_id=req.entry_id,
        actual_outcome=req.actual_outcome,
        actual_event_date=req.actual_event_date,
        feedback_notes=req.feedback_notes
    )
    if not res:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    return res

@router.get("/event-journal/stats", response_model=AccuracyStatistics)
async def get_accuracy_statistics(profile_id: Optional[str] = None):
    """Calculates live prediction accuracy statistics and calibration score."""
    return _journal_engine.calculate_accuracy_stats(profile_id)



