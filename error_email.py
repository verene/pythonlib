from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE
import getpass
import smtplib

def error_email(e="Something went wrong!", origin_script="", errmsg="",
    email_recipients_list=None, host='stmp.host.example', port='100'):

    if email_recipients_list==None:
        email_recipients_list = getpass.getuser()
    if not isinstance(email_recipients_list, list):
        email_recipients_list = [email_recipients_list]
        
    #start SMTP server
    s = smtplib.SMTP(host=host, port=port)

    #create message
    msg = MIMEMultipart()
    message = "{}\n{}\n{}".format(origin_script, e, errmsg)
    msg['From']=getpass.getuser()
    msg['To']=COMMASPACE.join(email_recipients_list)
    msg['Subject']="Error encountered in {}".format(origin_script)
    msg.attach(MIMEText(message, 'plain'))

    #send email
    s.send_message(msg)
    del msg

if __name__=="__main__":
    error_email()