"""package with scripts controlling the execution of tankoh2 features"""








if __name__ == '__main__':
    from tankoh2.control.control_metal import createDesign as createDesignMetal
    from tankoh2.control.control_winding import createDesign as createDesignWinding
    import tankoh2.design.existingdesigns as parameters

    params = parameters.defaultDesign.copy()
    params = parameters.defaultUnsymmetricDesign.copy()

    params['nodeNumber'] = 50
    createDesignWinding(**params.copy())
    runMetalCalc = False
    if runMetalCalc:
        params['materialName'] = 'alu6061T6'
        #params['materialName'] = 'alu2219Brewer'
        #params['materialName'] = 'alu2219'
        createDesignMetal(**params.copy())


