import sqlite3
from contextlib import closing
from pathlib import Path
from config import Config
import os
# def init_db():
#     """Initialize the database with required tables"""
#     db_path = Path(Config.DATABASE_URI.replace('sqlite:///', ''))
#     db_path.parent.mkdir(parents=True, exist_ok=True)
    
#     with closing(get_db_connection()) as conn:
#         with conn:
#             conn.execute('''
#                 CREATE TABLE IF NOT EXISTS users (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     name TEXT NOT NULL,
#                     email TEXT NOT NULL UNIQUE,
#                     face_encoding TEXT,
#                     alipay_user_id TEXT,
#                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#                 )
#             ''')
#             conn.execute('''
#                 CREATE TABLE IF NOT EXISTS payments (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     user_id INTEGER NOT NULL,
#                     amount REAL NOT NULL,
#                     status TEXT DEFAULT 'pending',
#                     alipay_trade_no TEXT,
#                     out_trade_no TEXT UNIQUE,
#                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#                     paid_at TIMESTAMP,
#                     FOREIGN KEY(user_id) REFERENCES users(id)
#                 )
#             ''')

def init_db(app=None):
    # with closing(sqlite3.connect(os.getenv('DATABASE'))) as conn:
    conn = get_db_connection(app)
    with conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                face_encoding TEXT,
                alipay_user_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                alipay_trade_no TEXT,
                out_trade_no TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                paid_at TIMESTAMP,
                payment_token TEXT UNIQUE,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS user_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                image_data TEXT NOT NULL,
                face_encoding TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
    conn.close()
        
# def get_db_connection():
#     """Get a database connection"""
#     return sqlite3.connect(Config.DATABASE_URI.replace('sqlite:///', ''))

def get_db_connection(app=None):
    """Get a database connection using app configuration"""
    if app is not None:
        # Use the app's configured database path
        return sqlite3.connect(app.config['DATABASE'])
    else:
        # Fallback for cases where app isn't available (like during init)
        db_path = os.getenv('DATABASE', 'face_payment.db')
        return sqlite3.connect(db_path)

def save_user(name, email, face_encoding=None, alipay_user_id=None):
    """Save a new user to the database"""
    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (name, email, face_encoding, alipay_user_id)
            VALUES (?, ?, ?, ?)
        ''', (name, email, face_encoding, alipay_user_id))
        conn.commit()
        return cursor.lastrowid

def get_user_by_id(user_id):
    """Get user by ID"""
    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        return cursor.fetchone()

# def save_payment(user_id, amount, out_trade_no, status='pending'):
#     """Save payment record"""
#     with closing(get_db_connection()) as conn:
#         cursor = conn.cursor()
#         cursor.execute('''
#             INSERT INTO payments (user_id, amount, out_trade_no, status)
#             VALUES (?, ?, ?, ?)
#         ''', (user_id, amount, out_trade_no, status))
#         conn.commit()
#         return cursor.lastrowid
    
def save_payment(user_id, amount, out_trade_no, status='pending', payment_token=None):
    """Save payment record"""
    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        if payment_token:
            cursor.execute('''
                INSERT INTO payments (user_id, amount, out_trade_no, status, payment_token)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, amount, out_trade_no, status, payment_token))
        else:
            cursor.execute('''
                INSERT INTO payments (user_id, amount, out_trade_no, status)
                VALUES (?, ?, ?, ?)
            ''', (user_id, amount, out_trade_no, status))
        conn.commit()
        return cursor.lastrowid