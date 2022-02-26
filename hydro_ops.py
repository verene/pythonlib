import datetime as dt
import io
import numpy as np
import os
import pytz
import pandas as pd
import requests

today = pytz.timezone("US/Pacific").localize(dt.datetime.now())

def tofloat(x):
    '''Cleanly converts argument to a float; if argument cannot be converted, returns None instead of thowing exception.'''
    try:
        return float(x)
    except:
        return None

def get_usgs(station, resamp=None, sd=today, ed=today, out_tz='utc', datastream='flow'):
    '''
    Returns a time series of publicly available USGS data.
    Parameters:
        station int (or str): USGS ID. Required, no default.
        resamp str: pandas-compatible string indicating desired resample interval. Optional, default None.
        sd datetime.date: desired start date of returned data (inclusive). Optional, default today (however, if
            ed is equal to sd, the most recent seven days of data will be returned, ending on ed).
        ed datetime.date: desired end date of returned data (inclusive). Optional, default today.
        out_tz str: timezone of the output time series data. Optional, default UTC.
        datastream str: type of USGS data to return. One of flow, elev, or temp; default flow. 
    '''

    if sd==ed:
        sd = ed - dt.timedelta(days=7)
    
    #USGS datastreams: 10 = water temp, 60 = discharge, 65 = gage height
    ds = {'flow': '60', 'streamflow': '60', 'discharge': '60', 'outflow': '60',
          'elev': '65', 'elevation': '65',
          'temp': '10', 'watertemp': '10', 'temperature': '10'}
    
    url = 'https://nwis.waterdata.usgs.gov/nwis/uv?cb_000{}=on&format=rdb&site_no={}&period=&begin_date={}&end_date={}' \
            .format(ds[datastream], station, sd.strftime("%Y-%m-%d"), ed.strftime("%Y-%m-%d"))
    print(url)
    response = requests.get(url)
    if response.status_code == 200:
        s = response.content

        #figure out how many header rows to skip
        r = requests.get(url, stream=True)
        n=0
        for line in r.iter_lines():
            l = line.decode('utf-8')
            if l[0]=='#':
                n+=1
            else:
                break
        df = pd.read_csv(io.StringIO(s.decode('utf-8').replace("\t\t", "\t")), header=0, sep="\t", skiprows=list(range(n))+[n+1])
        #Fill in any primary sensor data with the secondary sensor data, if present
        pri = df.columns.tolist()[4]
        if df.shape[1] >= 7:
            sec = df.columns.tolist()[5]
            df[pri].fillna(df[sec], inplace=True)

        #Add time zone information to timestamp to make tz-aware / convert tz as needed
        tzoff = {'PST': 8, 'PDT': 7, 'MST': 7, 'MDT': 6, 'CST': 6, 'CDT': 5, 'EST': 5, 'EDT': 4}
        dttz = [f'{df["datetime"][i]}:00-0{tzoff[df["tz_cd"][i]]}' for i in range(len(df))]

        ts = pd.to_datetime(dttz, infer_datetime_format=True, utc=True)
        if out_tz.lower()!='utc':
            ts = ts.tz_convert(pytz.timezone(out_tz))
        flowdf = df[pri].copy()
        flowdf.index = ts

        flowdf = flowdf.apply(lambda x: tofloat(x))
        if resamp is not None and isinstance(resamp, str):
            try:
                flowdf = flowdf.resample(resamp, label='right', closed='right').mean()
            except Exception as e:
                print("WARNING: Resample failed")
                print(e)
                pass
        return flowdf
    else:
        print("WARNING: Could not retrieve data from USGS")
        return None


def get_usace(station, resamp=None, sd=today, ed=today, out_tz='US/Pacific', datastream='outflow', per='H', metric='avg', revraw='REV', units='kcfs'):
    '''
    Returns a time series of publicly available US Army Corps of Engineers (USACE) data available through
        the Data Query 2.0 website.
    Parameters:
        station int (or str): USACE ID. Required, no default.
        resamp str: pandas-compatible string indicating desired resample interval. Optional, default None.
        sd datetime.date: desired start date of returned data (inclusive). Optional, default today (however, if
            ed is equal to sd, the most recent seven days of data will be returned, ending on ed).
        ed datetime.date: desired end date of returned data (inclusive). Optional, default today.
        out_tz str: timezone of the output time series data. Optional, default UTC.
        datastream str: type of USGS data to return. One of flow, elev, or temp; default flow. 
        per str: pandas-compatible string indicating native time interval of the query datastream. Optional, default H.
        metric str: type of query metric. Optional among avg or inst (instantaneous); default avg.
        revraw str: indicator of whether requested data is revised or raw. Optional among 'rev' or 'raw'; default rev.
        units str: native units of requested data. Optional; default kcfs.
    '''

    sd = pd.to_datetime(sd)
    ed = pd.to_datetime(ed)
    try:    
        sd = pytz.timezone('US/Pacific').localize(sd).astimezone('Etc/GMT+8')
        ed = pytz.timezone('US/Pacific').localize(ed).astimezone('Etc/GMT+8')
    except:
        print("sd and ed are ALREADY tz aware {} {}".format(sd.strftime("%Y-%m-%d %H:%M:%S%z"), ed.strftime("%Y-%m-%d %H:%M:%S%z")))
        pass

    fac = 1.0
    if len(datastream) > 15 and 'CBT' in datastream:
        dd = datastream
        if 'Flow' in datastream:
            units = 'kcfs'
            fac = 1000.0
        elif 'Elev' in datastream or 'Snow' in datastream:
            units = 'ft'
        elif 'Temp' in datastream:
            units = 'F'
        else:
            units = 'in'
        if 'units' not in datastream:
            unitstr = ":units={}".format(units)
        else:
            unitstr = ""
    else:
        ds = {'inflow': ['Flow-In', 'kcfs'], 'fb': ['Elev-Forebay', 'ft'], 'tw': ['Elev-Tailwater', 'ft'], 'ouflow': ['Flow-Out', 'kcfs'],
              'pcp': ['Precip-Inc', 'in'], 'snow': ['Depth-Snow-Inc', 'ft'], 'airtemp': ['Temp-Air', 'F']}
        pr = {'D': '~1Day.1Day', 'H': '1Hour.1Hour'}
        mt = {'avg': 'Ave', 'max': 'Max', 'tot': 'Total', 'inst': 'Inst', 'min': 'Min'}

        if metric == 'inst':
            pr[per] = pr[per].split(".")[0]+".0"
            
        dd = ".".join([ds[datastream][0], mt[metric], pr[per], "CBT-"+revraw.upper()])
        unitstr = ":units={}".format(ds[datastream][1])
        if 'kcfs' in ds[datastream][1]:
            fac = 1000.0

    usace_official = 'https://www.nwd-wc.usace.army.mil'
    usace_mirror = 'http://pweb.crohms.org'
    url_args = '/dd/common/web_service/webexec/ecsv?id={}.{}{}&headers=true&filename=&timezone=PST&startdate={}+08:00'\
                '&end_date={}+08:00'.format(station, dd, unitstr, sd.strftime("%Y-%m-%d"), ed.strftime("%Y-%m-%d"))
    url = usace_official+url_args
    print(url)

    try:
        df = pd.read_csv(url, header=0, index_col=0, parse_dates=True, names=["date", "station"])
        df.index = pd.to_datetime(df.index).tz_localize(tz='Etc/GMT+8')

    except Exception as e:
        print("USACE exception: {}".format(e))
        url = usace_mirror+url_args
        print("Trying mirror site: {}".format(url))
        df = pd.read_csv(url, header=0, index_col=0, parse_dates=True, names=["date", "station"])
        try:
            df.index = pd.to_datetime(df.index).tz_convert(tz='US/Pacific')
        except TypeError:
            try:
                df.index = pd.to_datetime(df.index).tz_localize(tz='US/Pacific')
            except Exception as e:
                errmsg = f"ERROR: could not convert USACE index to timestamps\n{df.head()}"
                print(errmsg)
                error_email(e=e, errmsg=errmsg, origin_script=__name__)
                raise
            pass

    df_target = df[(df.index > sd) & (df.index <= ed)].copy()
    df_target.index = pd.to_datetime(df_target.index, infer_datetime_format=True, utc=False)
    if out_tz.lower()!='Etc/GMT+8':
        df_target.index = df_target.index.tz_convert(pytz.timezone(out_tz))

    df_target['station'][:] = [tofloat(x)*fac for x in df_target['station']]
    if resamp is not None and isinstance(resamp, str):
        try:
            df_target = df_target.resample(resamp, label='right', closed='right').mean()
        except Exception as e:
            print("WARNING: Resample failed")
            print(e)

    return df_target


def make_tz_aware(ts, intz='US/Pacific', outtz='Etc/GMT+8', verbose=False):
    '''
    Returns a timezone-aware timestamp. If timestamp is already timezone aware, returns the original timestamp.
    Parameters:
        ts date/datetime/str Python can recognize as a date or datetime: object to be converted to timezone-aware.
            Required, no default.
        intz str: timezone code of ts as given. Optional, default US/Pacific.
        outtz str: timezone code of as desired. Optional, default Etc/GMT+8 (Pacific Standrad Time).
        verbose bool: whether to print informative messages. Optional, default False.
    '''
    ts = pd.to_datetime(ts)
    try:
        ts = ts.astype(dt.datetime)
    except:
        pass
    try:    
        ts = pytz.timezone('US/Pacific').localize(outtz).astimezone(outtz)
        if verbose:
            print("timestamp is NOW tz aware {}".format(ts.strftime("%Y-%m-%d %H:%M:%S%z")))
    except Exception as e:
        if verbose:
            print(e)
            print("timestamp was ALREADY tz aware {}".format(ts.strftime("%Y-%m-%d %H:%M:%S%z")))
        pass
    return ts
    
def get_usace_legacy(station='SKQ', sd=today.date()-dt.timedelta(days=2), ed=today.date(), resamp=None):
    '''
    Returns a timeseries of publicly available data from the USACE legacy site; intended for use for data not available through
        Data Query 2.0.
    The legacy USACE site returns daily data only, so no out_tz.
    The forebay value is the midnight instantaneous value.
    The outflow values represent the average daily flow, average from 0100->2400 and are supposed to post with the 2400 timestamp.
    '''
    sd = make_tz_aware(sd)
    ed = make_tz_aware(ed)
    
    if station.upper()=='SKQ' or station.capitalize()=='Kerr' or station.capitalize()=='Flathead':
        sitecode = 'flt_ker'
        colnames=['elev', 'outflow']
    else:
        sitecode = 'kot_qbyb'
        colnames=['inflow', 'elev', 'outflow']
        
    usace_official = 'https://www.nwd-wc.usace.army.mil'
    usace_mirror = 'http://pweb.crohms.org'
    url_args = '/nws/hh/textdata/{}.prn'.format(sitecode)
    url = usace_official+url_args
    print(f'Retrieving data from {url}')
    usecols = [1,2,3]+list(range(5,5+len(colnames)))
    try:
        df = pd.read_csv(url, sep="\s+", skiprows=5, header=None, index_col=0, usecols=usecols, parse_dates=[[0,1,2]],
                 infer_datetime_format=True, skipfooter=2, engine='python', names=['Date', 'Per', 'Beginning']+colnames)
        df.index = pd.to_datetime(df.index).tz_localize(tz='Etc/GMT+8')
        dfheaders = pd.read_csv(url, sep="\s+", header=None, index_col=None, skiprows=2, nrows=1)
    except Exception as e:
        print(e)
        url = usace_mirror+url_args
        print("Trying mirror site: {}".format(url))
        try:
            df = pd.read_csv(url, sep="\s+", skiprows=5, header=None, index_col=0, usecols=usecols, parse_dates=[[0,1,2]],
                 infer_datetime_format=True, skipfooter=2, engine='python', names=['Date', 'Per', 'Beginning']+colnames)
            df.index = pd.to_datetime(df.index).tz_localize(tz='Etc/GMT+8')
            dfheaders = pd.read_csv(url, sep="\s+", header=None, index_col=None, skiprows=2, nrows=1)
        except:
            print("ERROR: couldn't get data from USACE mirror site either")
            return None

    df.index = pd.to_datetime(df.index, infer_datetime_format=True, utc=False)
    df_target = df[(df.index > sd) & (df.index <= ed)]
    
    coldict={}
    for c in range(len(colnames)):
        coldict[colnames[c]] = dfheaders.iat[0,c]
    df_target = df_target.rename(coldict, axis=1)
    if resamp is not None and isinstance(resamp, str):
        try:
            df_target = df_target.resample(resamp, label='right', closed='right').mean()
        except Exception as e:
            print("WARNING: Resample failed")
            print(e)

    return df_target


def elev_to_vol(res, elev, out_units='af'):
    '''
    Returns estimated storage volume in acre-feet.
    Parameters:
    - res (string): Reservoir name. Required, no default.
    - elev (numeric): Elevation in feet to convert to a volume. Required, no default.
    - out_units (string): units of volume to return. Optional; default is acre-feet ('af').
      If not acre-feet, returns volume in second-foot-days.
    '''
    reservoirs = {
        'Ross': [0.027002111884936, -74.7116749777982, 51436.172],
        'Diablo': [5.8249850962311, -13121.0403804066, 7442032.492],
        'Gorge': [3.0182006032046, -5038.84270924663, 2106665.674],
        'Boundary': [15.6131553420564, -60476.4603852965, 58555209.311],
    }
    c = reservoirs[res]
    vol = np.sum(np.power(elev,2)*c[0], elev*c[1], c[2])
    if out_units=='af':
        return vol
    return vol/1.9835 #SFD

def cfs_af(val, to='af'):
    '''
    Convert cfs (flow rate) to acre-feet/day
    1 cfs * 1 day = 1 SFD (second food day... :-/ )
    = 1.9835 acre-feet
    = 2447 cubic meters
    '''
    fac = 1.9835
    if to=='af' or to=='kaf' or 'acre' in to or to=='acrefeet' or to=='af/d':
        print("{} cfs in acre-feet/day is: {}".format(val, val*fac))
        return val*fac
    else:
        print("{} acre-feet/day in cfs is: {}".format(val, val/fac))
        return val/fac


if __name__=='__main__':
    #Example usages of select functions

    home = os.path.expanduser("~") 
    ppt = 'US/Pacific'
    sd = dt.datetime(2000,1,1,0,0,0)
    ed = dt.datetime.now()

    nh = get_usgs('12178000', resamp=None, sd=sd, ed=ed, out_tz=ppt, datastream='flow')
    nh.to_csv('{}{}_Newhalem_USGS_daily.csv'.format(home, ed.strftime("%Y%m%d")))
    mm = get_usgs('12181000', resamp='15T', sd=sd, ed=ed, out_tz=ppt, datastream='flow')
    mm.to_csv('{}{}_Marblemount_USGS_daily.csv'.format(home, ed.strftime("%Y%m%d")))

    #usacedf = get_usace('ALF', sd=sd, ed=ed, out_tz=ppt, datastream='inflow', per='D')
    #print(usacedf)

    #skq = get_usace_legacy()
    #print(skq)

