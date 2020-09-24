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
import mycropychain as pychain

