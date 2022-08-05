"""
Characterize design input parameter for various projects
"""


import os
from collections import OrderedDict
import pandas as pd

from tankoh2 import programDir
from tankoh2.geometry.geoutils import getReducedDomePoints


allArgs = pd.DataFrame(
    [
        # General
        ['windingOrMetal', 'General', '', 'winding', '',
         'Switch between winding mode or metal design [winding, metal]', ''],
        ['tankname', 'General', 'name', 'tank_name', '', 'Name of the tank', ''],
        ['nodeNumber', 'General', 'number', 500, int, 'node number along the contour', ''],
        ['verbose', 'General', '', False, '', 'More console output', 'store_true'],
        ['verbosePlot', 'General', '', False, '', 'Plot the optimization target function', 'store_true'],
        ['help', 'General', '', '', '', 'show this help message and exit', 'help'],
        # Optimization
        ['maxlayers', 'Optimization', 'layers', 100, int, 'Maximum number of layers to be added', ''],
        ['relRadiusHoopLayerEnd', 'Optimization', '', 0.95, float,
         'relative radius (to cyl radius) where hoop layers end [-]', ''],
        # Geometry_Cylinder
        ['dcyl', 'Geometry_Cylinder', 'd_cyl', 400, float, 'Diameter of the cylindrical section [mm]', ''],
        ['lcyl', 'Geometry_Cylinder', 'l_cyl', 500, float, 'Length of the cylindrical section [mm]', ''],
        ['lcylByR', 'Geometry_Cylinder', '', 2.5, float, 'only if lcyl is not given [-]', ''],
        # Geometry_Dome
        ['domeType', 'Geometry_Dome', '', 'isotensoid', '',
         'Shape of dome geometry [isotensoid, circle, ellipse, custom]', ''],
        ['domeContour', 'Geometry_Dome', '(x,r)', (None,None), '',
         'Must be given if domeType==custom. X- and R-array should be given without whitespaces like '
         '"[x1,x2],[r1,r2]" in [mm]', ''],
        ['polarOpeningRadius', 'Geometry', 'r_po', 20, float, 'Polar opening radius [mm]', ''],
        ['domeLengthByR', 'Geometry_Dome', 'l/r_cyl', 0.5, float,
         'Axial length of the dome. Only used for domeType==ellipse [mm]', ''],
        ['alpha', 'Geometry_Dome', '(dcyl - dsmall)/dcyl', 0.5, float,
         'ratio of the difference of cylindrical and small radius to the cylindrical radius', ''],
        ['beta', 'Geometry_Dome', '(lcyl + lcone)/dcyl', 1.5, float,
         'ratio of the cylindrical and conical length to the cylindrical radius', ''],
        ['gamma', 'Geometry_Dome', 'lrad/(lrad + lcone)', 0.5, float,
         'ratio of the radial length to the sum f radial and conical length', ''],
        ['delta1', 'Geometry_Dome', 'ldome/rsmall', 0.5, float,
         'ratio of the semi axes of the elliptical dome end', ''],
        # Geometry_Dome2
        ['dome2Type', 'Geometry_Dome2', '', None, '',
         'Shape of dome geometry [isotensoid, circle, ellipse, custom]', ''],
        ['dome2Contour', 'Geometry_Dome2', '(x,r)', (None, None), '',
         'Must be given if domeType==custom. X- and R-array should be given without whitespaces like '
         '"[x1,x2],[r1,r2]" in [mm]', ''],
        ['dome2LengthByR', 'Geometry_Dome2', 'l/r_cyl', 0.5, float,
         'Axial length of the dome. Only used for domeType==ellipse [mm]', ''],
        # Design
        ['safetyFactor', 'Design', 'S', 2, float, 'Safety factor used in design [-]', ''],
        ['valveReleaseFactor', 'Design', 'f_pv', 1.1, float,
         'Factor defining additional pressure to account for the valve pressure inaccuracies', ''],
        ['pressure', 'Design', 'p_op', 5., float, 'Operational pressure [MPa]', ''],
        ['minPressure', 'Design', 'p_op_min', 0.1, float, 'Minimal operational pressure [MPa]', ''],
        ['burstPressure', 'Design', 'p_b', 10., float, 'Burst pressure [MPa]', ''],
        ['useHydrostaticPressure', 'Design', '', False, '',
         'Flag whether hydrostatic pressure according to CS 25.963 (d) should be applied', 'store_true'],
        ['tankLocation', 'Design', 'loc', 'wing_at_engine', '',
         'Location of the tank according to CS 25.963 (d). Only used if useHydrostaticPressure. '
         'Options: [wing_no_engine, wing_at_engine, fuselage]', ''],
        ['initialAnglesAndShifts', 'Design', 'angleShift', None, '',
         'List with tuples defining angles and shifts used before optimization starts', ''],
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
        # fatigue parameters
        ['pressureMin', 'Fatigue parameters', 'p_min',0.1, float, 'Minimal operating pressure [MPa]', ''],
        ['cycles', 'Fatigue parameters', '', 50000, int,
         'Number of operational cycles from pressureMin to pressure [-]', ''],
        ['heatUpCycles', 'Fatigue parameters', '', 100, int, 'Number of cycles to ambient T and p [-]', ''],
        ['simulatedLives', 'Fatigue parameters', '', 5, int, 'Number of simulated lifes (scatter) [-]', ''],
        ['Kt', 'Fatigue parameters', 'Kt', 5., float, 'Stress concentration factor [-]', ''],
        # aux thicknesses
        ['linerThickness', 'AuxThicknesses', 'linerThk', 0., float, 'Thickness of the liner [mm]', ''],
        ['insulationThickness', 'AuxThicknesses', 'insThk', 0., float, 'Thickness of the insluation [mm]', ''],
        ['fairingThickness', 'AuxThicknesses', 'fairingThk', 0., float, 'Thickness of the fairing [mm]', ''],

    ],
    columns=['name', 'group', 'metavar', 'default', 'type', 'help', 'action']
)

#  keywords only used for winding calculations
windingOnlyKeywords = allArgs[allArgs['group'] == 'Fiber roving parameters']['name'].tolist() + \
                      allArgs[allArgs['group'] == 'Optimization']['name'].tolist()
windingOnlyKeywords += ['failureMode']

#  keywords only used for metal calculations
metalOnlyKeywords = allArgs[allArgs['group'] == 'Fatigue parameters']['name'].tolist()


defaultDesign = OrderedDict(zip(allArgs['name'], allArgs['default']))

testPostprocessing = defaultDesign.copy()
testPostprocessing.update([
    ('initialAnglesAndShifts', [(7.862970189270743, 0), (90, 21.984637908159538)]),
    ('maxlayers', 2),
    ('nodeNumber', 1000),
    #('domeType', 'isotensoid_MuWind'),
    ])

# design to make plots where the layers are visible in µWind
plotDesign = defaultDesign.copy()
plotDesign.update([
    ('dcyl', plotDesign['dcyl']/4),
    ('lcyl', plotDesign['lcyl']/5),
    ('helixLayerThickenss', plotDesign['helixLayerThickenss']*2),
    ('hoopLayerThickness', plotDesign['hoopLayerThickness']*2),
    #('rovingWidth', plotDesign['rovingWidth']/1.5),
    ('burstPressure', 42.),
    ('maxlayers', 3),
    ('domeType', 'isotensoid_MuWind'),
    ('numberOfRovings', 4),
    ('polarOpeningRadius', 7),
    ])

defaultUnsymmetricDesign = defaultDesign.copy()
defaultUnsymmetricDesign.update([
    ('dome2Type', 'ellipse'), #defaultUnsymmetricDesign['domeType']),
    ('dome2Contour', defaultUnsymmetricDesign['dome2Contour']),
    ('dome2LengthByR', 1. #defaultUnsymmetricDesign['dome2LengthByR']
     ),
    ('domeType', 'ellipse'), #defaultUnsymmetricDesign['domeType']),
    ('domeLengthByR', 1. #defaultUnsymmetricDesign['dome2LengthByR']
     ),
    ])

# hymod design
# 12mm thickness in cylindrical section
hymodDesign = OrderedDict([
    ('tankname', 'hymodDesign'),
    ('burstPressure', 77.85),
    ('lcyl', 1000.),
    ('polarOpeningRadius', 23),
    ('dcyl', 300.)
])



NGTBITDesign = OrderedDict([
    ('tankname', 'NGT-BIT-2022-03-04'),
    ('pressure', 70), # MPa
    ('burstPressure', 140.), # MPa
    ('valveReleaseFactor', 1.),
    # Geometry
    ('polarOpeningRadius', 23),
    ('dcyl', 422.),
    ('lcyl', 500.),
    # design philosophy
    ('safetyFactor', 2.0),
    ('failureMode', 'fibreFailure'),
    # material
    ('materialName', 'CFRP_T700SC_LY556'),
    # fibre roving parameter
    # single ply thickness with 62% FVG
    ('hoopLayerThickness', 0.089605735), # thickness for 62% FVG
    ('helixLayerThickenss', 0.089605735), # thickness for 62% FVG
    # single ply thickness with 55% FVG
    #('hoopLayerThickness', 0.101010101), # thickness for 55% FVG
    #('helixLayerThickenss', 0.101010101), # thickness for 55% FVG
    # single ply thickness with 60% FVG
    #('hoopLayerThickness', 0.092592593), # thickness for 60% FVG
    #('helixLayerThickenss', 0.092592593), # thickness for 60% FVG
    ('rovingWidth', 8.00),
    ('numberOfRovings', 6), # number of spools usabale at INVENT
    ('tex', 800),
    ('fibreDensity', 1.8),
    # optimizer settings
    ('maxlayers', 200),
    ('verbose', True),
    ])

NGTBITDesignNewThk = NGTBITDesign.copy()
NGTBITDesignNewThk.pop('burstPressure')
NGTBITDesignNewThk.update([
    ('pressure', 70), # MPa
    ('nodeNumber', 2000),
    ('tankname', 'NGT-BIT-2022-07_new_thk'),
    ('dcyl', 400.), # due to shrinkage
    #('materialName', 'kuempers_k-preg-002-012-65-00'),
    ('hoopLayerThickness', 0.191), # thickness for 61% FVG
    ('helixLayerThickenss', 0.191), # thickness for 61% FVG
    ('rovingWidth', 4.00),
    ('numberOfRovings', 1), # number of used spools at FVT
    ('tex', 830),
    ('fibreDensity', 1.78),
    ('relRadiusHoopLayerEnd', 0.993),
    ('domeContour', getReducedDomePoints(os.path.join(programDir, 'data', 'Dome_contour_NGT-BIT-shrinkage.txt'), 4)),
    ('verbose', False),
    ])

NGTBITDesignNewThkCustomV2 = NGTBITDesignNewThk.copy()
NGTBITDesignNewThkCustomV2.update([
    ('initialAnglesAndShifts',
        [[7.12871052,0  ],[90,13.5       ],[8.5507069,0   ],[90,12.88636364],[90,12.27272727],[9.32314508,0  ],
        [90,11.65909091],[9.92738099,0  ],[90,11.04545455],[10.88676553,0 ],[11.56075346,0 ],[90,10.43181818],
        [12.46307046,0 ],[90,9.818181818],[13.60741528,0 ],[90,9.204545455],[13.73034838,0 ],[90,8.590909091],
        [13.92459572,0 ],[90,7.977272727],[14.80151089,0 ],[90,7.363636364],[14.832526,0   ],[90,6.75       ],
        [17.20627466,0 ],[90,6.136363636],[17.35186339,0 ],[90,5.522727273],[90,4.909090909],[17.54000139,0 ],
        [90,4.295454545],[21.45077766,0 ],[90,3.681818182],[90,3.068181818],[22.50403636,0 ],[90,2.454545455],
        [90,1.840909091],[23.34315396,0 ],[26.8693583,0  ],[90,1.227272727],[27.56435185,0 ],[90,0.613636364],
        [30.56698498,0 ],[90,0          ],[32.03011118,0 ],[32.67851261,0 ],]
     ),
    ('maxlayers', 46)
])

NGTBITDesignNewThkCustomV3 = NGTBITDesignNewThkCustomV2.copy()
NGTBITDesignNewThkCustomV3.update([
    ('initialAnglesAndShifts',
        [[7.12871052,0  ],[90,13.5       ],[7,0           ],[90,12.88636364],[90,12.27272727],[7.3,0         ],
        [90,11.65909091],[6.92738099,0  ],[90,11.04545455],[9.88676553,0  ],[11.56075346,0 ],[90,10.43181818],
        [12.46307046,0 ],[90,9.818181818],[13.60741528,0 ],[90,9.204545455],[13.73034838,0 ],[90,8.590909091],
        [13.92459572,0 ],[90,7.977272727],[14.80151089,0 ],[90,7.363636364],[15.3,0        ],[90,6.75       ],
        [16.20627466,0 ],[90,6.136363636],[17.35186339,0 ],[90,5.522727273],[90,4.909090909],[17.54000139,0 ],
        [90,4.295454545],[21.45077766,0 ],[90,3.681818182],[90,3.068181818],[22.50403636,0 ],[90,2.454545455],
        [90,1.840909091],[23.34315396,0 ],[26.8693583,0  ],[90,1.227272727],[27.56435185,0 ],[90,0.613636364],
        [30.56698498,0 ],[90,0          ],[32.03011118,0 ],[32.67851261,0 ],]
     ),
])

NGTBITDesign_old = OrderedDict([
    ('tankname', 'NGT-BIT-2020-09-16'),
    ('pressure', 70),
    ('valveReleaseFactor', 1.),
    # Geometry
    ('nodeNumber', 1000),
    ('polarOpeningRadius', 23),
    ('dcyl', 400.),
    ('lcyl', 500.),

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
    ('dcyl', 400.),
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
    ('tankname', 'vph_design1_iff_sf2.25'),
    ('lcyl', 3218.8),
    ('dcyl', 1200.*2),
    ('safetyFactor', 2.25),
    ('pressure', .2),  # pressure in MPa (bar / 10.)
    ('polarOpeningRadius', 120),
    ('failureMode', 'interFibreFailure'),
    ('domeType', 'circle'),  # [isotensoid, circle], if None isotensoid is used
    ('linerThickness', 0.5),
    ('insulationThickness', 127),
    ('fairingThickness', 0.5),
])

vphDesign1_isotensoid = vphDesign1.copy()
vphDesign1_isotensoid.update([
    ('lcyl', vphDesign1['lcyl'] + 546.66423),
    ('domeType', 'isotensoid'),])

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
                             ('dcyl', 260.),  # mm
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
    ('dcyl', 223.862*2),  # mm
    ('lcyl', 559.6572), #mm
    ('safetyFactor', 1.55),
    ('pressure', 0.25),  # pressure in MPa (bar / 10.)
    ('domeType', 'isotensoid'),
    ('failureMode', 'interFibreFailure'),
    ('useHydrostaticPressure', True),
])

ttDesignCh2 = ttDesignLh2.copy()
ttDesignCh2.update([
    ('tankname', 'tt_ch2'),
    ('dcyl', 269.66362*2),  # mm
    ('lcyl', 674.15906),  # mm
    ('pressure', 70.),  # pressure in MPa (bar / 10.)
    ('maxlayers', 200),
    ])

atheat = OrderedDict([
    # Medium: Helium
    # rocket d=438
    # rocket skin thk approx 5mm
    ('tankname', 'atheat_He'),
    ('polarOpeningRadius', 15),  # mm
    ('dcyl', 400),  # mm
    #('lcyl', 75),  # mm
    ('safetyFactor', 2.),
    ('pressure', 60),  # pressure in MPa (bar / 10.)
    ('domeType', 'isotensoid'),
    ('failureMode', 'fibreFailure'),
    ('useHydrostaticPressure', False),
    ('relRadiusHoopLayerEnd', 0.98),
    ('linerThickness', 3),
    ('volume', 0.037),
])

atheat2 = atheat.copy()
atheat2.update([
    ('tankname', 'atheat_He_fvt_geo'),
    ('polarOpeningRadius', NGTBITDesign['polarOpeningRadius']),
    ('domeContour', getReducedDomePoints(os.path.join(programDir, 'data', 'Dome_contour_NGT-BIT-shrinkage.txt'), 4)),
    ('domeType', 'generic'),
    ('lcyl', 77.75+11.55),  # mm
    ('dcyl', 400),  # mm
    ('pressure', 60),
    #('lcyl', 79.85),  # mm
    # ('initialAnglesAndShifts', [
    #     (7.862970189270743   , 0                    ),
    #     (90                  , 21.984637908159538   ),
    #     (13.866345007970057  , 0                    ),
    #     (13.866345007970057  , 0                    ),
    #     (58.4334573009439    , 0                    ),
    #     (69.01950346986695   , 0                    ),
    #     (47.36658070728886   , 0                    ),
    #     (9.171105727970618   , 0                    ),
    #     (9.539139023476652   , 0                    ),
    #     (25.001541085240873  , 0                    ),
    #     (90                  , -2.1997272973884687  ),]),
])

atheat3 = atheat2.copy()
atheat3.pop('domeContour')
atheat3.update([
    ('domeType', 'isotensoid'),
    ('dcyl', 370),  # mm
])

atheatAlu = atheat.copy()
atheatAlu.update([
    ('windingOrMetal', 'metal'),
    ('materialName', 'alu2219'),
])

tk_cgh2 = OrderedDict([
    ('tankname', 'tkms_cgh2'),
    ('polarOpeningRadius', 50),  # mm
    ('dcyl', 590),  # mm d_a - 2*t_estimate
    ('lcyl', 4500),  # mm - just an estimate for now
    ('safetyFactor', 1.5),
    ('pressure', 70),  # pressure in MPa (bar / 10.)
    ('domeType', 'isotensoid'),
    ('failureMode', 'fibreFailure'),
    ('useHydrostaticPressure', True),
    ('verbose', False),
])

conicalTankDesign = OrderedDict([
    ('tankname', 'conical_torispherical'),
    ('volume', 0.2),  # m^3
    ('dcyl', 500),  # mm
    ('polarOpeningRadius', 100),  # mm
    ('alpha', 0.5),
    ('beta', 1.5),  # (lCone + lRad) / dCyl
    ('gamma', 0.5),
    ('delta1', 0.8),
    ('domeType', 'conicalTorispherical'),
    ('dome2Type', 'ellipse'),
    ('dome2LengthByR', 0.5),
    ('pressure', 0.2),  # pressure in MPa (bar / 10.)
    ('failureMode', 'interFibreFailure'),
    ('useHydrostaticPressure', True),
    ('verbosePlot', True),
])

Kloepperboden = OrderedDict([
    ('tankname', 'kloepperboden'),
    ('volume', 5),  # m^3
    ('dcyl', 500),  # mm
    ('polarOpeningRadius', 40),  # mm
    ('domeType', 'torispherical'),
    ('pressure', 0.2),  # pressure in MPa (bar / 10.)
    ('failureMode', 'interFibreFailure'),
    ('useHydrostaticPressure', False),
    ('verbosePlot', True),
    ('nodeNumber', 500),
])

hytazerSmall = OrderedDict([
    # Medium: Helium
    # rocket d=438
    # rocket skin thk approx 5mm
    ('tankname', 'hytazer_small'),
    ('polarOpeningRadius', NGTBITDesign['polarOpeningRadius']),
    ('dcyl', 400),  # mm
    ('lcyl', 500),  # mm
    ('safetyFactor', 2),
    ('pressure', 5),  # pressure in MPa (bar / 10.)
    ('domeContour', getReducedDomePoints(os.path.join(programDir, 'data', 'Dome_contour_NGT-BIT-shrinkage.txt'), 4)),
    ('domeType', 'generic'),
    ('failureMode', 'fibreFailure'),
    ('useHydrostaticPressure', False),
    ('relRadiusHoopLayerEnd', 0.98),
    ('numberOfRovings', 2),
    ('polarOpeningRadius', 23),  # mm
])

if __name__ == '__main__':
    print("',\n'".join(defaultDesign.keys()))