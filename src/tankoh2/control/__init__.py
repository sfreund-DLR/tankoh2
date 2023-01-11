"""package with scripts controlling the execution of tankoh2 features"""

if __name__ == '__main__':
    from tankoh2.control.control_metal import createDesign as createDesignMetal
    from tankoh2.control.control_winding import createDesign as createDesignWinding
    import tankoh2.design.existingdesigns as parameters


    if 0:
        params = parameters.atheat3.copy()

        params.update([
            ('tankname', params['tankname']),
            ('verbosePlot', True),
            #('maxLayers', 20),
            ('targetFuncWeights', [1., 1., 0., 0., .25, 0.25])
        ])

        params.pop('initialAnglesAndShifts', None)

        runCompositCalc = True
        if runCompositCalc:
            createDesignWinding(**params.copy())

        runMetalCalc = False
        if runMetalCalc:
            params['materialName'] = 'alu6061T6'
            #params['materialName'] = 'alu2219Brewer'
            #params['materialName'] = 'alu2219'
            createDesignMetal(**params.copy())
    elif 1:

        params = parameters.vphDesign1_isotensoid.copy()

        params.update([
            ('tankname', params['tankname'] + '_PO_too_small'),
            ('verbosePlot', True),
            ('targetFuncWeights', [1.0, 0.2, 0.0, 0.0, 0, 0] ),
            ('dcyl'                , 2890.0),
            ('pressure'            , 0.397),
            ('lcyl'                , 862.5        ),
            ("numberOfRovings", 12,),
        ])
        createDesignWinding(**params.copy())
    else:
        paramsa = parameters.atheat3.copy()
        paramsa.update([
            ('verbosePlot', True),
            ('targetFuncWeights', [1., 0., 0., 0., .25, 0.2])
        ])

        paramsv = parameters.vph_helicalTest.copy()
        paramsv.update([
            ('verbosePlot', True),
            ('targetFuncWeights', [1., 0., 0., 0., .25, 0.2])
        ])

        # puck weight, bending weight, doHoopOpt, params
        inputs = [
            [1,0,False, paramsa],
            [0,1,False, paramsa],
            # [1,0.4,False, paramsa],
            # [1,0,True, paramsa],
            # [0,1,True, paramsa],
            # [1,0.4,True, paramsa],
            # [1,0,False, paramsv],
            # [0,1,False, paramsv],
            [1,0.4,False, paramsv],
                   ]
        results = []
        for puck, bend, doHoopOpt, params in inputs:
            from tankoh2 import settings
            settings.doHoopOpt = doHoopOpt
            params=params
            params.update([
                ('tankname', params['tankname'] + f'_p{puck}_b{bend}_doHoopOpt{doHoopOpt}'),
                ('targetFuncWeights', [puck, puck/4, 0., 0., bend, bend/4]),
                ('maxLayers',3),
            ])
            r = createDesignWinding(**params.copy())
            r.insert(0, params['tankname'])
            results.append(r)

        from tankoh2.service.utilities import indent
        from tankoh2.control.genericcontrol import resultNamesFrp
        print(indent([['name']+resultNamesFrp]+results))

