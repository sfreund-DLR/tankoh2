import numpy as np
import pandas as pd
import os
from matplotlib import pylab as plt
from itertools import zip_longest


def plotDataFrame(show, filename, dataframe, ax=None, vlines=None, vlineColors=[], title=None,
                  yLabel=None, xLabel=None, plotKwArgs = None):
    """plots puck properties

    :param show: show the plot created
    :param filename: save the plot to filename
    :param dataframe: dataframe with layers as columns and elementIds as index
    :param ax: matplotlib axes object
    :param vlines: x-coordinates with a vertical line to draw
    """
    if ax is None:
        fig = plt.figure(figsize=(15,9))
        useAx = fig.gca()
    else:
        useAx = ax
    if plotKwArgs is None:
        plotKwArgs = {}
    useLegend = plotKwArgs.get('legend', True)
    if 'legend' in plotKwArgs:
        plotKwArgs.pop('legend')
    if 'legendKwargs' in plotKwArgs:
        legendKwargs = plotKwArgs['legendKwargs']
        plotKwArgs.pop('legendKwargs')
    else:
        legendKwargs = {'bbox_to_anchor':(1.05, 1), 'loc':'upper left'} if ax is None else {'loc': 'best'}
    dataframe.plot(ax=useAx, legend=False, **plotKwArgs)
    if useLegend:
        useAx.legend(**legendKwargs)
    useAx.set(xlabel='' if xLabel is None else xLabel,
           ylabel='' if yLabel is None else yLabel,
           title='' if title is None else title)

    if vlines is not None:
        addVerticalLines(useAx, vlines, vlineColors)

    if ax is None:
        plt.subplots_adjust(right=0.75, left=0.10)
        saveShowClose(filename, show, fig)


def plotContour(show, filename, x, r, ax = None, plotContourCoordinates = True,
                vlines=None, vlineColors=[],
                **mplKwargs):
    """Plots the contour given by x and r coordinates

    :param show: Flag if the plot shall be shown
    :param filename: filename if the plot shall be saved
    :param x: vector with x-coordinates
    :param r: vector with r-coordinates
    :param title: plot title
    :param ax: matplotlib axes instance. If given, this instance will be used but only x by r plots are
        generated. If not given, a axes will be created
    :param plotContourCoordinates: flag if x and r should be plotted over the contour coordintes
        (like stress, strain, puck values)
    :param vlines: indices of vertical lines to plot
    :param vlineColors: colors of vertical lines to plot
    :param mplKwargs: arguments to matplotlib plots
        (see https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.plot.html)
    """
    if ax:
        plotContourCoordinates = False
    else:
        plotCount = 2 if plotContourCoordinates else 1
        fig, axs = plt.subplots(1, plotCount, figsize=(17, 5))
    if plotContourCoordinates:
        df = pd.DataFrame(np.array([x,r]).T, columns=['x','r'])
        plotDataFrame(show, None, df, ax=axs[0], yLabel='x,r', xLabel='Contour index',
                      vlines=vlines, vlineColors=vlineColors,
                      plotKwArgs= mplKwargs)
    useAx = axs[-1] if ax is None else ax
    df = pd.DataFrame(np.array([r]).T, index=pd.Index(x))
    mplKwargs = mplKwargs.copy()
    mplKwargs.update([('legend', False)])
    plotDataFrame(show, None, df, ax=useAx, yLabel='r', xLabel='x', plotKwArgs= mplKwargs)
    useAx.set_aspect('equal', adjustable='box')

    plt.axis('scaled')

    if ax is None:
        saveShowClose(filename, show, fig)


def addVerticalLines(ax, vlines, vlineColors=[]):
    """adds vertical lines to an existing plot.

    :param ax: matplotlib axes instance
    :param vlines: x-coordinates of vertical lines
    :param vlineColors: color of vertical lines
    """
    ymin, ymax = ax.get_ylim()
    for vline, color in zip_longest(vlines, vlineColors, fillvalue='black'):
        ax.plot([vline, vline], (ymin, ymax), color=color, linestyle='dashed')


def saveShowClose(filename = '', show=False, fig=None, verbosePlot = False):
    """saves and shows the actual plot and closes it afterwards
    :param filename: filename to save the plot. Not saved if not given
    :param show: shows the plot
    :param fig: figure object to be closed
    :param verbosePlot: also save as svg
    """
    if filename:
        plt.savefig(filename)
        if verbosePlot:
            os.makedirs(os.path.join(os.path.split(filename)[0], 'plots'), exist_ok=True)
            filePath, fileNameOnly = os.path.split(filename)
            plt.savefig(os.path.join(filePath, 'plots', os.path.splitext(fileNameOnly)[0] + '.svg'))
    if show:
        plt.show()
    if fig is not None:
        plt.close(fig)