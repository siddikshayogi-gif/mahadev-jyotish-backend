"""Vimshottari Dasha Engine.

Computes 5-level Vimshottari Dasha hierarchy:
Mahadasha -> Antardasha -> Pratyantardasha -> Sukshma -> Pran.

Calculates exact birth balance from Moon Nakshatra longitude at birth UTC and
enforces parent-child interval locking with zero gaps, overlaps, or drift.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Tuple, Optional
import uuid

from app.schemas.dasha_gochar_yoga import DashaPeriod, DashaHierarchyResult

# Vimshottari sequence: (Lord, Years)
VIMSHOTTARI_LORDS: List[Tuple[str, float]] = [
    ("Ketu", 7.0),
    ("Venus", 20.0),
    ("Sun", 6.0),
    ("Moon", 10.0),
    ("Mars", 7.0),
    ("Rahu", 18.0),
    ("Jupiter", 16.0),
    ("Saturn", 19.0),
    ("Mercury", 17.0)
]

TOTAL_VIMSHOTTARI_YEARS = 120.0
NAKSHATRA_ARC_DEG = 13.333333333333334  # 13°20'
LEVEL_NAMES = {
    1: "Mahadasha",
    2: "Antardasha",
    3: "Pratyantardasha",
    4: "Sukshma",
    5: "Pran"
}

# The reference software likely uses 365.25 (Julian year)
# or 365.242199 (Tropical year).
# Gregorian 365.2425 is also common.
DAYS_PER_YEAR = 365.25 # Switching to 365.25 for better reference alignment

def _dt_to_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()

def _subdivide_interval(
    parent_start: datetime,
    parent_end: datetime,
    parent_lord: str,
    level: int
) -> List[Tuple[str, datetime, datetime]]:
    """Subdivides a parent Dasha interval into 9 child intervals.
    
    Order starts from parent_lord in Vimshottari sequence.
    Applies strict interval locking: child 9 end_date is set exactly to parent_end.
    """
    lord_names = [lord for lord, _ in VIMSHOTTARI_LORDS]
    parent_idx = lord_names.index(parent_lord)
    
    parent_duration_sec = (parent_end - parent_start).total_seconds()
    
    children = []
    current_start = parent_start
    
    for i in range(9):
        curr_idx = (parent_idx + i) % 9
        child_lord, child_years = VIMSHOTTARI_LORDS[curr_idx]
        
        fraction = child_years / TOTAL_VIMSHOTTARI_YEARS
        child_sec = parent_duration_sec * fraction
        
        if i == 8:
            # Enforce exact parent_end boundary for the last child (interval locking)
            child_end = parent_end
        else:
            child_end = current_start + timedelta(seconds=child_sec)
            
        children.append((child_lord, current_start, child_end))
        current_start = child_end
        
    return children

class DashaEngine:
    """Deterministic Vimshottari Dasha Engine."""
    
    def calculate_dasha_hierarchy(
        self,
        moon_longitude: float,
        birth_datetime_utc: datetime,
        target_datetime_utc: Optional[datetime] = None,
        max_depth: int = 5,
        profile_id: str = "prof_default",
        calculation_id: Optional[str] = None
    ) -> DashaHierarchyResult:
        """Calculates 5-level Vimshottari Dasha hierarchy and active chain."""
        if birth_datetime_utc.tzinfo is None:
            birth_datetime_utc = birth_datetime_utc.replace(tzinfo=timezone.utc)
            
        if target_datetime_utc is None:
            target_datetime_utc = datetime.now(timezone.utc)
        elif target_datetime_utc.tzinfo is None:
            target_datetime_utc = target_datetime_utc.replace(tzinfo=timezone.utc)
            
        calc_id = calculation_id or f"dasha_{uuid.uuid4().hex[:12]}"
        
        # 1. Moon Nakshatra & Birth Balance Calculation
        moon_lon = moon_longitude % 360.0
        nak_idx = int(moon_lon / NAKSHATRA_ARC_DEG)
        if nak_idx > 26:
            nak_idx = 26
            
        lord_idx = nak_idx % 9
        first_lord, first_years = VIMSHOTTARI_LORDS[lord_idx]
        
        deg_in_nak = moon_lon % NAKSHATRA_ARC_DEG
        fraction_passed = deg_in_nak / NAKSHATRA_ARC_DEG
        fraction_remaining = 1.0 - fraction_passed
        
        # 2. Build Mahadashas (120 years span starting from birth balance)
        first_md_sec = first_years * DAYS_PER_YEAR * 86400.0
        elapsed_sec = first_md_sec * fraction_passed

        first_md_start = birth_datetime_utc - timedelta(seconds=elapsed_sec)

        mahadasha_list: List[DashaPeriod] = []
        
        curr_start = first_md_start
        for i in range(9):
            m_idx = (lord_idx + i) % 9
            m_lord, m_years = VIMSHOTTARI_LORDS[m_idx]
            
            m_sec = m_years * DAYS_PER_YEAR * 86400.0
            m_start = curr_start
            m_end = m_start + timedelta(seconds=m_sec)
            curr_start = m_end
            
            is_active_md = m_start <= target_datetime_utc < m_end
            status = "CURRENT" if is_active_md else ("PAST" if m_end <= target_datetime_utc else "FUTURE")

            # Effective start for the very first Dasha in the timeline (cannot be before birth)
            effective_start = m_start
            if i == 0:
                effective_start = birth_datetime_utc

            # Recursively build sub-periods only if it's active MD OR if we want to explore (limited)
            # To support the "explorer", we might just return the MDs and let another call fetch sub-periods
            sub_ads = None
            if max_depth >= 2 and is_active_md:
                 sub_ads = self._build_sub_periods(m_start, m_end, m_lord, level=2, max_depth=max_depth, target_utc=target_datetime_utc, parent_lords=[m_lord])
                
            mahadasha_list.append(
                DashaPeriod(
                    level=1,
                    level_name=LEVEL_NAMES[1],
                    lord=m_lord,
                    start_date_utc=_dt_to_iso(effective_start),
                    end_date_utc=_dt_to_iso(m_end),
                    theoretical_start_date_utc=_dt_to_iso(m_start),
                    sub_periods=sub_ads,
                    status=status,
                    parent_lords=[]
                )
            )
            
        # 3. Find Active 5-level Dasha Chain at target_datetime_utc
        active_chain = self._find_active_chain(
            moon_lon=moon_lon,
            birth_utc=birth_datetime_utc,
            target_utc=target_datetime_utc,
            max_depth=max_depth
        )
        for i, d in enumerate(active_chain):
            d.status = "CURRENT"
            d.parent_lords = [active_chain[j].lord for j in range(i)]

        return DashaHierarchyResult(
            calculation_id=calc_id,
            profile_id=profile_id,
            moon_longitude=moon_lon,
            birth_date_utc=_dt_to_iso(birth_datetime_utc),
            target_date_utc=_dt_to_iso(target_datetime_utc),
            active_chain=active_chain,
            mahadashas=mahadasha_list
        )
        
    def _build_sub_periods(
        self,
        parent_start: datetime,
        parent_end: datetime,
        parent_lord: str,
        level: int,
        max_depth: int,
        target_utc: datetime,
        parent_lords: List[str]
    ) -> List[DashaPeriod]:
        """Recursively subdivides parent interval down to max_depth with interval locking."""
        child_tuples = _subdivide_interval(parent_start, parent_end, parent_lord, level)
        periods = []
        
        for c_lord, c_start, c_end in child_tuples:
            sub_list = None
            is_active = c_start <= target_utc < c_end

            # Only expand active chain to save memory/payload if level is deep
            should_expand = True
            if level >= 2:
                should_expand = is_active

            if level < max_depth and should_expand:
                sub_list = self._build_sub_periods(c_start, c_end, c_lord, level + 1, max_depth, target_utc, parent_lords + [c_lord])
                
            periods.append(
                DashaPeriod(
                    level=level,
                    level_name=LEVEL_NAMES[level],
                    lord=c_lord,
                    start_date_utc=_dt_to_iso(c_start),
                    end_date_utc=_dt_to_iso(c_end),
                    sub_periods=sub_list,
                    status="CURRENT" if is_active else ("PAST" if c_end <= target_utc else "FUTURE"),
                    parent_lords=parent_lords
                )
            )

        return periods

    def get_sub_periods(
        self,
        parent_lord: str,
        parent_start_iso: str,
        parent_end_iso: str,
        parent_level: int,
        target_date_iso: Optional[str] = None,
        birth_date_iso: Optional[str] = None
    ) -> List[DashaPeriod]:
        """Calculates 9 sub-periods for a specific parent interval, with birth truncation."""
        p_start = datetime.fromisoformat(parent_start_iso.replace("Z", "+00:00"))
        p_end = datetime.fromisoformat(parent_end_iso.replace("Z", "+00:00"))

        target_dt = datetime.now(timezone.utc)
        if target_date_iso:
            target_dt = datetime.fromisoformat(target_date_iso.replace("Z", "+00:00"))

        birth_dt = None
        if birth_date_iso:
            birth_dt = datetime.fromisoformat(birth_date_iso.replace("Z", "+00:00"))

        child_level = parent_level + 1
        if child_level > 5:
            return []

        child_tuples = _subdivide_interval(p_start, p_end, parent_lord, child_level)

        periods = []
        for c_lord, c_start, c_end in child_tuples:
            # Skip child periods that end before birth
            if birth_dt and c_end <= birth_dt:
                continue

            # Truncate start if it begins before birth
            effective_start = c_start
            if birth_dt and c_start < birth_dt:
                effective_start = birth_dt

            status = "CURRENT" if effective_start <= target_dt < c_end else ("PAST" if c_end <= target_dt else "FUTURE")
            periods.append(
                DashaPeriod(
                    level=child_level,
                    level_name=LEVEL_NAMES[child_level],
                    lord=c_lord,
                    start_date_utc=_dt_to_iso(effective_start),
                    end_date_utc=_dt_to_iso(c_end),
                    theoretical_start_date_utc=_dt_to_iso(c_start),
                    status=status
                )
            )
        return periods

    def get_dasha_at(
        self,
        moon_longitude: float,
        birth_datetime_utc: datetime,
        target_datetime: datetime
    ) -> List[DashaPeriod]:
        """Canonical method to resolve 5-level Dasha at a specific timestamp."""
        res = self.calculate_dasha_hierarchy(
            moon_longitude=moon_longitude,
            birth_datetime_utc=birth_datetime_utc,
            target_datetime_utc=target_datetime,
            max_depth=5
        )
        return res.active_chain

    def get_periods_in_range(
        self,
        moon_longitude: float,
        birth_datetime_utc: datetime,
        start_dt: datetime,
        end_dt: datetime,
        max_level: int = 2
    ) -> List[Tuple[str, datetime, datetime, int, List[str]]]:
        """Returns all Dasha periods of specified levels that overlap with the given range."""
        if birth_datetime_utc.tzinfo is None: birth_datetime_utc = birth_datetime_utc.replace(tzinfo=timezone.utc)
        if start_dt.tzinfo is None: start_dt = start_dt.replace(tzinfo=timezone.utc)
        if end_dt.tzinfo is None: end_dt = end_dt.replace(tzinfo=timezone.utc)

        # 1. Find the first Mahadasha start
        moon_lon = moon_longitude % 360.0
        nak_idx = int(moon_lon / NAKSHATRA_ARC_DEG)
        if nak_idx > 26: nak_idx = 26
        lord_idx = nak_idx % 9
        first_lord, first_years = VIMSHOTTARI_LORDS[lord_idx]

        deg_in_nak = moon_lon % NAKSHATRA_ARC_DEG
        fraction_passed = deg_in_nak / NAKSHATRA_ARC_DEG
        first_md_start = birth_datetime_utc - timedelta(seconds=first_years * DAYS_PER_YEAR * 86400.0 * fraction_passed)

        overlapping = []
        curr_start = first_md_start
        for i in range(20): # Cover approx 250 years
            m_idx = (lord_idx + i) % 9
            m_lord, m_years = VIMSHOTTARI_LORDS[m_idx]
            m_sec = m_years * DAYS_PER_YEAR * 86400.0
            m_end = curr_start + timedelta(seconds=m_sec)

            # Check overlap
            if curr_start <= end_dt and m_end >= start_dt:
                overlapping.append((m_lord, curr_start, m_end, 1, []))

                if max_level >= 2:
                    ads = _subdivide_interval(curr_start, m_end, m_lord, 2)
                    for a_lord, a_start, a_end in ads:
                        if a_start <= end_dt and a_end >= start_dt:
                            overlapping.append((a_lord, a_start, a_end, 2, [m_lord]))

                            if max_level >= 3:
                                pds = _subdivide_interval(a_start, a_end, a_lord, 3)
                                for p_lord, p_start, p_end in pds:
                                    if p_start <= end_dt and p_end >= start_dt:
                                        overlapping.append((p_lord, p_start, p_end, 3, [m_lord, a_lord]))

                                        if max_level >= 4:
                                            for s_lord, s_start, s_end in _subdivide_interval(p_start, p_end, p_lord, 4):
                                                if s_start <= end_dt and s_end >= start_dt:
                                                    overlapping.append((s_lord, s_start, s_end, 4, [m_lord, a_lord, p_lord]))
                                                    if max_level >= 5:
                                                        for pr_lord, pr_start, pr_end in _subdivide_interval(s_start, s_end, s_lord, 5):
                                                            if pr_start <= end_dt and pr_end >= start_dt:
                                                                overlapping.append((pr_lord, pr_start, pr_end, 5, [m_lord, a_lord, p_lord, s_lord]))

            curr_start = m_end
            if curr_start > end_dt:
                break

        return overlapping

    def _find_active_chain(
        self,
        moon_lon: float,
        birth_utc: datetime,
        target_utc: datetime,
        max_depth: int = 5
    ) -> List[DashaPeriod]:
        """Finds active 5-level Dasha chain at target_utc without generating full 120-year tree."""
        # 1. Find active Mahadasha
        moon_lon = moon_lon % 360.0
        nak_idx = int(moon_lon / NAKSHATRA_ARC_DEG)
        if nak_idx > 26:
            nak_idx = 26
        lord_idx = nak_idx % 9
        first_lord, first_years = VIMSHOTTARI_LORDS[lord_idx]
        
        deg_in_nak = moon_lon % NAKSHATRA_ARC_DEG
        fraction_passed = deg_in_nak / NAKSHATRA_ARC_DEG
        fraction_remaining = 1.0 - fraction_passed
        
        first_md_sec = first_years * DAYS_PER_YEAR * 86400.0
        elapsed_sec = first_md_sec * fraction_passed
        first_md_start = birth_utc - timedelta(seconds=elapsed_sec)
        
        curr_start = first_md_start
        curr_lord = ""
        curr_start_time = birth_utc
        curr_end_time = birth_utc
        
        for i in range(9):
            m_idx = (lord_idx + i) % 9
            m_lord, m_years = VIMSHOTTARI_LORDS[m_idx]
            m_sec = m_years * DAYS_PER_YEAR * 86400.0
            
            if i == 0:
                m_start = first_md_start
                m_end = birth_utc + timedelta(seconds=first_md_sec * fraction_remaining)
            else:
                m_start = curr_start
                m_end = m_start + timedelta(seconds=m_sec)
                
            curr_start = m_end
            
            if m_start <= target_utc <= m_end or (i == 8 and target_utc > m_end) or (i == 0 and target_utc < m_start):
                curr_lord = m_lord
                curr_start_time = m_start
                curr_end_time = m_end
                break

        active_chain: List[DashaPeriod] = []
        p_start = curr_start_time
        p_end = curr_end_time
        p_lord = curr_lord
        
        active_chain.append(
            DashaPeriod(
                level=1,
                level_name=LEVEL_NAMES[1],
                lord=p_lord,
                start_date_utc=_dt_to_iso(max(birth_utc, p_start)),
                end_date_utc=_dt_to_iso(p_end),
                theoretical_start_date_utc=_dt_to_iso(p_start)
            )
        )
        
        # Descend through level 2..max_depth
        for lvl in range(2, max_depth + 1):
            sub_tuples = _subdivide_interval(p_start, p_end, p_lord, lvl)
            match_tuple = None
            for c_lord, c_start, c_end in sub_tuples:
                if c_start <= target_utc <= c_end:
                    match_tuple = (c_lord, c_start, c_end)
                    break
            if match_tuple is None:
                # Fallback to nearest boundary
                if target_utc < sub_tuples[0][1]:
                    match_tuple = sub_tuples[0]
                else:
                    match_tuple = sub_tuples[-1]
                    
            p_lord, p_start, p_end = match_tuple
            active_chain.append(
                DashaPeriod(
                    level=lvl,
                    level_name=LEVEL_NAMES[lvl],
                    lord=p_lord,
                    start_date_utc=_dt_to_iso(p_start),
                    end_date_utc=_dt_to_iso(p_end)
                )
            )
            
        return active_chain
