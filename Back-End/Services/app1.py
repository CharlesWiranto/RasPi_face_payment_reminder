from flask import Flask, Response, request, jsonify
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
from database import get_db_connection, init_db
from camFace import VideoCamera  
from dotenv import load_dotenv
import atexit

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
    'APP_PRIVATE_KEY': open('keys/app_private_key.pem').read(),
    'ALIPAY_PUBLIC_KEY': open('keys/alipay_public_key.pem').read(),
    'DATABASE': 'face_payment.db',
    'SMTP_SERVER': 'smtp.qq.com',
    'SMTP_PORT': 587,
    'EMAIL_FROM': os.getenv('EMAIL_FROM'),
    'EMAIL_PASSWORD': os.getenv('EMAIL_AUTH'),
    'DATABASE': os.getenv('DATABASE', 'face_payment.db')
})
# Initialize services
camera = VideoCamera()
alipay_service = AlipayService(app)

# Known faces cache
known_faces = {}
known_face_names = []

def gen_frames(camera):
    """Video streaming generator function."""
    while True:
        frame = camera.get_frame()
        if frame is None:
            break
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

# @app.route('/video_feed')
# def video_feed():
#     """Video streaming route. Put this in the src attribute of an img tag."""
#     return Response(gen_frames(camera),
#                     mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/video_feed')
def video_feed():
    """Video streaming route with face detection."""
    def generate():
        while True:
            # Use get_frame_with_faces instead of get_frame
            frame, has_face = camera.get_frame_with_faces()
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
    frame_bytes, has_face = camera.get_frame_with_faces()
    
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

# @app.route('/video_feed')
# def video_feed():
#     """Video streaming route that handles disconnections gracefully."""
#     def generate():
#         while True:
#             frame = camera.get_frame()
#             if frame is None:
#                 print("No frame available, retrying...")
#                 time.sleep(0.1)
#                 continue
                
#             yield (b'--frame\r\n'
#                    b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
#             time.sleep(0.05)  # Control frame rate

#     return Response(generate(),
#                    mimetype='multipart/x-mixed-replace; boundary=frame')

# @app.route('/capture')
# def capture():
#     """Capture route that saves the image and returns its URL."""
#     try:
#         # Get frame from camera
#         frame = camera.get_frame()
#         if frame is None:
#             return jsonify({'status': 'failed', 'error': 'Could not capture image'})
        
#         # Generate filename
#         timestamp = time.strftime("%Y%m%d-%H%M%S")
#         filename = f"static/captures/{timestamp}.jpg"
#         os.makedirs('static/captures', exist_ok=True)
        
#         # Save the image
#         with open(filename, 'wb') as f:
#             f.write(frame)
        
#         return jsonify({
#             'status': 'success',
#             'image_url': f'/static/captures/{timestamp}.jpg'
#         })
#     except Exception as e:
#         return jsonify({'status': 'failed', 'error': str(e)})

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

def load_known_faces():
    with closing(sqlite3.connect(app.config['DATABASE'])) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, email, face_encoding FROM users WHERE face_encoding IS NOT NULL')
        for user_id, name, email, face_encoding in cursor.fetchall():
            try:
                encoding = np.frombuffer(base64.b64decode(face_encoding), dtype=np.float64)
                known_faces[user_id] = encoding
                known_face_names.append({'id': user_id, 'name': name, 'email': email})
                print(f"Loaded {name}'s face encoding")
            except Exception as e:
                print(f"Error loading face encoding for {name}: {str(e)}")

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
        with smtplib.SMTP(app.config['SMTP_SERVER'], app.config['SMTP_PORT']) as server:
            server.starttls()
            server.login(app.config['EMAIL_FROM'], app.config['EMAIL_PASSWORD'])
            server.sendmail(app.config['EMAIL_FROM'], [to_email], msg.as_string())
        print(f"Email sent to {to_email}")
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

# @app.route('/api/register', methods=['POST'])
# def register_user():
#     required_fields = ['image', 'name', 'email']
#     if not all(field in request.json for field in required_fields):
#         return jsonify({'error': 'Missing required fields'}), 400
    
#     try:
#         # Save face encoding and user info to database
#         image_data = request.json['image']
#         name = request.json['name']
#         email = request.json['email']
#         alipay_user_id = request.json.get('alipay_user_id')
        
#         # Decode and process image
#         image_bytes = base64.b64decode(image_data)
#         nparr = np.frombuffer(image_bytes, np.uint8)
#         image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
#         rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
#         # print(rgb_image)
#         # Get face encoding
#         face_encodings = face_recognition.face_encodings(rgb_image)
#         # print(face_encodings)
#         if not face_encodings:
#             return jsonify({'error': 'No faces detected in image'}), 400
            
#         # Convert encoding to storable format
#         encoding_bytes = base64.b64encode(face_encodings[0].tobytes()).decode('utf-8')
#         print(encoding_bytes)
#         print(name, email, alipay_user_id)
#         # Save to database
#         with closing(get_db_connection()) as conn:
#             cursor = conn.cursor()
#             cursor.execute('''
#                 INSERT INTO users (name, email, face_encoding, alipay_user_id)
#                 VALUES (?, ?, ?, ?)
#             ''', (name, email, encoding_bytes, alipay_user_id))
#             user_id = cursor.lastrowid
#             conn.commit()
        
#         print(user_id, name, email)
        
#         return jsonify({
#             'status': 'success',
#             'user_id': user_id,
#             'name': name,
#             'email': email
#         })
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

# @app.route('/capture')
# def capture():
#     """Capture route that saves multiple images and returns their URLs."""
#     try:
#         captured_images = []
#         for i in range(5):  # Capture 5 images
#             # Get frame from camera
#             frame = camera.get_frame()
#             if frame is None:
#                 return jsonify({'status': 'failed', 'error': 'Could not capture image'})
            
#             # Generate filename
#             timestamp = time.strftime("%Y%m%d-%H%M%S")
#             filename = f"static/captures/{timestamp}_{i}.jpg"
#             os.makedirs('static/captures', exist_ok=True)
            
#             # Save the image
#             with open(filename, 'wb') as f:
#                 f.write(frame)
            
#             captured_images.append(f'/static/captures/{timestamp}_{i}.jpg')
#             time.sleep(0.5)  # Small delay between captures
        
#         return jsonify({
#             'status': 'success',
#             'image_urls': captured_images
#         })
#     except Exception as e:
#         return jsonify({'status': 'failed', 'error': str(e)})

@app.route('/capture')
def capture():
    """Capture route that ensures valid face images"""
    max_attempts = 5
    attempt = 0
    
    while attempt < max_attempts:
        try:
            frame = camera.get_frame()
            if frame is None:
                attempt += 1
                time.sleep(0.5)
                continue
            
            # Verify frame is valid JPEG data
            if not frame.startswith(b'\xff\xd8'):
                attempt += 1
                continue
            
            # Convert to numpy array for face detection
            nparr = np.frombuffer(frame, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                attempt += 1
                continue
                
            # Convert to RGB for face recognition
            rgb_image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Verify face detection
            face_locations = face_recognition.face_locations(rgb_image)
            if not face_locations:
                attempt += 1
                print(f"Attempt {attempt}: No face detected")
                time.sleep(0.5)
                continue
                
            # If we get here, we have a valid face image
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"static/captures/{timestamp}.jpg"
            os.makedirs('static/captures', exist_ok=True)
            
            # Atomic write operation
            temp_filename = f"{filename}.tmp"
            with open(temp_filename, 'wb') as f:
                f.write(frame)
                f.flush()
                os.fsync(f.fileno())
            
            if os.path.getsize(temp_filename) == len(frame):
                os.rename(temp_filename, filename)
                return jsonify({
                    'status': 'success',
                    'image_url': f'/static/captures/{timestamp}.jpg',
                    'attempts': attempt + 1
                })
            
        except Exception as e:
            attempt += 1
            print(f"Capture attempt {attempt} failed: {str(e)}")
    
    return jsonify({
        'status': 'failed',
        'error': f'Could not capture valid face image after {max_attempts} attempts'
    }), 400

@app.route('/api/capture_multiple', methods=['POST'])
def capture_multiple_images():
    """Capture multiple valid face images"""
    try:
        num_images = int(request.json.get('count', 5))
        min_images = min(num_images, 10)  # Max 10 images at once
        max_attempts_per_image = 5
        captured_images = []
        
        for i in range(min_images):
            attempt = 0
            captured = False
            
            while attempt < max_attempts_per_image and not captured:
                frame = camera.get_frame()
                if frame is None:
                    attempt += 1
                    time.sleep(0.5)
                    continue
                
                # Verify JPEG header
                if not frame.startswith(b'\xff\xd8'):
                    attempt += 1
                    continue
                
                # Process for face detection
                nparr = np.frombuffer(frame, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if img is None:
                    attempt += 1
                    continue
                    
                rgb_image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                face_locations = face_recognition.face_locations(rgb_image)
                
                if not face_locations:
                    attempt += 1
                    print(f"Image {i+1} attempt {attempt}: No face detected")
                    time.sleep(0.5)
                    continue
                
                # Valid face image found
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                filename = f"static/captures/{timestamp}_{i}.jpg"
                os.makedirs('static/captures', exist_ok=True)
                
                # Save image
                with open(filename, 'wb') as f:
                    f.write(frame)
                
                # Add to results
                captured_images.append({
                    'url': f'/static/captures/{timestamp}_{i}.jpg',
                    'filename': filename,
                    'image': base64.b64encode(frame).decode('utf-8'),
                    'attempts': attempt + 1
                })
                captured = True
                time.sleep(0.3)  # Small delay between captures
            
            if not captured:
                return jsonify({
                    'status': 'failed',
                    'error': f'Could not capture valid face image {i+1} after {max_attempts_per_image} attempts',
                    'captured': captured_images
                }), 400
        
        return jsonify({
            'status': 'success',
            'images': captured_images,
            'message': f'Successfully captured {len(captured_images)} valid face images'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'failed',
            'error': str(e)
        }), 500

# @app.route('/capture')
# def capture():
#     """Capture route that properly saves JPEG images"""
#     try:
#         frame = camera.get_frame()
#         if frame is None:
#             return jsonify({'status': 'failed', 'error': 'Could not capture image'})
        
#         # Verify frame is valid JPEG data
#         if not frame.startswith(b'\xff\xd8'):
#             return jsonify({'status': 'failed', 'error': 'Invalid JPEG data'})
        
#         timestamp = time.strftime("%Y%m%d-%H%M%S")
#         filename = f"static/captures/{timestamp}.jpg"
#         os.makedirs('static/captures', exist_ok=True)
        
#         # Atomic write operation
#         temp_filename = f"{filename}.tmp"
#         with open(temp_filename, 'wb') as f:
#             f.write(frame)
#             f.flush()
#             os.fsync(f.fileno())
        
#         # Verify the written file
#         if os.path.getsize(temp_filename) == len(frame):
#             os.rename(temp_filename, filename)
#         else:
#             os.remove(temp_filename)
#             return jsonify({'status': 'failed', 'error': 'Failed to save image'})
        
#         return jsonify({
#             'status': 'success',
#             'image_url': f'/static/captures/{timestamp}.jpg'
#         })
#     except Exception as e:
#         return jsonify({'status': 'failed', 'error': str(e)})

# @app.before_request
# def verify_capture_dir():
#     if request.path.startswith('/capture'):
#         capture_dir = 'static/captures'
#         if not os.path.exists(capture_dir):
#             os.makedirs(capture_dir)
#         if not os.access(capture_dir, os.W_OK):
#             return jsonify({'error': 'Capture directory not writable'}), 500

# # app.py - Add these new endpoints and modify existing ones

# @app.route('/api/capture_multiple', methods=['POST'])
# def capture_multiple_images():
#     """Capture multiple images and return their URLs and image data"""
#     try:
#         num_images = int(request.json.get('count', 5))
#         min_images = min(num_images, 10)  # Max 10 images at once
        
#         captured_images = []
#         for i in range(min_images):
#             frame = camera.get_frame()
#             if frame is None:
#                 continue
                
#             timestamp = time.strftime("%Y%m%d-%H%M%S")
#             filename = f"static/captures/{timestamp}_{i}.jpg"
#             os.makedirs('static/captures', exist_ok=True)
            
#             # Save to file
#             with open(filename, 'wb') as f:
#                 f.write(frame)
            
#             # Convert to base64 for the response
#             image_base64 = base64.b64encode(frame).decode('utf-8')
            
#             captured_images.append({
#                 'url': f'/static/captures/{timestamp}_{i}.jpg',
#                 'filename': filename,
#                 'image': image_base64  # Include base64 encoded image data
#             })
#             time.sleep(0.5)  # Small delay between captures
            
#         return jsonify({
#             'status': 'success',
#             'images': captured_images
#         })
#     except Exception as e:
#         return jsonify({'status': 'failed', 'error': str(e)})

# @app.route('/api/capture_multiple', methods=['POST'])
# def capture_multiple_images():
#     """Capture multiple images and return their URLs"""
#     try:
#         num_images = int(request.json.get('count', 5))
#         min_images = min(num_images, 10)  # Max 10 images at once
        
#         captured_images = []
#         for i in range(min_images):
#             frame = camera.get_frame()
#             if frame is None:
#                 continue
                
#             timestamp = time.strftime("%Y%m%d-%H%M%S")
#             filename = f"static/captures/{timestamp}_{i}.jpg"
#             os.makedirs('static/captures', exist_ok=True)
            
#             with open(filename, 'wb') as f:
#                 f.write(frame)
            
#             captured_images.append({
#                 'url': f'/static/captures/{timestamp}_{i}.jpg',
#                 'filename': filename
#             })
#             time.sleep(0.5)  # Small delay between captures
            
#         return jsonify({
#             'status': 'success',
#             'images': captured_images
#         })
#     except Exception as e:
#         return jsonify({'status': 'failed', 'error': str(e)})

# @app.route('/api/register', methods=['POST'])
# def register_user():
#     required_fields = ['images', 'name', 'email']
#     if not all(field in request.json for field in required_fields):
#         return jsonify({'error': 'Missing required fields'}), 400
    
#     try:
#         # Get user info
#         name = request.json['name']
#         email = request.json['email']
#         alipay_user_id = request.json.get('alipay_user_id')
#         image_urls = request.json['images']
        
#         print(f"Using database at: {app.config['DATABASE']}")
#         print(f"Absolute path: {os.path.abspath(app.config['DATABASE'])}")
        
#         # First create user record
#         with closing(get_db_connection(app)) as conn:
#             cursor = conn.cursor()
#             cursor.execute('''
#                 INSERT INTO users (name, email, alipay_user_id)
#                 VALUES (?, ?, ?)
#             ''', (name, email, alipay_user_id))
#             user_id = cursor.lastrowid
            
#             # Process each image
#             for image_url in image_urls:
#                 try:
#                     print(image_url)
#                     # Read the image file
#                     image_path = image_url.replace('/static/captures/', 'static/captures/')
                    
#                     # Verify image exists
#                     if not os.path.exists(image_path):
#                         print(f"Image not found: {image_path}")
#                         continue
                        
#                     # Read image with OpenCV
#                     image = cv2.imread(image_path)
#                     if image is None:
#                         print(f"Failed to decode image: {image_path}")
#                         continue
                        
#                     # Convert to RGB (dlib expects RGB)
#                     rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    
#                     # Verify image dimensions
#                     if rgb_image.size == 0:
#                         print(f"Empty image: {image_path}")
#                         continue
                        
#                     # Get face locations first
#                     face_locations = face_recognition.face_locations(rgb_image)
#                     if not face_locations:
#                         print(f"No faces detected in: {image_path}")
#                         continue
                        
#                     # Get face encodings
#                     face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
#                     if not face_encodings:
#                         print(f"Could not extract encodings from: {image_path}")
#                         continue
                        
#                     # Convert encoding to storable format
#                     encoding_bytes = base64.b64encode(face_encodings[0].tobytes()).decode('utf-8')
                    
#                     # Store image and encoding
#                     with open(image_path, 'rb') as f:
#                         image_data = base64.b64encode(f.read()).decode('utf-8')
#                     print(image_data)
#                     print(encoding_bytes)
#                     cursor.execute('''
#                         INSERT INTO user_images (user_id, image_data, face_encoding)
#                         VALUES (?, ?, ?)
#                     ''', (user_id, image_data, encoding_bytes))
                    
#                 except Exception as e:
#                     print(f"Error processing image {image_path}: {str(e)}")
#                     continue
            
#             conn.commit()
            
#         return jsonify({
#             'status': 'success',
#             'user_id': user_id,
#             'name': name,
#             'email': email,
#             'images_count': len(image_urls)
#         })
        
#     except Exception as e:
#         print(f"Error in register_user: {str(e)}")
#         return jsonify({'error': "Registration failed. Please try again."}), 500
def safe_imread(image_path):
    """Robust image reading with validation"""
    try:
        # Read as binary first
        with open(image_path, 'rb') as f:
            img_data = f.read()
            
        # Verify JPEG header
        if not img_data.startswith(b'\xff\xd8'):
            print(f"Invalid JPEG header in {image_path}")
            return None
            
        # Convert to numpy array
        nparr = np.frombuffer(img_data, np.uint8)
        
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
        # Get user info
        name = request.json['name']
        email = request.json['email']
        alipay_user_id = request.json.get('alipay_user_id')
        image_urls = request.json['images']
        
        # First create user record
        with closing(get_db_connection(app)) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (name, email, alipay_user_id)
                VALUES (?, ?, ?)
            ''', (name, email, alipay_user_id))
            user_id = cursor.lastrowid
            
            successful_encodings = 0
            
            # Process each image
            for image_url in image_urls:
                try:
                    image_path = image_url.replace('/static/captures/', 'static/captures/')
                    
                    # Verify file exists and has content
                    if not os.path.exists(image_path):
                        print(f"Image not found: {image_path}")
                        continue
                        
                    if os.path.getsize(image_path) == 0:
                        print(f"Empty image file: {image_path}")
                        continue
                    
                    # Robust image reading
                    image = safe_imread(image_path)
                    if image is None:
                        continue
                        
                    # Convert to RGB
                    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    
                    # Verify image properties
                    print(f"Processing image: {image_path}")
                    print(f"Shape: {rgb_image.shape}, Type: {rgb_image.dtype}")
                    
                    # Face detection
                    face_locations = face_recognition.face_locations(rgb_image)
                    if not face_locations:
                        print(f"No faces detected in {image_path}")
                        continue
                        
                    # Get encodings
                    face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
                    if not face_encodings:
                        print(f"Couldn't extract encodings from {image_path}")
                        continue
                        
                    # Store data
                    encoding_bytes = base64.b64encode(face_encodings[0].tobytes()).decode('utf-8')
                    with open(image_path, 'rb') as f:
                        image_data = base64.b64encode(f.read()).decode('utf-8')
                    
                    cursor.execute('''
                        INSERT INTO user_images (user_id, image_data, face_encoding)
                        VALUES (?, ?, ?)
                    ''', (user_id, image_data, encoding_bytes))
                    successful_encodings += 1
                    
                    print(f"Successfully processed {image_path}")
                    
                except Exception as e:
                    print(f"Error processing image {image_path}: {str(e)}")
                    continue
            
            conn.commit()
            
            if successful_encodings == 0:
                return jsonify({
                    'status': 'failed',
                    'error': 'Could not process any valid images'
                }), 400
            
            return jsonify({
                'status': 'success',
                'user_id': user_id,
                'name': name,
                'email': email,
                'processed_images': successful_encodings
            })
            
    except Exception as e:
        print(f"Registration error: {str(e)}")
        return jsonify({'error': 'Registration failed'}), 500

# @app.route('/api/register', methods=['POST'])
# def register_user():
#     required_fields = ['images', 'name', 'email']
#     if not all(field in request.json for field in required_fields):
#         return jsonify({'error': 'Missing required fields'}), 400
    
#     try:
#         # Save user info to database
#         name = request.json['name']
#         email = request.json['email']
#         alipay_user_id = request.json.get('alipay_user_id')
#         image_urls = request.json.get('image_urls', [])
        
#         with closing(get_db_connection()) as conn:
#             cursor = conn.cursor()
#             cursor.execute('''
#                 INSERT INTO users (name, email, alipay_user_id)
#                 VALUES (?, ?, ?)
#             ''', (name, email, alipay_user_id))
#             user_id = cursor.lastrowid
            
#             # Process each image
#             for i, image_data in enumerate(request.json['images']):
#                 # Decode and process image
#                 image_bytes = base64.b64decode(image_data)
#                 nparr = np.frombuffer(image_bytes, np.uint8)
#                 image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
#                 rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                
#                 # Get face encoding
#                 face_encodings = face_recognition.face_encodings(rgb_image)
#                 if not face_encodings:
#                     continue  # Skip if no face detected
                    
#                 # Convert encoding to storable format
#                 encoding_bytes = base64.b64encode(face_encodings[0].tobytes()).decode('utf-8')
                
#                 # Save face encoding with optional image URL
#                 image_url = image_urls[i] if i < len(image_urls) else None
#                 cursor.execute('''
#                     INSERT INTO face_encodings (user_id, face_encoding, image_url)
#                     VALUES (?, ?, ?)
#                 ''', (user_id, encoding_bytes, image_url))
            
#             conn.commit()
        
#         return jsonify({
#             'status': 'success',
#             'user_id': user_id,
#             'name': name,
#             'email': email
#         })
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

@app.route('/api/recognize', methods=['POST'])
def recognize_face():
    if 'image' not in request.json:
        return jsonify({"error": "No image provided"}), 400
    
    try:
        # Decode base64 image
        image_data = request.json['image']
        image_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Convert to RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        face_locations = face_recognition.face_locations(rgb_image)
        face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
        
        if not face_encodings:
            print("No Face detected")
            return jsonify({"error": "No faces detected"}), 400
        print(face_encodings)
        # Compare with known faces
        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(
                list(known_faces.values()), 
                face_encoding,
                tolerance=0.6
            )
            print(matches)
            if True in matches:
                print("match")
                matched_index = matches.index(True)
                user_info = known_face_names[matched_index]
                user_id = user_info['id']
                
                # Calculate confidence
                face_distances = face_recognition.face_distance(
                    list(known_faces.values()), 
                    face_encoding
                )
                confidence = (1 - face_distances[matched_index]) * 100
                
                # Create payment
                amount = 10.00  # Example amount
                payment_link = alipay_service.create_payment(
                    user_id=user_id,
                    amount=amount,
                    subject=f"Face Recognition Payment - {user_info['name']}"
                )
                
                # Save payment record
                out_trade_no = f"facepay_{user_id}_{int(time.time())}"
                save_payment_record(user_id, amount, out_trade_no)
                
                # Send notification email
                email_sent = send_email(
                    user_info['email'],
                    user_info['name'],
                    payment_link
                )
                
                return jsonify({
                    "status": "success",
                    "user": {
                        "id": user_id,
                        "name": user_info['name'],
                        "email": user_info['email']
                    },
                    "confidence": float(confidence),
                    "payment_url": payment_link,
                    "email_sent": email_sent,
                    "timestamp": datetime.now().isoformat()
                })
        
        return jsonify({"error": "Face not recognized"}), 400
        
    except Exception as e:
        app.logger.error(f"Recognition error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.teardown_appcontext
def teardown_camera(exception):
    if camera.vs is not None:
        camera.vs.release()
        
# Ensure proper cleanup
def cleanup():
    if hasattr(camera, 'vs') and camera.vs is not None:
        camera.vs.release()
    print("Application exiting - camera released")


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

if __name__ == '__main__':
    init_db(app)
    load_known_faces()
    os.makedirs('static/captures', exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)