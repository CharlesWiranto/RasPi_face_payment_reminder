from flask import Flask, request, jsonify
from flask_cors import CORS  # Add this import
import face_recognition
import cv2
import numpy as np
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import base64
import time
from payment_service import AlipayService
import sqlite3
from contextlib import closing
from database import get_db_connection
from config import Config

app = Flask(__name__)

app.config.update({
    'SMTP_SERVER': 'smtp.qq.com',
    'SMTP_PORT': 465,  # Correct for QQ Mail
    'EMAIL_FROM': "charleswirantolgl@qq.com",
    'EMAIL_PASSWORD': "whopwummfcngbfbh"  # Your authorization code
})

def send_email(to_email, name, payment_url=None):
    subject = "人脸识别通知"
    body = f"您好 {name}，我们已识别到您的人脸。识别时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    if payment_url:
        body += f"\n\n请完成支付: {payment_url}"

    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = app.config['EMAIL_FROM']
    msg['To'] = to_email

    try:
        print("⌛ Attempting to connect to SMTP server...")
        context = smtplib.ssl.create_default_context()
        
        with smtplib.SMTP_SSL(
            app.config['SMTP_SERVER'],
            app.config['SMTP_PORT'],
            context=context,
            timeout=20
        ) as server:
            print("🔐 Connected to server. Attempting login...")
            server.login(app.config['EMAIL_FROM'], app.config['EMAIL_PASSWORD'])
            print("✉️ Login successful. Sending email...")
            server.sendmail(app.config['EMAIL_FROM'], [to_email], msg.as_string())
            print(f"✅ Email successfully sent to {to_email}")
            return True
            
    except smtplib.SMTPAuthenticationError:
        print("❌ Authentication failed. Please verify:")
        print("- Your authorization code is correct (not your QQ password)")
        print("- SMTP service is enabled in QQ Mail settings")
    except smtplib.SMTPServerDisconnected as e:
        print(f"❌ Server disconnected: {e}")
        print("Possible causes:")
        print("- Network firewall blocking the connection")
        print("- QQ Mail server temporarily unavailable")
        print("- Incorrect port (should be 465 for SSL)")
    except Exception as e:
        print(f"❌ Unexpected error: {repr(e)}")
    return False

import smtplib, ssl

def test_qq_smtp():
    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(
            'smtp.qq.com',
            465,
            context=context,
            timeout=20
        ) as server:
            server.login("2728642293@qq.com", "whopwummfcngbfbh")
            print("✅ Login successful!")
            return True
    except Exception as e:
        print(f"❌ Failed at step: {'login' if '2728642293' in str(e) else 'connection'}")
        print(f"Error details: {repr(e)}")
        return False


if __name__ == '__main__':
    # app.run(host='0.0.0.0', port=5000, debug=True)
    # test_qq_smtp()
    send_email("charleswirantolgl@qq.com", "Charles", "http://localhost:8086")
    # send_email("2728642293@qq.com", "Charles", "http://localhost:8086")
    # send_email("1073772039@qq.com", "李涵", "http://localhost:8086")