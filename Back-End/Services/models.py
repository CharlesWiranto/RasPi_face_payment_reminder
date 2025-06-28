from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='CNY')
    status = db.Column(db.String(20), default='pending')  # pending, paid, failed
    alipay_trade_no = db.Column(db.String(64))  # Alipay transaction ID
    out_trade_no = db.Column(db.String(64), unique=True)  # Your order number
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime)
    
    user = db.relationship('User', backref='payments')

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    face_encoding = db.Column(db.Text)  # Store face encodings
    alipay_user_id = db.Column(db.String(64))  # Optional: store Alipay user ID
    created_at = db.Column(db.DateTime, default=datetime.utcnow)