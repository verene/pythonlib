import functools
import numpy as np
import operator
import rpy2.robjects as ro

def hyman_meanpres_spline(ts=None, icdf=None, px=None, xnum=100):
    '''
    Computes the mean-preserved Hyman-filtered cubic spline of a list of numbers (ts)
    e.g. smoothly upscale a timeseries forecast (monthly to daily)
    If icdf (inverse cdf) is passed instead of ts, then spline the inv cdf as is.
    e.g. create a smooth cdf given a list of p-values.
    For either, optionally pass the corresponding x-values, for uneven spacing (px).
    Returns evenly-spaced x and corresponding y values for spline.
    NOTE: You must have the R package 'splinefun' installed on your computer and in your
        PATH for this function to work.
    '''
    
    if px==None:
        if ts != None:
            px = np.linspace(0, len(ts), len(ts)+1)
        elif icdf != None:
            px = np.linspace(0, len(icdf), len(icdf)+1)
        else:
            print("ERROR in hyman_meanpres_spline: nothing passed in for ts or icdf")
            return
    if icdf==None:
        py = [0]*len(px)
        for i in range(len(ts)):
            py[i+1] = py[i]+ts[i]*(px[i+1]-px[i])
    else:
        py = icdf
    rx = ro.FloatVector(px)
    ry = ro.FloatVector(py)
    r_spline = ro.r['splinefun']
    s = r_spline(x=rx, y=ry, method='hyman')
    x_splined = np.linspace(min(px), max(px), xnum)
    rx_splined = ro.FloatVector(x_splined)
    if ts!=None:
        derivative = 1
    else:
        derivative = 0
    y_splined = s(rx_splined, deriv=derivative)
    return x_splined, y_splined

def sumproduct(*lists):
    '''
    Returns the dot product of multiple (two or more) vectors contained in lists argument.
    '''
    return sum(functools.reduce(operator.mul, data) for data in zip(*lists))