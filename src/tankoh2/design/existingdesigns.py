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
        ['maxLayers', 'Optimization', 'layers', 100, int, 'Maximum number of layers to be added', ''],
        ['relRadiusHoopLayerEnd', 'Optimization', '', 0.95, float,
         'relative radius (to cyl radius) where hoop layers end [-]', ''],
        ['targetFuncWeights', 'Optimization', 'tfWeights', [1.,.2,1.,0, .25, 0.1], list,
         'Weights to the target function constituents: maxPuck, maxCritPuck, sumPuck, layerMass', ''],
        # Geometry
        ['dcyl', 'Geometry', 'd_cyl', 400, float,
         'Diameter of the cylindrical section [mm]. Can be automatically adapted if volume is given', ''],
        ['lcyl', 'Geometry', 'l_cyl', 500, float,
         'Length of the cylindrical section [mm]. Can be automatically adapted if volume is given', ''],
        ['lcylByR', 'Geometry', '', 2.5, float, 'only if lcyl is not given [-]', ''],
        ['volume', 'Geometry', '', None, float,
         'Volume requirement [m**3]. If it does not fit to other geometry parameters, '
         'l_cyl is adapted and if l_cly would be below 150mm d_cyl is adapted', ''],
        # Geometry_Dome
        ['domeType', 'Geometry_Dome', '', 'isotensoid', '',
         'Shape of dome geometry [isotensoid, isotensoid_MuWind, circle, ellipse, custom]', ''],
        ['domeContour', 'Geometry_Dome', '(x,r)', (None,None), '',
         'Must be given if domeType==custom. X- and R-array should be given without whitespaces like '
         '"[x1,x2],[r1,r2]" in [mm]', ''],
        ['polarOpeningRadius', 'Geometry', 'r_po', 20, float, 'Polar opening radius [mm]', ''],
        ['domeLengthByR', 'Geometry_Dome', 'l/r_cyl', 0.5, float,
         'Axial length of the dome. Only used for domeType==ellipse [mm]', ''],
        ['alpha', 'Geometry_Dome', '(dcyl - dsmall)/dcyl', 0.5, float,
         'ratio of the difference of cylindrical and small diameter to the cylindrical diameter', ''],
        ['beta', 'Geometry_Dome', '(lrad + lcone)/dcyl', 1.5, float,
         'ratio of sum of the radial and conical length to the cylindrical diameter', ''],
        ['gamma', 'Geometry_Dome', 'lrad/(lrad + lcone)', 0.5, float,
         'ratio of the radial length to the sum of radial and conical length', ''],
        ['delta1', 'Geometry_Dome', 'ldome/rsmall', 0.5, float,
         'ratio of the semi axes of the elliptical dome end', ''],
        # Geometry_Dome2
        ['dome2Type', 'Geometry_Dome2', '', None, '',
         'Shape of dome geometry [isotensoid, isotensoid_MuWind circle, ellipse, custom]', ''],
        ['dome2Contour', 'Geometry_Dome2', '(x,r)', (None, None), '',
         'Must be given if domeType==custom. X- and R-array should be given without whitespaces like '
         '"[x1,x2],[r1,r2]" in [mm]', ''],
        ['dome2LengthByR', 'Geometry_Dome2', 'l/r_cyl', 0.5, float,
         'Axial length of the dome. Only used for domeType==ellipse [mm]', ''],
        # Design
        ['safetyFactor', 'Design', 'S', 2, float, 'Safety factor used in design [-]', ''],
        ['valveReleaseFactor', 'Design', 'f_pv', 1.1, float,
         'Factor defining additional pressure to account for the valve pressure inaccuracies', ''],
        ['h2Mass', 'Geometry', '', None, float, 'H2 Mass, defines volume if given & no volume given'],
        ['temperature', 'Design', '', 23, float,
         'Temperature, for differentiating between cryogenic and compressed storage and finding density [K]', ''],
        ['pressure', 'Design', 'p_op', 5., float, 'Operational pressure [MPa]', ''],
        ['minPressure', 'Design', 'p_op_min', 0.1, float, 'Minimal operational pressure [MPa]', ''],
        ['burstPressure', 'Design', 'p_b', 10., float,
         'Burst pressure [MPa]. If given, pressure, useHydrostaticPressure, safetyFactor, '
         'valveReleaseFactor are not used', ''],
        ['maxFill', 'Design', 'p_b', 0.9, float,
         'Max fill level for liquid storage', ''],
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
        ['layerThk', 'Fiber roving parameters', 'thk', 0.125, float, 'Thickness of layers [mm]', ''],
        ['layerThkHoop', 'Fiber roving parameters', 'thk', None, float,
         'Thickness of hoop (circumferential) layers [mm]', ''],
        ['layerThkHelical', 'Fiber roving parameters', 'thk', None, float,
         'Thickness of helical layers [mm]. If None, layerThkHoop is used', ''],
        ['rovingWidth', 'Fiber roving parameters', 'witdh', 3.175, float, 'Width of one roving [mm]', ''],
        ['rovingWidthHoop', 'Fiber roving parameters', 'witdhHoop', None, float,
         'Width of one roving in hoop layer [mm]', ''],
        ['rovingWidthHelical', 'Fiber roving parameters', 'witdhHelical', None, float,
         'Width of one roving in helical layer [mm]. If None, rovingWidthHoop is used', ''],
        ['numberOfRovings', 'Fiber roving parameters', '#', 4, int,
         'Number of rovings (rovingWidthHoop*numberOfRovings=bandWidth)', ''],
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
    ('maxLayers', 2),
    ('nodeNumber', 1000),
    #('domeType', 'isotensoid'),
    ])

# design to make plots where the layers are visible in µWind
plotDesign = OrderedDict([
    ('tankname', 'plotDesign'),
    ('dcyl', defaultDesign['dcyl']/4),
    ('lcyl', defaultDesign['lcyl']/5),
    ('layerThk', defaultDesign['layerThk']*2),
    ('burstPressure', 42.),
    ('maxLayers', 3),
    ('domeType', 'isotensoid'),
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
    ('temperature',293),
    ('lcyl', 1000.),
    ('polarOpeningRadius', 23),
    ('dcyl', 300.),
    ('temperature', 293),
])



NGTBITDesign = OrderedDict([
    ('tankname', 'NGT-BIT-2022-03-04'),
    ('pressure', 70), # MPa
    ('burstPressure', 140.), # MPa
    ('valveReleaseFactor', 1.),
    ('temperature',293),
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
    ('layerThkHoop', 0.089605735), # thickness for 62% FVG
    ('layerThkHelical', 0.089605735), # thickness for 62% FVG
    # single ply thickness with 55% FVG
    #('layerThkHoop', 0.101010101), # thickness for 55% FVG
    #('layerThkHelical', 0.101010101), # thickness for 55% FVG
    # single ply thickness with 60% FVG
    #('layerThkHoop', 0.092592593), # thickness for 60% FVG
    #('layerThkHelical', 0.092592593), # thickness for 60% FVG
    ('rovingWidth', 8.00),
    ('numberOfRovings', 6), # number of spools usabale at INVENT
    ('tex', 800),
    ('fibreDensity', 1.8),
    # optimizer settings
    ('maxLayers', 3),
    ('verbose', False),
    ('temperature', 293),
    ])

NGTBIT_Invent = NGTBITDesign.copy()
NGTBIT_Invent.update([
    ('tankname', 'NGT-BIT-Invent'),
    ('dcyl', 206.205492 * 2),
    ('rovingWidthHoop', 13.1 / 4),
    ('rovingWidthHelical', 12.5 / 4),
    ('layerThkHoop', 0.226),
    ('layerThkHelical', 0.236),
    ('numberOfRovings', 4),
    ('domeContour', getReducedDomePoints(os.path.join(programDir, 'data', 'Dome_contour_NGT-BIT-measured_modPO.txt'), 4)),
])

NGTBIT_Invent_ReorderLay = NGTBIT_Invent.copy()
NGTBIT_Invent_ReorderLay.update([
    ('initialAnglesAndShifts',
     [
(90, 15   ),(90, 13.5 ),(8.188, 0 ),(8.188, 0 ),(90, 12   ),(90, 10.5 ),(8.1, 0),(8.1, 0),(90, 9    ),
(90, 7.5  ),(8., 0),(8., 0),(90, 6    ),(90, 4.5  ),(8., 0),(13.491, 0),(90, 3    ),(90, 1.5  ),(14.388, 0),
(17.427, 0),(90, 0    ),(90, -1.5 ),(17.827, 0),(18.846, 0),(90, -3   ),(90, -4.5 ),(22.75, 0 ),(24.432, 0),
(90, -6   ),(90, -7.5 ),(24.926, 0),(29.079, 0),(30.886, 0),(90, -9   ),(90, -10.5),(90, -12  ),(90, -13.5),
(90, -15  ),
     ]
     ),
    ('maxlayers', 38),
    ])


NGTBITDesignNewThk = NGTBITDesign.copy()  # use new thickness for kuempers material and winding at FVT
NGTBITDesignNewThk.pop('burstPressure')
NGTBITDesignNewThk.update([
    ('pressure', 70), # MPa
    ('nodeNumber', 2000),
    ('tankname', 'NGT-BIT-2022-07_new_thk'),
    ('dcyl', 400.), # due to shrinkage
    #('materialName', 'kuempers_k-preg-002-012-65-00'),
    ('layerThkHoop', 0.191), # thickness for 61% FVG
    ('layerThkHelical', 0.191), # thickness for 61% FVG
    ('rovingWidthHoop', 4.00),
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
    ('maxLayers', 46)
])

NGTBITDesignNewThkCustomV3 = NGTBITDesignNewThkCustomV2.copy()
NGTBITDesignNewThkCustomV3.update([
    ('initialAnglesAndShifts',
        [[7.12871052,0 ],[90,13.5       ],[7,0           ],[90,12.88636364],[90,12.27272727],[7.3,0         ],
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
    ('temperature',293),
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
    ('layerThkHoop', 0.125),
    ('layerThkHelical', 0.129),
    ('rovingWidthHoop', 3.175),
    ('numberOfRovings', 4), # number of spools usabale at INVENT
    ('tex', 446),
    ('fibreDensity', 1.78),
    # optimizer settings
    ('maxLayers', 200)
    ])

NGTBITDesign_small = OrderedDict([
    ('tankname', 'NGT-BIT-small'),
    ('temperature',293),
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
    ('layerThkHoop', 0.125),
    ('layerThkHelical', 0.129),
    ('rovingWidthHoop', 3.175),
    ('numberOfRovings', 12),
    ('tex', 800),
    ('fibreDensity', 1.78),
    # optimizer settings
    ('maxLayers', 200)
    ])

vphDesign1 = OrderedDict([
    ('tankname', 'vph_design1_iff_sf2.25'),
    ('lcyl', 3218.8),
    ('dcyl', 1200.*2),
    ('safetyFactor', 2.25),
    ('pressure', .2),  # [MPa]
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

vph_hoopTest = vphDesign1_isotensoid.copy()
vph_hoopTest.pop('lcyl')
vph_hoopTest.pop('safetyFactor')
vph_hoopTest.update([
    ('dcyl', 3790.0), ('lcyl', 824.325), ('pressure', 0.478),
    ('verbosePlot', True),
    ('numberOfRovings', 30),
    ('initialAnglesAndShifts',
     [(4.202, 0   ),(90, 34.254 ),(10.248, 0  ),(90, 42.627 ),(90, 23.136 ),(12.988, 0  ),(90, 39.755 ),
      (6.343, 0   ),(90, 42.627 ),(90, 337.686),(90, 48.631 ),(90, 83.767 ),(10.511, 0  ),(90, 48.631 ),
      #(90, 83.767 ),(90, 48.631 ),(90, 396.533),(90, 48.631 ),(90, 48.631 ),(90, 83.767 ),(90, 48.631 ),
      #(6.382, 0   ),(90, 48.631 ),(90, 48.631 ),(90, 83.767 ),(90, 83.767 ),(90, 48.631 ),(90, 48.631 ),
      #(90, 48.631 ),(90, 83.767 ),(90, 83.767 ),(90, 48.631 ),(90, 49.299 ),(90, 11.789 ),(90, 11.789 ),
      #(90, 11.789 ),(14.631, 0  ),(90, 48.631 ),(90, 48.631 ),(90, 2.568  ),
      #(90, 11.789 ),(90, 11.789 ),(90, 11.789 ),(90, 11.789 ),(90, 11.789 ),(90, 11.789 ),(90, 11.789 ),
      #(90, 11.789 ),(90, 11.789 ),(7.854, 0   ),(90, 11.789 ),(90, 11.789 ),(90, 11.789 ),(90, 11.789 ),
      ]     ),
    #('maxLayers', 10)
])

vph_helicalTest = vphDesign1_isotensoid.copy()
vph_helicalTest.pop('lcyl')
vph_helicalTest.pop('safetyFactor')
vph_helicalTest.update([
    ('dcyl', 2620.0), ('lcyl', 3257.97), ('pressure', 0.874  ),
    ('verbosePlot', True),
    ('numberOfRovings', 12),
])

kautextDesign = OrderedDict([
                             # General
                             ('tankname', 'Kautext'),
                             #('nodeNumber', 500),  # might not exactly be matched due to approximations
                             ('verbose', False),

                             # Optimization
                             ('maxLayers', 100),

                             # Geometry
                             #('domeType', pychain.winding.DOME_TYPES.ISOTENSOID),  # CIRCLE; ISOTENSOID
                             #('domeContour', (None, None)),  # (x,r)
                             ('polarOpeningRadius', 4.572604469),  # mm
                             ('dcyl', 260.),  # mm
                             ('lcyl', 588.), #mm
                             #('lcylByR', 2.5),

                             # Design
                             ('safetyFactor', 2.0),
                             ('pressure', 70.),  # [MPa]
                             ('failureMode', 'fibreFailure'),

                             # Material
                             ('materialName', 'CFRP_T700SC_LY556'),

                             # Fiber roving parameter
                             ('layerThkHoop', 0.125),
                             ('layerThkHelical', 0.129),
                             ('rovingWidthHoop', 3.175),
                             ('numberOfRovings', 12),
                             # bandWidth = rovingWidthHoop * numberOfRovings
                             ('tex', 800),  # g / km
                             ('fibreDensity', 1.78),  # g / cm^3
                             ])

ttDesignLh2 = OrderedDict([
    ('tankname', 'tt_lh2'),
    ('polarOpeningRadius', 40),  # mm
    ('dcyl', 223.862*2),  # mm
    ('lcyl', 559.6572), #mm
    ('safetyFactor', 1.55),
    ('pressure', 0.25),  # [MPa]
    ('domeType', 'isotensoid'),
    ('failureMode', 'interFibreFailure'),
    ('useHydrostaticPressure', True),
])

ttDesignCh2 = ttDesignLh2.copy()
ttDesignCh2.update([
    ('tankname', 'tt_ch2'),
    ('dcyl', 269.66362*2),  # mm
    ('lcyl', 674.15906),  # mm
    ('pressure', 70.),  # [MPa]
    ('maxLayers', 200),
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
    ('pressure', 60),  # [MPa]
    ('temperature',293),
    ('domeType', 'isotensoid'),
    ('failureMode', 'fibreFailure'),
    ('useHydrostaticPressure', False),
    ('relRadiusHoopLayerEnd', 0.98),
    ('linerThickness', 3),
    ('volume', 0.037),
    ('temperature', 293),
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
])

atheat3 = atheat2.copy()
atheat3.pop('domeContour')
atheat3.update([
    ('tankname', 'atheat_He'),
    ('domeType', 'isotensoid'),
    ('dcyl', 370),  # mm
])

atheat4 = atheat3.copy()
atheat4.update([
    ('dcyl', 356),  # mm
    ('rovingWidthHoop', 3),
    ('linerThickness', 3),
    ('domeType', 'torispherical'),
    ('maxLayers', 4),
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
    ('pressure', 70),  # [MPa]
    ('temperature',293),
    ('domeType', 'isotensoid'),
    ('failureMode', 'fibreFailure'),
    ('useHydrostaticPressure', True),
    ('verbose', False),
])

conicalTankDesign = OrderedDict([
    ('tankname', 'conicalTankDesign'),
    ('volume', 20),  # m^3
    ('dcyl', 3000),  # mm
    ('polarOpeningRadius', 100),  # mm
    ('alpha', 0.831),
    ('beta', 2.453),
    ('gamma', 0.796),
    ('safetyFactor', 2),
    ('domeType', 'conicalTorispherical'),
    ('dome2Type', 'isotensoid'),
    ('pressure', 0.172),  # pressure in MPa (bar / 10.)
    ('failureMode', 'interFibreFailure'),
    ('tankLocation', 'fuselage'),
    ('useHydrostaticPressure', True),
    ('numberOfRovings', 12),
    ('minPressure', 0.12),
    ('verbosePlot', True),
    ('nodeNumber', 1000),
    ('targetFuncWeights', [1.,.25,2.,.1, 0, 0])
])

hytazer = OrderedDict([
    ('tankname', 'hytazer_front_defined'),
    ('volume', 23.252),  # m^3
    ('dcyl', 2678),  # mm
    ('polarOpeningRadius', 50),  # mm
    ('alpha', 0.893),
    ('beta', 2.541),
    ('gamma', 0.67),
    ('safetyFactor', 1.33),
    ('domeType', 'isotensoid'),
    ('dome2Type', 'torispherical'),
    ('pressure', 0.2),  # [MPa]
    ('failureMode', 'interFiberFailure'),
    ('tankLocation', 'fuselage'),
    ('useHydrostaticPressure', True),
    ('numberOfRovings', 12),
    ('minPressure', 0.11),
    ('verbosePlot', True),
    ('nodeNumber', 1000),
])


hytazerSMR1 = OrderedDict([ # short/medium range single aisle aircraft, tank #1
    ('tankname', 'hytazer_smr_ff_10bar'),
    ('polarOpeningRadius', 100),
    ('dcyl', 2 * (1716 + defaultDesign['linerThickness'])),  # mm
    ('pressure', .2),  # [MPa]
    ('domeType', 'isotensoid'),
    ('useHydrostaticPressure', True),
    ('volume', 23.252),
    ('failureMode', 'interFibreFailure'),
    ('safetyFactor', 1.33),
    ('nodeNumber', 1000),
    ('materialName', 'CFRP_T700SC_LY556'),
    ('valveReleaseFactor', 1.1),
    ('verbosePlot', True),
    ('numberOfRovings', 12),
    ('targetFuncWeights', [1.,.2,.0,.0,0.,0.]),
])
hytazerSMR1['tankname'] = f'hytazer_smr_{"ff" if hytazerSMR1["failureMode"] == "fibreFailure" else "iff"}_' \
                          f'{hytazerSMR1["pressure"]*10}bar'


hytazerSMR2 = hytazerSMR1.copy()
hytazerSMR2.update([
    ('volume', 23.252),
    ('dcyl', 1431 * 2 + 2 * defaultDesign['linerThickness']),  # mm
    ('lcyl', 150),  # mm
    ('domeType', 'conicalIsotensoid'), # alternative: conicalTorispherical
    # TODO: beta etc.
])

hytazerD400 = OrderedDict([
    ('tankname', 'hytazer_small'),
    ('polarOpeningRadius', NGTBITDesign['polarOpeningRadius']),
    ('dcyl', 400),  # mm
    ('lcyl', 500),  # mm
    ('safetyFactor', 2),
    ('pressure', 5),  # [MPa]
    ('domeContour', getReducedDomePoints(os.path.join(programDir, 'data', 'Dome_contour_NGT-BIT-shrinkage.txt'), 4)),
    ('domeType', 'generic'),
    ('failureMode', 'fibreFailure'),
    ('useHydrostaticPressure', False),
    ('relRadiusHoopLayerEnd', 0.98),
    ('numberOfRovings', 2),
    ('nodeNumber', 500),
])

upLiftHalfTank400 = hytazerD400.copy()
upLiftHalfTank400.pop('pressure')
upLiftHalfTank400.update([
    ('tankname', 'upLiftHalfTank400'),
    ('lcyl', 500),  # mm
    ('burstPressure', 5),  # [MPa]
    ('temperature', 77),
    ('failureMode', 'interFibreFailure'),
    ('numberOfRovings', 4),
])

dLightBase = OrderedDict([
    ('polarOpeningRadius', 50),
    ('dcyl', 1820 - 2 * (2 + 50 + 50)),  # mm, 1820 is fuselage outer d
    ('safetyFactor', 2),
    ('valveReleaseFactor', 1.1),
    ('pressure', 70),  # [MPa]
    ('domeType', 'isotensoid'),
    ('failureMode', 'fibreFailure'),
    ('useHydrostaticPressure', False),
    ('relRadiusHoopLayerEnd', 0.98),
    ('nodeNumber', 500),
    ('maxLayers', 500),
    ('temperature', 293),
    ('linerThickness', 3),
    ('numberOfRovings', 4),
    ('linerThickness', 3),
])


dLightConventional = dLightBase.copy()
dLightConventional.update([
    ('tankname', 'dLight_conventional'),
    ('volume', 3 * 2/3),  # m**3,  use 2/3 of required volume for front tank to utilize full diameter
])
dLight3tanks = dLightBase.copy()
dLight3tanks.update([
    ('tankname', 'dLight_3tanks'),
    ('dcyl', 796-100),  # three cylinders inside
    ('volume', 3.775/3),
])

dLight7tanks = dLightBase.copy()
dLight7tanks.update([
    ('tankname', 'dLight_7tanks'),
    ('dcyl', 572-50),  # seven cylinders inside
    ('volume', 3.775/7),
])

dLight7tanks_600bar = dLightBase.copy()
dLight7tanks_600bar.update([
    ('tankname', 'dLight_7tanks_600bar'),
    ('dcyl', 572-50),  # seven cylinders inside
    ('h2Mass', 150/7),
    ('pressure', 60),  # [MPa]
])

dLight7tanks_700bar_T1000G = dLightBase.copy()
dLight7tanks_700bar_T1000G.update([
    ('tankname', 'dLight_7tanks_700bar_T1000G'),
    ('materialName', 'CFRP_T1000G_LY556'),
    ('dcyl', 572-50),  # seven cylinders inside
    ('h2Mass', 150/7),  # storageMass
    ('pressure', 70),  # [MPa]
    ('tex', 485),
    ('fibreDensity', 1.80),
    ('maxFill', 0.95),
    ('nodeNumber', 1000),
])

shipping = OrderedDict([
    ('tankname', 'shipping'),
    ('polarOpeningRadius', 200),  # mm
    ('dcyl', 5000),  # mm d_a - 2*t_estimate
    ('lcyl', 50000),  # mm - just an estimate for now
    ('safetyFactor', 2),
    ('pressure', 1),  # [MPa]
    ('temperature',293),
    ('domeType', 'isotensoid'),
    ('failureMode', 'fibreFailure'),
    ('useHydrostaticPressure', False),
    ('verbosePlot', True),
    ('tex', defaultDesign['tex']*12),
    ('rovingWidth', defaultDesign['rovingWidth']*12),
])


if __name__ == '__main__':
    print("',\n'".join(defaultDesign.keys()))