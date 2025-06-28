import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

class Config:
    # Flask
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')
    
    # Database
    # DATABASE_URI = os.getenv('DATABASE_URL', f'sqlite:///{BASE_DIR}/instance/face_payment.db')
    DATABASE_URI = os.getenv('DATABASE_URL', f'sqlite:///{BASE_DIR}/face_payment.db')
    
    # Alipay
    ALIPAY_APP_ID = os.getenv('ALIPAY_APP_ID')
    ALIPAY_GATEWAY = 'https://openapi.alipaydev.com/gateway.do' if FLASK_ENV == 'development' else 'https://openapi.alipay.com/gateway.do'
    ALIPAY_NOTIFY_URL = os.getenv('ALIPAY_NOTIFY_URL', 'http://localhost:8086/api/payment/notify')
    ALIPAY_RETURN_URL = os.getenv('ALIPAY_RETURN_URL', 'http://localhost:8086/payment/success')
    ALIPAY_DEBUG = FLASK_ENV == 'development'
    
    # Email
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.qq.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 465))
    EMAIL_FROM = os.getenv('EMAIL_FROM')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
    
    # Face Recognition
    KNOWN_FACES_DIR = BASE_DIR / 'known_faces'
    
    @classmethod
    def init_app(cls, app):
        app.config.from_object(cls)