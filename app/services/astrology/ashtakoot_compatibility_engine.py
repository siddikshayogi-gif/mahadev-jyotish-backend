"""36-Gun Ashtakoot & Dual Overlay Compatibility Engine.

Executes exact 36-Gun Ashtakoot matching (Varna, Vashya, Tara, Yoni, Graha Maitri, Gana, Bhakoot, Nadi),
Nadi & Bhakoot Dosh Parihar rules, and Manglik Dosh cancellation checks.
"""

from typing import Dict, List, Tuple, Any, Optional
from pydantic import BaseModel

from app.services.astrology.astrology_constants import RASHI_NAMES, RASHI_LORDS, NAKSHATRA_NAMES
from app.services.astrology.vedic_engine import VedicEngine, NATURAL_FRIENDS, NATURAL_ENEMIES
from app.schemas.canonical_astrology import CanonicalAstrologyResult

# ---------------------------------------------------------
# Ashtakoot Constants & Reference Tables
# ---------------------------------------------------------

# Varna: 0=Aries (Kshatriya=3), 1=Taurus (Vaishya=2), 2=Gemini (Shudra=1), 3=Cancer (Brahmin=4)
VARNA_MAP = [3, 2, 1, 4, 3, 2, 1, 4, 3, 2, 1, 4]  # Rashi 0..11 -> Varna Level 1..4

# Gana for 27 Nakshatras: 1=Deva, 2=Manushya, 3=Rakshasa
# 0: Ashwini(Deva), 1: Bharani(Man), 2: Krittika(Rak), 3: Rohini(Man), 4: Mrigashira(Deva), 5: Aridra(Man),
# 6: Punarvasu(Deva), 7: Pushya(Deva), 8: Ashlesha(Rak), 9: Magha(Rak), 10: Purva Phal(Man), 11: Uttara Phal(Man),
# 12: Hasta(Deva), 13: Chitra(Rak), 14: Swati(Deva), 15: Vishakha(Rak), 16: Anuradha(Deva), 17: Jyeshta(Rak),
# 18: Moola(Rak), 19: Purvashadha(Man), 20: Uttarashadha(Man), 21: Shravana(Deva), 22: Dhanishta(Rak),
# 23: Shatabhisha(Rak), 24: Purva Bhadra(Man), 25: Uttara Bhadra(Man), 26: Revati(Deva)
GANA_MAP = [1, 2, 3, 2, 1, 2, 1, 1, 3, 3, 2, 2, 1, 3, 1, 3, 1, 3, 3, 2, 2, 1, 3, 3, 2, 2, 1]

# Nadi for 27 Nakshatras: 1=Adi, 2=Madhya, 3=Antya
# 0: Adi, 1: Madhya, 2: Antya, 3: Antya, 4: Madhya, 5: Adi, 6: Adi, 7: Madhya, 8: Antya...
NADI_MAP = [1, 2, 3, 3, 2, 1, 1, 2, 3, 3, 2, 1, 1, 2, 3, 3, 2, 1, 1, 2, 3, 3, 2, 1, 1, 2, 3]

# Yoni Animal for 27 Nakshatras (0..13)
# 0: Horse, 1: Elephant, 2: Sheep, 3: Serpent, 4: Dog, 5: Cat, 6: Rat,
# 7: Cow, 8: Buffalo, 9: Tiger, 10: Deer, 11: Monkey, 12: Mongoose, 13: Lion
YONI_MAP = [0, 1, 2, 3, 3, 4, 5, 2, 5, 6, 6, 7, 8, 9, 7, 9, 10, 10, 4, 11, 12, 11, 13, 0, 13, 8, 1]

# Sworn enemy Yoni pairs
YONI_ENEMIES = {
    (0, 8), (8, 0),   # Horse vs Buffalo
    (1, 13), (13, 1), # Elephant vs Lion
    (2, 11), (11, 2), # Sheep vs Monkey
    (3, 12), (12, 3), # Serpent vs Mongoose
    (4, 10), (10, 4), # Dog vs Deer
    (5, 6), (6, 5),   # Cat vs Rat
    (7, 9), (9, 7)    # Cow vs Tiger
}

class GunDetailFact(BaseModel):
    name: str
    max_points: float
    obtained_points: float
    description: str
    dosh_present: bool = False
    parihar_applied: bool = False

class ManglikDetailFact(BaseModel):
    person_name: str
    is_manglik: bool
    manglik_houses: List[int]
    cancellation_reasons: List[str]

class AshtakootMatchingResult(BaseModel):
    groom_name: str
    bride_name: str
    total_score: float  # 0 to 36
    score_percentage: float  # 0 to 100
    compatibility_verdict: str  # "EXCELLENT", "GOOD", "AVERAGE", "POOR"
    gun_details: List[GunDetailFact]
    bhakoot_dosh_parihar: bool
    nadi_dosh_parihar: bool
    groom_manglik: ManglikDetailFact
    bride_manglik: ManglikDetailFact
    is_manglik_match_acceptable: bool
    summary_hindi: str
    summary_english: str

class AshtakootCompatibilityEngine:
    def __init__(self):
        self.vedic_engine = VedicEngine()

    def evaluate_matching(
        self,
        groom_canonical: CanonicalAstrologyResult,
        bride_canonical: CanonicalAstrologyResult,
        groom_name: str = "Groom",
        bride_name: str = "Bride"
    ) -> AshtakootMatchingResult:
        # Extract Moon facts for Groom and Bride
        g_moon = next(p for p in groom_canonical.planets if p.body == "Moon")
        b_moon = next(p for p in bride_canonical.planets if p.body == "Moon")

        g_rashi = g_moon.rashi
        g_nak = g_moon.nakshatra
        g_lord = g_moon.sign_lord

        b_rashi = b_moon.rashi
        b_nak = b_moon.nakshatra
        b_lord = b_moon.sign_lord

        details: List[GunDetailFact] = []

        # 1. Varna (1 Point)
        g_varna = VARNA_MAP[g_rashi]
        b_varna = VARNA_MAP[b_rashi]
        varna_pts = 1.0 if g_varna >= b_varna else 0.0
        details.append(GunDetailFact(
            name="Varna (वर्ण)", max_points=1.0, obtained_points=varna_pts,
            description=f"Groom Varna: {g_varna}, Bride Varna: {b_varna}."
        ))

        # 2. Vashya (2 Points)
        vashya_pts = 2.0 if g_rashi == b_rashi else 1.0
        if abs(g_rashi - b_rashi) in [1, 5, 7]: vashya_pts = 1.5
        details.append(GunDetailFact(
            name="Vashya (वश्य)", max_points=2.0, obtained_points=vashya_pts,
            description=f"Groom Rashi: {RASHI_NAMES[g_rashi]}, Bride Rashi: {RASHI_NAMES[b_rashi]}."
        ))

        # 3. Tara (3 Points)
        t1 = ((g_nak - b_nak) % 9) + 1
        t2 = ((b_nak - g_nak) % 9) + 1
        fav_taras = [2, 4, 6, 8, 9]
        t1_good = t1 in fav_taras
        t2_good = t2 in fav_taras
        tara_pts = 3.0 if (t1_good and t2_good) else (1.5 if (t1_good or t2_good) else 0.0)
        details.append(GunDetailFact(
            name="Tara (तारा)", max_points=3.0, obtained_points=tara_pts,
            description=f"Tara Counts: {t1} & {t2}."
        ))

        # 4. Yoni (4 Points)
        g_yoni = YONI_MAP[g_nak]
        b_yoni = YONI_MAP[b_nak]
        if g_yoni == b_yoni: yoni_pts = 4.0
        elif (g_yoni, b_yoni) in YONI_ENEMIES: yoni_pts = 0.0
        else: yoni_pts = 2.0
        details.append(GunDetailFact(
            name="Yoni (योनि)", max_points=4.0, obtained_points=yoni_pts,
            description=f"Yoni Types: {g_yoni} & {b_yoni}."
        ))

        # 5. Graha Maitri (5 Points)
        if g_lord == b_lord: maitri_pts = 5.0
        elif b_lord in NATURAL_FRIENDS.get(g_lord, []) and g_lord in NATURAL_FRIENDS.get(b_lord, []): maitri_pts = 5.0
        elif b_lord in NATURAL_FRIENDS.get(g_lord, []) or g_lord in NATURAL_FRIENDS.get(b_lord, []): maitri_pts = 4.0
        elif b_lord in NATURAL_ENEMIES.get(g_lord, []) and g_lord in NATURAL_ENEMIES.get(b_lord, []): maitri_pts = 0.0
        else: maitri_pts = 3.0
        details.append(GunDetailFact(
            name="Graha Maitri (ग्रह मैत्री)", max_points=5.0, obtained_points=maitri_pts,
            description=f"Groom Lord: {g_lord}, Bride Lord: {b_lord}."
        ))

        # 6. Gana (6 Points)
        g_gana = GANA_MAP[g_nak]
        b_gana = GANA_MAP[b_nak]
        if g_gana == b_gana: gana_pts = 6.0
        elif (g_gana == 1 and b_gana == 2) or (g_gana == 2 and b_gana == 1): gana_pts = 5.0
        elif (g_gana == 1 and b_gana == 3): gana_pts = 1.0
        else: gana_pts = 0.0
        details.append(GunDetailFact(
            name="Gana (गण)", max_points=6.0, obtained_points=gana_pts,
            description=f"Groom Gana: {g_gana}, Bride Gana: {b_gana}."
        ))

        # 7. Bhakoot (7 Points) & Bhakoot Dosh Parihar
        rashi_diff = (g_rashi - b_rashi) % 12
        bhakoot_dosh = rashi_diff in [1, 5, 7, 11]  # 2/12, 6/8, 5/9, 7/11 relative
        bhakoot_parihar = False

        if bhakoot_dosh:
            # Parihar 1: Same Rashi Lord (e.g. Aries/Scorpio=Mars, Taurus/Libra=Venus)
            if g_lord == b_lord or b_lord in NATURAL_FRIENDS.get(g_lord, []):
                bhakoot_parihar = True

        if not bhakoot_dosh:
            bhakoot_pts = 7.0
        elif bhakoot_parihar:
            bhakoot_pts = 7.0
        else:
            bhakoot_pts = 0.0

        details.append(GunDetailFact(
            name="Bhakoot (भकूट)", max_points=7.0, obtained_points=bhakoot_pts,
            description="Bhakoot Dosh Parihar applied." if bhakoot_parihar else ("Bhakoot Dosh Present." if bhakoot_dosh else "Auspicious Bhakoot."),
            dosh_present=bhakoot_dosh and not bhakoot_parihar,
            parihar_applied=bhakoot_parihar
        ))

        # 8. Nadi (8 Points) & Nadi Dosh Parihar
        g_nadi = NADI_MAP[g_nak]
        b_nadi = NADI_MAP[b_nak]
        nadi_dosh = (g_nadi == b_nadi)
        nadi_parihar = False

        if nadi_dosh:
            # Parihar Rules: Different Nakshatra within same Rashi or Same Rashi Lord
            if g_rashi != b_rashi and g_lord == b_lord:
                nadi_parihar = True
            elif g_nak != b_nak and g_rashi == b_rashi:
                nadi_parihar = True

        if not nadi_dosh:
            nadi_pts = 8.0
        elif nadi_parihar:
            nadi_pts = 8.0
        else:
            nadi_pts = 0.0

        details.append(GunDetailFact(
            name="Nadi (नाड़ी)", max_points=8.0, obtained_points=nadi_pts,
            description="Nadi Dosh Parihar applied." if nadi_parihar else ("Nadi Dosh Present." if nadi_dosh else "Auspicious Nadi."),
            dosh_present=nadi_dosh and not nadi_parihar,
            parihar_applied=nadi_parihar
        ))

        # Total Gun Score
        total_gun = sum(d.obtained_points for d in details)
        percentage = round((total_gun / 36.0) * 100.0, 1)

        if total_gun >= 28: verdict = "EXCELLENT"
        elif total_gun >= 20: verdict = "GOOD"
        elif total_gun >= 18: verdict = "AVERAGE"
        else: verdict = "POOR"

        # Manglik Analysis
        g_manglik = self._evaluate_manglik(groom_canonical, groom_name)
        b_manglik = self._evaluate_manglik(bride_canonical, bride_name)

        # Dual Manglik Cancellation
        is_manglik_match_ok = True
        if g_manglik.is_manglik and not b_manglik.is_manglik:
            is_manglik_match_ok = False
        elif not g_manglik.is_manglik and b_manglik.is_manglik:
            is_manglik_match_ok = False

        sum_hi = f"{groom_name} और {bride_name} का अष्टकूट मिलान स्कोर: {total_gun}/36 ({percentage}%) - {verdict}। "
        if bhakoot_parihar: sum_hi += "भकूट दोष परिहार लागू। "
        if nadi_parihar: sum_hi += "नाड़ी दोष परिहार लागू। "

        sum_en = f"{groom_name} & {bride_name} Ashtakoot Score: {total_gun}/36 ({percentage}%) - {verdict}. "
        if bhakoot_parihar: sum_en += "Bhakoot Dosh Parihar applied. "
        if nadi_parihar: sum_en += "Nadi Dosh Parihar applied. "

        return AshtakootMatchingResult(
            groom_name=groom_name,
            bride_name=bride_name,
            total_score=total_gun,
            score_percentage=percentage,
            compatibility_verdict=verdict,
            gun_details=details,
            bhakoot_dosh_parihar=bhakoot_parihar,
            nadi_dosh_parihar=nadi_parihar,
            groom_manglik=g_manglik,
            bride_manglik=b_manglik,
            is_manglik_match_acceptable=is_manglik_match_ok,
            summary_hindi=sum_hi,
            summary_english=sum_en
        )

    def _evaluate_manglik(self, canonical: CanonicalAstrologyResult, name: str) -> ManglikDetailFact:
        vedic = self.vedic_engine.calculate_vedic_chart(canonical)
        mars_p = next(p for p in vedic.planets if p.body == "Mars")

        # Houses from D1 Lagna, Moon, and Venus
        h_lagna = mars_p.house_d1
        h_moon = mars_p.chandra_kundali_house

        v_p = next(p for p in vedic.planets if p.body == "Venus")
        h_venus = ((mars_p.rashi - v_p.rashi) % 12) + 1

        manglik_houses = []
        for h, label in [(h_lagna, "Lagna"), (h_moon, "Moon"), (h_venus, "Venus")]:
            if h in [1, 4, 7, 8, 12] and h not in manglik_houses:
                manglik_houses.append(h)

        is_manglik = len(manglik_houses) > 0
        reasons = []

        if is_manglik:
            # Cancellation checks
            if mars_p.rashi in [0, 7]:  # Aries/Scorpio (Own Sign)
                is_manglik = False
                reasons.append("Mars in own sign (Aries/Scorpio).")
            elif mars_p.rashi == 9:     # Exalted Capricorn
                is_manglik = False
                reasons.append("Mars exalted in Capricorn.")
            elif h_lagna == 4 and mars_p.rashi in [0, 7]:
                is_manglik = False
                reasons.append("Mars in 4th house in own sign.")

        return ManglikDetailFact(
            person_name=name,
            is_manglik=is_manglik,
            manglik_houses=manglik_houses,
            cancellation_reasons=reasons
        )
