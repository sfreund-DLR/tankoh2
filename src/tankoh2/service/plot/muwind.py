"""plot functions for µWind specific values"""

from matplotlib import pylab as plt
import numpy as np
import os


from tankoh2.service.plot.generic import plotDataFrame, saveShowClose


def plotPuckAndTargetFunc(puck, tfValues, anglesShifts, layerNumber, runDir,
                          verbosePlot, useFibreFailure, show,
                          elemIdxmax, hoopStart, hoopEnd, newDesignIndexes, targetFuncScaling):
    """"""
    puck.columns = ['lay{}_{:04.1f}'.format(i, angle) if i >= layerNumber-10 or i < 2 else '_' for i, (angle, _) in enumerate(anglesShifts[:-1])]
    puck.index = puck.index + 0.5
    puckLabelName = 'max puck fibre failure' if useFibreFailure else 'max puck inter fibre failure'
    useTwoPlots = verbosePlot and tfValues is not None
    fig, axs = plt.subplots(1, 2 if useTwoPlots else 1, figsize=(16 if useTwoPlots else 10, 7))
    if useTwoPlots:
        plotTargetFunc(axs[1], tfValues, anglesShifts, puckLabelName, targetFuncScaling, None, None, False)
        ax = axs[0]
    else:
        ax = axs  # if only one subplot is used, axs is no iterable
    plotDataFrame(False, '', puck, ax,
                  vlines=[hoopStart, hoopEnd, elemIdxmax + 0.5] + newDesignIndexes,
                  vlineColors=['black', 'black', 'red'] + ['green'] * len(newDesignIndexes),
                  yLabel=puckLabelName, xLabel='Contour index',
                  plotKwArgs={'legendKwargs':{'loc':'center left', 'bbox_to_anchor':(1.03, 0.5)}, 'linewidth':1.0})
    ax.lines[0].set_color('maroon')
    ax.get_legend().legendHandles[0].set_color('maroon')
    if layerNumber > 1:
        ax.lines[1].set_color('darkolivegreen')
        ax.get_legend().legendHandles[1].set_color('darkolivegreen')
    for i in range(2,len(puck.columns)-10):
        ax.lines[i].set_color('black')
    fig.tight_layout()
    saveShowClose(os.path.join(runDir, f'puck_{layerNumber}.png') if runDir else '',
                  show=show, fig=fig, verbosePlot=verbosePlot)


def plotTargetFunc(ax, tfValues, anglesShifts, puckLabelName, targetFuncScaling, runDir, layerNumber, show):
    # create target function plot
    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=(8, 7))
    else:
        fig = None
    xLabel = 'angle' if anglesShifts[-1][0] < 89 else 'hoop shift'
    angleOrHoopShift = anglesShifts[-1][0] if anglesShifts[-1][0] < 89 else anglesShifts[-1][1]
    tfX = tfValues[0]
    tfMaxIndexes = tfValues[-1]
    tfValues = tfValues[1:-1]
    weights, scaling = targetFuncScaling
    labelNames = [puckLabelName, f'{puckLabelName[4:]} at last crit location', 'puck sum', 'mass']
    labelNames = [f'{labelName}, weight: {round(weight,4)}, scaleFac: {round(scale,4)}'
                  for labelName, weight, scale in zip(labelNames, weights, scaling)]
    for values, labelName in zip(tfValues, labelNames):
        if np.all(values < 1e-8): 
            continue
        ax.plot(tfX, values, label=labelName)
    if tfValues.shape[0] == 4:  # plot weighted sum
        ax.plot(tfX, tfValues.sum(axis=0), label='target function: weighted sum')

    # plot optimal angle or shift as vertical line
    ax.plot([angleOrHoopShift] * 2, [0, 1.1 * np.max(tfValues.sum(axis=0))],
            linestyle='dashed', color='green', label=f'new design {xLabel}')
    ax.set_ylabel('Target function')
    ax.set_xlabel(xLabel)
    ax2 = ax.twinx()  # plot on secondary axes
    ax2.set_ylabel('Contour index of highest Puck value')
    ax2.scatter(tfX, tfMaxIndexes, label='Contour index of highest Puck value', s=2, color='orange')
    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax2.legend(lines + lines2, labels + labels2, loc='lower center', bbox_to_anchor=(0.5, 1.01))
    if fig:
        fig.tight_layout()
    saveShowClose(os.path.join(runDir, f'tf_{layerNumber}.png') if runDir else '',
                  show=show, fig=fig)


def plotStressEpsPuck(show, filename, S11, S22, S12, epsAxialBot, epsAxialTop, epsCircBot, epsCircTop, puckFF, puckIFF):
    fig, axs = plt.subplots(3, 3, figsize=(18,10))
    axs = iter(axs.T.flatten())
    singleLegend = True

    ax = next(axs)
    ax.set_title('eps axial')
    ax.plot(epsAxialBot, label='epsAxialBot')
    ax.plot(epsAxialTop, label='epsAxialTop')
    if not singleLegend:
        ax.legend()

    ax = next(axs)
    ax.set_title('eps circ')
    ax.plot(epsCircBot, label='epsCircBot')
    ax.plot(epsCircTop, label='epsCircTop')
    if singleLegend:
        ax.legend(loc='upper left', bbox_to_anchor=(.05, -0.2))
    else:
        ax.legend()

    ax = next(axs)
    ax.remove()

    ax = next(axs)
    ax.set_title('S11')
    for layerIndex, stressLayer11 in enumerate(S11.T):
        ax.plot(stressLayer11, label=f'layer {layerIndex}')
    if not singleLegend:
        ax.legend()

    ax = next(axs)
    ax.set_title('S22')
    for layerIndex, stressLayer22 in enumerate(S22.T):
        ax.plot(stressLayer22, label=f'layer {layerIndex}')
    if not singleLegend:
        ax.legend()

    ax = next(axs)
    ax.set_title('S12')
    for layerIndex, stressLayer22 in enumerate(S12.T):
        ax.plot(stressLayer22, label=f'layer {layerIndex}')
    if singleLegend:
        ax.legend(loc='upper left', bbox_to_anchor=(1.1, 0.99))
    else:
        ax.legend()


    ax = next(axs)
    ax.set_title('puck fibre failure')
    puckFF.plot(ax=ax, legend=False)
    if not singleLegend:
        ax.legend()

    ax = next(axs)
    ax.set_title('puck inter fibre failure')
    puckIFF.plot(ax=ax, legend=False)
    if not singleLegend:
        ax.legend()

    ax = next(axs)
    ax.remove()

    if filename:
        plt.savefig(filename)
    if show:
        plt.show()
    plt.close(fig)


def plotThicknesses(show, filename, thicknesses):
    #thicknesses = thicknesses.iloc[::-1,:].reset_index(drop=True)
    fig, axs = plt.subplots(1, 2, figsize=(17, 5))
    plotDataFrame(show, None, thicknesses, ax=axs[0], title='Layer thicknesses', yLabel='thickness [mm]',
                  xLabel='Contour index')
    plotDataFrame(show, None, thicknesses, ax=axs[1], title='Cumulated layer thickness', yLabel='thickness [mm]',
                  xLabel='Contour index', plotKwArgs={'stacked':True})

    if filename:
        plt.savefig(filename)
    if show:
        plt.show()
    plt.close(fig)


