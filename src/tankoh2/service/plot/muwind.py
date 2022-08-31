"""plot functions for µWind specific values"""

from matplotlib import pylab as plt
import numpy as np
import os


from tankoh2.service.plot.generic import plotDataFrame, saveShowClose


def plotPuckAndTargetFunc(puck, tfValues, anglesShifts, angleOrHoopShift, layerNumber, runDir,
                          verbosePlot, useFibreFailure, show,
                          elemIdxmax, hoopStart, hoopEnd, newDesignIndexes):
    """"""
    puck.columns = ['lay{}_{:04.1f}'.format(i, angle) for i, (angle, _) in enumerate(anglesShifts[:-1])]
    puck.index = puck.index + 0.5
    yLabel = 'puck fibre failure' if useFibreFailure else 'puck inter fibre failure'
    fig, axs = plt.subplots(1, 2 if verbosePlot else 1, figsize=(15 / (1 if verbosePlot else 2), 7))
    if verbosePlot:
        # create target function plot
        xLabel = 'angle' if anglesShifts[-1][0] < 90 else 'hoop shift'
        ax = axs[1]
        ax.plot(tfValues[0], tfValues[1], label=yLabel)
        # plot optimal angle or shift as vertical line
        ax.plot([angleOrHoopShift] * 2, [0, 1.1 * np.max(tfValues[1])], linestyle='dashed', color='green')
        ax.set_ylabel(yLabel)
        ax.set_xlabel(xLabel)
        ax2 = ax.twinx()  # plot on secondary axes
        ax2.set_ylabel('Contour index of highest Puck value')
        ax2.scatter(tfValues[0], tfValues[2], label='Contour index of highest Puck value', s=1,
                    color='orange')
        lines, labels = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax2.legend(lines[:1] + lines2, labels[:1] + labels2)
        ax = axs[0]
    else:
        ax = axs  # if only one subplot is used, axs is no iterable
    plotDataFrame(False, '', puck, ax,
                  vlines=[elemIdxmax + 0.5, hoopStart, hoopEnd] + newDesignIndexes,
                  vlineColors=['red', 'black', 'black'] + ['green'] * len(newDesignIndexes),
                  yLabel=yLabel, xLabel='Contour index')
    saveShowClose(os.path.join(runDir, f'puck_{layerNumber}.png'), show=show, fig=fig)


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


