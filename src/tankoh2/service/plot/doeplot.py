"""plots for design of experiments (DOE)"""
import numpy as np
from matplotlib import pyplot as plt


def plotGeometryRange(lowerBoundDict, upperBoundDict, plotDir='', show=False, samples=None, addBox=False):
    """Plot diameter vs volume

    :param lowerBoundDict: dict with lower bounds
    :param upperBoundDict: dict with upper bounds
    :param plotDir: directroy to save plot
    :param show: show plot
    :param samples: samples to be included in plot as scatter
    :return: None
    """
    lb, ub = lowerBoundDict, upperBoundDict
    def volumeFunc(d, lcyl):
        """volume of a tank with circular domes [m**3]

        Used as rough estimation!"""
        return 4 / 3 * np.pi * (d/2) ** 3 + lcyl * np.pi * (d/2) ** 2

    diameters = (lb['dcyl'], ub['dcyl'])
    diameters = np.array(diameters) / 1e3  # convert to m
    lcyls = np.array([lb['lcyl'], ub['lcyl']]) / 1e3  # convert to m


    fig = plt.figure(figsize=(15,6))
    axes = [fig.add_subplot(1, 2, 1), fig.add_subplot(1, 2, 2)]
    axes[1].set_yscale("log")
    for ax in axes:
        ax.set_title("Parameter bounds")
        ax.set_xlabel('Diameter [m]')
        ax.set_ylabel('Volume [m^3]')
        color = 'tab:blue'
        for lcyl in lcyls:
            x = np.linspace(*diameters, 51)
            volumes1 = [volumeFunc(d, lcyl) for d in x]
            ax.plot(x, volumes1, color=color, label=f'lcyl={lcyl}')
            color = 'tab:orange'
        ax.legend()
        if samples is not None:
            samplesR, samplesLcyl = samples[:2, :]
            samplesR = samplesR / 1e3
            samplesLcyl = samplesLcyl / 1e3

            volumes2 = volumeFunc(samplesR, samplesLcyl)
            ax.scatter(samplesR, volumes2, label=f'samples')
        if addBox:
            ax.add_patch(plt.Rectangle((1.2, 3), 1.2, 4, ec="red", fc="none"))
            ax.add_patch(plt.Rectangle((2, 20), 1.6, 10, ec="green", fc="none"))

    if plotDir:
        plt.savefig(plotDir+'/geometryRange.png')
    if show:
        plt.show()
