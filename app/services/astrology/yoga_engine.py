"""Classical Vedic Yoga Evaluation Engine.

Evaluates catalogued classical Vedic Yogas with deterministic rules and strict source citations.
"""

from typing import List, Dict, Optional
import uuid

from app.schemas.vedic_astrology import VedicChartResult, Dignity
from app.schemas.dasha_gochar_yoga import YogaFact, YogaResult

class YogaEngine:
    """Deterministic Classical Yoga Evaluation Engine."""

    def evaluate_yogas(
        self,
        vedic_chart: VedicChartResult,
        profile_id: str = "prof_default"
    ) -> YogaResult:
        """Evaluates catalogued classical Yogas for the provided Vedic chart."""
        yogas: List[YogaFact] = []

        planet_dict = {p.body: p for p in vedic_chart.planets}
        house_lord_dict = {h.house_number: h.house_lord for h in vedic_chart.house_lordships}

        lagna_rashi = vedic_chart.d1_lagna.rashi
        moon_planet = planet_dict.get("Moon")
        sun_planet = planet_dict.get("Sun")
        mercury_planet = planet_dict.get("Mercury")
        jupiter_planet = planet_dict.get("Jupiter")
        mars_planet = planet_dict.get("Mars")
        venus_planet = planet_dict.get("Venus")
        saturn_planet = planet_dict.get("Saturn")

        # 1. Gajakesari Yoga (Jupiter in Kendra from Moon)
        if jupiter_planet and moon_planet:
            jup_house_from_moon = ((jupiter_planet.rashi - moon_planet.rashi) % 12) + 1
            if jup_house_from_moon in [1, 4, 7, 10]:
                yogas.append(
                    YogaFact(
                        id="gajakesari_yoga",
                        name="Gajakesari Yoga",
                        name_hindi="गजकेसरी योग",
                        category="SPECIAL",
                        description="Jupiter in Kendra (1, 4, 7, 10) from Moon brings wisdom, wealth, reputation, and virtuous character.",
                        planets_involved=["Jupiter", "Moon"],
                        houses_involved=[jupiter_planet.house_d1, moon_planet.house_d1],
                        is_active=True,
                        strength_score=85.0,
                        source_reference="Brihat Parashara Hora Shastra Ch. 36, Sloka 3"
                    )
                )

        # 2. Budhaditya Yoga (Sun & Mercury in same house)
        if sun_planet and mercury_planet:
            if sun_planet.house_d1 == mercury_planet.house_d1:
                yogas.append(
                    YogaFact(
                        id="budhaditya_yoga",
                        name="Budhaditya Yoga",
                        name_hindi="बुधादित्य योग",
                        category="SPECIAL",
                        description="Sun and Mercury conjunct in the same house confers high intelligence, administrative skill, and learning.",
                        planets_involved=["Sun", "Mercury"],
                        houses_involved=[sun_planet.house_d1],
                        is_active=True,
                        strength_score=75.0,
                        source_reference="Brihat Parashara Hora Shastra Ch. 36, Sloka 8"
                    )
                )

        # 3. Pancha Mahapurusha Yogas (Mars, Mercury, Jupiter, Venus, Saturn in Kendra & Own/Exalted)
        mahapurusha_configs = [
            ("Ruchaka Yoga", "रुचक योग", mars_planet, "Mars", "courage, leadership, and athletic vigor", "BPHS Ch. 76"),
            ("Bhadra Yoga", "भद्र योग", mercury_planet, "Mercury", "sharp intellect, eloquence, and commercial success", "BPHS Ch. 76"),
            ("Hamsa Yoga", "हंस योग", jupiter_planet, "Jupiter", "spiritual wisdom, purity, and universal reverence", "BPHS Ch. 76"),
            ("Malavya Yoga", "मालव्य योग", venus_planet, "Venus", "artistic grace, luxury, vehicles, and marital bliss", "BPHS Ch. 76"),
            ("Sasa Yoga", "शश योग", saturn_planet, "Saturn", "authority over masses, perseverance, and political acumen", "BPHS Ch. 76")
        ]

        for y_name, y_hindi, p_obj, p_name, desc, src in mahapurusha_configs:
            if p_obj:
                if p_obj.house_d1 in [1, 4, 7, 10] and p_obj.dignity in [Dignity.OWN_SIGN, Dignity.EXALTED, Dignity.MOOLATRIKONA]:
                    yogas.append(
                        YogaFact(
                            id=y_name.lower().replace(" ", "_"),
                            name=y_name,
                            name_hindi=y_hindi,
                            category="MAHAPURUSHA",
                            description=f"{p_name} exalted or in own sign in Kendra house ({p_obj.house_d1}) bestows {desc}.",
                            planets_involved=[p_name],
                            houses_involved=[p_obj.house_d1],
                            is_active=True,
                            strength_score=90.0,
                            source_reference=f"Brihat Parashara Hora Shastra Ch. 76 (Pancha Mahapurusha)"
                        )
                    )

        # 4. Raja Yogas (Kendra lord + Trikona lord conjunction)
        kendra_houses = [1, 4, 7, 10]
        trikona_houses = [1, 5, 9]

        raja_yoga_pairs = []
        for k_h in kendra_houses:
            k_lord_name = house_lord_dict.get(k_h)
            if not k_lord_name:
                continue
            k_lord_p = planet_dict.get(k_lord_name)
            if not k_lord_p:
                continue

            for t_h in trikona_houses:
                t_lord_name = house_lord_dict.get(t_h)
                if not t_lord_name or t_lord_name == k_lord_name:
                    continue
                t_lord_p = planet_dict.get(t_lord_name)
                if not t_lord_p:
                    continue

                if k_lord_p.house_d1 == t_lord_p.house_d1:
                    pair_key = tuple(sorted([k_lord_name, t_lord_name]))
                    if pair_key not in raja_yoga_pairs:
                        raja_yoga_pairs.append(pair_key)
                        yogas.append(
                            YogaFact(
                                id=f"raja_yoga_{k_lord_name}_{t_lord_name}".lower(),
                                name=f"Raja Yoga ({k_lord_name} + {t_lord_name})",
                                name_hindi=f"राजयोग ({k_lord_name} + {t_lord_name})",
                                category="RAJA_YOGA",
                                description=f"Kendra lord ({k_h}H) {k_lord_name} conjunct Trikona lord ({t_h}H) {t_lord_name} in House {k_lord_p.house_d1} confers high power, status, and success.",
                                planets_involved=[k_lord_name, t_lord_name],
                                houses_involved=[k_lord_p.house_d1, k_h, t_h],
                                is_active=True,
                                strength_score=88.0,
                                source_reference="Brihat Parashara Hora Shastra Ch. 35, Sloka 11"
                            )
                        )

        # 5. Dhana Yogas (2nd & 11th lord connection)
        h2_lord = house_lord_dict.get(2)
        h11_lord = house_lord_dict.get(11)
        if h2_lord and h11_lord:
            p2 = planet_dict.get(h2_lord)
            p11 = planet_dict.get(h11_lord)
            if p2 and p11:
                if p2.house_d1 == p11.house_d1 or (p2.house_d1 in [2, 11] and p11.house_d1 in [2, 11]):
                    yogas.append(
                        YogaFact(
                            id="dhana_yoga_2_11",
                            name="Dhana Yoga (2nd & 11th Lords)",
                            name_hindi="धन योग (द्वितीयेश व एकादशेश)",
                            category="DHANA_YOGA",
                            description=f"Strong association between 2nd house lord ({h2_lord}) and 11th house lord ({h11_lord}) creates continuous financial inflow and wealth accumulation.",
                            planets_involved=[h2_lord, h11_lord],
                            houses_involved=[p2.house_d1, p11.house_d1, 2, 11],
                            is_active=True,
                            strength_score=82.0,
                            source_reference="Brihat Parashara Hora Shastra Ch. 41"
                        )
                    )

        # 6. Vipreet Raja Yogas (Harsha, Sarala, Vimala)
        vry_configs = [
            (6, "Harsha Yoga", "हर्ष योग", "6th lord in dusthana (6, 8, or 12) grants victory over enemies, health immunity, and fame."),
            (8, "Sarala Yoga", "सरल योग", "8th lord in dusthana (6, 8, or 12) grants long life, courage, and triumph over obstacles."),
            (12, "Vimala Yoga", "विमल योग", "12th lord in dusthana (6, 8, or 12) grants independent spirit, financial frugality, and happiness.")
        ]

        for house_num, v_name, v_hindi, v_desc in vry_configs:
            lord_name = house_lord_dict.get(house_num)
            if lord_name:
                lord_p = planet_dict.get(lord_name)
                if lord_p and lord_p.house_d1 in [6, 8, 12]:
                    yogas.append(
                        YogaFact(
                            id=f"vipreet_{v_name.lower().replace(' ', '_')}",
                            name=f"Vipreet Raja Yoga ({v_name})",
                            name_hindi=f"विपरीत राजयोग ({v_hindi})",
                            category="VIPREET",
                            description=f"Lord of house {house_num} ({lord_name}) placed in dusthana house {lord_p.house_d1}: {v_desc}",
                            planets_involved=[lord_name],
                            houses_involved=[lord_p.house_d1, house_num],
                            is_active=True,
                            strength_score=80.0,
                            source_reference="Uttara Kalamrita Ch. 4, Sloka 22"
                        )
                    )

        # 7. Chandra-Mangala Yoga
        if moon_planet and mars_planet:
            if moon_planet.house_d1 == mars_planet.house_d1 or abs(moon_planet.house_d1 - mars_planet.house_d1) == 6:
                yogas.append(
                    YogaFact(
                        id="chandra_mangala_yoga",
                        name="Chandra-Mangala Yoga",
                        name_hindi="चन्द्र-मंगल योग",
                        category="SPECIAL",
                        description="Moon and Mars in conjunction or opposition creates immense financial enterprise, passion, and resourcefulness.",
                        planets_involved=["Moon", "Mars"],
                        houses_involved=[moon_planet.house_d1, mars_planet.house_d1],
                        is_active=True,
                        strength_score=78.0,
                        source_reference="Saravali Ch. 15, Sloka 11"
                    )
                )

        calc_id = f"yogas_{uuid.uuid4().hex[:12]}"

        return YogaResult(
            calculation_id=calc_id,
            profile_id=profile_id,
            total_yogas_found=len(yogas),
            yogas=yogas
        )
