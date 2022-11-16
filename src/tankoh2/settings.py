"""read/write setting file"""

import json
import os, sys

from tankoh2.service.exception import Tankoh2Error

myCrOSettings = None
exampleSettingsFileName = 'settings_example.json'
useRstOutput = False
minCylindricalLength = 150
epsilon = 1e-8

optimizerSeed = None
"""Seed for evolutionary optimization for repeatable runs. If -1, no seed is used"""


class PychainMock():
    """This class is a mock of pychain.

    When pychain can not be imported, it stores the respective error message.
    The error will be raised when trying to access pychain attributes.
    By this, tankoh2 standalone functions can be used without error messages due to missing pychain."""
    def __init__(self, errorMsg = None):
        self.errorMsg = errorMsg

    def __getattr__(self, item):
        raise Tankoh2Error(self.errorMsg)

def applySettings(filename=None):
    """reads settings from the settingsfile"""
    global myCrOSettings, useRstOutput, optimizerSeed
    from tankoh2 import log
    pychain = PychainMock()
    defaultSettingsFileName = 'settings.json'
    searchDirs = ['.', os.path.dirname(__file__), os.path.dirname(os.path.dirname(os.path.dirname(__file__)))]
    if filename is None:
        for searchDir in searchDirs:
            if defaultSettingsFileName in os.listdir(searchDir):
                # look for settings file in actual folder
                filename = os.path.join(searchDir, defaultSettingsFileName)
    if filename is None:
        writeSettingsExample()
        pychain.errorMsg = f'Could not find the settings file "{defaultSettingsFileName}" in the ' \
                           f'following folders: {searchDirs}.\n' \
                           f'An example settings file is written to ./{exampleSettingsFileName}.\n' \
                           f'Please add the requried settings and rename the file to ' \
                           f'{exampleSettingsFileName.replace("_example", "")}.'
        return pychain

    with open(filename, 'r') as f:
        settings = json.load(f)

    if 'useRstInputOutput' in settings:
        useRstOutput = 'true' == settings['useRstInputOutput'].lower()
    if 'optimizerSeed' in settings:
        if not isinstance(settings['optimizerSeed'], int):
            raise Tankoh2Error(f'Parameter "optimizerSeed" in the settings file "{filename}" must be int.')
        optimizerSeed = settings['optimizerSeed']
        if optimizerSeed == -1:
            optimizerSeed = None

    #############################################################################
    # Read pychain and abq_pychain path and put it in sys.path
    #############################################################################
    # v0.95.3
    major, minor = str(sys.version_info.major), str(sys.version_info.minor)
    pyVersionString = f'{major}_{minor}'
    pythonApiPath = os.path.join(settings['mycropychainPath'], f'pythonAPI\{pyVersionString}')
    if not os.path.exists(pythonApiPath):
        # v 0.90c
        pythonApiPath = os.path.join(settings['mycropychainPath'], f'pythonAPI\python{pyVersionString}_x64')
        if not os.path.exists(pythonApiPath):
            # v 0.95.2
            pythonApiPath = os.path.join(settings['mycropychainPath'], f'pythonAPI\python{pyVersionString}')
    #abaqusPythonLibPath = os.path.join(settings['mycropychainPath'], 'abaqus_interface_0_89')
    abaqusPythonLibPath = os.path.join(settings['mycropychainPath'], 'abaqus_interface_0_95_4')

    log.info(f'Append mycropychain path to sys path: {pythonApiPath}')
    sys.path.append(pythonApiPath)
    
    # import API - MyCrOChain GUI with activated TCP-Connector needed
    pychainActive = True
    try:
        # v <= 0.90
        import mycropychain as pychain
    except ModuleNotFoundError:
        # v > 0.90
        try:
            if minor == '6':
                import mycropychain36 as pychain
            else: # minor == '8'
                import mycropychain38 as pychain
        except ModuleNotFoundError:
            pychain = PychainMock('Could not find package "mycropychain". '
                                  'Please check the path to mycropychain in the settings file.')
            return pychain
        else:
            if len(pychain.__dict__) < 10:
                pychainActive = False
    else:
        if len(pychain.__dict__) < 10:
            pychainActive = False

    if not pychainActive:
        # len(pychain.__dict__) was 8 on failure and 17 on success
        pychain = PychainMock('Could not connect to mycropychain GUI. '
                              'Did you start the GUI and activated "TCP Conn."?')
        return pychain
    else:
        # set general path information
        myCrOSettings = pychain.utility.MyCrOSettings()
        myCrOSettings.abaqusPythonLibPath = abaqusPythonLibPath

def writeSettingsExample():
    """writes an example for settings"""
    from tankoh2 import log
    log.info(f'write file {exampleSettingsFileName}')
    with open(exampleSettingsFileName, 'w') as f:
        json.dump({'comment': "Please rename this example file to 'settings.json' and include "
                              "'mycropychainPath' to run µWind. For paths in Windows, please use '\\' or '/'",
                   'mycropychainPath': '',
                   "useRstInputOutput": "false",
                   "doc_useRstInputOutput": 'flag to write result tables for rst',
                   "optimizerSeed": -1,
                   "doc_optimizerSeed": 'Seed for evolutionary optimization for repeatable runs. '
                                        'If -1, no seed is used',
                   },
                  f, indent=2)


if __name__ == '__main__':
    writeSettingsExample()
