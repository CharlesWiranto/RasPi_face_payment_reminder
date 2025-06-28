import os
import cv2
import numpy as np
from camFace import VideoCamera
from database import get_db_connection
import base64
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def train_face_recognizer():
    """Train the face recognizer with images from database"""
    faces = []
    labels = []
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Get all user images
            cursor.execute('''
                SELECT u.id, ui.image_data 
                FROM users u
                JOIN user_images ui ON u.id = ui.user_id
            ''')
            
            for user_id, image_data in cursor.fetchall():
                try:
                    # Decode base64 image
                    img_data = base64.b64decode(image_data)
                    nparr = np.frombuffer(img_data, np.uint8)
                    img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
                    
                    if img is None:
                        logger.warning(f"Could not decode image for user {user_id}")
                        continue
                        
                    # Preprocess the image
                    img = preprocess_face_image(img)
                    
                    # Detect face (ensure we're using the face region)
                    face_cascade = cv2.CascadeClassifier(
                        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                    )
                    detected_faces = face_cascade.detectMultiScale(
                        img,
                        scaleFactor=1.1,
                        minNeighbors=5,
                        minSize=(30, 30)
                    )
                    if len(detected_faces) == 0:
                        logger.warning(f"No face detected in image for user {user_id}")
                        continue
                        
                    x, y, w, h = detected_faces[0]
                    face_roi = img[y:y+h, x:x+w]
                    
                    # Resize to consistent dimensions
                    face_roi = cv2.resize(face_roi, (200, 200))
                    
                    faces.append(face_roi)
                    labels.append(user_id)
                    
                except Exception as e:
                    logger.error(f"Error processing image for user {user_id}: {str(e)}")
                    continue
        
        if len(faces) == 0:
            logger.error("No valid face images found for training")
            return False
            
        # Get the camera instance and train recognizer
        camera = VideoCamera()
        camera.train_recognizer(faces, labels)
        
        logger.info(f"Successfully trained with {len(faces)} face images")
        return True
        
    except Exception as e:
        logger.error(f"Training failed: {str(e)}")
        return False

def preprocess_face_image(image):
    """Apply preprocessing to face images"""
    # Equalize histogram to improve contrast
    image = cv2.equalizeHist(image)
    
    # Apply Gaussian blur to reduce noise
    image = cv2.GaussianBlur(image, (3, 3), 0)
    
    return image

if __name__ == '__main__':
    train_face_recognizer()