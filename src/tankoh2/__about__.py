'''
Central information about the software package 

It is a single location for this information. 
See https://packaging.python.org/en/latest/single_source_version.html
variant 3. 
'''

from os.path import dirname, abspath, basename
import datetime


try:
    __programDir__ = dirname(abspath(__file__))
    if not 'site-packages' in __programDir__:
        # not installed
        __programDir__ = dirname(dirname(__programDir__))

    __title__ = basename(dirname(__file__))
except NameError:
    # in case the file is analyzed via exec(), there is no __file__ variable. 
    # In this case __programDir__ and __title__ must be defined elsewhere
    __programDir__ = None
    __title__ = None

__description__ = 'Design and optimization of H2 tanks using muChain'
__version__ = "2.4.1"
__author__ = 'Sebastian Freund, Caroline Lueders'
__email__ = 'sebastian.freund@dlr.de'
__license__ = 'MIT'
__copyright__ = "Copyright (C) 2023 Deutsches Zentrum fuer Luft- und Raumfahrt(DLR, German Aerospace Center)"
__url__ = 'https://github.com/sfreund-DLR/tankoh2'
__keywords__ = 'tank h2 optimization design fem model'







