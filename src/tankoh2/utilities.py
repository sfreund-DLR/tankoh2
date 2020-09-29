"""utility methods"""

import json

from tankoh2.exception import Tankoh2Error

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

