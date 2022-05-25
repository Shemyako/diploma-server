import smtplib
# from email import encoders
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
# from email.mime.base import MIMEBase

def send_mail( ):
    fromaddr = "pesopolis.school@gmail.com"
    toaddr = ["naumov-04@mail.ru", "3a380e4b389b@mail.ru", "nlev2000@mail.ru", "nlev2000mail@gmail.com"]
    mypass = "pass"
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(fromaddr, mypass)
    body = "Это пробное сообщение123"
    for i in toaddr:
        msg = MIMEMultipart()
        msg['From'] = fromaddr
        msg['To'] =  i
        msg['Subject'] = "Привет1"
        msg.attach(MIMEText(body, 'plain'))
        text = msg.as_string()
        server.sendmail(fromaddr, i, text)
    server.quit()

send_mail()