"""plots for design of experiments (DOE)"""
import numpy as np
from matplotlib import pyplot as plt


def plotGeometryRange(lowerBoundDict, upperBoundDict, plotDir='', show=False, samples=None):
    """Plot diameter vs volume

    :param lowerBoundDict: dict with lower bounds
    :param upperBoundDict: dict with upper bounds
    :param plotDir: directroy to save plot
    :param show: show plot
    :param samples: samples to be included in plot as scatter
    :return: None
    """
    lb, ub = lowerBoundDict, upperBoundDict
    def volumeFunc(d, lcylByR):
        """volume of a tank with circular domes [m**3]"""
        return 4 / 3 * np.pi * d ** 3 + d * lcylByR * np.pi * d ** 2

    diameters = (lb['dcyl'], ub['dcyl'])
    diameters = np.array(diameters) / 1e3  # convert to m
    lcyls = (lb['lcyl'], ub['lcyl']) if 'lcyl' in lb else (np.array([lb['lcylByR'], ub['lcylByR']]) * diameters / 2)
    if samples is not None:
        samplesR, sampleslcylByR = samples[:2, :]
        samplesR = samplesR / 1e3

    fig = plt.figure(figsize=(15,6))
    axes = [fig.add_subplot(1, 2, 1), fig.add_subplot(1, 2, 2)]
    axes[1].set_yscale("log")
    for ax in axes:
        ax.set_title("Parameter bounds")
        ax.set_xlabel('Diameter [m]')
        ax.set_ylabel('Volume [m^3]')
        color = 'tab:blue'
        for lcyl in lcyls:
            x = np.linspace(*diameters, 11)
            volumes = [volumeFunc(r, lcyl) for r in x]
            ax.plot(x, volumes, color=color, label=f'lcyl={lcyl}')
            color = 'tab:orange'
        ax.legend()
        if samples is not None:
            volumes = volumeFunc(samplesR, sampleslcylByR)
            ax.scatter(samplesR, volumes, label=f'samples')

    if plotDir:
        plt.savefig(plotDir+'/geometryRange.png')
    if show:
        plt.show()