"""utility functions"""

import math
import re
import functools
import io
import itertools
import numpy as np
import time
import os
from os.path import exists, join, abspath
from datetime import datetime
import getpass
import sys
import glob

from tankoh2 import programDir, log


def importFreeCad():
    """searches for the freecad folder and puts it into the system path"""
    stdInstallPath = f'C:\\Users\\{getpass.getuser()}\\AppData\\Local\\Programs\\'
    searchPaths = glob.glob(stdInstallPath+'/FreeCAD*')[::-1]

    for searchPath in searchPaths:
        if exists(join(searchPath, 'bin')) and exists(join(searchPath, 'bin', 'FreeCAD.exe')):
            freecadLibPaths = [join(searchPath, 'lib'), join(searchPath, 'bin')]
            log.debug(f'Add freecad to path: {freecadLibPaths}')
            sys.path.extend(freecadLibPaths)
            os.environ['PATH'] = ';'.join(freecadLibPaths + [os.environ['PATH']])
            break
    else:
        log.info(f'Could not find FreeCAD (required if conical dome shapes used). '
                 f'Searched in this folder: {stdInstallPath}')


def getTimeString(useMilliSeconds=False):
    """returns a time string of the format: yyyymmdd_hhmmss"""
    dt = datetime.now()
    return dt.strftime("%Y%m%d_%H%M%S") + ('_{}'.format(dt.microsecond) if useMilliSeconds else '')


def makeAllDirs(directory):
    absPath = abspath(directory)
    for i in range(0,absPath.count(os.sep))[::-1]:
        #Split path into subpaths beginning from the top of the drive
        subPath = absPath.rsplit(os.sep,i)[0]
        if not exists(subPath):
            os.makedirs(subPath)


def getRunDir(runDirExtension='', useMilliSeconds=False):
    """Creates a folder that will be used as directory for the actual run.

    The created folder has this name::

        tmp/tank_<timestamp><runDirExtension>

    :param runDirExtension: optional string appended to the folder name. Defaults to ''
    :param useMilliSeconds: include milliseconds to the run dir name or not
    :returns: absolute path to the new folder

    Example::

        >> getRunDir('_bar', False)
        C:/tankoh2/tmp/tank_20170206_152323_bar

    """
    if runDirExtension and runDirExtension[0] != '_':
        runDirExtension = '_' + runDirExtension
    while True:
        runDir = join(programDir, 'tmp', 'tank_' + getTimeString(useMilliSeconds)) + runDirExtension
        if exists(runDir):
            log.warning('runDir already exists. Wait 1s and retry with new timestring.')
            time.sleep(1)
        else:
            makeAllDirs(runDir)
            break

    return runDir


def createRstTable(inputMatrix, numberOfHeaderLines=1):
    """Returns a string containing a well formatted table that can be used in rst-documentation.

    :param inputMatrix: A sequence of sequences of items, one sequence per row.
    :param numberOfHeaderLines: number of lines that are used as header. the header is printed bold.
    :return: string containing well formatted rst table

    Example::

        >>> from fa_pyutils.service.stringutils import createRstTable
        >>> a=[]
        >>> a.append(['','major','minor','revision'])
        >>> a.append(['Example','13','2','0'])
        >>> a.append([  'Explanation','New feature, incompatibe to prev versions','New feature, compatible to prev versions','Patch/Bugfix'])
        >>> print(createRstTable(a))
        +-------------+-------------------------------------------+------------------------------------------+--------------+
        |             | major                                     | minor                                    | revision     |
        +=============+===========================================+==========================================+==============+
        | Example     | 13                                        | 2                                        | 0            |
        +-------------+-------------------------------------------+------------------------------------------+--------------+
        | Explanation | New feature, incompatibe to prev versions | New feature, compatible to prev versions | Patch/Bugfix |
        +-------------+-------------------------------------------+------------------------------------------+--------------+
    """
    tableString = indent(inputMatrix, separateRows=True, hasHeader=True, headerChar="-", prefix="| ", postfix=" |")
    tableLines = tableString.splitlines()
    # get second row to extract the position of '|'
    pipePositions = []
    line = tableLines[1]
    for index, character in enumerate(line):
        if character == "|":
            pipePositions.append(index)

    # alter tableLines containing text
    for halfLineNumber, line in enumerate(tableLines[::2]):
        for index in pipePositions:
            line = line[:index] + "+" + line[index + 1 :]
        tableLines[halfLineNumber * 2] = line

    tableLines[2 * numberOfHeaderLines] = tableLines[2 * numberOfHeaderLines].replace("-", "=")
    return "\n".join(tableLines)

def indent(rows, hasHeader=False, headerChar='-', delim=' | ', justify='left',
           separateRows=False, prefix='', postfix='', wrapfunc=lambda x: wrap_npstr(x)):  # lambda x:x):
    """
    Indents a table by column.

    :param rows: A sequence of sequences of items, one sequence per row.

    :param hasHeader: True if the first row consists of the columns' names.

    :param headerChar: Character to be used for the row separator line
      (if hasHeader==True or separateRows==True).

    :param delim: The column delimiter.

    :param justify: Determines how are data justified in their column.
      Valid values are 'left','right' and 'center'.

    :param separateRows: True if rows are to be separated by astr
     line of 'headerChar's.

    :param prefix: A string prepended to each printed row.

    :param postfix: A string appended to each printed row.

    :param wrapfunc: A function f(text) for wrapping text; each element in
      the table is first wrapped by this function.

    remark:

    :Author: George Sakkis
    :Source: http://code.activestate.com/recipes/267662/
    :License: MIT (http://code.activestate.com/help/terms/)
    """

    # closure for breaking logical rows to physical, using wrapfunc
    def rowWrapper(row):
        newRows = [str(wrapfunc(item)).split('\n') for item in row]
        return [[substr or '' for substr in item] for item in map(lambda *x: x, *newRows)]

    # break each logical row into one or more physical ones
    logicalRows = [rowWrapper(row) for row in rows]
    # columns of physical rows
    columns = list(itertools.zip_longest(*[row[0] for row in logicalRows]))
    # get the maximum of each column by the string length of its items
    maxWidths = [max([len(str(item)) for item in column]) for column in columns]
    rowSeparator = headerChar * (len(prefix) + len(postfix) + sum(maxWidths) + \
                                 len(delim) * (len(maxWidths) - 1))
    # select the appropriate justify method
    justify = {'center': str.center, 'right': str.rjust, 'left': str.ljust}[justify.lower()]
    output = io.StringIO()
    if separateRows:
        print(rowSeparator, file=output)
    for physicalRows in logicalRows:
        for row in physicalRows:
            outRow = prefix + delim.join([justify(str(item), width) for (item, width) in zip(row, maxWidths)]) + postfix
            print(outRow, file=output)
        if separateRows or hasHeader: print(rowSeparator, file=output); hasHeader = False
    return output.getvalue()


def wrap_npstr(text):
    """A function to distinguisch between np-arrays and others.
    np-arrays are returned as string without newline symbols that are usually returned by np.ndarray.__str__()
    """
    if isinstance(text, np.ndarray):
        text = np.array2string(text, separator=',').replace('\n', '')
    return text


def wrap_onspace(text, width):
    """A word-wrap function that preserves existing line breaks
    and most spaces in the text. Expects that existing line
    breaks are posix newlines (\\n).
    """
    return functools.reduce(lambda line, word, width=width: '%s%s%s' %
                                                            (line,
                                                             ' \n'[(len(line[line.rfind('\n') + 1:])
                                                                    + len(word.split('\n', 1)[0]
                                                                          ) >= width)],
                                                             word),
                            text.split(' ')
                            )


def wrap_onspace_strict(text, width):
    """Similar to wrap_onspace, but enforces the width constraint:
    words longer than width are split."""
    wordRegex = re.compile(r'\S{' + str(width) + r',}')
    return wrap_onspace(wordRegex.sub(lambda m: wrap_always(m.group(), width), text), width)


def wrap_always(text, width):
    """A simple word-wrap function that wraps text on exactly width characters.
    It doesn't split the text in words."""
    return '\n'.join([text[width * i:width * (i + 1)] \
                      for i in range(int(math.ceil(1. * len(text) / width)))])


if __name__ == '__main__':
    input = [
        ['Configuration', 'Puck Weight', 'Bending weight', 'Hoop shift opt', 'Number of layers', 'Remark/Addition'],
        # ['Test Conf', 1,0,71],
        # ['Test Conf', 0,1,70],
        # ['Test Conf', 1,0.5,70],
        # ['Test Conf', 1, 0.25, 66, 'Use hoop shift opt'],
        # ['Problem Conf', 1,0,31],
        # ['Problem Conf', 0,1,33],
        # ['Problem Conf', 1,0.5,31],
        ['Test Conf', 1, 0, 'no hoop shift opt', 65, ''],
        ['Test Conf', 0, 1, 'no hoop shift opt', 88, ''],
        ['Test Conf', 1, 0.4, 'no hoop shift opt', 67, ''],
        ['Test Conf', 1, 0, 'hoop shift opt', 65, ''],
        ['Test Conf', 0, 1, 'hoop shift opt', 88, ''],
        ['Test Conf', 1, 0.4, 'hoop shift opt', 67, ''],
        ['Problem Conf', 1, 0, 'no hoop shift opt', 30, ''],
        ['Problem Conf', 0, 1, 'no hoop shift opt', 100, 'reached max layers'],
        ['Problem Conf', 1, 0.4, 'no hoop shift opt', 100, 'reached max layers'],

    ]
    print(createRstTable(input))

