# Optimization Function

There are various variants for the actual layer-based optimization in tankoh2. All tested variants are described here.

Goal of a target function:
- have a good balance between minimizing the last maximum and minimizing puck at all elements

## Min(Max(Puck))
This is the most basic approach: Minimize the maximal puck value in all elements and all layers.

![lay4](sfreund-DLR/tankoh2/doc/images/optimization/minmaxpuck_4.png)
![lay5](sfreund-DLR/tankoh2/doc/images/optimization/minmaxpuck_5.png)
![lay6](sfreund-DLR/tankoh2/doc/images/optimization/minmaxpuck_6.png)
![lay7](sfreund-DLR/tankoh2/doc/images/optimization/minmaxpuck_7.png)


Con: This approach minimizes the whole dome region (or hoop region in hoop case) but does not find the optimium to work on one peak at a time. As seen in the images, this produces a ping-pong like behavior. It minimizes both, but not one peak properly at a time.

In example "conicalTankDesign" (commit bb76384) this method resulted in  layers

## Min(Max(Puck(crit index)))
This approach minimizes the puck value at the very exact peak of the last iteration. 


![lay3](sfreund-DLR/tankoh2/doc/images/optimization/minmaxcritpuck_3.png)
![lay4](sfreund-DLR/tankoh2/doc/images/optimization/minmaxcritpuck_4.png)
![lay5](sfreund-DLR/tankoh2/doc/images/optimization/minmaxcritpuck_5.png)

con: the next peak may be right next to the last one. So a target function that incorporates the total maximum or the neighborhood of the
last critial location might be beneficial

In example "conicalTankDesign" (commit bb76384) this method resulted in  layers


## Weighted Min(Max(Puck)) and Min(Max(Puck(crit index)))
see [issue 60](https://github.com/sfreund-DLR/tankoh2/issues/60)

Due to the problems with both singular methods before, they are combined in a weighted sum in order to incorporate both effects: 
local minimization and a global minimization. Also a mass function was added as side kick ;-)

These Weights are used:
- 1 Min(Max(Puck))
- 0.5 Min(Max(Puck(crit index)))
- 0.1 next Layer Mass

It improves the above behavior

In example "conicalTankDesign" (commit bb76384) this method resulted in 14 layers

