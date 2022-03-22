"""package with scripts controlling the execution of tankoh2 features"""








if __name__ == '__main__':
    from tankoh2.control.control_metal import createDesign as createDesignMetal
    from tankoh2.control.control_winding import createDesign as createDesignWinding
    import tankoh2.design.existingdesigns as allParamSets

    params = allParamSets.ttDesignLh2
    params = allParamSets.ttDesignCh2
    #params = allParamSets.vphDesign1
    #params['verbose'] = True

    createDesignWinding(**params.copy())
    params['materialName'] = 'alu2219'
    createDesignMetal(**params.copy())


