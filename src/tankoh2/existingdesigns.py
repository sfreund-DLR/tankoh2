""""""
from collections import OrderedDict
import os

from tankoh2 import programDir, pychain

defaultDesign = OrderedDict([
    # General
    ('tankname', 'exact_h2'),
    ('nodeNumber', 500),  # might not exactly be matched due to approximations
    ('dataDir', os.path.join(programDir, 'data')),
    ('verbose', False),

    # Optimization
    ('maxlayers', 100),

    # Geometry
    ('domeType', 'ISOTENSOID'),  # [isotensoid, circle], if None isotensoid is used
    ('domeContour', (None, None)),  # (x,r)
    ('minPolarOpening', 20),  # mm, radius
    ('dzyl', 400.),  # mm
    ('lzylByR', 2.5),

    # Design
    ('safetyFactor', 2.25),
    ('valveReleaseFactor', 1.1),  # factor for the valve release at burst pressure
    ('pressure', 5.),  # pressure in MPa (bar / 10.)
    ('useHydrostaticPressure', True),  # according to 25.963 (d)
    ('tankLocation', 'wing_at_engine'),  # [wing_no_engine, wing_at_engine, fuselage]
    ('useFibreFailure', True),

    # Material
    ('materialname', 'CFRP_HyMod'),

    # Fiber roving parameter
    ('hoopLayerThickness', 0.125),
    ('helixLayerThickenss', 0.129),
    ('rovingWidth', 3.175),
    ('numberOfRovings', 4),
    # bandWidth = rovingWidth * numberOfRovings
    ('tex', 446),  # g / km
    ('fibreDensity', 1.78),  # g / cm^3
    ])

# HyMod
# 12mm thickness in cylindrical section
#

hymodDesign = OrderedDict([
    ('tankname', 'hymodDesign'),
    ('burstPressure', 77.85),
    ('lzyl', 1000.),
    ('minPolarOpening', 23),
    ('dzyl', 300.)
])


NGTBITDesign = OrderedDict([
    ('tankname', 'NGT-BIT-2020-09-16'),
    ('pressure', 70),
    # Geometry
    ('minPolarOpening', 23),
    ('dzyl', 400.),
    ('lzyl', 500.),
    # design philosophy
    ('safetyFactor', 2.0),
    ('useFibreFailure', True),
    # material
    ('materialname', 'CFRP_T700SC_LY556'),
    # fibre roving parameter
    ('hoopLayerThickness', 0.125),
    ('helixLayerThickenss', 0.129),
    ('rovingWidth', 3.175),
    ('numberOfRovings', 12),
    ('tex', 800),
    ('fibreDensity', 1.78),
    # optimizer settings
    ('maxlayers', 200)
    ])

vphDesign1 = OrderedDict([
    ('tankname', 'vph_design1'),
    ('lzyl', 3218.8),
    ('dzyl', 1200.*2),
    ('safetyFactor', 2.25),
    ('pressure', .2),  # pressure in MPa (bar / 10.)
    ('minPolarOpening', 120),
    ('domeType', 'circle'),  # [isotensoid, circle], if None isotensoid is used
])




kautextDesign = OrderedDict([
                             # General
                             ('tankname', 'Kautext'),
                             #('nodeNumber', 500),  # might not exactly be matched due to approximations
                             ('dataDir', os.path.join(programDir, 'data')),
                             ('verbose', False),

                             # Optimization
                             ('maxlayers', 100),

                             # Geometry
                             #('domeType', pychain.winding.DOME_TYPES.ISOTENSOID),  # CIRCLE; ISOTENSOID
                             #('domeContour', (None, None)),  # (x,r)
                             ('minPolarOpening', 4.572604469),  # mm
                             ('dzyl', 260.),  # mm
                             ('lzyl', 588.), #mm
                             #('lzylByR', 2.5),

                             # Design
                             ('safetyFactor', 2.0),
                             ('pressure', 70.),  # pressure in MPa (bar / 10.)
                             ('useFibreFailure', True),

                             # Material
                             ('materialname', 'CFRP_T700SC_LY556'),

                             # Fiber roving parameter
                             ('hoopLayerThickness', 0.125),
                             ('helixLayerThickenss', 0.129),
                             ('rovingWidth', 3.175),
                             ('numberOfRovings', 12),
                             # bandWidth = rovingWidth * numberOfRovings
                             ('tex', 800),  # g / km
                             ('fibreDensity', 1.78),  # g / cm^3
                             ])


