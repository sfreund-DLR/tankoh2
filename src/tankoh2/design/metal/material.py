"""Characterize metal material properties at cryogenic temperatures"""

from collections import OrderedDict


alu2219 = OrderedDict([  # at T=20K
    ('roh', 2825),  # kg/m**3
    ('sigma_t', 172.4),  # MPa
    #('E', None),
    ('weldEfficiency', 1),  # [-]
    ('c1', 0.),  # tbd
    ('c2', 0.),  # tbd
])

defaultMetalMaterial = alu2219.copy()



