""""""
from collections import OrderedDict
import os

from tankoh2 import programDir, pychain

defaultDesign = ([
                  # General
                  ('tankname', 'exact_h2'),
                  ('nodeNumber', 500),  # might not exactly be matched due to approximations
                  ('dataDir', os.path.join(programDir, 'data')),
                  ('verbose', False),

                  # Optimization
                  ('maxlayers', 100),

                  # Geometry
                  ('domeType', pychain.winding.DOME_TYPES.ISOTENSOID),  # CIRCLE; ISOTENSOID
                  ('domeContour', (None, None)),  # (x,r)
                  ('minPolarOpening', 20),  # mm
                  ('dzyl', 400.),  # mm
                  ('lzylByR', 2.5),

                  # Design
                  ('safetyFactor', 2.25),
                  ('pressure', 5.),  # pressure in MPa (bar / 10.)
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

hymodDesign = OrderedDict([('burstPressure', 77.85),
                           ('lzyl', 1000.),
                           ('minPolarOpening', 23),
                           ('dzyl', 300.)
                           ])


NGTBITDesign = OrderedDict([('tankname', 'NGT-BIT-2020-09-16'),
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
                            ('numberOfRovings', 4),
                            #('tex', int(446)),
                            ('fibreDensity', 1.78),
                            # optimizer settings
                            ('maxlayers', 200)
                            ])


