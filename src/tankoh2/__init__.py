"""
h2 tank optimization
"""

import logging
import sys

from tankoh2.__about__ import __title__, __version__, __programDir__
from tankoh2.settings import applySettings

# main program information
name = __title__
programDir = __programDir__
version = __version__

# create logger
formatStr = "%(levelname)s\t%(asctime)s: %(message)s"
logging.basicConfig(stream=sys.stdout, format=formatStr, level=logging.INFO)
log = logging.root

# make mycropychain available
applySettings()
pychain = None

try:
    # v <= 0.90
    import mycropychain as pychain
except ModuleNotFoundError:
    # v > 0.90
    if sys.version_info.minor == '6':
        import mycropychain36 as pychain
    else:  # sys.version_info.minor == '8'
        import mycropychain38 as pychain
