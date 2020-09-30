"""utility methods"""

import json
import shutil

from tankoh2.exception import Tankoh2Error

def copyAsJson(filename, typename):
    """copy a file creating a .json file

    Files in mycrowind have specific file types although they are json files.
    This method creates an additional json file besides the original file."""
    if filename.endswith(f'.{typename}'):
        # also save as json for syntax highlighting
        shutil.copy2(filename, filename + '.json')


def updateName(jsonFilename, name, objsName):
    """updates the name of an item in a json file.

    The given json file will be updated in place

    :param jsonFilename: name of json file
    :param name: name that should be updated
    :param objsName: name of the object which name tag should be updated
    """
    with open(jsonFilename) as jsonFile:
        data = json.load(jsonFile)
    item = data
    for objName in objsName:
        try:
            item = item[objName]
        except KeyError:
            raise Tankoh2Error(f'Tree of "{objsName}" not included in "{jsonFilename}"')
    item["name"] = name
    with open(jsonFilename, "w") as jsonFile:
        json.dump(data, jsonFile, indent=4)

