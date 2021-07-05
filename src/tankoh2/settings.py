"""read/write setting file"""

import json
import os, sys

from tankoh2.exception import Tankoh2Error

myCrOSettings = None
exampleFileName = 'settings_example.json'

def applySettings(filename=None):
    """reads settings from the settingsfile"""
    from tankoh2 import log
    defaultSettingsFileName = 'settings.json'
    searchDirs = ['.', os.path.dirname(__file__), os.path.dirname(os.path.dirname(os.path.dirname(__file__)))]
    if filename is None:
        for searchDir in searchDirs:
            if defaultSettingsFileName in os.listdir(searchDir):
                # look for settings file in actual folder
                filename = os.path.join(searchDir, defaultSettingsFileName)
    if filename is None:
        writeSettingsExample()
        raise Tankoh2Error(
            f'Could not find the settings file "{defaultSettingsFileName}" in the following folders: {searchDirs}.\n'
            f'An example settings file is written to ./{exampleFileName}.\n'
            f'Please add the requried settings and rename the file to {exampleFileName.replace("_example","")}.')

    with open(filename, 'r') as f:
        settings = json.load(f)
<<<<<<< HEAD
    major, minor = str(sys.version_info.major), str(sys.version_info.minor)
    pyVersionString = major+minor
    # v 0.90c
    pythonApiPath = os.path.join(settings['mycropychainPath'], f'pythonAPI\python{pyVersionString}_x64')
    if not os.path.exists(pythonApiPath):
        # v 0.95.2
        pythonApiPath = os.path.join(settings['mycropychainPath'], f'pythonAPI\python{pyVersionString}')
        if not os.path.exists(pythonApiPath):
            # v0.95.3
            pyVersionString = f'{major}_{minor}'
            pythonApiPath = os.path.join(settings['mycropychainPath'], f'pythonAPI\{pyVersionString}')
=======
    pyVersionString = sys.version[0]+sys.version[2]
    print('pyVersion', pyVersionString)
    pythonApiPath = os.path.join(settings['mycropychainPath'], f'pythonAPI\python{pyVersionString}')
>>>>>>> 6ff21b7 (settings -- get folder of abaqus_interface from current muChain version)
    #abaqusPythonLibPath = os.path.join(settings['mycropychainPath'], 'abaqus_interface_0_89')
    abaqusPythonLibPath = os.path.join(settings['mycropychainPath'], 'abaqus_interface_0_95')

    log.info(f'Append mycropychain path to sys path: {pythonApiPath}')
    sys.path.append(pythonApiPath)
    
    # import API - MyCrOChain GUI with activiated TCP-Connector needed
    try:
        import mycropychain as pychain
    except ModuleNotFoundError:
        try:
            if minor == '6':
                import mycropychain36 as pychain
            else: # minor == '8'
                import mycropychain38 as pychain
        except ModuleNotFoundError:

            raise Tankoh2Error('Could not find package "mycropychain". Please check the path to mycropychain in the '
                               'settings file.')
        else:
            if len(pychain.__dict__) < 10:
                # len(pychain.__dict__) was 8 on failure and 17 on success
                raise Tankoh2Error('Could not connect to mycropychain GUI. Did you start the GUI and activated "TCP Conn."?')

        # set general path information
        global myCrOSettings
        myCrOSettings = pychain.utility.MyCrOSettings()
        myCrOSettings.abaqusPythonLibPath = abaqusPythonLibPath


def writeSettingsExample():
    """writes an example for settings"""
    from tankoh2 import log
    log.info(f'write file {exampleFileName}')
    with open('settings_example.json', 'w') as f:
        json.dump({'comment': "Please rename this example file to 'settings.json' and include the required settings. "
                              "For paths, please use '\\' or '/'",
                   'mycropychainPath': ''},
                  f, indent=2)


if __name__ == '__main__':
    writeSettingsExample()
