
from tankoh2.control.genericcontrol import parseDesignArgs
from tankoh2.design.existingdesigns import defaultDesign


def test_parseDesignArgs():
    defaultArgs = defaultDesign.copy()
    defaultArgs['domeType'] = 'circle' # to not use µWind in test

    defaultArgs['lcyl'] = 2000
    kwargs = parseDesignArgs(defaultArgs.copy())
    assert kwargs['lcyl'] == 2000

    defaultArgs['lcylByR'] = 2
    defaultArgs['dcyl'] = 2000
    defaultArgs.pop('lcyl')
    kwargs = parseDesignArgs(defaultArgs.copy())
    assert kwargs['lcyl'] == 2000





