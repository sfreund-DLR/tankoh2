.. SPDX-FileCopyrightText: 2022 German Aerospace Center (DLR)
..
.. SPDX-License-Identifier: MIT

tankoh2 documentation
=====================


.. only:: html

    :Release: |version|
    :Date: |today|

.. documentation master file, created by
   sphinx-quickstart on Wed Apr 20 14:51:03 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

-----
Scope
-----
TODO

-----
Usage
-----

::

   | usage: tankoh2 [--windingOrMetal WINDINGORMETAL] [--tankname name]
   |                [--nodeNumber number] [--verbose] [--help] [--maxLayers layers]
   |                [--relRadiusHoopLayerEnd RELRADIUSHOOPLAYEREND]
   |                [--domeType DOMETYPE] [--domeContour x,r]
   |                [--polarOpeningRadius r_po] [--dcly d_cyl] [--lcyl l_cyl]
   |                [--lcylByR LCYLBYR] [--domeLengthByR l/r_cyl]
   |                [--safetyFactor S] [--valveReleaseFactor f_pv]
   |                [--pressure p_op] [--minPressure p_op_min]
   |                [--burstPressure p_b] [--useHydrostaticPressure]
   |                [--tankLocation loc] [--materialName name] [--failureMode mode]
   |                [--hoopLayerThickness thk] [--helixLayerThickenss thk]
   |                [--rovingWidth witdh] [--numberOfRovings #] [--tex TEX]
   |                [--fibreDensity FIBREDENSITY] [--pressure min p_min]
   |                [--cycles CYCLES] [--heatUpCycles HEATUPCYCLES]
   |                [--simulatedLives SIMULATEDLIVES] [--Kt Kt]
   |
   | Design and optimization of H2 tanks using muChain. Use the following optional
   | arguments to customize the tank design. Any argument not given, will be
   | extended by the ones defined in tankoh2.design.existingdesigns.defaultDesign.
   |
   | General:
   |   --windingOrMetal WINDINGORMETAL
   |                         Switch between winding mode or metal design [winding,
   |                         metal] (default: winding)
   |   --tankname name       Name of the tank (default: tank_name)
   |   --nodeNumber number   node number along the contour (default: 500)
   |   --verbose             More console output (default: False)
   |   --help                show this help message and exit
   |
   | Optimization:
   |   --maxLayers layers    Maximum number of layers to be added (default: 100)
   |   --relRadiusHoopLayerEnd RELRADIUSHOOPLAYEREND
   |                         relative radius (to cyl radius) where hoop layers end
   |                         [-] (default: 0.95)
   |
   | Geometry:
   |   --domeType DOMETYPE   Shape of dome geometry [isotensoid, circle, ellipse,
   |                         custom] (default: isotensoid)
   |   --domeContour (x,r)   Must be given if domeType==custom. X- and R-array
   |                         should be given without whitespaces like
   |                         "[x1,x2],[r1,r2]" in [mm] (default: (None, None))
   |   --polarOpeningRadius r_po
   |                         Polar opening radius [mm] (default: 20)
   |   --dcly d_cyl          Diameter of the cylindrical section [mm] (default:
   |                         400)
   |   --lcyl l_cyl          Length of the cylindrical section [mm] (default: 500)
   |   --lcylByR LCYLBYR     only if lcyl is not given [-] (default: 2.5)
   |   --domeLengthByR l/r_cyl
   |                         Axial length of the dome. Only used for
   |                         domeType==ellipse [mm] (default: 0.5)
   |
   | Design:
   |   --safetyFactor S      Safety factor used in design [-] (default: 2)
   |   --valveReleaseFactor f_pv
   |                         Factor defining additional pressure to account for the
   |                         valve pressure inaccuracies (default: 1.1)
   |   --pressure p_op       Operational pressure [MPa] (default: 5.0)
   |   --minPressure p_op_min
   |                         Minimal operational pressure [MPa] (default: 0.1)
   |   --burstPressure p_b   Burst pressure [MPa] (default: 10.0)
   |   --useHydrostaticPressure
   |                         Flag whether hydrostatic pressure according to CS
   |                         25.963 (d) should be applied (default: False)
   |   --tankLocation loc    Location of the tank according to CS 25.963 (d). Only
   |                         used if useHydrostaticPressure. Options:
   |                         [wing_no_engine, wing_at_engine, fuselage] (default:
   |                         wing_at_engine)
   |
   | Material:
   |   --materialName name   For metal tanks: name of the material defined in
   |                         tankoh2.design.metal.material. For wound tanks: name
   |                         of the .json for a µWind material definiton (e.g. in
   |                         tankoh2/data/CFRP_HyMod.json). If only a name is
   |                         given, the file is assumed to be in tankoh2/data
   |                         (default: CFRP_HyMod)
   |   --failureMode mode    Use pucks failure mode [fibreFailure,
   |                         interFibreFailure] (default: fibreFailure)
   |
   | Fiber roving parameters:
   |   --hoopLayerThickness thk
   |                         Thickness of hoop (circumferential) layers [mm]
   |                         (default: 0.125)
   |   --helixLayerThickenss thk
   |                         Thickness of helical layers [mm] (default: 0.129)
   |   --rovingWidth witdh   Width of one roving [mm] (default: 3.175)
   |   --numberOfRovings #   Number of rovings
   |                         (rovingWidth*numberOfRovings=bandWidth) (default: 4)
   |   --tex TEX             tex number [g/km] (default: 446)
   |   --fibreDensity FIBREDENSITY
   |                         Fibre density [g/cm^3] (default: 1.78)
   |
   | Fatigue parameters:
   |   --pressure min p_min  Minimal operating pressure [MPa] (default: 0.1)
   |   --cycles CYCLES       Number of operational cycles [-] (default: 50000)
   |   --heatUpCycles HEATUPCYCLES
   |                         Number of cycles to amibent T and p [-] (default: 100)
   |   --simulatedLives SIMULATEDLIVES
   |                         Number of simulated lifes (scatter) [-] (default: 5)
   |   --Kt Kt               Stress concentration factor [-] (default: 5.0)







---------
Reference
---------

.. toctree::
   :maxdepth: 2

   winding
   optimization
   bending
   metal
   tankoh2



   

Indices and tables
==================

used bib

.. bibliography::
   :cited:

unused bib

.. bibliography::
   :notcited:



.. raw:: latex

   \listoffigures
   \listoftables

.. only:: html

   * :ref:`genindex`
   * :ref:`modindex`
   * :ref:`search`





