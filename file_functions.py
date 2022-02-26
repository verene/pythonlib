import datetime as dt
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE
from error_email import error_email
import getpass
import os
import smtplib
import yaml


def send_html_email(message, subject, smtphost='defaulthost', smtpport='defaultport', yaml_path=None, dist_name=None,
    from_user=None, img_full_path=None, file_atts=None, testmode=True):
    '''
    Sends an html email with message text, an optional image pasted below, and optional file attachements.
    Parameters:
        message str: Text body of the email to be sent. Required, no default.
        subject str: Subject line of the email to be sent. Required, no default.
        smtphost str: SMTP server host. Optional; user must fill in their own default value after cloning repo.
        smtpport str: SMTP port number as a string. Optional; user must fill in their own default value after cloning repo.
        yaml_path str: Absolute path to yaml files containing email distribution lists and email signatures. Optional,
            default None. If not provided, home path will be used. If yaml files do not exist, the email will be sent
            to the from_user.
        dist_name str: name of distribution list from which to retrieve list of recipient emails. The distribution list name
            must be a key in a file called "email_signatures.yaml" located at yaml_path (defaults to home path).
            Note, if dist_name=None email will be sent to the from_user.
            Optional, default None.
        from_user: username for the persom from whom the email will be sent. The from_user should be a key in the
            email_signatures.yaml. If key not found, or no argument passed, the from_user will be the current system user.
            Optional, default None.
        img_full_path str: Full path including file name of image to include in the body of the email below the message text
            and above the signature. Optional, default None.
        file_atts list of str: List of full paths to files to be included as attachments on the email. Optional, default None.
        testmode bool: Whether to run this function in testmode. If run in testmode, the email will be sent to the from_user.
            Optional, True or False; default True.
    '''
    if not yaml_path:
        yaml_path = os.path.expanduser("~")
    if not from_user:
        from_user = os.getlogin()
    email_dist = "email_dist_lists.yaml"
    signatures = "email_signatures.yaml"

    try:
        with open(yaml_path+signatures) as sf:
            (sigs) = yaml.full_load(sf)
        email_list = [sigs[from_user]['from']]
        signature = "<br><br>"+sigs[from_user]['html_signature']
    except:
        email_list = [getpass.getuser()]
        signature = "<br><br>"+from_user
        pass

    FROM_list=email_list
    
    if testmode or dist_name==None:
        TO_list = email_list
        CC_list = []
    else:
        try:
            with open(yaml_path+email_dist) as ef:
                (email_distrib) = yaml.full_load(ef)
                TO_list = email_distrib[dist_name]['to']
                try:
                    CC_list = email_distrib[dist_name]['cc']
                except:
                    CC_list = None
                    pass
        except:
            TO_list = from_user
            CC_list = None

    #start SMTP server
    s = smtplib.SMTP(host=smtphost, port=smtpport)

    #create message
    msg = MIMEMultipart()
    msg['From']=COMMASPACE.join(FROM_list)
    msg['To']=COMMASPACE.join(TO_list)
    if CC_list:
        msg['Cc']=COMMASPACE.join(CC_list)
    msg['Subject']=subject
    
    #If image path given, include image in body of email below the message text
    if img_full_path:
        with open(img_full_path, 'rb') as fp:
            img = MIMEImage(fp.read())
        fp.close()
        img.add_header('Content-ID', '<0>')
        msg.attach(img)
        print("Copied {} into the email body.".format(img_full_path))
        msg.attach(MIMEText('<html><body>{}<p><img src="cid:0"></p>{}</body></html>'.format(message, signature), 'html', 'utf-8'))
    else:
        msg.attach(MIMEText(message+signature, 'html'))

    #Attatch any files.
    for f in file_atts or []:
        with open(f, "rb") as fa:
            part = MIMEApplication(fa.read(), Name=os.path.basename(f))
        part['Content-Disposition'] = f'attachment; filename={os.path.basename(f)}'
        msg.attach(part)

    #Attempt to send the email a maximum of five times. After five failed tries, send an error email to user.
    email_retries = 5
    while email_retries > 0:
        try:
            s.send_message(msg)
            email_retries = 0
            break
        except Exception as e:
            if email_retries == 1:
                errmsg = "Failed to send email.\n"
                print(e)
                print(errmsg)
                error_email(e, email_list, __file__, errmsg)
                email_retries = 0
                break
            else:
                pass
        email_retries -= 1
    del msg


def find_latest(t_yr, y_mo, y_mo_fmt, path, str_match_list, mo_fmt_case='cap'):
    '''
    Finds the file with the most recent date in its name and with a name matching str_match_list
     at the given path.
    Returns the name of the most recent dated file.
    Parameters:
    - t_yr: target year to match in file name (as a two- or four-digit string or int)
    - y_mo: target month to match in file name (as a one- or two-digit string or int)
    - y_mo_fmt: format of month to be matched in file name, in python datetime.strftime format
      e.g. "%b" matches a month in the format "Jan", "Feb", etc.
           "%m" matches a month in the format "01", "02", etc.
    - path: full path to the location of the files to search through
    - str_match_list: list of strings to match in the file name.
    - mo_fmt_case: indicate if the month format should be all caps, or all lower case.
      default is 'cap' which uses the default capitalization in Python.
    '''
    if isinstance(y_mo, str):
        y_mo = int(y_mo)
    if isinstance(t_yr, str):
        if len(t_yr)==4:
            t_yr=int(t_yr)
        elif len(t_yr)==2:
            t_yr=int(t_yr)+2000
        else:
            print(f"ERROR: t_yr {t_yr} not recognized as a valid year!")
            return
    candidate_files = [f for f in os.listdir(path) if str_match_list[0] in f]
    for strmatch in str_match_list[1:]:
        candidate_files = [f for f in candidate_files if strmatch in f]
    candidate_files = [f for f in candidate_files if f[0] != "~"] #Filter out open copies of files
    if y_mo == 1:
        mos = [1, 12]
    else:
        mos = list(range(y_mo, 0, -1))
    for m in mos:
        mon = dt.date(t_yr,m,1).strftime(y_mo_fmt)
        if mo_fmt_case.lower() == "upper":
            mon =  mon.upper()
        elif mo_fmt_case.lower() == "lower":
            mon = mon.lower()
        t_fs = [f for f in candidate_files if mon in f]
        #print(t_fs)
        if len(t_fs)>0:
            f_latest = sorted(t_fs)[-1]
            print("latest: {}".format(f_latest))
            break
    return f_latest