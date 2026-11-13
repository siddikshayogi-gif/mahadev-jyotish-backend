import sys
from unittest.mock import MagicMock

# Create a mock for swisseph
swe = MagicMock()
swe.version = "2.10.00"
swe.SUN = 0; swe.MOON = 1; swe.MARS = 4; swe.MERCURY = 2; swe.JUPITER = 5; swe.VENUS = 3; swe.SATURN = 6; swe.MEAN_NODE = 10
swe.SIDM_LAHIRI = 1; swe.FLG_SPEED = 256; swe.FLG_SWIEPH = 2; swe.FLG_SIDEREAL = 64

# Mock some default values
swe.julday.return_value = 2450849.75
swe.get_ayanamsa_ut.return_value = 23.83

# Default calc_ut return (Moon at approx 38.92 deg - Taurus/Krittika)
# For Vineet Yogi: End of Sun Dasha = 01-08-1998.
# Birth = 05-02-1998.
# Duration = 177 days (assuming 365.2425 days/year).
# Sun total = 6 years = 2191.455 days.
# Remaining fraction = 177 / 2191.455 = 0.0807684
# Remaining arc = 13.3333333 * 0.0807684 = 1.076912
# Krittika ends at 40.0. Moon longitude = 40.0 - 1.076912 = 38.923088
swe.calc_ut.return_value = ([38.923088, 0, 0, 13.0, 0, 0], 0)

# Default houses_ex return
swe.houses_ex.return_value = ([17.5, 47.5, 77.5, 107.5, 137.5, 167.5, 197.5, 227.5, 257.5, 287.5, 317.5, 347.5], [17.5, 107.5, 0])

# Inject the mock into sys.modules
sys.modules["swisseph"] = swe
