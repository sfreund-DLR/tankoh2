from matplotlib import pylab as plt


def plotDataFrame(show, filename, dataframe, axes=None, vlines=None, vlineColors=None, title=None,
                  yLabel=None, xLabel='Contour coordinate', plotKwArgs = None):
    """plots puck properties

    :param show: show the plot created
    :param filename: save the plot to filename
    :param dataframe: dataframe with layers as columns and elementIds as index
    :param axes: matplotlib axes object
    :param vlines: x-coordinates with a vertical line to draw
    """
    if axes is None:
        fig = plt.figure(figsize=(15,9))
        ax = fig.gca()
    else:
        ax = axes
    if plotKwArgs is None:
        plotKwArgs = {}
    dataframe.plot(ax=ax, **plotKwArgs)
    legendKwargs = {'bbox_to_anchor':(1.05, 1), 'loc':'upper left'} if axes is None else {'loc':'best'}
    ax.legend(**legendKwargs)
    ax.set(xlabel=xLabel,
           ylabel='' if yLabel is None else yLabel,
           title='' if title is None else title)

    if vlines is not None:
        if vlineColors is None:
            vlineColors = 'black'
        ymin, ymax = dataframe.min().min(), dataframe.max().max()
        plt.vlines(vlines, ymin, ymax + 0.1*(ymax-ymin), colors=vlineColors, linestyles='dashed')

    if axes is None:
        plt.subplots_adjust(right=0.75, left=0.10)
        if filename:
            plt.savefig(filename)
        if show:
            plt.show()
        plt.close(fig)