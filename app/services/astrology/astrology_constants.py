"""Astrological constants for Rashi, Nakshatra, and Vimshottari Lordship calculations."""

RASHI_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

RASHI_LORDS = [
    "Mars", "Venus", "Mercury", "Moon",
    "Sun", "Mercury", "Venus", "Mars",
    "Jupiter", "Saturn", "Saturn", "Jupiter"
]

NAKSHATRA_NAMES = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu",
    "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta",
    "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha",
    "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada",
    "Uttara Bhadrapada", "Revati"
]

VIMSHOTTARI_LORDS = [
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"
]

VIMSHOTTARI_YEARS = {
    "Ketu": 7,
    "Venus": 20,
    "Sun": 6,
    "Moon": 10,
    "Mars": 7,
    "Rahu": 18,
    "Jupiter": 16,
    "Saturn": 19,
    "Mercury": 17
}

NAKSHATRA_ARC = 13.333333333333334 # 13°20' in degrees

def get_rashi_info(sidereal_longitude: float):
    lon = sidereal_longitude % 360.0
    rashi_idx = int(lon // 30)
    rashi_name = RASHI_NAMES[rashi_idx]
    sign_lord = RASHI_LORDS[rashi_idx]
    degree_in_rashi = lon % 30.0
    return rashi_idx, rashi_name, sign_lord, degree_in_rashi

def get_nakshatra_info(sidereal_longitude: float):
    lon = sidereal_longitude % 360.0
    nak_idx = int(lon // NAKSHATRA_ARC)
    if nak_idx >= 27:
        nak_idx = 26
    nak_name = NAKSHATRA_NAMES[nak_idx]
    star_lord = VIMSHOTTARI_LORDS[nak_idx % 9]
    
    # Pada (1 to 4)
    arc_in_nak = lon - (nak_idx * NAKSHATRA_ARC)
    pada = int(arc_in_nak // (NAKSHATRA_ARC / 4.0)) + 1
    if pada > 4:
        pada = 4

    # Sub Lord calculation
    star_lord_idx = VIMSHOTTARI_LORDS.index(star_lord)
    current_offset = 0.0
    sub_lord = star_lord
    for i in range(9):
        p_name = VIMSHOTTARI_LORDS[(star_lord_idx + i) % 9]
        p_years = VIMSHOTTARI_YEARS[p_name]
        p_sub_arc = NAKSHATRA_ARC * (p_years / 120.0)
        if current_offset <= arc_in_nak < (current_offset + p_sub_arc):
            sub_lord = p_name
            break
        current_offset += p_sub_arc

    return nak_idx, nak_name, star_lord, pada, sub_lord
