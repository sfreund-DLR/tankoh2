# Optimization Function

There are various variants for the actual layer-based optimization in tankoh2. All tested variants are described here.

Goal of a target function:
- have a good balance between minimizing the last maximum and minimizing puck at all elements

## Min(Max(Puck))
This is the most basic approach: Minimize the maximal puck value in all elements and all layers.




Con: This approach minimizes the whole dome region (or hoop region in hoop case) but does not find the optimium to work on one peak at a time. 

## Min(Max(Puck(crit index)))


This approach minimizes the puck value at the very exact peak of the last iteration. 

todo: images

con: the next peak may be right next to the last one. So a target function that incorporates the total maximum or the neighborhood of the 
last critial location might be beneficial



## Weighted Min(Max(Puck)) and Min(Max(Puck(crit index)))
see [issue 60](https://github.com/sfreund-DLR/tankoh2/issues/60)

Due to the problems with the singular methods before, they are combined in a weighted sum in order to incorporate both effects: 
local minimization and a global minimization. Also a mass function was added as side kick ;-)

These Weights are used:
- 1 Min(Max(Puck))
- 0.5 Min(Max(Puck(crit index)))
- 0.1 next Layer Mass



