"""read/write setting file"""

import json
import os, sys

myCrOSettings = None

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
        log.error(
            f'Could not find the settings file "{defaultSettingsFileName}" in the following folders: {searchDirs}')

    with open(filename, 'r') as f:
        settings = json.load(f)
    pyVersionString = sys.version[0]+sys.version[2]
    pythonApiPath = os.path.join(settings['mycropychainPath'], f'pythonAPI\python{pyVersionString}_x64')
    abaqusPythonLibPath = os.path.join(settings['mycropychainPath'], 'abaqus_interface_0_89')

    sys.path.append(pythonApiPath)
    # import API - MyCrOChain GUI with activiated TCP-Connector needed
    try:
        import mycropychain as pychain
    except ModuleNotFoundError:
        log.error('Could not find package "mycropychain". Please check the path to mycropychain in the settings?')
    else:
        if len(pychain.__dict__) < 10:
            # len(pychain.__dict__) was 8 on failure and 17 on success
            log.error('Could not connect to mycropychain GUI. Did you start the GUI and activated "TCP Conn."?')

        # set general path information
        global myCrOSettings
        myCrOSettings = pychain.utility.MyCrOSettings()
        myCrOSettings.abaqusPythonLibPath = abaqusPythonLibPath


def writeSettingsExample():
    """writes an example for settings"""
    from tankoh2 import log
    outFileName = 'settings_example.json'
    log.info(f'write file {outFileName}')
    with open('settings_example.json', 'w') as f:
        json.dump({'comment': "Please rename this example file to 'settings.json' and include the required settings. "
                              "For paths, please use '\\' or '/'",
                   'mycropychainPath': ''},
                  f, indent=2)


if __name__ == '__main__':
    writeSettingsExample()
