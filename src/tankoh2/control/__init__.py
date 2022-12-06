"""package with scripts controlling the execution of tankoh2 features"""








if __name__ == '__main__':
    from tankoh2.control.control_metal import createDesign as createDesignMetal
    from tankoh2.control.control_winding import createDesign as createDesignWinding
    import tankoh2.design.existingdesigns as parameters

    if 0:
        params = parameters.vphDesign1_isotensoid.copy()

        params['dcyl'] = 7500
        params['lcylByR'] = 2
        params['maxLayers'] = 2
        params['failureMode'] = 'fibreFailure'
        params['verbosePlot'] = True

        runCompositCalc = True
        if runCompositCalc:
            createDesignWinding(**params.copy())

        runMetalCalc = False
        if runMetalCalc:
            params['materialName'] = 'alu6061T6'
            #params['materialName'] = 'alu2219Brewer'
            #params['materialName'] = 'alu2219'
            createDesignMetal(**params.copy())
    else:
        name = 'exact_cyl_isotensoid'
        sampleXFile = '' # + 'C:/PycharmProjects/tankoh2/tmp/doe_isotensoid_MuWind_puckff_20221205_152849/sampleX.txt'
        from tankoh2.control.control_doe import mainControl, getDesignAndBounds
        if 1:
            mainControl(name, sampleXFile)
        else:
            from tankoh2.service.plot.doe import plotGeometryRange
            from delismm.model.doe import DOEfromFile
            samples = DOEfromFile(sampleXFile) if sampleXFile else None
            _, lb, ub, _ = getDesignAndBounds(name)
            plotGeometryRange(lb, ub, show=True, samples=samples)


