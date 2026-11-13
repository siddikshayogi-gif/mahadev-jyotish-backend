"""Date Extractor Utility.

Extracts specific dates from user natural language queries for historical or future lookup.
"""

import re
from datetime import datetime, timezone
from typing import Optional

# Month name mapping
MONTHS_HI = {
    "january": 1, "jan": 1, "जनवरी": 1,
    "february": 2, "feb": 2, "फरवरी": 2,
    "march": 3, "mar": 3, "मार्च": 3,
    "april": 4, "apr": 4, "अप्रैल": 4,
    "may": 5, "मई": 5,
    "june": 6, "jun": 6, "जून": 6,
    "july": 7, "jul": 7, "जुलाई": 7,
    "august": 8, "aug": 8, "अगस्त": 8,
    "september": 9, "sep": 9, "सितंबर": 9, "सितम्बर": 9,
    "october": 10, "oct": 10, "अक्टूबर": 10, "अक्टूबर": 10,
    "november": 11, "nov": 11, "नवंबर": 11, "नवम्बर": 11,
    "december": 12, "dec": 12, "दिसंबर": 12, "दिसम्बर": 12
}

class DateExtractor:
    """Extracts target dates from question text (English or Hindi)."""

    def extract_date(self, question: str) -> Optional[datetime]:
        q_lower = question.lower()

        # 1. DD/MM/YYYY or DD-MM-YYYY
        match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', q_lower)
        if match:
            try:
                day, month, year = map(int, match.groups())
                return datetime(year, month, day, 12, 0, tzinfo=timezone.utc)
            except ValueError:
                pass

        # 2. YYYY-MM-DD
        match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', q_lower)
        if match:
            try:
                year, month, day = map(int, match.groups())
                return datetime(year, month, day, 12, 0, tzinfo=timezone.utc)
            except ValueError:
                pass

        # 3. Text dates: "15 March 2025" or "मार्च 15, 2025" or "2025 march 15"
        for month_name, month_num in MONTHS_HI.items():
            if month_name in q_lower:
                # Find day and year near month
                day_match = re.search(r'\b(\d{1,2})\b', q_lower)
                year_match = re.search(r'\b(20\d{2}|19\d{2})\b', q_lower)
                if year_match:
                    year = int(year_match.group(1))
                    day = int(day_match.group(1)) if day_match else 1
                    try:
                        return datetime(year, month_num, day, 12, 0, tzinfo=timezone.utc)
                    except ValueError:
                        pass

        return None
