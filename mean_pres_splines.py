import numpy as np
import rpy2.robjects as ro
import pandas as pd

def hyman_meanpres_spline(ts=None, cdf=None, px=None, xnum=100):
    '''Computes the mean-preserved (Hermite) Hyman-filtered cubic spline of a list of numbers
    assumed to be a timeseries (ts) or directly from a CDF (cdf).
    If ts is passed, creates a cdf
    e.g. smoothly upscale a timeseries forecast (monthly to daily)
    If cdf is passed instead of ts, then splines
    the cdf as is, e.g. create a smooth cdf given a list of p-values
    For either, optionally pass the corresponding x-values, for uneven spacing (px)
    Returns evenly-spaced x and corresponding y values for spline'''
    
    if px==None:
        #If prediction quantiles (x-values) were not passed, then construct evenly 
        # spaced intervals
        if ts != None:
            px = np.linspace(0, len(ts), len(ts)+1)
        elif cdf != None:
            px = np.linspace(0, len(cdf), len(cdf)+1)
        else:
            print("ERROR in hyman_meanpres_spline: nothing passed in for ts or cdf")
            raise
    if cdf==None:
        #If no CDF was passed, then construct CDF from ts
        py = [0]*len(px) #initialize list of target values
        for i in range(len(ts)):
            py[i+1] = py[i]+ts[i]*(px[i+1]-px[i])
    else:
        py = cdf
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

def spline_fx(qvals, raw_cdf, inc=0.5):
    '''
    Computes and returns a forecast timeseries for the requested forecast quantile.
    Uses Hyman-filtered mean-preserving spline to interpolate forecast distribution to
    extract the requested quantile forecast values for each step of the forecast.
    Parameters:
        qvals float or list of floats: Number(s) between 1 and 99 indicating the
            desired forecast quantile(s) to be returned. Required, no default.
        raw_cdf pandas dataframe: Probabilistic distribution including
            all original/raw forecast quantiles, covering the full period of interest. Note:
            spacing between forecast periods must be equal for an accurate interpolation (e.g.
            all time steps must be hourly / daily / monthly; no mixed interval forecasts.)
        inc float: increment (step) size in percents, indicating the granularity of desired
            forecast quantiles. Optional; default 0.5 (increments of half a percent)
    '''

    inc = inc/100.0 #Work in fractions
    #TODO: detect if qvals require some other increment size
    upper = qs[0]
    lower = qs[-1]
    xnum = (upper-lower)/inc + 1.0

    if not isinstance(qvals, list):
        qvals=[qvals]
    idx = [int((qval-1)*(lower/inc)) for qval in qvals]
    qvalname = ["Q"+str(qval) for qval in qvals]
    
    #Initialize dataframe
    fxdf = pd.DataFrame(columns=qvalname)

    #Existing forecast quantiles to interpolate between
    #TODO: Add functionality to allow/detect other raw forecast quantiles in qs below.
    qs=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.975, 0.99]

    #For each time interval in the forecast
    for m in range(len(raw_cdf)):
        #Extract a list containing forecast values at each quantile
        fls = list(raw_cdf.iloc[m,:])
        #Spline the forecast distribution
        xs, for_samples=hyman_meanpres_spline(cdf=fls, px=qs, xnum=xnum)
        #Get the forecast values for the desired quantile(s) and add them to the dataframe to be returned
        fxdf.loc[raw_cdf.index[m]]=[round(for_samples[i]) for i in idx]

    return fxdf
