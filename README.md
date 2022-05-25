# tankoh2
Design and optimization of H2 tanks. 

For metal structures, tankoh2 is a standalone pre-design tool. 
For CFRP structures, a detailed winding optimization is performed. 
The winding simulation is carried out by [µChain](https://www.mefex.de/software/)

## Features 

- Material/layup read/write
- Create dome and liner from cylindrical length and radius or using a dome contour
- Setup of a vessel model
- Optimization of each layer with respect to minimizing puck fibre failure
- Create and run DOE with support of DLR tools (delismm, fa_pyutils)
- Routines for the improvement of the FEM model generatred by Abaqus CAE
- Planned features:
  - Global optimization of 
    - All angles of helical layers
    - All hoop layer shifts
    - Target: mass minimization
    - Constraint: puck fibre failure
  - Improved DOE: Liner and fitting adjustment w.r.t. vessel geometry
  - Abaqus: introduction of the abaqus solver at the end of the optimization process

## Installation

### Requirements

Python Packages:
- Numpy
- Scipy
- Pandas

Requirements from [µChain](https://www.mefex.de/software/):
- Python 3.8 (x64) + Numpy 1.20.0

### Installation from source
Get tankoh2 from 

```
https://github.com/sfreund-DLR/tankoh2.git
```

For winding: In the folder `/src/tankoh2/`, create a file `settings.json`
and include the path to [µChains](https://www.mefex.de/software/) python API. 
In most recent µChain-Versions, the python API is located in `pythonAPI/3_8` or
`pythonAPI/3_6` in the µChain installation directory.

```
{
  "mycropychainPath": "<path_to_muChain>"
}
```

### Test the installation

```
cd <path_to_tankoh2>/src
python -m tankoh2 --help
```

You can perform a standalone test for metal tanks

```
cd <path_to_tankoh2>/src
python -m tankoh2 --materialName alu2219 --windingOrMetal metal --domeType circle
```

## Usage
A full list the available parameters is created with 

```
cd <path_to_tankoh2>/src
python -m tankoh2 --help
```

### Winding

For winding mode, a valid µWind license is required!
Run the following, to start a winding optimization.

```
cd <path_to_tankoh2>/src
python -m tankoh2
```

### Metal

A design run for metal structures can be run by

```
cd <path_to_tankoh2>/src
python -m tankoh2 --materialName alu2219 --windingOrMetal metal --domeType circle
```


## Contributing to _tankoh2_

We welcome your contribution!

If you want to provide a code change, please:

* Create a fork of the project.
* Develop the feature/patch
* Provide a merge request.

> If it is the first time that you contribute, please add yourself to the list
> of contributors below.


## Citing

Please cite name and web address of the project

## License

see [license](LICENSE.md)

## Change Log

see [changelog](changelog.md)

## Authors

[Sebastian Freund](mailto:sebastian.freund@dlr.de)
[Caroline Lüders](mailto:caroline.lueders@dlr.de)




