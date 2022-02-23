from matplotlib import pylab as plt

from tankoh2.service.plot.generic import plotDataFrame


def plotStressEpsPuck(show, filename, S11, S22, S12, epsAxialBot, epsAxialTop, epsCircBot, epsCircTop, puckFF, puckIFF):
    fig, axs = plt.subplots(2, 3, figsize=(18,10))
    axs = iter(axs.T.flatten())

    ax = next(axs)
    ax.set_title('S11')
    for layerIndex, stressLayer11 in enumerate(S11.T):
        ax.plot(stressLayer11, label=f'layer {layerIndex}')
        ax.legend()

    ax = next(axs)
    ax.set_title('S22')
    for layerIndex, stressLayer22 in enumerate(S22.T):
        ax.plot(stressLayer22, label=f'layer {layerIndex}')
        ax.legend()

    ax = next(axs)
    ax.set_title('eps axial')
    ax.plot(epsAxialBot, label='epsAxialBot')
    ax.plot(epsAxialTop, label='epsAxialTop')
    ax.legend()

    ax = next(axs)
    ax.set_title('eps circ')
    ax.plot(epsCircBot, label='epsCircBot')
    ax.plot(epsCircTop, label='epsCircTop')
    ax.legend()

    ax = next(axs)
    ax.set_title('puck fibre failure')
    puckFF.plot(ax=ax)
    ax.legend(loc='lower left')

    ax = next(axs)
    ax.set_title('puck inter fibre failure')
    puckIFF.plot(ax=ax)
    ax.legend(loc='lower left')

    if filename:
        plt.savefig(filename)
    if show:
        plt.show()
    plt.close(fig)


def plotThicknesses(show, filename, thicknesses):
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


