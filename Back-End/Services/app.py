from flask import Flask, Response, request, jsonify
from flask_cors import CORS  # Add this import
import face_recognition
import cv2
import numpy as np
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import  MIMEMultipart
from email.mime.base import MIMEBase
from email.header import Header
from email import encoders
from datetime import datetime
import base64
import time
from payment_service import AlipayService
import sqlite3
from contextlib import closing
from database import get_db_connection, init_db, save_payment
from camFace import VideoCamera  
from dotenv import load_dotenv
import atexit
from PIL import Image
import io
# from uuid import uuid4
import uuid
import RPi.GPIO as GPIO
import time
import math
# import datetime
import threading
from gpiozero import LED
from time import sleep

app = Flask(__name__)
load_dotenv()

# Configure CORS
CORS(app, resources={
    r"/api/*": {
        # "origins": ["http://localhost:8080", "http://127.0.0.1:8080"],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type"]
    },
    r"/video_feed": {
        "methods": ["GET"]
    },
    r"/capture": {
        "methods": ["GET"]
    }
})

# Configuration
app.config.update({
    'ALIPAY_APP_ID': os.getenv('ALIPAY_APP_ID'),
    'ALIPAY_GATEWAY': 'https://openapi.alipaydev.com/gateway.do' if os.getenv('FLASK_ENV') == 'development' else 'https://openapi.alipay.com/gateway.do',
    'ALIPAY_NOTIFY_URL': os.getenv('ALIPAY_NOTIFY_URL'),
    'ALIPAY_RETURN_URL': os.getenv('ALIPAY_RETURN_URL'),
    'ALIPAY_DEBUG': os.getenv('FLASK_ENV') == 'True',
    # 'APP_PRIVATE_KEY': open('keys/app_private_key.pem').read(),
    # 'ALIPAY_PUBLIC_KEY': open('keys/alipay_public_key.pem').read(),
    'APP_PRIVATE_KEY': open('keys/zfb_private_key.pem').read(),
    'ALIPAY_PUBLIC_KEY': open('keys/zfb_public_key.pem').read(),
    'DATABASE': 'face_payment.db',
    'SMTP_SERVER': 'smtp.qq.com',
    'SMTP_PORT': 587,
    'EMAIL_FROM': os.getenv('EMAIL_FROM'),
    'EMAIL_PASSWORD': os.getenv('EMAIL_AUTH'),
    'DATABASE': os.getenv('DATABASE', 'face_payment.db'),
    'AMOUNT': os.getenv('FEE', '0.1'),
    'LED_PIN_RED': int(os.getenv('LED_PIN_RED', '2')),
    'LED_PIN_GREEN': int(os.getenv('LED_PIN_GREEN', '3')),
    'SERVO_HORI_PIN': int(os.getenv('SERVO_HORI_PIN', '17')),
    'SERVO_VERT_PIN': int(os.getenv('SERVO_VERT_PIN', '27'))
})
# Initialize services
camera = VideoCamera()
alipay_service = AlipayService(app)

# Known faces cache
known_faces = {}
known_face_names = []
last_recognized_user_data = []
last_recognized_frame_user = ""

# GPIO Setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(app.config['SERVO_HORI_PIN'], GPIO.OUT)
GPIO.setup(app.config['SERVO_VERT_PIN'], GPIO.OUT)
pwm_hori = GPIO.PWM(app.config['SERVO_HORI_PIN'], 50)  # 50Hz frequency for horizontal servo
pwm_vert = GPIO.PWM(app.config['SERVO_VERT_PIN'], 50)  # 50Hz frequency for vertical servo
pwm_hori.start(0)
pwm_vert.start(0)

# Movement control variables
is_looping = False
loop_thread = None

auto_face_tracking = False
face_tracking_thread = None
face_detected_during_scan = False

current_angle_hori = 90  # Horizontal servo angle
current_angle_vert = 90  # Vertical servo angle

try:
    LED_AVAILABLE = True
    print("✅ gpiozero库可用，LED控制已启用")
except ImportError:
    print("⚠️ gpiozero不可用，LED控制功能禁用")
    LED_AVAILABLE = False

# 初始化LED
if LED_AVAILABLE:
    try:
        red = LED(app.config['LED_PIN_RED'])
        green = LED(app.config['LED_PIN_GREEN'])
        print(f"✅ LED初始化成功 (GPIO {app.config['LED_PIN_RED']} {app.config['LED_PIN_GREEN']})")
    except Exception as e:
        print(f"❌ LED初始化失败: {e}")
        red = None
        green = None
else:
    red = None
    green = None

def blink_led(color):
    if color == 'red':
        if red:
            # 在新线程中运行，避免阻塞
            threading.Thread(target=lambda: red.blink(on_time=0.3, off_time=0.3, n=10), daemon=True).start()
            print("🔆 LED开始闪烁...")
    elif color == 'green':
        if green:
            # 在新线程中运行，避免阻塞
            threading.Thread(target=lambda: green.blink(on_time=0.3, off_time=0.3, n=10), daemon=True).start()
            print("🔆 LED开始闪烁...")
    else:
        print("💡 LED闪烁模拟 (GPIO不可用)")


# # 设置GPIO模式
# GPIO.setmode(GPIO.BCM)
# GPIO.setup(LED_PIN, GPIO.OUT)
# GPIO.output(LED_PIN, GPIO.LOW)

def gen_frames(camera):
    """Video streaming generator function."""
    while True:
        frame = camera.get_frame()
        if frame is None:
            break
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    """Video streaming route with face detection."""
    print("calling /video_feed")
    def generate():
        while True:
            # Use get_frame_with_faces instead of get_frame
            frame, recognized_user_data = camera.get_frame_with_faces()
            # print(recognized_user_data)
            if (recognized_user_data):
                global last_recognized_user_data, last_recognized_frame_user
                last_recognized_user_data = recognized_user_data
                last_recognized_frame_user = frame
            if frame is None:
                print("No frame available, retrying...")
                time.sleep(0.1)
                continue
                
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.05)  # Control frame rate

    return Response(generate(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/test_face_detection')
def test_face_detection():
    # Get a single frame with face detection
    frame_bytes, recognized_user_data = camera.get_frame_with_faces()
    
    if frame_bytes is None:
        return "Failed to capture frame", 500
        
    # Save to file for debugging
    with open('test_detection.jpg', 'wb') as f:
        f.write(frame_bytes)
        
    return f"""
    <h1>Face Detection Test</h1>
    <p>Face detected: {has_face}</p>
    <img src="/test_detection.jpg" style="max-width: 100%;">
    <p><a href="/video_feed">View video feed</a></p>
    """

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

def load_known_faces():
    """Load known faces from database and train recognizer"""
    faces = []
    labels = []
    
    with closing(sqlite3.connect(app.config['DATABASE'])) as conn:
        cursor = conn.cursor()
        # Get all user images
        cursor.execute('''
            SELECT u.id, u.name, u.email, ui.image_data 
            FROM users u
            JOIN user_images ui ON u.id = ui.user_id
        ''')
        
        for user_id, name, email, image_data in cursor.fetchall():
            try:
                # Decode base64 image
                img_data = base64.b64decode(image_data)
                nparr = np.frombuffer(img_data, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
                
                if img is not None:
                    # Resize to consistent dimensions
                    img = cv2.resize(img, (200, 200))
                    faces.append(img)
                    labels.append(user_id)
                    
                    # Store user info
                    camera.label_to_user[user_id] = {
                        'id': user_id,
                        'name': name,
                        'email': email
                    }
            except Exception as e:
                print(f"Error loading face for {name}: {str(e)}")
    
    if faces:
        camera.train_recognizer(faces, labels)
        print(f"Loaded {len(faces)} face images for recognition")

def detect_faces(image):
    """Detect faces using OpenCV's Haar Cascade"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30)
    )
    return faces

def compare_faces(known_faces, test_image, threshold=0.6):
    """Simple face comparison using OpenCV"""
    # Convert to grayscale
    test_gray = cv2.cvtColor(test_image, cv2.COLOR_BGR2GRAY)
    
    matches = []
    for user_id, known_face in known_faces.items():
        # Resize images to same dimensions
        known_face = cv2.resize(known_face, (test_gray.shape[1], test_gray.shape[0]))
        
        # Calculate similarity (simple histogram comparison)
        hist1 = cv2.calcHist([known_face], [0], None, [256], [0,256])
        hist2 = cv2.calcHist([test_gray], [0], None, [256], [0,256])
        similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        
        matches.append((user_id, similarity))
    
    # Sort by similarity and return best match if above threshold
    matches.sort(key=lambda x: x[1], reverse=True)
    if matches and matches[0][1] > threshold:
        return matches[0]
    return None


def send_email(to_email, name, payment_url=None, image=None):
    subject = "人脸识别通知"
    body = f"您好 {name}，我们已识别到您的人脸。识别时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    if payment_url:
        body += f"\n\n请完成支付: {payment_url}"
    
    # 触发LED闪烁 
    # blink_led('green')    
    
    # Create a MIMEMultipart message with UTF-8 encoding
    msg = MIMEMultipart()
    msg['Subject'] = Header(subject, 'utf-8')  # Encode subject with UTF-8
    msg['From'] = app.config['EMAIL_FROM']
    msg['To'] = to_email
    
    # Attach the text body with UTF-8 encoding
    text_part = MIMEText(body, 'plain', 'utf-8')
    msg.attach(text_part)
    
    if image:
        try:
            image_decode64 = base64.b64decode(image)
            img_part = MIMEBase('application', 'octet-stream')
            img_part.set_payload(image_decode64)
            img_part.add_header('Content-Disposition', 'attachment', filename='face_image.jpg')
            img_part.add_header('Content-ID', '<face_image>')
            img_part.add_header('X-Attachment-Id', 'face_image')
            # Encode the image part properly
            encoders.encode_base64(img_part)
            msg.attach(img_part)
        except Exception as e:
            print(f"Failed to attach image: {e}")
    
    try:
        with smtplib.SMTP(app.config['SMTP_SERVER'], app.config['SMTP_PORT']) as server:
            server.starttls()
            server.login(app.config['EMAIL_FROM'], app.config['EMAIL_PASSWORD'])
            # Convert the message to string with proper encoding
            server.sendmail(app.config['EMAIL_FROM'], [to_email], msg.as_string())
        print(f"Email sent to {to_email}")
        # Flash LED on/off 3 times quickly
        for _ in range(3):
            GPIO.output(LED_PIN, GPIO.HIGH)
            time.sleep(0.3)  # On for 0.3 seconds
            GPIO.output(LED_PIN, GPIO.LOW)
            time.sleep(0.3)  # Off for 0.3 seconds
        # Ensure LED is off at the end
        GPIO.output(LED_PIN, GPIO.LOW)
        return True
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False

def save_payment_record(user_id, amount, out_trade_no, status='pending'):
    with closing(sqlite3.connect(app.config['DATABASE'])) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO payments (user_id, amount, out_trade_no, status)
            VALUES (?, ?, ?, ?)
        ''', (user_id, amount, out_trade_no, status))
        conn.commit()
        return cursor.lastrowid

def update_payment_status(out_trade_no, trade_no, status):
    with closing(sqlite3.connect(app.config['DATABASE'])) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE payments 
            SET status = ?, alipay_trade_no = ?, paid_at = CURRENT_TIMESTAMP
            WHERE out_trade_no = ?
        ''', (status, trade_no, out_trade_no))
        conn.commit()

@app.route('/capture')
def capture():
    """More reliable capture endpoint"""
    max_attempts = 3
    last_exception = None
    
    for attempt in range(max_attempts):
        try:
            frame = camera.get_frame()
            if frame is None:
                print(f"Attempt {attempt + 1}: No frame captured")
                time.sleep(0.5)
                continue
                
            # Verify JPEG header
            if not frame.startswith(b'\xff\xd8'):
                print(f"Attempt {attempt + 1}: Invalid JPEG header")
                continue
                
            # Test decoding
            nparr = np.frombuffer(frame, np.uint8)
            test_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if test_img is None:
                print(f"Attempt {attempt + 1}: Failed to decode image")
                continue
                
            # Save the valid image
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"static/captures/{timestamp}.jpg"
            os.makedirs('static/captures', exist_ok=True)
            
            # Write in one atomic operation
            with open(filename, 'wb') as f:
                f.write(frame)
                
            return jsonify({
                'status': 'success',
                'image_url': f'/static/captures/{timestamp}.jpg'
            })
            
        except Exception as e:
            last_exception = e
            print(f"Capture attempt {attempt + 1} failed: {str(e)}")
            time.sleep(0.5)
    
    return jsonify({
        'status': 'failed',
        'error': 'Could not capture valid image',
        'details': str(last_exception) if last_exception else 'Unknown error'
    }), 500
    
@app.before_request
def verify_capture_dir():
    if request.path.startswith('/capture'):
        capture_dir = 'static/captures'
        if not os.path.exists(capture_dir):
            os.makedirs(capture_dir)
        if not os.access(capture_dir, os.W_OK):
            return jsonify({'error': 'Capture directory not writable'}), 500

# app.py - Add these new endpoints and modify existing ones

@app.route('/api/capture_multiple', methods=['POST'])
def capture_multiple_images():
    """Capture multiple images and return their URLs and image data"""
    try:
        num_images = int(request.json.get('count', 5))
        min_images = min(num_images, 10)  # Max 10 images at once
        
        captured_images = []
        for i in range(min_images):
            frame = camera.get_frame()
            if frame is None:
                continue
                
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"static/captures/{timestamp}_{i}.jpg"
            os.makedirs('static/captures', exist_ok=True)
            
            # Save to file
            with open(filename, 'wb') as f:
                f.write(frame)
            
            # Convert to base64 for the response
            image_base64 = base64.b64encode(frame).decode('utf-8')
            
            captured_images.append({
                'url': f'/static/captures/{timestamp}_{i}.jpg',
                'filename': filename,
                'image': image_base64  # Include base64 encoded image data
            })
            time.sleep(0.5)  # Small delay between captures
            
        return jsonify({
            'status': 'success',
            'images': captured_images
        })
    except Exception as e:
        return jsonify({'status': 'failed', 'error': str(e)})

def safe_imread(image_path):
    """More robust image reading with validation"""
    try:
        # Read as binary first
        with open(image_path, 'rb') as f:
            img_bytes = f.read()
        
        # Verify we have valid image data
        if not img_bytes or len(img_bytes) < 10:  # Minimum size for any image
            print(f"Invalid image data (too small) in {image_path}")
            return None
            
        # Verify JPEG header (if expecting JPEG)
        if not img_bytes.startswith(b'\xff\xd8'):
            print(f"Invalid JPEG header in {image_path}")
            return None
            
        # Convert to numpy array properly
        nparr = np.frombuffer(img_bytes, dtype=np.uint8)
        
        # Decode with OpenCV
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Validate image
        if img is None:
            print(f"OpenCV failed to decode {image_path}")
            return None
            
        if not isinstance(img, np.ndarray) or img.size == 0:
            print(f"Invalid image array in {image_path}")
            return None
            
        return img
    except Exception as e:
        print(f"Error reading {image_path}: {str(e)}")
        return None


@app.route('/api/register', methods=['POST'])
def register_user():
    required_fields = ['images', 'name', 'email']
    if not all(field in request.json for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        name = request.json['name']
        email = request.json['email']
        alipay_user_id = request.json.get('alipay_user_id')
        image_urls = request.json['images']
        
        # Validate at least 3 images are provided
        if len(image_urls) < 3:
            return jsonify({'error': 'At least 3 images are required for registration'}), 400
            
        with closing(get_db_connection(app)) as conn:
            cursor = conn.cursor()
            
            # Check if user already exists
            cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
            if cursor.fetchone():
                return jsonify({'error': 'User with this email already exists'}), 400
                
            # Insert new user
            cursor.execute('''
                INSERT INTO users (name, email, alipay_user_id)
                VALUES (?, ?, ?)
            ''', (name, email, alipay_user_id))
            user_id = cursor.lastrowid
            
            successful_images = 0
            
            for image_url in image_urls:
                try:
                    image_path = image_url.replace('/static/captures/', 'static/captures/')
                    
                    # Read and validate image
                    img = cv2.imread(image_path)
                    if img is None:
                        continue
                        
                    # Convert to grayscale for face detection
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    
                    # Detect face
                    faces = camera.face_cascade.detectMultiScale(
                        gray,
                        scaleFactor=1.1,
                        minNeighbors=5,
                        minSize=(100, 100)  # Larger minimum size for registration
                    )
                    
                    if len(faces) == 0:
                        continue
                        
                    # Use the first face found
                    x, y, w, h = faces[0]
                    face_roi = img[y:y+h, x:x+w]
                    
                    # Encode as JPEG
                    ret, buffer = cv2.imencode('.jpg', face_roi)
                    if not ret:
                        continue
                        
                    image_base64 = base64.b64encode(buffer).decode('utf-8')
                    
                    cursor.execute('''
                        INSERT INTO user_images (user_id, image_data)
                        VALUES (?, ?)
                    ''', (user_id, image_base64))
                    successful_images += 1
                    
                except Exception as e:
                    print(f"Error processing image {image_url}: {str(e)}")
                    continue
            
            conn.commit()
            
            if successful_images < 3:
                # Rollback if we didn't get enough good images
                cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
                conn.commit()
                return jsonify({
                    'error': f'Only {successful_images} valid face images captured. Need at least 3.'
                }), 400
            
            # Train the recognizer with new data
            load_known_faces()
            
            return jsonify({
                'status': 'success',
                'user_id': user_id,
                'name': name,
                'email': email,
                'processed_images': successful_images
            })
            
    except Exception as e:
        print(f"Registration error: {str(e)}")
        return jsonify({'error': 'Registration failed'}), 500

@app.route('/api/recognize', methods=['POST'])
def recognize_face():
    """Improved recognition endpoint with better error handling"""
    try:
        # Validate input
        if not request.json or 'image' not in request.json:
            return jsonify({"error": "No image provided"}), 400
            
        # Decode base64 image
        try:
            image_bytes = base64.b64decode(request.json['image'])
            nparr = np.frombuffer(image_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                return jsonify({"error": "Invalid image data"}), 400
        except Exception as e:
            return jsonify({"error": "Could not decode image"}), 400
            
        # Convert to grayscale for face detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Equalize histogram to improve contrast
        gray = cv2.equalizeHist(gray)
        
        # Detect faces with conservative parameters
        faces = camera.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.2,
            minNeighbors=7,
            minSize=(100, 100),  # Larger minimum size for recognition
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        if len(faces) == 0:
            return jsonify({"error": "No faces detected in the image"}), 400
            
        # Process each detected face
        results = []
        for (x, y, w, h) in faces:
            # Extract face ROI
            face_roi = frame[y:y+h, x:x+w]
            
            # Recognize the face
            user_info, confidence = camera.recognize_face(face_roi)
            
            if user_info:
                # Create payment record
                amount = 10.00
                out_trade_no = f"facepay_{user_info['id']}_{int(time.time())}"
                save_payment_record(user_info['id'], amount, out_trade_no)
                
                # Generate payment link
                payment_link = alipay_service.create_payment(
                    user_id=user_info['id'],
                    amount=amount,
                    subject=f"Face Payment - {user_info['name']}",
                    # out_trade_no=out_trade_no
                )
                
                # Send email
                email_sent = send_email(
                    user_info['email'],
                    user_info['name'],
                    payment_link
                )
                
                results.append({
                    "user": user_info,
                    "confidence": float(100 - confidence),
                    "payment_url": payment_link,
                    "email_sent": email_sent,
                    "timestamp": datetime.now().timestamp() #datetime.now().isoformat()
                })
        
        if results:
            return jsonify({
                "status": "success",
                "results": results
            })
            
        return jsonify({"error": "No recognized faces (confidence too low)"}), 400
        
    except Exception as e:
        print(f"Recognition error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/get_recognition_results', methods=['GET'])
def get_recognition_results():
    print("calling /api/get_recognition_results")
    try:
        print("abc")
        # results, timestamp = camera.get_last_recognition_results()
        global last_recognized_user_data, last_recognized_frame_user
        results = last_recognized_user_data
        frame = last_recognized_frame_user
        print("def")
        # print(results)
        if not results:
            return jsonify({"success": False, "error": "No recent recognitions"}), 404
        print(results)
        # Process results to include payment links
        processed_results = []
        amount = app.config['AMOUNT']
        for result in results:
            user_info = result['user']
            # 在recognize_face和get_recognition_results端点中修改支付部分：
            # payment_result = alipay_service.create_payment(
            #     user_id=user_info['id'],
            #     amount=amount,
            #     subject=f"Face Payment - {user_info['name']}",
            # )
            # payment_token = str(uuid.uuid4())
            # payment_id = save_payment_record(
            #     user_info['id'], 
            #     amount, 
            #     f"facepay_{user_info['id']}_{int(time.time())}",
            #     payment_token=payment_token
            # )
            
            payment_token = str(uuid.uuid4())
            payment_id = save_payment(
                user_info['id'], 
                amount, 
                f"facepay_{user_info['id']}_{int(time.time())}",
                payment_token=payment_token
            )
            print(amount)
            # payment_link = payment_result['payment_url']
            # out_trade_no = payment_result['out_trade_no']

            # 保存支付记录
            # save_payment_record(user_info['id'], amount, out_trade_no)

            
            # # Create payment record
            # amount = 10.00
            # out_trade_no = f"facepay_{user_info['id']}_{int(time.time())}"
            # save_payment_record(user_info['id'], amount, out_trade_no)
            
            # Generate payment link
            # payment_link = alipay_service.create_payment(
            #     user_id=user_info['id'],
            #     amount=amount,
            #     subject=f"Face Payment - {user_info['name']}",
            #     # out_trade_no=out_trade_no
            # )
            print(type(frame))
            processed_results.append({
                "user": user_info,
                "confidence": result['confidence'],
                # "payment_url": payment_link,
                "payment_id": payment_id,
                "payment_token": payment_token,
                "amount": amount,
                "timestamp": result['timestamp'], #datetime.fromtimestamp(result['timestamp']).isoformat()
                "frame": base64.b64encode(frame).decode('utf-8') if frame else None
            })
        print("aab")
        print(processed_results)
        last_recognized_user_data = []
        last_recognized_frame_user = ""
        return jsonify({
            "success": True,
            "results": processed_results
        })
        
    except Exception as e:
        print(f"Error in get_recognition_results: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@app.route('/api/send_recognition_email', methods=['POST'])
def send_recognition_email():
    try:
        results = request.json
        if not results:
            return jsonify({"success": False, "error": "No faces to recognize"}), 400
            
        recent_results = [
            r for r in results['data']
            if time.time() - r['timestamp'] < 5
        ]
        
        if not recent_results:
            return jsonify({"success": False, "error": "No recent recognitions"}), 400
        
        # Get frontend URL from Origin header or Referer header
        frontend_url = request.headers.get('Origin') or \
                      request.headers.get('Referer') or \
                      request.host_url
        
        # Ensure it ends with a slash
        frontend_url = frontend_url.rstrip('/') + '/'
        
        email_results = []
        for result in recent_results:
            user_info = result['user']
            
            # Generate payment page URL with token using frontend URL
            payment_url = f"{frontend_url}payments?payment_id={result['payment_id']}&token={result['payment_token']}"
            
            email_sent = send_email(
                user_info['email'],
                user_info['name'],
                payment_url,
                result['frame']
            )
            
            email_results.append({
                "user": user_info,
                "email_sent": email_sent,
                "payment_url": payment_url
            })
            blink_led('green')
            
        return jsonify({
            "success": True,
            "results": email_results
        })
        
    except Exception as e:
        print(f"Error in send_recognition_email: {str(e)}")
        blink_led('red')
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500        

        
@app.teardown_appcontext
def teardown_camera(exception):
    if camera.vs is not None:
        camera.vs.release()

# @app.teardown_appcontext
# def shutdown(exception=None):
#     cleanup()

# # Ensure proper cleanup
# def cleanup():
#     if hasattr(camera, 'vs') and camera.vs is not None:
#         camera.vs.release()
#     print("Application exiting - camera released")
#     global servo_active
#     with servo_lock:
#         servo_active = False
#     if servo_thread and servo_thread.is_alive():
#         servo_thread.join()
#     pwm.stop()
#     GPIO.cleanup()
#     print("Servo resources cleaned up")

@app.route('/api/payment/notify', methods=['POST'])
def payment_notify():
    try:
        data = request.form.to_dict()
        if not alipay_service.verify_notification(data):
            return 'failure', 400
        
        # Process payment
        out_trade_no = data['out_trade_no']
        trade_no = data['trade_no']
        amount = float(data['total_amount'])
        status = data['trade_status']
        
        # Update database
        update_payment_status(out_trade_no, trade_no, status)
        
        return 'success'
    except Exception as e:
        app.logger.error(f"Payment notification error: {str(e)}")
        return 'failure', 500

@app.route('/api/payment/status/<order_id>', methods=['GET'])
def payment_status(order_id):
    try:
        with closing(sqlite3.connect(app.config['DATABASE'])) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.status, p.amount, u.name 
                FROM payments p
                JOIN users u ON p.user_id = u.id
                WHERE p.out_trade_no = ?
            ''', (order_id,))
            result = cursor.fetchone()
            
            if result:
                return jsonify({
                    'status': result[0],
                    'amount': result[1],
                    'name': result[2]
                })
            return jsonify({'error': 'Order not found'}), 404
    except Exception as e:
        app.logger.error(f"Payment status error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/payment/details', methods=['GET'])
def payment_details():
    try:
        payment_id = request.args.get('payment_id')
        token = request.args.get('token')
        
        if not payment_id or not token:
            return jsonify({'success': False, 'error': 'Missing parameters'}), 400
            
        with closing(get_db_connection(app)) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.*, u.name, u.email 
                FROM payments p
                JOIN users u ON p.user_id = u.id
                WHERE p.id = ? AND p.payment_token = ?
            ''', (payment_id, token))
            
            payment = cursor.fetchone()
            
            if not payment:
                return jsonify({'success': False, 'error': 'Payment not found'}), 404
                
            # Convert to dict
            payment_data = {
                'id': payment[0],
                'user_id': payment[1],
                'amount': payment[2],
                'status': payment[3],
                'alipay_trade_no': payment[4],
                'out_trade_no': payment[5],
                'created_at': payment[6],
                'paid_at': payment[7],
                'token': payment[8],
                'user': {
                    'name': payment[9],
                    'email': payment[10]
                }
            }
            
            return jsonify({
                'success': True,
                'payment': payment_data
            })
            
    except Exception as e:
        app.logger.error(f"Payment details error: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/payment/initiate', methods=['POST'])
def payment_initiate():
    try:
        data = request.json
        payment_id = data.get('payment_id')
        token = data.get('token')
        
        if not payment_id or not token:
            return jsonify({'success': False, 'error': 'Missing parameters'}), 400
            
        with closing(get_db_connection(app)) as conn:
            cursor = conn.cursor()
            
            # Verify payment exists and is pending
            cursor.execute('''
                SELECT p.amount, u.name, u.id, p.out_trade_no
                FROM payments p
                JOIN users u ON p.user_id = u.id
                WHERE p.id = ? AND p.payment_token = ? AND p.status = 'pending'
            ''', (payment_id, token))
            
            payment = cursor.fetchone()
            
            if not payment:
                return jsonify({'success': False, 'error': 'Invalid payment'}), 400
                
            amount, name, user_id, out_trade_no = payment
            
            # Update payment status directly to 'completed'
            cursor.execute('''
                UPDATE payments 
                SET status = 'completed', 
                    paid_at = CURRENT_TIMESTAMP
                WHERE id = ? AND payment_token = ?
            ''', (payment_id, token))
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'Payment completed successfully',
                'payment_id': payment_id,
                'amount': amount,
                'user': name
            })
            
    except Exception as e:
        app.logger.error(f"Payment initiation error: {str(e)}")
        return jsonify({
            'success': False, 
            'error': 'Payment processing failed',
            'details': str(e)
        }), 500
        
def angle_to_duty(angle):
    """Convert angle to duty cycle (2%-12%)"""
    return angle / 18 + 2

def quintic_easing(t):
    """Quintic easing function for ultra-smooth motion"""
    return t * t * t * (t * (t * 6 - 15) + 10)

def smooth_move_hori(start, end, duration=2.0):
    """Smooth horizontal movement with advanced easing"""
    global current_angle_hori
    steps = max(30, int(duration * 30))  # Dynamic step calculation
    delay = duration / steps
    
    for i in range(steps + 1):
        t = i / steps
        eased_t = quintic_easing(t)
        current_angle_hori = start + (end - start) * eased_t
        pwm_hori.ChangeDutyCycle(angle_to_duty(current_angle_hori))
        time.sleep(delay)

def smooth_move_vert(start, end, duration=2.0):
    """Smooth vertical movement with advanced easing"""
    global current_angle_vert
    steps = max(30, int(duration * 30))  # Dynamic step calculation
    delay = duration / steps
    
    for i in range(steps + 1):
        t = i / steps
        eased_t = quintic_easing(t)
        current_angle_vert = start + (end - start) * eased_t
        pwm_vert.ChangeDutyCycle(angle_to_duty(current_angle_vert))
        time.sleep(delay)

def set_angle_hori(angle, duration=0.5):
    """Move horizontal servo directly to specified angle with optional duration"""
    global current_angle_hori
    if duration <= 0:
        # Immediate movement
        current_angle_hori = angle
        pwm_hori.ChangeDutyCycle(angle_to_duty(angle))
    else:
        # Smooth movement
        smooth_move_hori(current_angle_hori, angle, duration)
    
    # After movement, keep the servo at the target angle
    time.sleep(0.1)  # Small delay to ensure movement completes
    pwm_hori.ChangeDutyCycle(0)  # This stops sending pulses but keeps position

def set_angle_vert(angle, duration=0.5):
    """Move vertical servo directly to specified angle with optional duration"""
    global current_angle_vert
    if duration <= 0:
        # Immediate movement
        current_angle_vert = angle
        pwm_vert.ChangeDutyCycle(angle_to_duty(angle))
    else:
        # Smooth movement
        smooth_move_vert(current_angle_vert, angle, duration)
    
    # After movement, keep the servo at the target angle
    time.sleep(0.1)  # Small delay to ensure movement completes
    pwm_vert.ChangeDutyCycle(0)  # This stops sending pulses but keeps position

def continuous_loop(duration=2.0):
    """Continuous back-and-forth movement for horizontal servo"""
    global is_looping
    while is_looping:
        smooth_move_hori(0, 180, duration/2)
        smooth_move_hori(180, 0, duration/2)

# API Endpoints
@app.route('/api/servo/start_loop', methods=['POST'])
def start_loop():
    global is_looping, loop_thread
    
    try:
        if is_looping:
            return jsonify({"status": "error", "message": "Loop already running"}), 400
            
        duration = request.json.get('duration', 2.0)
        is_looping = True
        loop_thread = threading.Thread(target=continuous_loop, args=(duration,))
        loop_thread.start()
        
        return jsonify({
            "status": "success",
            "message": f"Started continuous loop with {duration}s cycle",
            "duration": duration
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/servo/stop_loop', methods=['POST'])
def stop_loop():
    global is_looping, loop_thread, current_angle_hori
    
    try:
        if not is_looping:
            return jsonify({"status": "error", "message": "No loop running"}), 400
            
        is_looping = False
        if loop_thread:
            loop_thread.join()
        
        # After stopping the loop, set the servo to its current angle position
        # and stop sending pulses to prevent jitter
        pwm_hori.ChangeDutyCycle(angle_to_duty(current_angle_hori))
        time.sleep(0.1)  # Small delay to ensure position is set
        pwm_hori.ChangeDutyCycle(0)  # Stop sending pulses but maintain position
        
        return jsonify({
            "status": "success",
            "message": "Stopped continuous loop and servo position stabilized",
            "final_angle": current_angle_hori
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/servo/move', methods=['POST'])
def move_servo():
    try:
        if is_looping:
            return jsonify({"error": "Cannot move while looping is active"}), 400
            
        data = request.get_json()
        start_angle = data.get('start_angle', 0)
        end_angle = data.get('end_angle', 180)
        duration = data.get('duration', 2.0)
        servo_type = data.get('servo_type', 'horizontal')  # 'horizontal' or 'vertical'
        
        if not (0 <= start_angle <= 180) or not (0 <= end_angle <= 180):
            return jsonify({"error": "Angles must be between 0 and 180 degrees"}), 400
        
        if servo_type == 'horizontal':
            smooth_move_hori(start_angle, end_angle, duration)
        elif servo_type == 'vertical':
            print("vertical req")
            smooth_move_vert(start_angle, end_angle, duration)
        else:
            return jsonify({"error": "Invalid servo_type. Use 'horizontal' or 'vertical'"}), 400
            
        return jsonify({
            "status": "success",
            "message": f"{servo_type.capitalize()} servo moved from {start_angle}° to {end_angle}°",
            "duration": duration
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/servo/set_angle', methods=['POST'])
def servo_set_angle():
    try:
        if is_looping:
            return jsonify({"error": "Cannot set angle while looping is active"}), 400
            
        data = request.get_json()
        angle = data.get('angle', 90)
        duration = data.get('duration', 0.5)  # Default 0.5s movement
        servo_type = data.get('servo_type', 'horizontal')  # 'horizontal' or 'vertical'
        
        if not (0 <= angle <= 180):
            return jsonify({"error": "Angle must be between 0 and 180 degrees"}), 400
        
        if servo_type == 'horizontal':
            set_angle_hori(angle, duration)
            current_angle = current_angle_hori
        elif servo_type == 'vertical':
            print("vertical req")
            set_angle_vert(angle, duration)
            current_angle = current_angle_vert
        else:
            return jsonify({"error": "Invalid servo_type. Use 'horizontal' or 'vertical'"}), 400
            
        return jsonify({
            "status": "success",
            "message": f"{servo_type.capitalize()} servo set to {angle}°",
            "current_angle": current_angle,
            "servo_type": servo_type,
            "duration": duration
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/servo/stop', methods=['POST'])
def stop_servo():
    global is_looping
    try:
        is_looping = False
        pwm_hori.ChangeDutyCycle(0)  # Stop sending pulses to horizontal servo
        pwm_vert.ChangeDutyCycle(0)  # Stop sending pulses to vertical servo
        return jsonify({"status": "success", "message": "Both servos stopped"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/servo/autodetectface', methods=['POST'])
def auto_detect_face():
    """Auto servo control: scan environment then focus on detected face"""
    global auto_face_tracking, face_tracking_thread, is_looping
    
    try:
        data = request.get_json() or {}
        action = data.get('action', 'start')  # 'start' or 'stop'
        
        if action == 'start':
            if auto_face_tracking:
                return jsonify({
                    "status": "error", 
                    "message": "Face tracking already active"
                }), 400
            
            # 停止任何现有的循环
            is_looping = False
            if loop_thread and loop_thread.is_alive():
                loop_thread.join()
            
            auto_face_tracking = True
            face_tracking_thread = threading.Thread(target=auto_face_detection_with_scan)
            face_tracking_thread.daemon = True
            face_tracking_thread.start()
            
            return jsonify({
                "status": "success",
                "message": "Started environment scan for face detection (8 seconds)"
            })
            
        elif action == 'stop':
            if not auto_face_tracking:
                return jsonify({
                    "status": "error", 
                    "message": "Face tracking not active"
                }), 400
            
            auto_face_tracking = False
            is_looping = False  # 同时停止扫描循环
            
            if face_tracking_thread and face_tracking_thread.is_alive():
                face_tracking_thread.join(timeout=3)
            
            # 停止舵机
            pwm_hori.ChangeDutyCycle(0)
            pwm_vert.ChangeDutyCycle(0)
            
            return jsonify({
                "status": "success",
                "message": "Stopped face detection and tracking"
            })
            
        else:
            return jsonify({"error": "Invalid action. Use 'start' or 'stop'"}), 400
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def auto_face_detection_with_scan():
    """执行环境扫描然后聚焦到检测到的人脸"""
    global auto_face_tracking, face_detected_during_scan, is_looping, current_angle_hori
    
    print("🔍 开始环境扫描模式 (8秒扫描 0-180°)")
    
    # 重置检测标志
    face_detected_during_scan = False
    
    # 第一阶段：8秒环境扫描
    scan_success = perform_environment_scan()
    
    if not auto_face_tracking:
        return
    
    if scan_success:
        print("✅ 扫描期间检测到人脸，开始精确跟踪模式")
        # 第二阶段：精确人脸跟踪
        precise_face_tracking()
    else:
        print("⚠️ 8秒扫描完成，未检测到人脸")
        # 可以选择重复扫描或停止
        auto_face_tracking = False

def perform_environment_scan():
    """执行8秒的环境扫描 (0-180度)"""
    global auto_face_tracking, face_detected_during_scan, is_looping, current_angle_hori
    
    # 启动8秒的连续扫描循环
    is_looping = True
    scan_duration = 8.0  # 8秒总扫描时间
    
    # 使用独立的扫描线程
    scan_thread = threading.Thread(target=continuous_scan_with_detection, args=(scan_duration,))
    scan_thread.daemon = True
    scan_thread.start()
    
    # 等待扫描完成或检测到人脸
    scan_thread.join()
    
    return face_detected_during_scan

def continuous_scan_with_detection(duration=8.0):
    """带人脸检测的连续扫描"""
    global is_looping, face_detected_during_scan, current_angle_hori, auto_face_tracking
    
    start_time = time.time()
    cycle_time = duration / 2  # 每个单向扫描的时间
    
    print(f"🔄 开始连续扫描: {duration}秒 (0° ↔ 180°)")
    
    while is_looping and auto_face_tracking and (time.time() - start_time < duration):
        # 检查是否检测到人脸
        if check_for_face_during_scan():
            print("👤 扫描中检测到人脸，停止扫描！")
            face_detected_during_scan = True
            is_looping = False
            break
        
        # 执行一个扫描周期 (0° → 180° → 0°)
        remaining_time = duration - (time.time() - start_time)
        if remaining_time <= 0:
            break
            
        # 第一半：0° → 180°
        half_cycle_time = min(cycle_time, remaining_time / 2)
        smooth_move_with_detection(0, 180, half_cycle_time)
        
        if face_detected_during_scan or not is_looping or not auto_face_tracking:
            break
            
        # 第二半：180° → 0°
        remaining_time = duration - (time.time() - start_time)
        if remaining_time <= 0:
            break
            
        half_cycle_time = min(cycle_time, remaining_time / 2)
        smooth_move_with_detection(180, 0, half_cycle_time)
        
        if face_detected_during_scan or not is_looping or not auto_face_tracking:
            break
    
    is_looping = False
    print(f"🏁 扫描完成 (耗时: {time.time() - start_time:.1f}秒)")

def smooth_move_with_detection(start_angle, end_angle, duration):
    """带人脸检测的平滑移动"""
    global current_angle_hori, face_detected_during_scan, is_looping, auto_face_tracking
    
    steps = max(20, int(duration * 10))  # 每秒10步
    delay = duration / steps
    
    for i in range(steps + 1):
        if not is_looping or not auto_face_tracking or face_detected_during_scan:
            break
            
        t = i / steps
        eased_t = quintic_easing(t)
        current_angle_hori = start_angle + (end_angle - start_angle) * eased_t
        pwm_hori.ChangeDutyCycle(angle_to_duty(current_angle_hori))
        
        # 每隔几步检查一次人脸检测
        if i % 3 == 0:  # 每3步检查一次
            if check_for_face_during_scan():
                print(f"👤 在角度 {current_angle:.1f}° 检测到人脸！")
                face_detected_during_scan = True
                break
        
        time.sleep(delay)

def check_for_face_during_scan():
    """扫描期间检查是否有人脸"""
    try:
        frame_bytes, recognized_users = camera.get_frame_with_faces()
        
        if frame_bytes is None:
            return False
        
        # 解码图像
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return False
        
        # 检测人脸
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = camera.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(60, 60)
        )
        
        return len(faces) > 0
        
    except Exception as e:
        print(f"人脸检测错误: {str(e)}")
        return False

def precise_face_tracking():
    """精确的人脸跟踪模式"""
    global auto_face_tracking, current_angle
    
    print("🎯 进入精确人脸跟踪模式")
    
    # 稳定跟踪计数器
    stable_frames = 0
    recognition_attempts = 0
    max_recognition_attempts = 10
    
    while auto_face_tracking:
        try:
            frame_bytes, recognized_users = camera.get_frame_with_faces()
            
            if frame_bytes is None:
                time.sleep(0.1)
                continue
            
            # 解码图像
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                time.sleep(0.1)
                continue
            
            # 检测人脸位置
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = camera.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(80, 80)
            )
            
            if len(faces) > 0:
                # 选择最大的人脸
                largest_face = max(faces, key=lambda face: face[2] * face[3])
                x, y, w, h = largest_face
                
                # 计算人脸中心和偏移
                face_center_x = x + w // 2
                frame_center_x = frame.shape[1] // 2
                offset_pixels = face_center_x - frame_center_x
                
                # 计算角度偏移 (调整系数)
                angle_offset = (offset_pixels / frame_center_x) * 25  # 减小调整幅度
                
                print(f"📍 人脸跟踪: 偏移={offset_pixels}px, 角度调整={angle_offset:.1f}°")
                
                # 如果偏移较大，调整舵机
                if abs(angle_offset) > 3:  # 更小的死区
                    target_angle = current_angle_hori + angle_offset
                    target_angle = max(0, min(180, target_angle))
                    
                    print(f"🎯 调整舵机: {current_angle_hori:.1f}° → {target_angle:.1f}°")
                    set_angle_hori(target_angle, 0.2)  # 更快的响应
                    stable_frames = 0
                else:
                    stable_frames += 1
                    print(f"✓ 人脸居中，稳定帧数: {stable_frames}")
                
                # 检查识别结果
                if recognized_users and len(recognized_users) > 0:
                    print(f"🎉 成功识别用户: {[user['user']['name'] for user in recognized_users]}")
                    
                    # 识别成功，保持位置一段时间后停止
                    print("✅ 识别完成，保持位置3秒后停止")
                    time.sleep(3)
                    auto_face_tracking = False
                    break
                else:
                    recognition_attempts += 1
                    if recognition_attempts >= max_recognition_attempts:
                        print("⏱️ 达到最大识别尝试次数，继续跟踪...")
                        recognition_attempts = 0
                
                time.sleep(0.1)  # 快速响应
                
            else:
                print("❌ 丢失人脸目标，重新扫描...")
                stable_frames = 0
                
                # 短暂的重新扫描
                quick_rescan_success = quick_rescan_for_face()
                if not quick_rescan_success:
                    print("🔍 未找到人脸，停止跟踪")
                    auto_face_tracking = False
                    break
                    
        except Exception as e:
            print(f"❌ 精确跟踪错误: {str(e)}")
            time.sleep(0.5)
    
    print("🛑 精确人脸跟踪结束")

def quick_rescan_for_face():
    """快速重新扫描寻找丢失的人脸"""
    global current_angle, auto_face_tracking
    
    # 在当前位置周围快速扫描 ±30度
    search_range = 30
    search_angles = [
        current_angle,
        current_angle - 15,
        current_angle + 15,
        current_angle - 30,
        current_angle + 30
    ]
    
    for angle in search_angles:
        if not auto_face_tracking:
            return False
            
        # 限制角度范围
        angle = max(0, min(180, angle))
        
        print(f"🔍 快速扫描角度: {angle:.1f}°")
        set_angle_hori(angle, 0.3)
        time.sleep(0.3)
        
        # 检查是否找到人脸
        if check_for_face_during_scan():
            print(f"✅ 在角度 {angle:.1f}° 重新找到人脸")
            return True
    
    return False

# 更新状态查询端点
@app.route('/api/servo/status', methods=['GET'])
def servo_status():
    """获取舵机当前状态"""
    return jsonify({
        "current_angle_hori": current_angle_hori,
        "current_angle_vert": current_angle_vert,
        "current_angle": current_angle_hori,  # For backward compatibility
        "is_looping": is_looping,
        "auto_face_tracking": auto_face_tracking,
        "face_detected_during_scan": face_detected_during_scan,
        "face_tracking_active": face_tracking_thread and face_tracking_thread.is_alive() if face_tracking_thread else False
    })


# 修改cleanup函数以包含面部跟踪清理
def cleanup():
    global auto_face_tracking, is_looping
    print("🧹 Cleaning up resources...")
    
    # 停止面部跟踪
    auto_face_tracking = False
    if face_tracking_thread and face_tracking_thread.is_alive():
        face_tracking_thread.join(timeout=2)
    
    # 停止舵机循环
    is_looping = False
    if loop_thread and loop_thread.is_alive():
        loop_thread.join(timeout=2)
    
    # 清理GPIO
    pwm_hori.stop()
    pwm_vert.stop()
    GPIO.cleanup()
    
    print("✅ Cleanup completed")

if __name__ == '__main__':
    try:
        init_db(app)
        load_known_faces()
        os.makedirs('static/captures', exist_ok=True)
        app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
    except KeyboardInterrupt:
        print("\nStopping server...")
        is_looping = False
    finally:
        cleanup()