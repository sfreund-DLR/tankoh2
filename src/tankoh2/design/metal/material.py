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
alu2219 = OrderedDict([ # T851
    # at T=20K
    ('roh', 2825),  # kg/m**3
    ('sigma_t', 420),  # MPa
    ('sigma_t_yield', 324),  # MPa
    ('E', 72395), #MPa
    ('weldEfficiency', 1),  # [-]
    ('c1', 0.),  # tbd
    ('c2', 0.),  # tbd
    ('SN_parameters', [20.68, -9.84, 0.63, 0]), # see formula in tankoh2.design.metal.mechanics.getCyclesToFailure
    ('Kt_used', 2.), # Kt factor used to create SN_parameters
])

defaultMetalMaterial = alu2219.copy()
alu2219Brewer = alu2219.copy()
alu2219Brewer.update([
    ('sigma_t', 172.4),  # MPa ultimate design conditions including fatigue
    ('sigma_t_yield', 1),  # MPa - not mentioned by brewer
    ('E', 72400), #MPa Alu2219T87 from Gomez: Liquid hydrogen fuel tanks for commercial aviation: Structural sizing and stress analysis
])

# from https://www.efunda.com/materials/alloys/aluminum/show_aluminum.cfm?ID=AA_6061
alu6061T6 = OrderedDict([  # at T=20K
    ('roh', 2700),  # kg/m**3
    ('sigma_t', 310),  # MPa ultimate design conditions
    ('sigma_t_yield', 275),  # MPa ultimate design conditions
    ('E', 75000),
    ('weldEfficiency', 1),  # [-]
    ('c1', 0.),  # tbd
    ('c2', 0.),  # tbd
    ('SN_parameters', [20.68, -9.84, 0.63, 0]), # see formula in tankoh2.design.metal.mechanics.getCyclesToFailure
    ('Kt_used', 1.), # Kt factor used to create SN_parameters
    # ('', ''),
])



