from matplotlib import pylab as plt

from tankoh2.service.plot.generic import plotDataFrame


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
    thicknesses = thicknesses.iloc[::-1,:].reset_index(drop=True)
    fig, axs = plt.subplots(1, 2, figsize=(17, 5))
    plotDataFrame(show, None, thicknesses, axes=axs[0], title='Layer thicknesses', yLabel='thickness [mm]',
                  xLabel='contour coordinate')
    plotDataFrame(show, None, thicknesses, axes=axs[1], title='Cumulated layer thickness', yLabel='thickness [mm]',
                  xLabel='contour coordinate', plotKwArgs={'stacked':True})

    if filename:
        plt.savefig(filename)
    if show:
        plt.show()
    plt.close(fig)


