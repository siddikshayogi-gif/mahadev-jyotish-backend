"""Mental Peace & Stress Alert Engine.

Calculates real-time mental peace score (0-100) and detects Ashtama/Dwadasha Moon transits
and stressful Dasha activations.
Provides classical BPHS / Jyotish Ratnakar remedies & mantras.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.schemas.canonical_astrology import CanonicalAstrologyResult
from app.services.astrology.gochar_engine import GocharEngine
from app.services.astrology.dasha_engine import DashaEngine
from app.services.astrology.vedic_engine import VedicEngine

CLASSICAL_REMEDIES = {
    "STRESS_ALERT": {
        "mantra_hindi": "ॐ नमः शिवाय ॥ (108 बार जाप करें)",
        "mantra_sanskrit": "ॐ त्र्यम्बकं यजामहे सुगन्धिं पुष्टिवर्धनम्। उर्वारुकमिव बन्धनान्मृत्यॉर्मुक्षीय मामृतात्॥",
        "upaya_hindi": "भगवान शिव को कच्चा दूध और जल अर्पित करें। शाम को 15 मिनट ध्यान (Meditation) करें और शांत रहें।",
        "upaya_english": "Offer water/milk to Lord Shiva. Practice 15 minutes of mindfulness meditation in the evening."
    },
    "MODERATE_PACING": {
        "mantra_hindi": "ॐ सोमाय नमः ॥ (21 बार जाप)",
        "mantra_sanskrit": "ॐ सों सोमाय नमः॥",
        "upaya_hindi": "चंद्रमा को अर्घ्य दें और पर्याप्त जल का सेवन करें। किसी भी वाद-विवाद से बचें।",
        "upaya_english": "Offer Arghya to the Moon and drink adequate water. Avoid unnecessary arguments."
    },
    "PEACEFUL": {
        "mantra_hindi": "ॐ नमो भगवते वासुदेवाय ॥",
        "mantra_sanskrit": "ॐ श्रीं ह्रीं क्लीं श्री सिद्ध लक्ष्म्यै नमः॥",
        "upaya_hindi": "आपका दिन अनुकूल है। सकारात्मक कार्यों में ऊर्जा लगाएं और ईश्वर का आभार व्यक्त करें।",
        "upaya_english": "Auspicious day for mental peace. Channel your energy into creative work."
    }
}

class StressAlertResult(BaseModel):
    status: str  # "PEACEFUL", "MODERATE_PACING", "STRESS_ALERT"
    mental_peace_score: float  # 0 to 100
    transit_moon_house_from_lagna: int
    transit_moon_house_from_chandra: int
    is_ashtama_moon: bool
    is_dwadasha_moon: bool
    active_dasha_chain: List[str]
    stress_factors: List[str]
    mantra_hindi: str
    mantra_sanskrit: str
    remedy_hindi: str
    remedy_english: str

class MentalPeaceStressEngine:
    def __init__(self):
        self.gochar_engine = GocharEngine()
        self.dasha_engine = DashaEngine()
        self.vedic_engine = VedicEngine()

    def evaluate_mental_peace(
        self,
        canonical_natal: CanonicalAstrologyResult,
        target_datetime_utc: Optional[datetime] = None
    ) -> StressAlertResult:
        if target_datetime_utc is None:
            target_datetime_utc = datetime.now(timezone.utc)
        if target_datetime_utc.tzinfo is None:
            target_datetime_utc = target_datetime_utc.replace(tzinfo=timezone.utc)

        vedic = self.vedic_engine.calculate_vedic_chart(canonical_natal)
        gochar = self.gochar_engine.calculate_gochar_snapshot(canonical_natal, target_datetime_utc)

        moon_p = next(p for p in canonical_natal.planets if p.body == "Moon")
        birth_utc = datetime.fromisoformat(canonical_natal.birth.utc_instant.replace("Z", "+00:00"))
        if birth_utc.tzinfo is None: birth_utc = birth_utc.replace(tzinfo=timezone.utc)

        dasha = self.dasha_engine.calculate_dasha_hierarchy(
            moon_longitude=moon_p.sidereal_longitude,
            birth_datetime_utc=birth_utc,
            target_datetime_utc=target_datetime_utc,
            max_depth=5
        )
        active_chain = [d.lord for d in dasha.active_chain]

        # Transit Moon analysis
        t_moon = next(t for t in gochar.transits if t.body == "Moon")
        h_lagna = t_moon.house_from_d1_lagna
        h_chandra = t_moon.house_from_moon

        is_ashtama = (h_lagna == 8 or h_chandra == 8)
        is_dwadasha = (h_lagna == 12 or h_chandra == 12)

        score = 85.0
        factors = []

        if is_ashtama:
            score -= 30.0
            factors.append("गोचर चंद्रमा अष्टम (8th) भाव में स्थित है - मानसिक अस्थिरता सम्भव।")
        elif is_dwadasha:
            score -= 20.0
            factors.append("गोचर चंद्रमा द्वादश (12th) भाव में स्थित है - अकारण चिंता या थकान सम्भव।")
        elif h_lagna == 6 or h_chandra == 6:
            score -= 15.0
            factors.append("गोचर चंद्रमा षष्ठ (6th) भाव में स्थित है।")

        # Dasha Lords Stress Factor
        stressful_planets = {"Saturn", "Rahu", "Ketu", "Mars"}
        # Find 6th, 8th, 12th lords from D1
        dusthana_lords = {h.house_lord for h in vedic.house_lordships if h.house_number in [6, 8, 12]}
        stressful_planets.update(dusthana_lords)

        # Check Active Dasha chain (MD, AD, PD)
        for idx, lord in enumerate(active_chain[:3]):
            if lord in stressful_planets:
                penalty = 12.0 if idx == 0 else (8.0 if idx == 1 else 5.0)
                score -= penalty
                factors.append(f"सक्रिय दशा स्वामी {lord} तनाव कारक हो सकता है।")

        # Transit Saturn / Rahu aspect on Moon
        t_saturn = next((t for t in gochar.transits if t.body == "Saturn"), None)
        if t_saturn and t_saturn.house_from_moon in [1, 8, 12]:
            score -= 15.0
            factors.append("शनि की साढ़ेसाती या ढैय्या गोचर प्रभाव।")

        score = max(10.0, min(98.0, round(score, 1)))

        if score < 50.0:
            status = "STRESS_ALERT"
        elif score < 75.0:
            status = "MODERATE_PACING"
        else:
            status = "PEACEFUL"

        remedy_info = CLASSICAL_REMEDIES[status]

        return StressAlertResult(
            status=status,
            mental_peace_score=score,
            transit_moon_house_from_lagna=h_lagna,
            transit_moon_house_from_chandra=h_chandra,
            is_ashtama_moon=is_ashtama,
            is_dwadasha_moon=is_dwadasha,
            active_dasha_chain=active_chain,
            stress_factors=factors if factors else ["मानसिक स्थिति शांत और संतुलित है।"],
            mantra_hindi=remedy_info["mantra_hindi"],
            mantra_sanskrit=remedy_info["mantra_sanskrit"],
            remedy_hindi=remedy_info["upaya_hindi"],
            remedy_english=remedy_info["upaya_english"]
        )
