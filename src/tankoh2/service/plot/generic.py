import numpy as np
import pandas as pd
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
    dataframe.plot(ax=useAx, legend=False, **plotKwArgs)
    if useLegend:
        legendKwargs = {'bbox_to_anchor':(1.05, 1), 'loc':'upper left'} if ax is None else {'loc': 'best'}
        useAx.legend(**legendKwargs)
    useAx.set(xlabel='' if xLabel is None else xLabel,
           ylabel='' if yLabel is None else yLabel,
           title='' if title is None else title)

    if vlines is not None:
        ymin, ymax = dataframe.min().min(), dataframe.max().max()
        ymax += 0.1*(ymax-ymin)

        for vline, color in zip_longest(vlines, vlineColors, fillvalue='black'):
            useAx.plot([vline, vline], (ymin, ymax), color=color, linestyle='dashed')
        #plt.vlines(vlines, ymin, ymax + , colors=vlineColors, linestyles='dashed')

    if ax is None:
        plt.subplots_adjust(right=0.75, left=0.10)
        saveShowClose(filename, show, fig)


def plotContour(show, filename, x, r, title, parameter, ax = None, plotContourCoordinates = True, **mplKwargs):
    """Plots the contour given by x and r coordinates

    :param show: Flag if the plot shall be shown
    :param filename: filename if the plot shall be saved
    :param x: vector with x-coordinates
    :param r: vector with r-coordinates
    :param ax: matplotlib axes instance. If given, this instance will be used but only x by r plots are
        generated. If not given, a axes will be created
    :param plotContourCoordinates: flag if x and r should be plotted over the contour coordintes
        (like stress, strain, puck values)
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
        plotDataFrame(show, None, df, ax=axs[0], title=title, yLabel='x,r', xLabel='Contour index',
                      plotKwArgs= mplKwargs)
    useAx = axs[-1] if ax is None else ax
    df = pd.DataFrame(np.array([r]).T, columns=[parameter], index=pd.Index(x))
    mplKwargs = mplKwargs.copy()
    mplKwargs.update([('legend', False)])
    plotDataFrame(show, None, df, ax=useAx, title=title, yLabel='r', xLabel='x', plotKwArgs= mplKwargs)
    useAx.set_aspect('equal', adjustable='box')

    plt.axis('scaled')

    if ax is None:
        saveShowClose(filename, show, fig)


def saveShowClose(filename = '', show=False, fig=None):
    """saves and shows the actual plot and closes it afterwards
    :param filename: filename to save the plot. Not saved if not given
    :param show: shows the plot
    :param fig: figure object to be closed
    """
    if filename:
        plt.savefig(filename)
    if show:
        plt.show()
    if fig is not None:
        plt.close(fig)