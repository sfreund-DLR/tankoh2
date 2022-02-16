"""Characterize metal material properties at cryogenic temperatures"""

from collections import OrderedDict

from tankoh2.service.exception import Tankoh2Error

def getMaterial(materialName):
    """Returns the material definition as dict.

    It uses the materials defined in this module
    :param materialName: name of material. Must be an attribute of this module
    :return: dict with material properties
    """
    import tankoh2.design.metal.material as materials
    try:
        material = getattr(materials, materialName)
    except AttributeError:
        raise Tankoh2Error(f'The given material "{materialName}" is not defined in '
                           f'tankoh2.design.metal.material')
    return material


# from Winnefeld: Modelling and Designing Cryogenic Hydrogen Tanks for Future Aircraft Applications
alu2219 = OrderedDict([  # at T=20K
    ('roh', 2825),  # kg/m**3
    ('sigma_t', 172.4),  # MPa ultimate design conditions
    ('E', 72400), #MPa Alu2219T87 from Gomez: Liquid hydrogen fuel tanks for commercial aviation: Structural sizing and stress analysis
    ('weldEfficiency', 1),  # [-]
    ('c1', 0.),  # tbd
    ('c2', 0.),  # tbd
])

defaultMetalMaterial = alu2219.copy()


# from https://www.efunda.com/materials/alloys/aluminum/show_aluminum.cfm?ID=AA_6061
alu6061T6 = OrderedDict([  # at T=20K
    ('roh', 2700),  # kg/m**3
    ('sigma_t', 310),  # MPa ultimate design conditions
    ('sigma_t_yield', 275),  # MPa ultimate design conditions
    ('E', 75000),
    ('weldEfficiency', 1),  # [-]
    ('c1', 0.),  # tbd
    ('c2', 0.),  # tbd
])



