---------------------------------------------
Tank Mass Assessment Using Isotropic Material
---------------------------------------------

Mechanics
---------
see :cite:`Schwaigerer.1983` and :cite:`Winnefeld.2018`

.. math::

    s = \frac{p \cdot d}{\nu (2 K/S-p)} + c_1 + c_2

where

- s: wall thickness
- p: burst pressure
- d: inner diameter
- :math:`\nu`: reduction factor due to welding or bolts
- K: allowable stress
- S: safety factor
- :math:`c_1` - Addition for negative tolerances
- :math:`c_2` - Addition for wear

Safety Factor
-------------
According to :cite:`Schwaigerer.1983`

Classification
**************
- Proportional safety factor
- Linear addtions

Possible Contents
*****************
- Structures with alternating loads
    - S=1.5-2.5
    - Lastspielsicherheit 2-10 (Faktor auf erwartete Lastwechsel)
    - :math:`c_1` - Addition for negative tolerances
    - :math:`c_2` - Addition for wear (:math:`c_2` =1mm, can be omitted for s>30mm)


