

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
import sys

from tankoh2 import description, name
from tankoh2.design.existingdesigns import allArgs
from tankoh2.control.control_winding import createDesign as createDesignWinding
from tankoh2.control.control_metal import createDesign as createDesignMetal
from tankoh2.service.exception import Tankoh2Error


parserDesc = f"""{description}.
Use the following optional arguments to customize the tank design. 
Any argument not given, will be extended by the ones defined in 
tankoh2.design.existingdesigns.defaultDesign."""
parser = ArgumentParser(prog = name, description=parserDesc, add_help=False,
                        formatter_class=ArgumentDefaultsHelpFormatter)

grouped=allArgs.groupby('group')

for groupName, argsGroup in grouped:
    parserGroup = parser.add_argument_group(groupName)
    for name, group, metavar, default, dataType, helpStr, action in argsGroup.iloc:
        kwargs = {}
        kwargs.update({'metavar':metavar} if metavar else {})
        kwargs.update({'default':default} if default else {})
        kwargs.update({'type':dataType} if dataType else {})
        kwargs.update({'action':action} if action else {})
        parserGroup.add_argument(f"--{name}", help=helpStr, **kwargs)

options = parser.parse_args()
params = vars(options)
windingOrMetal = params.pop('windingOrMetal').lower()
try:
    if windingOrMetal == 'winding':
        createDesignWinding(**params)
    elif windingOrMetal == 'metal':
        createDesignMetal(**params)
    else:
        raise Tankoh2Error(f'Parameter "windingOrMetal" can only be one of [winding, metal] but got '
                           f'{windingOrMetal}')
except:
    sys.stdout.flush()
    raise

