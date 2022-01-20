# tankoh2
Design and optimization of H2 tanks. 
For metal structures, tankoh2 is standalone, for CFRP structures, 
the winding simulation is carried out by [µChain](https://www.mefex.de/software/)

## Features 

- Material/layup read/write
- Create dome and liner from zylindrical length and radius or using a dome contour
- Setup of a vessel model
- Optimization of each layer with respect to minimizing puck fibre failure
- Create and run DOE with support of DLR tools (delismm, fa_pyutils)
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

Requirements from [muChain](https://www.mefex.de/software/):
- Python 3.6 (x64) + Numpy 1.16.2
- Python 3.8 (x64) + Numpy 1.19.1


### Installation from source
Get tankoh2 from 

```
https://github.com/sfreund-DLR/tankoh2.git
```
In the folder `/src/tankoh2/`, create a the file `settings.json`
and include the path to [muChain](https://www.mefex.de/software/) like this:

```
{
  "mycropychainPath": "<path_to_muChain>"
}
```

### Test the installation
In python execute: 

```
import tankoh2
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




