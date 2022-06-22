"""Create plots for vph project - will be removed/reintegrated elsewhere in the future"""


import matplotlib
import matplotlib.pyplot as plt
import pickle
import numpy as np
import pandas as pd

import tankoh2.design.existingdesigns as allParamSets
from tankoh2.design.metal.material import alu6061T6
from tankoh2.design.metal.mechanics import getMaxWallThickness


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
    elif 1:
        df = pd.DataFrame([
            [0, 31, 31, 0],  # liner mass from thomas
            [435.445, 341.637493, 107.8643, 341.637493],
            [271+90] * 4,  # Mirco spheres + emergency insulation
            [400] * 4,
            ],
            columns=['Aluminium 6061', 'CFRP circ', 'CFRP isotensoid', 'CFRP linerless'],
            index=['Liner', 'Inner shell', 'Insulation', 'Outer shell']).T
        df = df.drop(index=['CFRP linerless'])
        refSum = df.loc['CFRP circ',:].sum()
    else:
        df = pd.DataFrame([
            [0, 31, 31, 0, 31],  # liner mass from thomas
            [435.445, 341.637493, 107.8643, 341.637493, 66.188744],
            #[271+90] * 4,  # Mirco spheres + emergency insulation
            #[400] * 4,
            ],
            columns=['Aluminium 6061', 'CFRP circ', 'CFRP isotensoid', 'CFRP linerless', 'CFRP fibre failure'],
            index=['Liner', 'Shell', #'Insulation', 'Outer shell'
                   ]).T
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
        kwargs = {'hatch':'/'} if colName == 'Outer shell' else {}
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
            t, ff = getMaxWallThickness(pDesign, 2.25*pDesign, alu6061T6, 2400, pMinOperation=pMinOperation,
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



def getLinerContour(designArgs):
    from tankoh2.geometry.dome import getDome
    from tankoh2.geometry.liner import Liner
    domeType = designArgs['domeType'].lower()
    polarOpeningRadius = designArgs['polarOpeningRadius']  # mm
    dcyl = designArgs['dcyl']  # mm
    if 'lcyl' not in designArgs:
        designArgs['lcyl'] = designArgs['lcylByR'] * dcyl / 2
    lcylinder = designArgs['lcyl']  # mm
    dome = getDome(dcyl / 2, polarOpeningRadius, domeType, designArgs.get('domeLengthByR', 0.) * dcyl / 2)
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

