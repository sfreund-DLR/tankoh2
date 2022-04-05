"""Create plots for vph project - will be removed/reintegrated elsewhere in the future"""


import matplotlib
import matplotlib.pyplot as plt
import pickle
import numpy as np
import pandas as pd
from reliability.PoF import stress_strain_life_parameters_from_data

import tankoh2.design.existingdesigns as allParamSets
from tankoh2.design.metal.material import alu6061T6
from tankoh2.design.metal.mechanics import getMaxWallThickness2


def massPlot():
    horizontal = True
    plt.style.use('ggplot')
    matplotlib.rcParams['font.size'] = 16
    if 0:
        df = pd.DataFrame([
            [0, 31, 31, 31, 0 , 31],  # liner mass from thomas
            [435.445, 341.637493, 66.188744, 107.8643, 341.637493, 341.637493],
            [200] * 5 + [271],
            [0]*5+[400],
            ],
            columns=['Aluminium 6061', 'CFRP IFF circ', 'CFRP FF circ', 'CFRP IFF isotensoid', 'CFRP linerless', 'CFRP vaccuum'],
            index=['Liner', 'Shell', 'Insulation', '2nd shell']).T
        refSum = df.loc['CFRP IFF circ', :].sum()
    else:
        df = pd.DataFrame([
            [0, 31, 31, 0],  # liner mass from thomas
            [435.445, 341.637493, 107.8643, 341.637493],
            [271+90] * 4,  # Mirco spheres + emergency insulation
            [400] * 4,
            ],
            columns=['Aluminium 6061', 'CFRP circ', 'CFRP isotensoid', 'CFRP linerless'],
            index=['Liner', 'Inner shell', 'Insulation', 'Outer shell']).T
        refSum = df.loc['CFRP circ',:].sum()
    df = df.round()
    yName = 'Mass [-]'
    if 1: # use relative values
        df = df / refSum
        df = df.round(2)
        refSum = 1
        yName = 'Relative ' + yName

    fig, ax = plt.subplots(figsize=(9,4.5) if horizontal else (7,7))
    plt.tick_params(left=False)
    if horizontal:
        ax.invert_yaxis()
        matplotlib.rcParams['axes.xmargin'] = 0.05
    width = 0.66  # the width of the bars: can also be len(x) sequence
    bottoms = np.zeros((len(df.index),))
    indexes = np.arange(len(df.index))
    for colName in df:
        row = df[colName]
        kwargs = {'hatch':'/'} if colName == df.columns[-1] else {}
        if horizontal:
            bc = ax.barh(indexes, row, width, left=bottoms, label=colName, **kwargs)
        else:
            bc = ax.bar(indexes, row, width, bottom=bottoms, label=colName, **kwargs)
        if colName != df.columns[-1]:
            ax.bar_label(bc, label_type='center', fontsize=12)
        bottoms += row.array.T
    ax.bar_label(bc, fontsize=12)

    linewidth = 1
    #ax.set_title('Relative tank mass')
    if horizontal:
        ax.legend(loc='center', bbox_to_anchor=(0., 1.08, 1., .202), mode='expand', ncol=2, )
        plt.rcParams['xtick.labeltop'] = True
        ax.set_xlabel(yName)
        labels = [idx+'  ' for idx in df.index]
        ax.set_yticks(indexes, labels=labels)
        ax.axvline(refSum, color='dimgray', linewidth=linewidth, linestyle='dashed')
        ax.axvline(df.iloc[1, :-1].sum(), color='dimgray', linewidth=linewidth, linestyle='dashed')
        ax.axvline(df.iloc[1, :-2].sum(), color='dimgray', linewidth=linewidth, linestyle='dashed')
        ax.axvline(df.iloc[1, :-3].sum(), color='dimgray', linewidth=linewidth, linestyle='dashed')
    else:
        ax.axhline(refSum, color='dimgray', linewidth=linewidth, linestyle='dashed')
        ax.axhline(df.iloc[1,:-1].sum(), color='dimgray', linewidth=linewidth, linestyle='dashed')
        ax.axhline(df.iloc[1,:-2].sum(), color='dimgray', linewidth=linewidth, linestyle='dashed')
        ax.axhline(df.iloc[1,:-3].sum(), color='dimgray', linewidth=linewidth, linestyle='dashed')
        ax.set_ylabel(yName)
        ax.set_xticks(indexes, labels=df.index, rotation=60)
        ax.xaxis.tick_top()
        ax.legend(loc='center', bbox_to_anchor=(0., -.11, 1., .10), mode='expand', ncol=4)
    fig.tight_layout()
    plt.show()


def fatiguePlot(createData = True, plotData = True):

    filenamePickle = 'fatiguefactor.pickle'

    data = None
    if createData:
        # make data
        count = 20
        X, Y = np.meshgrid(np.linspace(0.0, 1, count), np.linspace(np.log10(1), np.log10(100), count))
        Z=[]
        for pMinRelative,heatUpCycles in zip(X.flatten(),np.power(10,Y.flatten())):
            pDesign = 0.24
            pMinOperation = pDesign * pMinRelative
            t, ff = getMaxWallThickness2(pDesign, alu6061T6, 2400, 2.25, pMinOperation=pMinOperation,
                                 heatUpCycles=heatUpCycles, Kt=4)
            Z.append(ff)

        Z=np.reshape(Z, (count,count))
        data = (X,Y,Z)

        with open(filenamePickle, 'wb') as f:
            f.write(pickle.dumps(data))

    if plotData:
        if data is None:
            with open(filenamePickle, 'rb') as f:
                X,Y,Z = pickle.loads(f.read())
        levels = np.linspace(Z.min(), Z.max(), 9)
        # plot
        fig, ax = plt.subplots(figsize=(5,3.8))

        fs = 15
        cs = ax.contourf(X, Y, Z, levels=levels)
        ax.set_xlabel(r'$\Delta p_{op\_min}/\Delta p_{op\_max}$', fontsize = fs)
        ax.set_ylabel(r'# Cycles to Ambient Conditions', fontsize = fs)
        plt.yticks(np.linspace(Y.min(), Y.max(), 3),['1','10','100'])
        ax.set_title('Fatigue Factor', fontsize = fs)
        cbar = fig.colorbar(cs)
        #cbar.set_label('Fatigue Factor', fontsize = fs)

        plt.tight_layout()
        plt.savefig(r'C:\Users\freu_se\Documents\Projekte\EXACT\03_Kommunikation\2022_03_31_MTR\fatigue factor.png')
        plt.show()



def strainLifePlot():
    # values from mmpds
    E = 68258.124
    epsilon_f = 3.5
    sigma_f = 803.65
    b, c = -0.1351, -0.9745

    plt.figure(figsize=(9, 4))
    plt.rcParams['font.size'] = 20
    cycles_2Nt = (epsilon_f * E / sigma_f) ** (1 / (b - c))
    cycles_2Nf_array = np.logspace(1, 8, 1000)
    epsilon_total = (sigma_f / E) * cycles_2Nf_array ** b + epsilon_f * cycles_2Nf_array ** c
    epsilon_total_at_cycles_2Nt = (sigma_f / E) * cycles_2Nt ** b + epsilon_f * cycles_2Nt ** c
    plt.loglog(cycles_2Nf_array, epsilon_total, color='red', alpha=0.8,
               label=str(r'$\epsilon_{tot}$ = $\epsilon_{plastic}$ + $\epsilon_{elastic}$'), linewidth=3)
    plt.plot([cycles_2Nt, cycles_2Nt], [10 ** -6, epsilon_total_at_cycles_2Nt], 'red', linestyle='--',
             alpha=0.5, linewidth=2)
    flightCycles = 50000
    epsilon_total_at__flight_cycles = (sigma_f / E) * flightCycles ** b + epsilon_f * flightCycles ** c
    plt.plot([flightCycles] * 2, [10 ** -6, epsilon_total_at__flight_cycles], 'black', linestyle='--',
             alpha=0.5, linewidth=2)
    plastic_strain_line = epsilon_f * cycles_2Nf_array ** c
    elastic_strain_line = sigma_f / E * cycles_2Nf_array ** b
    plt.plot(cycles_2Nf_array, plastic_strain_line, 'orange', alpha=0.7, label='$\epsilon_{plastic}$',
             linewidth=3)
    plt.plot(cycles_2Nf_array, elastic_strain_line, 'steelblue', alpha=0.8, label='$\epsilon_{elastic}$',
             linewidth=3)
    # plt.scatter(cycles_2Nf, strain, 80, marker='.', color='k', label='Fatigue data')
    plt.xlabel('Reversals to failure $(N_f)$')
    plt.ylabel('Strain amplitude $(\epsilon_a)$')
    # plt.title('Strain-Life diagram')
    # cycles_min_log = 10 ** (int(np.floor(np.log10(min(cycles_2Nf)))) - 1)
    # cycles_max_log = 10 ** (int(np.ceil(np.log10(max(cycles_2Nf)))) + 1)
    # strain_min_log = 10 ** (int(np.floor(np.log10(min(strain)))) - 1)
    # strain_max_log = 10 ** (int(np.ceil(np.log10(max(strain)))) + 1)
    cycles_min_log = 10 ** (1)
    cycles_max_log = 10 ** (6)
    strain_min_log = 10 ** (-4)
    strain_max_log = 10 ** (-1)
    plt.text(cycles_2Nt, strain_min_log, str('$N_t$'), verticalalignment='bottom')
    plt.text(flightCycles, strain_min_log, str(r'$N_{flights}$'), verticalalignment='bottom')
    plt.xlim(cycles_min_log, cycles_max_log)
    plt.ylim(strain_min_log, strain_max_log)
    plt.grid(True)

    leg2 = plt.legend(bbox_to_anchor=(.8, 1.2), loc='upper left', borderaxespad=0.)
    # this is to make the first legend entry (the equation) bigger
    legend_texts2 = leg2.get_texts()
    legend_texts2[0]._fontproperties = legend_texts2[1]._fontproperties.copy()
    # legend_texts2[0].set_size(13)
    plt.tight_layout()
    plt.show()

def getLinerContour(designArgs):
    from tankoh2.geometry.dome import getDome
    from tankoh2.geometry.liner import Liner
    domeType = designArgs['domeType'].lower()
    polarOpeningRadius = designArgs['polarOpeningRadius']  # mm
    dcly = designArgs['dcly']  # mm
    if 'lcyl' not in designArgs:
        designArgs['lcyl'] = designArgs['lcylByR'] * dcly / 2
    lcylinder = designArgs['lcyl']  # mm
    dome = getDome(dcly / 2, polarOpeningRadius, domeType, designArgs.get('domeLengthByR', 0.) * dcly / 2)
    liner = Liner(dome, lcylinder)
    return liner.getContour()


def domeContourPlot():
    params = allParamSets.vphDesign1
    cCirc = getLinerContour(params)
    params = allParamSets.vphDesign1_isotensoid
    cIso = getLinerContour(params)

    fontsize = 16
    fig, ax = plt.subplots(1, 1, figsize=(5, 3))
    matplotlib.rcParams['font.size'] = fontsize
    for (x,r), name in zip([cCirc, cIso], ['Spherical dome', 'Isotensoid dome']):
        ax.plot(x, r, label=name, linewidth=3)
    ax.set_title("Contour")
    ax.set_xlabel('x', fontsize=fontsize)
    ax.set_ylabel('r', fontsize=fontsize)
    plt.xticks(fontsize=fontsize)
    plt.yticks(fontsize=fontsize)
    ax.legend()
    fig.tight_layout()
    plt.show()


if __name__ == '__main__':
    if 1:
        massPlot()
    elif 0:
        fatiguePlot()
    else:
        myplot()

