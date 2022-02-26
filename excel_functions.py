import datetime as dt
from error_email import error_email
import getpass
import os
from PIL import ImageGrab
import pythoncom
import win32com.client
    
def run_macro(excel, wb_name, module, macro):
    '''
    Runs a module.macro in a workbook named wb_name. 
    Parameters:
        excel win32com application instance: Required, no default.
        wb_name str: name of workbook in which the macro is located. Required, no default.
        module str: name of the module in wb_name containing the macro to be run. Required, no default.
        macro str: name of the macro located in module, in wb_name, to be run. Required, no default.
    '''
    torun = "{}!{}.{}".format(wb_name, module, macro)
    print("Running {}".format(torun))
    try:
        excel.Application.Run(torun)
    except:
        print("WARNING: Couldn't run {}. Attempting to run with just macro name.".format(torun))
        excel.Application.Run(macro)
    return
              
def start_excel(update_links_ask=False, visible=True, screen_update=True, alerting=False):
    '''
    Starts running MS Excel with win32com; returns application instance.
    Parameters:
        update_links_ask bool: whether to update links in workbooks opened. Default False.
        visible bool: whether to make Excel windows visible. Default True.
        screen_update bool: whether to update the display as updates are made to workbooks; True can lead to
            slower runtimes. Default True.
        alerting bool: whether to display alerts from Excel. Default False.
    '''
    #Allow multiple instances of Excel to run simulaneously
    pythoncom.CoInitialize()

    #Start an Excel instance
    excel = win32com.client.Dispatch("Excel.Application")
    try:
        excel.AskToUpdateLinks=update_links_ask
    except:
        pass
    try:
        excel.Visible = visible
    except:
        pass
    try:
        excel.ScreenUpdating = screen_update
    except:
        pass
    try:
        excel.DisplayAlerts = alerting
    except:
        pass
    return excel


def updatelinks(wb, verbose=False):
    '''
    Attempts to update all external links in a given workbook.
    Parameters:
        wb Excel workbook handle; required, no default.
        verbose bool: Indicates whether informattive messages should be printed to stdout.
            If verbose is set to true, prints text to inform if no external links are found in the workbook,
            or if exceptions were thrown when trying to update external links. Optional, default False.
    '''
    try:
        for link in wb.LinkSources():
            try: 
                wb.UpdateLink(Name=link)
            except Exception as e:
                if verbose:
                    print("Couldn't update links: {}".format(link))
                    print(e)
                pass
    except:
        if verbose:
            print("{} appears to have no external links to update.".format(wb.Name))
        pass
    return


def from_excel_ordinal(ordinal, _epoch0=None):
    '''
    Converts dates in ordinal format from Excel to a date.
    '''
    import datetime as dt
    if _epoch0==None:
        _epoch0 = dt.datetime(1899,12,31)
    if ordinal >= 60:
        ordinal -= 1  # Excel leap year bug, 1900 is not a leap year!
    return (_epoch0 + dt.timedelta(days=ordinal)).replace(microsecond=0)


def get_img(r1,c1,r2,c2,ws,dest_file='excel_image.bmp',img_path=None, overwrite=False):
    '''
    Saves a region of an Excel worksheet as an image.
    Parameters:
        r1 int: top row number bounding the target image. Required, no default.
        c1 int: left-side column number bounding the target image. Required, no default.
        r2 int: bottom row number bounding the target image. Required, no default.
        c1 int: right-side column number bounding the target image. Required, no default.
        ws Excel Worksheet handle. Required, no default.
        dest_file: Desired file name of the resulting image (should end in .bmp). Optional, default name provided.
        img_path: full path where the image should be saved. Optional; if none provided, users's home directory will be used.
    '''
    if not img_path:
        img_path = os.path.expanduser()
    if os.path.exists(img_path+dest_file):
        if overwrite:
            os.remove(img_path+dest_file)
        else:
            dest_file += "_{}".format(dt.datetime.now().strftime("%Y%m%d%H%m%S"))
    try:
        ws.Range(ws.Cells(r1,c1),ws.Cells(r2,c2)).CopyPicture(1,2)  
        img = ImageGrab.grabclipboard()
        imgFile = os.path.join(img_path,dest_file)
        img.save(imgFile)
        print("Saved {}".format(dest_file))
    except Exception as e:
        errmsg = "ERROR: Couldn't save {} with Image Grab".format(dest_file)
        print(errmsg, e)
        error_email(e, getpass.getuser(), __file__, errmsg)
        pass
    return
