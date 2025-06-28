import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from config import Config

def send_email(to_email, name, payment_url=None):
    """Send email notification"""
    subject = "Face Recognition Notification"
    body = f"Hello {name},\n\nYour face was recognized at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    if payment_url:
        body += f"\n\nPlease complete your payment: {payment_url}"
    
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = Config.EMAIL_FROM
    msg['To'] = to_email
    
    try:
        with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT) as server:
            server.starttls()
            server.login(Config.EMAIL_FROM, Config.EMAIL_PASSWORD)
            server.sendmail(Config.EMAIL_FROM, [to_email], msg.as_string())
        return True
    except Exception as e:
        print(f"Email sending failed: {str(e)}")
        return False