""""""


# HyMod
# 12mm thickness in cylindrical section
#

hymodDesign = dict([('burstPressure', 77.85),
                    ('lzyl', 1000.),
                    ('minPolarOpening', 23),
                    ('dzyl', 300.)
                    ])


NGTBITDesign = dict([('tankname', 'NGT-BIT-2020-09-16'), 
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


