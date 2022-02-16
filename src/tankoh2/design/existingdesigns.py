"""
Characterize design input parameter for various projects
"""



from collections import OrderedDict
import os

from tankoh2 import programDir

allDesignKeywords = (
    'tankname',
    'nodeNumber', # node number of full contour
    'dataDir',
    'verbose',
    'maxlayers',
    'domeType',
    'domeAxialHalfAxis', # Axial length of dome, required for domeContour=='ellipse'
    'domeContour', # overrides domeType and domeAxialHalfAxis. Must match dcly and polarOpeningRadius
    'polarOpeningRadius',
    'dcly',
    'lcylByR',
    'relRadiusHoopLayerEnd',
    'safetyFactor',
    'valveReleaseFactor',
    'pressure',
    'useHydrostaticPressure',
    'tankLocation',
    'useFibreFailure',
    'materialName',
    'hoopLayerThickness',
    'helixLayerThickenss',
    'rovingWidth',
    'numberOfRovings',
    'tex',
    'fibreDensity',
    'lcyl',
    'burstPressure',
    )

frpKeywords = (
    'dataDir',
    'domeType',
    'domeAxialHalfAxis',
    'domeContour',
    'polarOpeningRadius',
    'dcly',
    'lcylByR',
    'safetyFactor',
    'valveReleaseFactor',
    'pressure',
    'useHydrostaticPressure',
    'tankLocation',
    'materialName',
)

defaultDesign = OrderedDict([
    # General
    ('tankname', 'exact_h2'),
    ('nodeNumber', 500),
    ('dataDir', os.path.join(programDir, 'data')),
    ('verbose', False),

    # Optimization
    ('maxlayers', 100),
    ('relRadiusHoopLayerEnd', 0.95),  # relative radius (to cyl radius) where hoop layers end

    # Geometry
    ('domeType', 'ISOTENSOID'),  # [isotensoid, circle, ellipse, custom], if None isotensoid is used, if custom domeContour must be given
    ('domeContour', (None, None)),  # (x,r)
    ('polarOpeningRadius', 20),  # mm, radius
    ('dcly', 400.),  # mm
    ('lcylByR', 2.5),

    # Design
    ('safetyFactor', 2.25),
    ('valveReleaseFactor', 1.1),  # factor for the valve release at burst pressure [source: Brewer]
    ('pressure', 5.),  # pressure in MPa (bar / 10.)
    ('useHydrostaticPressure', True),  # according to FAR 25.963 (d)
    ('tankLocation', 'wing_at_engine'),  # [wing_no_engine, wing_at_engine, fuselage]
    ('useFibreFailure', True),

    # Material
    ('materialName', 'CFRP_HyMod'),

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
    ('lcyl', 1000.),
    ('polarOpeningRadius', 23),
    ('dcly', 300.)
])


NGTBITDesign = OrderedDict([
    ('tankname', 'NGT-BIT-2020-09-16'),
    ('pressure', 70),
    # Geometry
    ('polarOpeningRadius', 23),
    ('dcly', 400.),
    ('lcyl', 500.),
    # design philosophy
    ('safetyFactor', 2.0),
    ('useFibreFailure', True),
    # material
    ('materialName', 'CFRP_T700SC_LY556'),
    # fibre roving parameter
    #('hoopLayerThickness', 0.125),
    ('hoopLayerThickness', 0.25),
    #('helixLayerThickenss', 0.129),
    ('helixLayerThickenss', 0.25),
    ('rovingWidth', 3.175),
    ('numberOfRovings', 12),
    ('tex', 800),
    ('fibreDensity', 1.8),
    # optimizer settings
    ('maxlayers', 200)
    ])

NGTBITDesign_small = OrderedDict([
    ('tankname', 'NGT-BIT-small'),
    ('pressure', 10),
    # Geometry
    ('polarOpeningRadius', 23),
    ('dcly', 400.),
    ('lcyl', 290.),
    # design philosophy
    ('safetyFactor', 2.0),
    ('useFibreFailure', True),
    # material
    ('materialName', 'CFRP_T700SC_LY556'),
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
    ('lcyl', 3218.8),
    ('dcly', 1200.*2),
    ('safetyFactor', 2.25),
    ('pressure', .2),  # pressure in MPa (bar / 10.)
    ('polarOpeningRadius', 120),
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
                             ('polarOpeningRadius', 4.572604469),  # mm
                             ('dcly', 260.),  # mm
                             ('lcyl', 588.), #mm
                             #('lcylByR', 2.5),

                             # Design
                             ('safetyFactor', 2.0),
                             ('pressure', 70.),  # pressure in MPa (bar / 10.)
                             ('useFibreFailure', True),

                             # Material
                             ('materialName', 'CFRP_T700SC_LY556'),

                             # Fiber roving parameter
                             ('hoopLayerThickness', 0.125),
                             ('helixLayerThickenss', 0.129),
                             ('rovingWidth', 3.175),
                             ('numberOfRovings', 12),
                             # bandWidth = rovingWidth * numberOfRovings
                             ('tex', 800),  # g / km
                             ('fibreDensity', 1.78),  # g / cm^3
                             ])



if __name__ == '__main__':
    print("',\n'".join(defaultDesign.keys()))
