"""Deterministic KP (Krishnamurti Paddhati) Engine.

Executes exact KP calculations over canonical Swiss Ephemeris facts:
1. Exact Vimshottari proportional Sub Lord and Sub-Sub-Lord (SSL) calculations.
2. Placidus house planet occupancies and cusp lordships.
3. 4-Level House and Planet Significators.
4. Ruling Planets (RP) with Node Proxies.
5. Deterministic Event House Evidence generation.
"""
import datetime
from typing import List, Dict, Tuple, Set, Any
from app.services.astrology.astrology_constants import (
    RASHI_NAMES,
    RASHI_LORDS,
    NAKSHATRA_NAMES,
    VIMSHOTTARI_LORDS,
    VIMSHOTTARI_YEARS,
    NAKSHATRA_ARC,
    get_rashi_info,
    get_nakshatra_info
)
from app.schemas.canonical_astrology import CanonicalAstrologyResult
from app.schemas.kp_astrology import (
    KPCuspFact,
    KPPlanetFact,
    KPSignificators,
    HouseSignificatorsFact,
    PlanetSignificatorFact,
    NodeProxyFact,
    KPRulingPlanetsFact,
    KPEventRuleEvidence,
    KPChartResult
)

DAY_LORDS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]

def get_kp_sub_and_ssl(longitude: float) -> Tuple[str, str]:
    """Calculate exact Vimshottari proportional Sub Lord and Sub-Sub Lord (SSL)."""
    lon = longitude % 360.0
    nak_idx = int(lon // NAKSHATRA_ARC)
    if nak_idx >= 27:
        nak_idx = 26
    
    star_lord = VIMSHOTTARI_LORDS[nak_idx % 9]
    arc_in_nak = lon - (nak_idx * NAKSHATRA_ARC)

    # Calculate Sub Lord
    star_lord_idx = VIMSHOTTARI_LORDS.index(star_lord)
    sub_lord = star_lord
    p_sub_arc = 0.0
    sub_start_offset = 0.0

    current_offset = 0.0
    for i in range(9):
        p_name = VIMSHOTTARI_LORDS[(star_lord_idx + i) % 9]
        p_years = VIMSHOTTARI_YEARS[p_name]
        sub_arc = NAKSHATRA_ARC * (p_years / 120.0)
        
        if current_offset <= arc_in_nak < (current_offset + sub_arc) or (i == 8 and arc_in_nak >= current_offset):
            sub_lord = p_name
            p_sub_arc = sub_arc
            sub_start_offset = current_offset
            break
        current_offset += sub_arc

    # Calculate Sub-Sub Lord (SSL)
    arc_in_sub = arc_in_nak - sub_start_offset
    sub_lord_idx = VIMSHOTTARI_LORDS.index(sub_lord)
    ssl_lord = sub_lord

    ssl_offset = 0.0
    for j in range(9):
        q_name = VIMSHOTTARI_LORDS[(sub_lord_idx + j) % 9]
        q_years = VIMSHOTTARI_YEARS[q_name]
        ssl_arc = p_sub_arc * (q_years / 120.0)

        if ssl_offset <= arc_in_sub < (ssl_offset + ssl_arc) or (j == 8 and arc_in_sub >= ssl_offset):
            ssl_lord = q_name
            break
        ssl_offset += ssl_arc

    return sub_lord, ssl_lord

def is_lon_in_house(lon: float, cusp_start: float, cusp_end: float) -> bool:
    """Check if longitude lies within Placidus house starting at cusp_start and ending at cusp_end."""
    lon = lon % 360.0
    start = cusp_start % 360.0
    end = cusp_end % 360.0

    if start < end:
        return start <= lon < end
    else:
        # Spans across 360/0 degree boundary
        return lon >= start or lon < end

class KPEngine:
    def calculate_kp(self, canonical: CanonicalAstrologyResult) -> KPChartResult:
        # 1. Process Placidus Cusps with Sign/Star/Sub/SSL lords
        cusp_lons = [c.sidereal_longitude for c in canonical.kp.cusps]
        if len(cusp_lons) < 12:
            # Fallback if less than 12
            cusp_lons = [(canonical.angles.ascendant.sidereal_longitude + (i * 30.0)) % 360.0 for i in range(12)]

        # Map planets to Placidus houses
        planet_house_map: Dict[str, int] = {}
        house_occupants: Dict[int, List[str]] = {h: [] for h in range(1, 13)}

        for p in canonical.planets:
            p_lon = p.sidereal_longitude
            assigned_house = 1
            for h in range(1, 13):
                c_start = cusp_lons[h - 1]
                c_end = cusp_lons[h % 12]
                if is_lon_in_house(p_lon, c_start, c_end):
                    assigned_house = h
                    break
            planet_house_map[p.body] = assigned_house
            house_occupants[assigned_house].append(p.body)

        # Cusp facts
        cusp_facts: List[KPCuspFact] = []
        house_lords: Dict[int, str] = {}  # house_number -> sign_lord

        for i, c_lon in enumerate(cusp_lons):
            h_num = i + 1
            r_idx, r_name, sign_lord, deg_in_rashi = get_rashi_info(c_lon)
            n_idx, n_name, star_lord, pada, _ = get_nakshatra_info(c_lon)
            sub_lord, ssl_lord = get_kp_sub_and_ssl(c_lon)
            house_lords[h_num] = sign_lord

            cf = KPCuspFact(
                house_number=h_num,
                sidereal_longitude=c_lon,
                rashi=r_idx,
                rashi_name=r_name,
                degree_in_rashi=deg_in_rashi,
                sign_lord=sign_lord,
                star_lord=star_lord,
                sub_lord=sub_lord,
                sub_sub_lord=ssl_lord,
                occupants=house_occupants[h_num]
            )
            cusp_facts.append(cf)

        # 2. Process Planet facts
        planet_facts: List[KPPlanetFact] = []
        planet_star_lords: Dict[str, str] = {}

        for p in canonical.planets:
            p_lon = p.sidereal_longitude
            r_idx, r_name, sign_lord, deg_in_rashi = get_rashi_info(p_lon)
            n_idx, n_name, star_lord, pada, _ = get_nakshatra_info(p_lon)
            sub_lord, ssl_lord = get_kp_sub_and_ssl(p_lon)

            planet_star_lords[p.body] = star_lord
            h_occ = planet_house_map.get(p.body, 1)

            # Houses owned by this planet's sign lordship
            h_owned = [h for h, lord in house_lords.items() if lord == sign_lord]

            pf = KPPlanetFact(
                body=p.body,
                sidereal_longitude=p_lon,
                rashi=r_idx,
                rashi_name=r_name,
                degree_in_rashi=deg_in_rashi,
                house_occupying=h_occ,
                houses_owning=h_owned,
                sign_lord=sign_lord,
                star_lord=star_lord,
                sub_lord=sub_lord,
                sub_sub_lord=ssl_lord
            )
            planet_facts.append(pf)

        # 3. Compute 4-Level House Significators
        # Level 1: Planets in star of occupants of House H
        # Level 2: Occupants of House H
        # Level 3: Planets in star of Lord of House H
        # Level 4: Lord of House H
        house_sig_facts: List[HouseSignificatorsFact] = []
        planet_sig_map: Dict[str, Dict[int, List[int]]] = {
            p.body: {1: [], 2: [], 3: [], 4: []} for p in canonical.planets
        }

        for h_num in range(1, 13):
            occupants = house_occupants[h_num]
            h_lord = house_lords[h_num]

            # Level 1: Planets in star of occupants
            lvl1_planets = [
                p_name for p_name, s_lord in planet_star_lords.items() if s_lord in occupants
            ]

            # Level 2: Occupants
            lvl2_planets = list(occupants)

            # Level 3: Planets in star of house lord
            lvl3_planets = [
                p_name for p_name, s_lord in planet_star_lords.items() if s_lord == h_lord
            ]

            # Level 4: House Lord
            lvl4_house_lord = h_lord

            # Combine unique ordered
            combined_set = []
            for p_list in [lvl1_planets, lvl2_planets, lvl3_planets, [lvl4_house_lord]]:
                for p_item in p_list:
                    if p_item and p_item not in combined_set:
                        combined_set.append(p_item)

            sig_fact = HouseSignificatorsFact(
                house_number=h_num,
                significators=KPSignificators(
                    level1_planets_in_star_of_occupants=lvl1_planets,
                    level2_occupants=lvl2_planets,
                    level3_planets_in_star_of_lord=lvl3_planets,
                    level4_house_lord=lvl4_house_lord,
                    combined_significators=combined_set
                )
            )
            house_sig_facts.append(sig_fact)

            # Update reverse planet significators map
            for p_name in lvl1_planets:
                if h_num not in planet_sig_map[p_name][1]:
                    planet_sig_map[p_name][1].append(h_num)
            for p_name in lvl2_planets:
                if h_num not in planet_sig_map[p_name][2]:
                    planet_sig_map[p_name][2].append(h_num)
            for p_name in lvl3_planets:
                if h_num not in planet_sig_map[p_name][3]:
                    planet_sig_map[p_name][3].append(h_num)
            if h_lord in planet_sig_map:
                if h_num not in planet_sig_map[h_lord][4]:
                    planet_sig_map[h_lord][4].append(h_num)

        # Build PlanetSignificatorFact list
        planet_sig_facts: List[PlanetSignificatorFact] = []
        for p in canonical.planets:
            levels = planet_sig_map[p.body]
            all_signified = sorted(list(set(levels[1] + levels[2] + levels[3] + levels[4])))
            psf = PlanetSignificatorFact(
                planet=p.body,
                level1_houses=sorted(levels[1]),
                level2_houses=sorted(levels[2]),
                level3_houses=sorted(levels[3]),
                level4_houses=sorted(levels[4]),
                all_signified_houses=all_signified
            )
            planet_sig_facts.append(psf)

        # 4. Compute Ruling Planets (RP)
        asc_lon = canonical.angles.ascendant.sidereal_longitude
        asc_r_idx, _, asc_sign_lord, _ = get_rashi_info(asc_lon)
        _, _, asc_star_lord, _, asc_sub_lord = get_nakshatra_info(asc_lon)

        moon_p = next((p for p in canonical.planets if p.body == "Moon"), canonical.planets[0])
        moon_lon = moon_p.sidereal_longitude
        _, _, moon_sign_lord, _ = get_rashi_info(moon_lon)
        _, _, moon_star_lord, _, moon_sub_lord = get_nakshatra_info(moon_lon)

        # Day Lord (Weekday at birth)
        # Parse local_date / utc_instant to get day of week
        try:
            dt = datetime.datetime.fromisoformat(canonical.birth.utc_instant.replace("Z", "+00:00"))
            day_idx = dt.weekday()  # Monday is 0, Sunday is 6
            # Map Python weekday (Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6) to Day Lord
            # Sun->Sun, Mon->Moon, Tue->Mars, Wed->Mercury, Thu->Jupiter, Fri->Venus, Sat->Saturn
            weekday_map = ["Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Sun"]
            day_lord = weekday_map[day_idx]
        except Exception:
            day_lord = "Sun"

        # Rahu & Ketu proxy representations
        nodes_proxy: List[NodeProxyFact] = []
        for node_name in ["Rahu", "Ketu"]:
            node_p = next((p for p in canonical.planets if p.body == node_name), None)
            if node_p:
                proxies = [node_p.sign_lord, node_p.star_lord]
                nodes_proxy.append(NodeProxyFact(node=node_name, proxies=list(set(proxies))))

        # Core Ruling Planets list
        rp_list = []
        for rp in [asc_star_lord, asc_sign_lord, moon_star_lord, moon_sign_lord, day_lord]:
            if rp and rp not in rp_list:
                rp_list.append(rp)

        rp_fact = KPRulingPlanetsFact(
            lagna_sign_lord=asc_sign_lord,
            lagna_star_lord=asc_star_lord,
            lagna_sub_lord=asc_sub_lord,
            moon_sign_lord=moon_sign_lord,
            moon_star_lord=moon_star_lord,
            moon_sub_lord=moon_sub_lord,
            day_lord=day_lord,
            nodes_as_proxies=nodes_proxy,
            ruling_planets_list=rp_list
        )

        # 5. Compute KP Event Rule Evidence
        events_def = [
            {
                "name": "Marriage & Relationships",
                "primary": [7],
                "supporting": [2, 11],
                "obstruction": [1, 6, 10]
            },
            {
                "name": "Career & Promotion",
                "primary": [10],
                "supporting": [2, 6, 11],
                "obstruction": [1, 5, 9]
            },
            {
                "name": "Financial Gain & Wealth",
                "primary": [11],
                "supporting": [2, 6],
                "obstruction": [5, 8, 12]
            },
            {
                "name": "Health / Disease Recovery",
                "primary": [6],
                "supporting": [8, 12],
                "obstruction": [1, 5, 11]  # 1,5,11 act as recovery
            },
            {
                "name": "Higher Education",
                "primary": [9],
                "supporting": [4, 11],
                "obstruction": [3, 8]
            },
            {
                "name": "Foreign Travel",
                "primary": [3, 9, 12],
                "supporting": [],
                "obstruction": [4]
            }
        ]

        event_evidences: List[KPEventRuleEvidence] = []
        for ed in events_def:
            p_houses = ed["primary"]
            s_houses = ed["supporting"]
            o_houses = ed["obstruction"]
            fav_houses = set(p_houses + s_houses)

            fav_planets = []
            unfav_planets = []

            for psf in planet_sig_facts:
                signified = set(psf.all_signified_houses)
                has_fav = len(signified.intersection(fav_houses)) > 0
                has_obs = len(signified.intersection(set(o_houses))) > 0

                if has_fav and not has_obs:
                    fav_planets.append(psf.planet)
                elif has_obs and not has_fav:
                    unfav_planets.append(psf.planet)

            rule_text = (
                f"Primary Houses: {p_houses}, Supporting: {s_houses}, Obstruction: {o_houses}. "
                f"Favorable Planets signifying primary/supporting without obstruction: {', '.join(fav_planets) if fav_planets else 'None'}."
            )

            evidence = KPEventRuleEvidence(
                event_name=ed["name"],
                primary_houses=p_houses,
                supporting_houses=s_houses,
                obstruction_houses=o_houses,
                favorable_planets=fav_planets,
                unfavorable_planets=unfav_planets,
                rule_evidence=rule_text
            )
            event_evidences.append(evidence)

        return KPChartResult(
            calculation_id=canonical.identity.calculation_id,
            profile_id=canonical.identity.profile_id,
            input_hash=canonical.identity.input_hash,
            calculation_version="4.0.0",
            cusps=cusp_facts,
            planets=planet_facts,
            house_significators=house_sig_facts,
            planet_significators=planet_sig_facts,
            ruling_planets=rp_fact,
            event_evidences=event_evidences,
            metadata={
                "ayanamsha": canonical.provider.ayanamsha_name,
                "ayanamsha_value": canonical.provider.ayanamsha_value,
                "house_system": "Placidus (KP)",
                "node_mode": canonical.provider.node_mode
            }
        )
