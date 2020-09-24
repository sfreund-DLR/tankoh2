"""create logger"""

import logging
import sys

formatStr = "%(levelname)s\t%(asctime)s: %(message)s"
logging.basicConfig(stream=sys.stdout, format=formatStr, level=logging.INFO)

log = logging.root


