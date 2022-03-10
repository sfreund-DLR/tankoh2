"""
Characterize design input parameter for various projects
"""



from collections import OrderedDict
import pandas as pd
import os


allArgs = pd.DataFrame(
    [
        # General
        ['windingOrMetal', 'General', '', 'winding', '',
         'Switch between winding mode or metal design [winding, metal]', ''],
        ['tankname', 'General', 'name', 'tank_name', '', 'Name of the tank', ''],
        ['nodeNumber', 'General', 'number', 500, int, 'node number along the contour', ''],
        ['verbose', 'General', '', False, '', 'More console output', 'store_true'],
        ['help', 'General', '', '', '', 'show this help message and exit', 'help'],
        # Optimization
        ['maxlayers', 'Optimization', 'layers', 100, int, 'Maximum number of layers to be added', ''],
        ['relRadiusHoopLayerEnd', 'Optimization', '', 0.95, float,
         'relative radius (to cyl radius) where hoop layers end [-]', ''],
        # Geometry
        ['domeType', 'Geometry', '', 'isotensoid', '',
         'Shape of dome geometry [isotensoid, circle, ellipse, custom]', ''],
        ['domeContour', 'Geometry', '(x,r)', (None,None), '',
         'Must be given if domeType==custom. X- and R-array should be given without whitespaces like '
         '"[x1,x2],[r1,r2]" in [mm]', ''],
        ['polarOpeningRadius', 'Geometry', 'r_po', 20, float, 'Polar opening radius [mm]', ''],
        ['dcly', 'Geometry', 'd_cyl', 400, float, 'Diameter of the cylindrical section [mm]', ''],
        ['lcyl', 'Geometry', 'l_cyl', 500, float, 'Length of the cylindrical section [mm]', ''],
        ['lcylByR', 'Geometry', '', 2.5, float, 'only if lcyl is not given [-]', ''],
        ['domeLengthByR', 'Geometry', 'l/r_cyl', 0.5, float,
         'Axial length of the dome. Only used for domeType==ellipse [mm]', ''],
        # Design
        ['safetyFactor', 'Design', 'S', 2, float, 'Safety factor used in design [-]', ''],
        ['valveReleaseFactor', 'Design', 'f_pv', 1.1, float,
         'Factor defining additional pressure to account for the valve pressure inaccuracies', ''],
        ['pressure', 'Design', 'p_op', 5., float, 'Operational pressure [MPa]', ''],
        ['burstPressure', 'Design', 'p_b', 10., float, 'Burst pressure [MPa]', ''],
        ['useHydrostaticPressure', 'Design', '', False, '',
         'Flag whether hydrostatic pressure according to CS 25.963 (d) should be applied', 'store_true'],
        ['tankLocation', 'Design', 'loc', 'wing_at_engine', '',
         'Location of the tank according to CS 25.963 (d). Only used if useHydrostaticPressure. '
         'Options: [wing_no_engine, wing_at_engine, fuselage]', ''],
        # Material
        ['materialName', 'Material', 'name', 'CFRP_HyMod', '',
         'For metal tanks: name of the material defined in tankoh2.design.metal.material. '
         'For wound tanks: name of the .json for a µWind material definiton '
         '(e.g. in tankoh2/data/CFRP_HyMod.json). '
         'If only a name is given, the file is assumed to be in tankoh2/data', ''],
        ['failureMode', 'Material', 'mode', 'fibreFailure', '',
         'Use pucks failure mode [fibreFailure, interFibreFailure]', ''],
        # Fiber roving parameters
        ['hoopLayerThickness', 'Fiber roving parameters', 'thk', 0.125, float,
         'Thickness of hoop (circumferential) layers [mm]', ''],
        ['helixLayerThickenss', 'Fiber roving parameters', 'thk', 0.129, float,
         'Thickness of helical layers [mm]', ''],
        ['rovingWidth', 'Fiber roving parameters', 'witdh', 3.175, float, 'Width of one roving [mm]', ''],
        ['numberOfRovings', 'Fiber roving parameters', '#', 4, int,
         'Number of rovings (rovingWidth*numberOfRovings=bandWidth)', ''],
        ['tex', 'Fiber roving parameters', '', 446, float, 'tex number [g/km]', ''],
        ['fibreDensity', 'Fiber roving parameters', '', 1.78, float, 'Fibre density [g/cm^3]', ''],
    ],
    columns=['name', 'group', 'metavar', 'default', 'type', 'help', 'action']
)

frpKeywords = (
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

defaultDesign = OrderedDict(zip(allArgs['name'], allArgs['default']))
# hymod design
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
    ('valveReleaseFactor', 1.),
    # Geometry
    ('polarOpeningRadius', 23),
    ('dcly', 400.),
    ('lcyl', 500.),
    # design philosophy
    ('safetyFactor', 2.0),
    ('failureMode', 'fibreFailure'),
    # material
    ('materialName', 'CFRP_T700SC_LY556'),
    # fibre roving parameter
    #('hoopLayerThickness', 0.125),
    ('hoopLayerThickness', 0.089605735), # thickness for 62% FVG
    #('helixLayerThickenss', 0.129),
    ('helixLayerThickenss', 0.089605735), # thickness for 62% FVG
    ('rovingWidth', 8.00),
    ('numberOfRovings', 6), # number of spools usabale at INVENT
    ('tex', 800),
    ('fibreDensity', 1.8),
    # optimizer settings
    ('maxlayers', 200)
    ])

NGTBITDesign_old = OrderedDict([
    ('tankname', 'NGT-BIT-2020-09-16'),
    ('pressure', 70),
    ('valveReleaseFactor', 1.),
    # Geometry
    ('nodeNumber', 1000),
    ('polarOpeningRadius', 23),
    #('dcly', 400.),
    ('lcyl', 500.),

    ('dcly', 0.2754 * 2 * 1000),  # mm
    #('lcyl', 0.68862939 * 1000),  # mm
    # design philosophy
    ('safetyFactor', 2.0),
    ('failureMode', 'fibreFailure'),
    # material
    ('materialName', 'CFRP_T700SC_LY556'),
    # fibre roving parameter
    ('hoopLayerThickness', 0.125),
    ('helixLayerThickenss', 0.129),
    ('rovingWidth', 3.175),
    ('numberOfRovings', 4), # number of spools usabale at INVENT
    ('tex', 446),
    ('fibreDensity', 1.78),
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
    ('failureMode', 'fibreFailure'),
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
                             ('failureMode', 'fibreFailure'),

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

ttDesignLh2 = OrderedDict([
    ('tankname', 'tt_lh2'),
    ('polarOpeningRadius', 40),  # mm
    ('dcly', 223.862*2),  # mm
    ('lcyl', 559.6572), #mm
    ('safetyFactor', 2.0),
    ('pressure', 0.25),  # pressure in MPa (bar / 10.)
    ('domeType', 'isotensoid'),
    ('failureMode', 'interFibreFailure'),
    ('useHydrostaticPressure', True),
])

ttDesignCh2 = OrderedDict([
    ('tankname', 'tt_ch2'),
    ('polarOpeningRadius', 40),  # mm
    ('dcly', 269.66362*2),  # mm
    ('lcyl', 674.15906),  # mm
    ('safetyFactor', 2.0),
    ('pressure', 70.),  # pressure in MPa (bar / 10.)
    ('domeType', 'isotensoid'),
    #('domeType', 'ellipse'),
    ('useHydrostaticPressure', True),
    ('maxlayers', 200),
])

if __name__ == '__main__':
    print("',\n'".join(defaultDesign.keys()))
