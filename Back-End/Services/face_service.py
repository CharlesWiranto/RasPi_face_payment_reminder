import face_recognition
import cv2
import numpy as np
import base64
from database import get_db_connection
from config import Config

class FaceService:
    def __init__(self):
        self.known_faces = {}
        self.known_face_info = []
        self.load_known_faces()

    def load_known_faces(self):
        """Load known faces from database"""
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, name, email, face_encoding FROM users WHERE face_encoding IS NOT NULL')
            for user_id, name, email, face_encoding in cursor.fetchall():
                try:
                    encoding = np.frombuffer(base64.b64decode(face_encoding), dtype=np.float64)
                    self.known_faces[user_id] = encoding
                    self.known_face_info.append({
                        'id': user_id,
                        'name': name,
                        'email': email
                    })
                except Exception as e:
                    print(f"Error loading face for {name}: {str(e)}")

    def recognize_face(self, image_data):
        """Recognize face from base64 image data"""
        try:
            # Decode image
            image_bytes = base64.b64decode(image_data)
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Convert to RGB
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Detect faces
            face_locations = face_recognition.face_locations(rgb_image)
            face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
            
            if not face_encodings:
                return None
            
            # Compare with known faces
            for face_encoding in face_encodings:
                matches = face_recognition.compare_faces(
                    list(self.known_faces.values()), 
                    face_encoding,
                    tolerance=0.6
                )
                
                if True in matches:
                    matched_index = matches.index(True)
                    user_info = self.known_face_info[matched_index]
                    
                    # Calculate confidence
                    face_distances = face_recognition.face_distance(
                        list(self.known_faces.values()), 
                        face_encoding
                    )
                    confidence = (1 - face_distances[matched_index]) * 100
                    
                    return {
                        **user_info,
                        'confidence': confidence
                    }
            
            return None
        except Exception as e:
            print(f"Face recognition error: {str(e)}")
            return None

    def register_face(self, image_data, name, email):
        """Register a new face"""
        try:
            # Decode and process image
            image_bytes = base64.b64decode(image_data)
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Get face encoding
            face_encodings = face_recognition.face_encodings(rgb_image)
            if not face_encodings:
                return None
                
            # Convert encoding to storable format
            encoding_bytes = base64.b64encode(face_encodings[0].tobytes()).decode('utf-8')
            
            # Save to database
            user_id = save_user(name, email, encoding_bytes)
            
            # Update cache
            self.known_faces[user_id] = face_encodings[0]
            self.known_face_info.append({
                'id': user_id,
                'name': name,
                'email': email
            })
            
            return user_id
        except Exception as e:
            print(f"Face registration error: {str(e)}")
            return None