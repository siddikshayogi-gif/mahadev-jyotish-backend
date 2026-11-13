"""Vedic Core Calculation Engine.

Consumes CanonicalAstrologyResult (from Swiss Ephemeris) and computes deterministic
Vedic chart facts:
- D1 Rashi Chart (Whole Sign Houses)
- D9 Navamsha Chart (Deterministic 3°20' mapping)
- D10 Dashamsha Chart (Deterministic 3°00' mapping)\n- D2 Hora, D4 Chaturthamsha, D7 Saptamsha, D12 Dwadashamsha\n- D20 Vimshamsha, D24 Chaturvimshamsha/Siddhamsha\n- Ashtakavarga (BAV + SAV)\n- Phase-1 Shadbala supporting-strength layer
- Bhava Chalit (Placidus Cusp Midpoint boundaries)
- Chandra Kundali (Moon Rashi as House 1)
- House Lordship Engine
- Planetary Dignity Engine
- Vargottama Detection
"""

from typing import List, Dict, Tuple, Any
from app.schemas.canonical_astrology import CanonicalAstrologyResult
from app.schemas.vedic_astrology import (
    VedicChartResult,
    VedicPlanetFact,
    LagnaFact,
    HouseLordshipFact,
    BhavaChalitHouseFact,
    ChandraKundaliHouseFact,
    VargaChartFact,
    Dignity
)
from app.services.astrology.astrology_constants import (
    RASHI_NAMES,
    RASHI_LORDS
)

# ---------------------------------------------------------
# Planetary Dignity Reference Tables & Logic
# ---------------------------------------------------------

EXALTATION = {
    "Sun": (0, 10.0),      # Aries (0), peak 10°
    "Moon": (1, 3.0),      # Taurus (1), peak 3°
    "Mars": (9, 28.0),     # Capricorn (9), peak 28°
    "Mercury": (5, 15.0),  # Virgo (5), peak 15°
    "Jupiter": (3, 5.0),   # Cancer (3), peak 5°
    "Venus": (11, 27.0),   # Pisces (11), peak 27°
    "Saturn": (6, 20.0),   # Libra (6), peak 20°
    "Rahu": (1, None),     # Taurus (1)
    "Ketu": (7, None)      # Scorpio (7)
}

DEBILITATION = {
    "Sun": 6,      # Libra (6)
    "Moon": 7,     # Scorpio (7)
    "Mars": 3,     # Cancer (3)
    "Mercury": 11, # Pisces (11)
    "Jupiter": 9,  # Capricorn (9)
    "Venus": 5,    # Virgo (5)
    "Saturn": 0,   # Aries (0)
    "Rahu": 7,     # Scorpio (7)
    "Ketu": 1      # Taurus (1)
}

MOOLATRIKONA = {
    "Sun": (4, 0.0, 20.0),       # Leo 0°-20°
    "Moon": (1, 3.0, 30.0),      # Taurus 3°-30°
    "Mars": (0, 0.0, 12.0),      # Aries 0°-12°
    "Mercury": (5, 15.0, 20.0),  # Virgo 15°-20°
    "Jupiter": (8, 0.0, 10.0),   # Sagittarius 0°-10°
    "Venus": (6, 0.0, 15.0),     # Libra 0°-15°
    "Saturn": (10, 0.0, 20.0)    # Aquarius 0°-20°
}

OWN_SIGNS = {
    "Sun": [4],
    "Moon": [3],
    "Mars": [0, 7],
    "Mercury": [2, 5],
    "Jupiter": [8, 11],
    "Venus": [1, 6],
    "Saturn": [9, 10],
    "Rahu": [1, 2],
    "Ketu": [7, 8]
}

NATURAL_FRIENDS = {
    "Sun": ["Moon", "Mars", "Jupiter"],
    "Moon": ["Sun", "Mercury"],
    "Mars": ["Sun", "Moon", "Jupiter"],
    "Mercury": ["Sun", "Venus"],
    "Jupiter": ["Sun", "Moon", "Mars"],
    "Venus": ["Mercury", "Saturn"],
    "Saturn": ["Mercury", "Venus"],
    "Rahu": ["Venus", "Saturn", "Mercury"],
    "Ketu": ["Mars", "Venus", "Saturn"]
}

NATURAL_ENEMIES = {
    "Sun": ["Venus", "Saturn"],
    "Moon": [],
    "Mars": ["Mercury"],
    "Mercury": ["Moon"],
    "Jupiter": ["Mercury", "Venus"],
    "Venus": ["Sun", "Moon"],
    "Saturn": ["Sun", "Moon", "Mars"],
    "Rahu": ["Sun", "Moon", "Mars"],
    "Ketu": ["Sun", "Moon"]
}

def calculate_dignity(planet: str, rashi: int, degree_in_rashi: float) -> Dignity:
    """Computes exact Parashari planetary dignity deterministically."""
    # 1. Check Exaltation
    if planet in EXALTATION and EXALTATION[planet][0] == rashi:
        return Dignity.EXALTED

    # 2. Check Debilitation
    if planet in DEBILITATION and DEBILITATION[planet] == rashi:
        return Dignity.DEBILITATED

    # 3. Check Moolatrikona
    if planet in MOOLATRIKONA:
        m_rashi, m_start, m_end = MOOLATRIKONA[planet]
        if rashi == m_rashi and m_start <= degree_in_rashi <= m_end:
            return Dignity.MOOLATRIKONA

    # 4. Check Own Sign
    if planet in OWN_SIGNS and rashi in OWN_SIGNS[planet]:
        return Dignity.OWN_SIGN

    # 5. Check Sign Lord Relationship (Friendly / Neutral / Enemy)
    sign_lord = RASHI_LORDS[rashi]
    if sign_lord == planet:
        return Dignity.OWN_SIGN

    if sign_lord in NATURAL_FRIENDS.get(planet, []):
        return Dignity.FRIENDLY
    if sign_lord in NATURAL_ENEMIES.get(planet, []):
        return Dignity.ENEMY
    
    return Dignity.NEUTRAL

# ---------------------------------------------------------
# Varga Mathematical Division Formulas
# ---------------------------------------------------------

def calculate_d9_rashi(sidereal_longitude: float) -> Tuple[int, str]:
    """Calculates D9 (Navamsha) Rashi (0..11) and name.
    
    Each Navamsha = 3°20' = 3.3333333333333335°
    Movable (Chara 0,3,6,9): starts from sign itself.
    Fixed (Sthira 1,4,7,10): starts from 9th sign from itself.
    Dual (Dvisvabhava 2,5,8,11): starts from 5th sign from itself.
    """
    lon = sidereal_longitude % 360.0
    rashi = int(lon // 30.0)
    deg_in_sign = lon % 30.0
    
    navamsha_idx = int(deg_in_sign // (3.0 + 1.0/3.0)) # 0..8
    if navamsha_idx > 8:
        navamsha_idx = 8

    rashi_type = rashi % 3
    if rashi_type == 0:  # Movable (Chara)
        start_rashi = rashi
    elif rashi_type == 1:  # Fixed (Sthira)
        start_rashi = (rashi + 8) % 12
    else:  # Dual (Dvisvabhava)
        start_rashi = (rashi + 4) % 12

    d9_rashi = (start_rashi + navamsha_idx) % 12
    return d9_rashi, RASHI_NAMES[d9_rashi]

def calculate_d10_rashi(sidereal_longitude: float) -> Tuple[int, str]:
    """Calculates D10 (Dashamsha) Rashi (0..11) and name.
    
    Each Dashamsha = 3°
    Odd signs (0, 2, 4, 6, 8, 10): starts from sign itself.
    Even signs (1, 3, 5, 7, 9, 11): starts from 9th sign from itself.
    """
    lon = sidereal_longitude % 360.0
    rashi = int(lon // 30.0)
    deg_in_sign = lon % 30.0
    
    dashamsha_idx = int(deg_in_sign // 3.0) # 0..9
    if dashamsha_idx > 9:
        dashamsha_idx = 9

    is_odd_sign = (rashi % 2 == 0) # 0-indexed: 0=Aries (Odd), 1=Taurus (Even)
    if is_odd_sign:
        start_rashi = rashi
    else:
        start_rashi = (rashi + 8) % 12

    d10_rashi = (start_rashi + dashamsha_idx) % 12
    return d10_rashi, RASHI_NAMES[d10_rashi]


def calculate_d2_rashi(sidereal_longitude: float) -> Tuple[int, str]:
    """D2 Hora: odd signs Sun/Leo then Moon/Cancer; even signs reverse."""
    lon = sidereal_longitude % 360.0
    rashi = int(lon // 30.0)
    deg = lon % 30.0
    odd_sign = (rashi % 2 == 0)
    first_half = deg < 15.0
    if odd_sign:
        d2 = 4 if first_half else 3   # Leo, Cancer
    else:
        d2 = 3 if first_half else 4   # Cancer, Leo
    return d2, RASHI_NAMES[d2]


def calculate_d4_rashi(sidereal_longitude: float) -> Tuple[int, str]:
    """D4 Chaturthamsha: divisions map to 1st, 4th, 7th, 10th from sign."""
    lon = sidereal_longitude % 360.0
    rashi = int(lon // 30.0)
    idx = min(3, int((lon % 30.0) // 7.5))
    d4 = (rashi + idx * 3) % 12
    return d4, RASHI_NAMES[d4]


def calculate_d7_rashi(sidereal_longitude: float) -> Tuple[int, str]:
    """D7 Saptamsha: odd signs from self; even signs from 7th."""
    lon = sidereal_longitude % 360.0
    rashi = int(lon // 30.0)
    part = 30.0 / 7.0
    idx = min(6, int((lon % 30.0) // part))
    start = rashi if (rashi % 2 == 0) else (rashi + 6) % 12
    d7 = (start + idx) % 12
    return d7, RASHI_NAMES[d7]


def calculate_d12_rashi(sidereal_longitude: float) -> Tuple[int, str]:
    """D12 Dwadashamsha: 12 divisions counted sequentially from the sign."""
    lon = sidereal_longitude % 360.0
    rashi = int(lon // 30.0)
    idx = min(11, int((lon % 30.0) // 2.5))
    d12 = (rashi + idx) % 12
    return d12, RASHI_NAMES[d12]


def calculate_d20_rashi(sidereal_longitude: float) -> Tuple[int, str]:
    """D20 Vimshamsha (Parashari): movable starts Aries, fixed Sagittarius, dual Leo."""
    lon = sidereal_longitude % 360.0
    rashi = int(lon // 30.0)
    idx = min(19, int((lon % 30.0) // 1.5))
    rashi_type = rashi % 3
    if rashi_type == 0:       # movable
        start = 0             # Aries
    elif rashi_type == 1:     # fixed
        start = 8             # Sagittarius
    else:                     # dual
        start = 4             # Leo
    d20 = (start + idx) % 12
    return d20, RASHI_NAMES[d20]


def calculate_d24_rashi(sidereal_longitude: float) -> Tuple[int, str]:
    """D24 Chaturvimshamsha/Siddhamsha: odd starts Leo, even starts Cancer."""
    lon = sidereal_longitude % 360.0
    rashi = int(lon // 30.0)
    part = 30.0 / 24.0
    idx = min(23, int((lon % 30.0) // part))
    start = 4 if (rashi % 2 == 0) else 3  # Leo for odd, Cancer for even
    d24 = (start + idx) % 12
    return d24, RASHI_NAMES[d24]


D60_DEITIES = [
    "Ghora", "Rakshasa", "Deva", "Kubera", "Yaksha", "Kinnara", "Bhrashta", "Kulaghna",
    "Garala", "Agni", "Maya", "Preta", "Apampathi", "Devaganesha", "Indra", "Varuna",
    "Yama", "Panki", "Sarpadevata", "Amrita", "Chandra", "Vishnu", "Prabhanjana", "Vaivasvata",
    "Vamadeva", "Deva", "Ardra", "Kalinasa", "Kshiteesa", "Kamalakara", "Gulika", "Mrityu",
    "Kala", "Davagni", "Ghora", "Yama", "Kantaka", "Sudha", "Amrita", "Poornachandra",
    "Vishadagdha", "Kulanasa", "Vamsakshaya", "Utpata", "Kala", "Saumya", "Komala", "Sheetala",
    "Karaladamshtra", "Chandramukha", "Praveena", "Kalapavaka", "Dandayudha", "Nirmala", "Shubha", "Ashubha",
    "Atiseethala", "Sudhasheetala", "Dhwaja", "Sreeniketa"
]

def calculate_d30_rashi(sidereal_longitude: float) -> Tuple[int, str]:
    """D30 Trimshamsha (Parashari): 5 unequal divisions per sign."""
    lon = sidereal_longitude % 360.0
    rashi = int(lon // 30.0)
    deg = lon % 30.0
    odd_sign = (rashi % 2 == 0)

    if odd_sign:
        if deg < 5.0: d30 = 0        # Aries (Mars)
        elif deg < 10.0: d30 = 10    # Aquarius (Saturn)
        elif deg < 18.0: d30 = 8     # Sagittarius (Jupiter)
        elif deg < 25.0: d30 = 2     # Gemini (Mercury)
        else: d30 = 6                # Libra (Venus)
    else:
        if deg < 5.0: d30 = 1        # Taurus (Venus)
        elif deg < 12.0: d30 = 5     # Virgo (Mercury)
        elif deg < 20.0: d30 = 11    # Pisces (Jupiter)
        elif deg < 25.0: d30 = 9     # Capricorn (Saturn)
        else: d30 = 7                # Scorpio (Mars)

    return d30, RASHI_NAMES[d30]

def calculate_d60_rashi(sidereal_longitude: float) -> Tuple[int, str]:
    """D60 Shashtiamsha (Parashari): 60 equal divisions (0.5° each)."""
    lon = sidereal_longitude % 360.0
    rashi = int(lon // 30.0)
    k = min(59, int((lon % 30.0) // 0.5))
    odd_sign = (rashi % 2 == 0)

    if odd_sign:
        d60 = (rashi + k) % 12
    else:
        d60 = (rashi + 6 + k) % 12

    return d60, RASHI_NAMES[d60]

def get_d60_deity(sidereal_longitude: float) -> str:
    """Returns Parashari 60-Deity name for D60 Shashtiamsha."""
    lon = sidereal_longitude % 360.0
    rashi = int(lon // 30.0)
    k = min(59, int((lon % 30.0) // 0.5))
    odd_sign = (rashi % 2 == 0)
    if odd_sign:
        return D60_DEITIES[k]
    else:
        return D60_DEITIES[59 - k]


def _build_varga_fact(
    varga_name: str,
    asc_lon: float,
    planets,
    calculator,
) -> VargaChartFact:

    lagna_rashi, lagna_name = calculator(asc_lon)
    houses: Dict[str, List[str]] = {str(h): [] for h in range(1, 13)}
    planet_rashis: Dict[str, int] = {}
    planet_rashi_names: Dict[str, str] = {}
    planet_houses: Dict[str, int] = {}

    for p in planets:
        vr, vr_name = calculator(p.sidereal_longitude)
        h = ((vr - lagna_rashi) % 12) + 1
        houses[str(h)].append(p.body)
        planet_rashis[p.body] = vr
        planet_rashi_names[p.body] = vr_name
        planet_houses[p.body] = h

    return VargaChartFact(
        varga_name=varga_name,
        lagna_rashi=lagna_rashi,
        lagna_rashi_name=lagna_name,
        houses=houses,
        planet_rashis=planet_rashis,
        planet_rashi_names=planet_rashi_names,
        planet_houses=planet_houses,
    )


# ---------------------------------------------------------
# Bhava Chalit Boundaries Logic
# ---------------------------------------------------------

def _circular_midpoint(lon1: float, lon2: float) -> float:
    """Computes circular midpoint between two longitudes on 0..360 circle."""
    diff = (lon2 - lon1) % 360.0
    return (lon1 + diff / 2.0) % 360.0

def _is_between_circular(lon: float, start: float, end: float) -> bool:
    """Checks if longitude lies within arc from start to end clockwise."""
    lon = lon % 360.0
    start = start % 360.0
    end = end % 360.0
    if start < end:
        return start <= lon < end
    else:
        return lon >= start or lon < end

class VedicEngine:
    """Deterministic Vedic Astrology Engine."""

    def calculate_vedic_chart(self, canonical: CanonicalAstrologyResult) -> VedicChartResult:
        # 1. Extract Lagna (Ascendant) & D1 Lagna Rashi
        asc_lon = canonical.angles.ascendant.sidereal_longitude
        d1_lagna_rashi = canonical.angles.ascendant.rashi
        
        d1_lagna = LagnaFact(
            name="D1 Lagna",
            sidereal_longitude=asc_lon,
            rashi=d1_lagna_rashi,
            rashi_name=canonical.angles.ascendant.rashi_name,
            degree_in_rashi=canonical.angles.ascendant.degree_in_rashi,
            sign_lord=canonical.angles.ascendant.sign_lord
        )

        # 2. Extract D9 Lagna and D10 Lagna
        d9_lagna_rashi, d9_lagna_name = calculate_d9_rashi(asc_lon)
        d9_lagna = LagnaFact(
            name="D9 Lagna",
            sidereal_longitude=asc_lon,
            rashi=d9_lagna_rashi,
            rashi_name=d9_lagna_name,
            degree_in_rashi=asc_lon % 3.3333333333333335,
            sign_lord=RASHI_LORDS[d9_lagna_rashi]
        )

        d10_lagna_rashi, d10_lagna_name = calculate_d10_rashi(asc_lon)
        d10_lagna = LagnaFact(
            name="D10 Lagna",
            sidereal_longitude=asc_lon,
            rashi=d10_lagna_rashi,
            rashi_name=d10_lagna_name,
            degree_in_rashi=asc_lon % 3.0,
            sign_lord=RASHI_LORDS[d10_lagna_rashi]
        )

        # 3. Find Moon for Chandra Lagna
        moon_p = next(p for p in canonical.planets if p.body == "Moon")
        chandra_rashi = moon_p.rashi
        chandra_lagna = LagnaFact(
            name="Chandra Lagna",
            sidereal_longitude=moon_p.sidereal_longitude,
            rashi=chandra_rashi,
            rashi_name=moon_p.rashi_name,
            degree_in_rashi=moon_p.degree_in_rashi,
            sign_lord=moon_p.sign_lord
        )

        # 4. Calculate Bhava Chalit Midpoint Boundaries
        # Cusps 1..12 longitudes
        cusp_lons = [c.sidereal_longitude for c in canonical.kp.cusps]
        # Midpoints M_1..M_12
        midpoints = []
        for i in range(12):
            prev_cusp = cusp_lons[i - 1] # cusp_lons[-1] is cusp 12 for i=0
            curr_cusp = cusp_lons[i]
            m = _circular_midpoint(prev_cusp, curr_cusp)
            midpoints.append(m)

        # 5. Process Planets & Map Placements
        planet_facts: List[VedicPlanetFact] = []
        planet_dict_by_name: Dict[str, VedicPlanetFact] = {}

        # Tracking occupants for Vargas and Charts
        d1_house_occupants: Dict[str, List[str]] = {str(h): [] for h in range(1, 13)}
        d9_house_occupants: Dict[str, List[str]] = {str(h): [] for h in range(1, 13)}
        d10_house_occupants: Dict[str, List[str]] = {str(h): [] for h in range(1, 13)}
        chalit_house_occupants: Dict[str, List[str]] = {str(h): [] for h in range(1, 13)}
        chandra_house_occupants: Dict[str, List[str]] = {str(h): [] for h in range(1, 13)}

        for p in canonical.planets:
            # D1 Whole Sign House
            h_d1 = ((p.rashi - d1_lagna_rashi) % 12) + 1
            d1_house_occupants[str(h_d1)].append(p.body)

            # D9 Rashi & House
            d9_r, d9_r_name = calculate_d9_rashi(p.sidereal_longitude)
            h_d9 = ((d9_r - d9_lagna_rashi) % 12) + 1
            d9_house_occupants[str(h_d9)].append(p.body)

            # D10 Rashi & House
            d10_r, d10_r_name = calculate_d10_rashi(p.sidereal_longitude)
            h_d10 = ((d10_r - d10_lagna_rashi) % 12) + 1
            d10_house_occupants[str(h_d10)].append(p.body)

            # Bhava Chalit House
            chalit_h = 1
            for h in range(1, 13):
                m_start = midpoints[h - 1]
                m_end = midpoints[h % 12]
                if _is_between_circular(p.sidereal_longitude, m_start, m_end):
                    chalit_h = h
                    break
            chalit_house_occupants[str(chalit_h)].append(p.body)

            # Chandra Kundali House
            chandra_h = ((p.rashi - chandra_rashi) % 12) + 1
            chandra_house_occupants[str(chandra_h)].append(p.body)

            # Dignity
            dignity_val = calculate_dignity(p.body, p.rashi, p.degree_in_rashi)

            # Vargottama Check
            is_vargottama = (p.rashi == d9_r)

            fact = VedicPlanetFact(
                body=p.body,
                sidereal_longitude=p.sidereal_longitude,
                tropical_longitude=p.tropical_longitude,
                speed=p.speed,
                retrograde=p.retrograde,
                rashi=p.rashi,
                rashi_name=p.rashi_name,
                degree_in_rashi=p.degree_in_rashi,
                house_d1=h_d1,
                nakshatra=p.nakshatra,
                nakshatra_name=p.nakshatra_name,
                pada=p.pada,
                sign_lord=p.sign_lord,
                star_lord=p.star_lord,
                sub_lord=p.sub_lord,
                dignity=dignity_val,
                d9_rashi=d9_r,
                d9_rashi_name=d9_r_name,
                d9_house=h_d9,
                d10_rashi=d10_r,
                d10_rashi_name=d10_r_name,
                d10_house=h_d10,
                bhava_chalit_house=chalit_h,
                chandra_kundali_house=chandra_h,
                vargottama=is_vargottama
            )
            planet_facts.append(fact)
            planet_dict_by_name[p.body] = fact

        # 6. House Lordship Engine (D1 Whole Sign Houses 1..12)
        house_lordships: List[HouseLordshipFact] = []
        for h_num in range(1, 13):
            h_rashi = (d1_lagna_rashi + h_num - 1) % 12
            h_rashi_name = RASHI_NAMES[h_rashi]
            h_lord_name = RASHI_LORDS[h_rashi]

            # Find lord planet fact
            lord_p = planet_dict_by_name.get(h_lord_name)
            if lord_p:
                lord_natal_h = lord_p.house_d1
                lord_r = lord_p.rashi
                lord_r_name = lord_p.rashi_name
                lord_dignity = lord_p.dignity
            else:
                # Fallback for outer lords if any
                lord_natal_h = 1
                lord_r = h_rashi
                lord_r_name = h_rashi_name
                lord_dignity = Dignity.OWN_SIGN

            h_fact = HouseLordshipFact(
                house_number=h_num,
                rashi=h_rashi,
                rashi_name=h_rashi_name,
                house_lord=h_lord_name,
                lord_natal_house=lord_natal_h,
                lord_rashi=lord_r,
                lord_rashi_name=lord_r_name,
                lord_dignity=lord_dignity,
                occupants=d1_house_occupants[str(h_num)]
            )
            house_lordships.append(h_fact)

        # 7. Build Varga Summaries
        # Existing D1/D9/D10 remain fully backward-compatible.
        d1_planet_rashis = {p.body: p.rashi for p in planet_facts}
        d1_planet_rashi_names = {p.body: p.rashi_name for p in planet_facts}
        d1_planet_houses = {p.body: p.house_d1 for p in planet_facts}

        d9_planet_rashis = {p.body: p.d9_rashi for p in planet_facts}
        d9_planet_rashi_names = {p.body: p.d9_rashi_name for p in planet_facts}
        d9_planet_houses = {p.body: p.d9_house for p in planet_facts}

        d10_planet_rashis = {p.body: p.d10_rashi for p in planet_facts}
        d10_planet_rashi_names = {p.body: p.d10_rashi_name for p in planet_facts}
        d10_planet_houses = {p.body: p.d10_house for p in planet_facts}

        vargas = {
            "D1": VargaChartFact(
                varga_name="D1",
                lagna_rashi=d1_lagna_rashi,
                lagna_rashi_name=RASHI_NAMES[d1_lagna_rashi],
                houses=d1_house_occupants,
                planet_rashis=d1_planet_rashis,
                planet_rashi_names=d1_planet_rashi_names,
                planet_houses=d1_planet_houses,
            ),
            "D9": VargaChartFact(
                varga_name="D9",
                lagna_rashi=d9_lagna_rashi,
                lagna_rashi_name=d9_lagna_name,
                houses=d9_house_occupants,
                planet_rashis=d9_planet_rashis,
                planet_rashi_names=d9_planet_rashi_names,
                planet_houses=d9_planet_houses,
            ),
            "D10": VargaChartFact(
                varga_name="D10",
                lagna_rashi=d10_lagna_rashi,
                lagna_rashi_name=d10_lagna_name,
                houses=d10_house_occupants,
                planet_rashis=d10_planet_rashis,
                planet_rashi_names=d10_planet_rashi_names,
                planet_houses=d10_planet_houses,
            ),
            "D2": _build_varga_fact("D2", asc_lon, canonical.planets, calculate_d2_rashi),
            "D4": _build_varga_fact("D4", asc_lon, canonical.planets, calculate_d4_rashi),
            "D7": _build_varga_fact("D7", asc_lon, canonical.planets, calculate_d7_rashi),
            "D12": _build_varga_fact("D12", asc_lon, canonical.planets, calculate_d12_rashi),
            "D20": _build_varga_fact("D20", asc_lon, canonical.planets, calculate_d20_rashi),
            "D24": _build_varga_fact("D24", asc_lon, canonical.planets, calculate_d24_rashi),
            "D30": _build_varga_fact("D30", asc_lon, canonical.planets, calculate_d30_rashi),
            "D60": _build_varga_fact("D60", asc_lon, canonical.planets, calculate_d60_rashi),
        }

        # Attach D60 deity names metadata
        d60_fact = vargas["D60"]
        d60_deities = {p.body: get_d60_deity(p.sidereal_longitude) for p in canonical.planets}
        d60_deities["Ascendant"] = get_d60_deity(asc_lon)
        vargas["D60"] = VargaChartFact(
            varga_name=d60_fact.varga_name,
            lagna_rashi=d60_fact.lagna_rashi,
            lagna_rashi_name=d60_fact.lagna_rashi_name,
            houses=d60_fact.houses,
            planet_rashis=d60_fact.planet_rashis,
            planet_rashi_names=d60_fact.planet_rashi_names,
            planet_houses=d60_fact.planet_houses,
            metadata={"d60_deities": d60_deities}
        )

        # 8. Build Bhava Chalit Summary
        bhava_chalit_list: List[BhavaChalitHouseFact] = []
        for h in range(1, 13):
            m_start = midpoints[h - 1]
            m_end = midpoints[h % 12]
            c_mid = cusp_lons[h - 1]
            b_fact = BhavaChalitHouseFact(
                house_number=h,
                start_longitude=m_start,
                midpoint_longitude=c_mid,
                end_longitude=m_end,
                occupants=chalit_house_occupants[str(h)]
            )
            bhava_chalit_list.append(b_fact)

        # 9. Build Chandra Kundali Summary
        chandra_kundali_list: List[ChandraKundaliHouseFact] = []
        for h in range(1, 13):
            c_rashi = (chandra_rashi + h - 1) % 12
            ck_fact = ChandraKundaliHouseFact(
                house_number=h,
                rashi=c_rashi,
                rashi_name=RASHI_NAMES[c_rashi],
                sign_lord=RASHI_LORDS[c_rashi],
                occupants=chandra_house_occupants[str(h)]
            )
            chandra_kundali_list.append(ck_fact)

        # 10. Strength layers: Ashtakavarga + Phase-1 Shadbala support
        # Local imports avoid import cycles and keep the Vedic core modular.
        from app.services.astrology.ashtakavarga_engine import AshtakavargaEngine
        from app.services.astrology.shadbala_engine import ShadbalaEngine

        ashtakavarga_result = AshtakavargaEngine().calculate(
            planets=planet_facts,
            lagna_rashi=d1_lagna_rashi,
        )
        shadbala_result = ShadbalaEngine().calculate(planet_facts)

        return VedicChartResult(
            calculation_id=canonical.identity.calculation_id,
            profile_id=canonical.identity.profile_id,
            input_hash=canonical.identity.input_hash,
            calculation_version="4.0.0",
            d1_lagna=d1_lagna,
            d9_lagna=d9_lagna,
            d10_lagna=d10_lagna,
            chandra_lagna=chandra_lagna,
            planets=planet_facts,
            house_lordships=house_lordships,
            vargas=vargas,
            bhava_chalit=bhava_chalit_list,
            chandra_kundali=chandra_kundali_list,
            shadbala=shadbala_result,
            ashtakavarga=ashtakavarga_result,
            metadata={
                "ayanamsha_value": canonical.provider.ayanamsha_value,
                "julian_day_ut": canonical.birth.julian_day_ut,
                "engine": "Deterministic Vedic Engine v4.0",
                "added_vargas": ["D2", "D4", "D7", "D12", "D20", "D24"],
                "ashtakavarga": "PARASHARI_BAV_SAV",
                "shadbala": "PHASE1_NORMALIZED_SUPPORT"
            }
        )
