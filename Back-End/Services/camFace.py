from datetime import datetime
import threading
import cv2
import time
import numpy as np
from threading import Lock

class VideoCamera(object):
    _instance = None
    _lock = Lock()
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(VideoCamera, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, flip=False, cam_source=0):
        if not self._initialized:
            self.flip = flip
            self.cam_source = cam_source
            self.max_retries = 10
            self.vs = None
            self._initialized = True
            self._frame_lock = Lock()
            self.last_recognition_time = 0
            self.min_recognition_interval = 5  # seconds

            # Load face detector
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            if self.face_cascade.empty():
                raise RuntimeError("Could not load face detection model")
                
            # Initialize face recognizer
            # self.face_recognizer = cv2.face.EigenFaceRecognizer_create()  # Faster than LBPH
            # Or better, use DNN-based face recognition
            # self.face_net = cv2.dnn.readNetFromCaffe("deploy.prototxt", "res10_300x300_ssd_iter_140000.caffemodel")
            self.face_recognizer = cv2.face.LBPHFaceRecognizer_create()
            self.known_face_labels = []
            self.label_to_user = {}  # Maps label IDs to user info
            self.last_recognition_results = []
            self.last_recognition_time = 0
            self.recognition_lock = Lock()
            self._initialized = True
            
            self.initialize_camera()
            
            self.frame_buffer = None
            self.frame_available = threading.Event()
            self.processing_frame = False
            self.capture_thread = threading.Thread(target=self._capture_frames, daemon=True)
            self.capture_thread.start()
    
    def _capture_frames(self):
        """Dedicated thread for continuous frame capture"""
        while True:
            try:
                ret, frame = self.vs.read()
                if ret:
                    with self._frame_lock:
                        self.frame_buffer = frame
                        self.frame_available.set()
                time.sleep(0.033)  # ~30 FPS
            except Exception as e:
                print(f"Capture thread error: {str(e)}")
                time.sleep(1)
    
    def initialize_camera(self):
        if self.vs is not None:
            self.vs.release()
            time.sleep(2)  # Give time for camera to release
        
        for attempt in range(1, self.max_retries + 1):
            print(f"Camera attempt {attempt}/{self.max_retries}")
            
            try:
                # Try different backends in order of preference
                for backend in [cv2.CAP_V4L2, cv2.CAP_DSHOW, cv2.CAP_ANY]:
                    print(f"Trying backend: {backend}")
                    self.vs = cv2.VideoCapture(self.cam_source, backend)
                    
                    if self.vs.isOpened():
                        # Configure camera settings
                        self.vs.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        self.vs.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        self.vs.set(cv2.CAP_PROP_FPS, 30)
                        self.vs.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        
                        # Warm up camera
                        for _ in range(5):
                            self.vs.read()
                        
                        print(f"✅ Camera initialized with backend {backend}")
                        return
                    
                    print(f"⚠️ Failed with backend {backend}")
                    if self.vs is not None:
                        self.vs.release()
                
                print("⚠️ All backends failed")
                
            except Exception as e:
                print(f"Camera init error: {str(e)}")
                if self.vs is not None:
                    self.vs.release()
            
            time.sleep(2)  # Wait before retrying
        
        raise RuntimeError("Could not initialize camera after multiple attempts")

    def detect_faces(self, frame):
        try:
            # Convert to grayscale for face detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect faces with optimized parameters
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30),
                flags=cv2.CASCADE_SCALE_IMAGE
            )
            
            # Draw rectangles around faces
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                # Add text label
                cv2.putText(frame, 'Face', (x, y-10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,255,0), 2)
            
            return frame, len(faces) > 0
        except Exception as e:
            print(f"Face detection error: {str(e)}")
            return frame, False

    def get_frame_with_faces(self):
        """Get frame with face detection and recognition"""
        with self._frame_lock:
            if self.vs is None:
                self.initialize_camera()
                return None, False
                
            try:
                ret, frame = self.vs.read()
                if not ret:
                    print("❌ Failed to read frame from camera")
                    self.release()
                    self.initialize_camera()
                    return None, False

                frame = self.flip_if_needed(frame)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # Detect faces
                faces = self.face_cascade.detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=5,
                    minSize=(30, 30)
                )
                
                recognized_users = []
                
                for (x, y, w, h) in faces:
                    # Draw rectangle around face
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    
                    # Recognize face
                    face_roi = gray[y:y+h, x:x+w]
                    label, confidence = self.face_recognizer.predict(face_roi)
                    
                    # If confidence is good, get user info
                    if confidence < 80:  # Threshold for recognition
                        user_info = self.label_to_user.get(label)
                        if user_info:
                            # Draw name and confidence
                            text = f"{user_info['name']} ({100 - confidence:.1f}%)"
                            cv2.putText(frame, text, (x, y-10), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                            
                            # recognized_users.append(user_info)
                            recognized_users.append({
                                'user': user_info,
                                'confidence': float(100 - confidence),
                                'position': (x, y, w, h),
                                'timestamp': time.time()
                            })
                # print(recognized_users)
                # Encode the frame
                ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                
                return (jpeg.tobytes() if ret else None, recognized_users)
                
            except Exception as e:
                print(f"⚠️ Error in get_frame_with_faces: {str(e)}")
                self.release()
                return None, False
            
    def can_perform_recognition(self):
        now = time.time()
        return (now - self.last_recognition_time) >= self.min_recognition_interval

    def update_recognition_time(self):
        self.last_recognition_time = time.time()
        
    
    def update_recognition_results(self, results):
        with self.recognition_lock:
            self.last_recognition_results = results
            self.last_recognition_time = time.time()

    def get_last_recognition_results(self):
        with self.recognition_lock:
            return self.last_recognition_results.copy(), self.last_recognition_time
    # def get_frame_with_faces(self):
    #     with self._frame_lock:
    #         if self.vs is None:
    #             self.initialize_camera()
    #             return None, False
                
    #         try:
    #             ret, frame = self.vs.read()
    #             if not ret:
    #                 print("❌ Failed to read frame from camera")
    #                 self.release()
    #                 self.initialize_camera()
    #                 return None, False

    #             frame = self.flip_if_needed(frame)
                
    #             # Perform face detection
    #             frame_with_faces, face_detected = self.detect_faces(frame)
                
    #             # Encode the frame
    #             ret, jpeg = cv2.imencode('.jpg', frame_with_faces, 
    #                                    [cv2.IMWRITE_JPEG_QUALITY, 85])
                
    #             return (jpeg.tobytes() if ret else None, face_detected)
                
    #         except Exception as e:
    #             print(f"⚠️ Error in get_frame_with_faces: {str(e)}")
    #             self.release()
    #             return None, False
            
    def __del__(self):
        self.release()
    
    def release(self):
        if self.vs is not None:
            self.vs.release()
            self.vs = None
        print("Camera resources released")

    def flip_if_needed(self, frame):
        if self.flip:
            return cv2.flip(frame, 1)  # Horizontal flip
        return frame

    # def get_frame(self):
    #     with self._frame_lock:
    #         if self.vs is None:
    #             self.initialize_camera()
    #             return None
                
    #         try:
    #             ret, frame = self.vs.read()
    #             if not ret:
    #                 print("❌ Failed to read frame from camera")
    #                 self.release()
    #                 self.initialize_camera()
    #                 return None

    #             frame = self.flip_if_needed(frame)
    #             ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    #             return jpeg.tobytes() if ret else None
    #         except Exception as e:
    #             print(f"⚠️ Error getting frame: {str(e)}")
    #             self.release()
    #             return None
    def get_frame(self):
        with self._frame_lock:
            if self.vs is None:
                self.initialize_camera()
                return None
                
            try:
                # Try to read frame multiple times
                for _ in range(3):
                    ret, frame = self.vs.read()
                    if ret:
                        break
                    time.sleep(0.1)
                
                if not ret:
                    print("❌ Failed to read frame from camera after retries")
                    self.release()
                    self.initialize_camera()
                    return None

                frame = self.flip_if_needed(frame)
                
                # Add timestamp to frame
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cv2.putText(frame, timestamp, (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                ret, jpeg = cv2.imencode('.jpg', frame, [
                    cv2.IMWRITE_JPEG_QUALITY, 85,
                    cv2.IMWRITE_JPEG_PROGRESSIVE, 1,
                    cv2.IMWRITE_JPEG_OPTIMIZE, 1
                ])
                
                return jpeg.tobytes() if ret else None
            except Exception as e:
                print(f"⚠️ Error getting frame: {str(e)}")
                self.release()
                return None

    def get_object(self):
        found_objects = False
        with self._frame_lock:
            if self.vs is None:
                self.initialize_camera()
                return None, found_objects
                
            try:
                ret, frame = self.vs.read()
                if not ret:
                    print("❌ Failed to read frame from camera")
                    self.release()
                    self.initialize_camera()
                    return None, found_objects

                frame = self.flip_if_needed(frame).copy()
                
                if self.face_classifier is not None:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    objects = self.face_classifier.detectMultiScale(
                        gray,
                        scaleFactor=1.1,
                        minNeighbors=5,
                        minSize=(30, 30),
                        flags=cv2.CASCADE_SCALE_IMAGE
                    )

                    if len(objects) > 0:
                        found_objects = True
                        # Draw rectangles around detected faces
                        for (x, y, w, h) in objects:
                            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

                ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                return (jpeg.tobytes() if ret else None, found_objects)
                
            except Exception as e:
                print(f"⚠️ Error detecting objects: {str(e)}")
                self.release()
                return None, found_objects
    def train_recognizer(self, faces, labels):
        """Train the face recognizer with new data"""
        with self._frame_lock:
            try:
                if len(faces) > 0:
                    self.face_recognizer.train(faces, np.array(labels))
                    self.known_face_labels = labels
                    print(f"Recognizer trained with {len(faces)} faces for {len(labels)} users")
            except Exception as e:
                print(f"Training error: {str(e)}")

    def preprocess_face(self, face_image):
        """Preprocess face image before recognition"""
        # Convert to grayscale if not already
        if len(face_image.shape) > 2:
            face_image = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY)
        
        # Equalize histogram
        face_image = cv2.equalizeHist(face_image)
        
        # Apply Gaussian blur
        face_image = cv2.GaussianBlur(face_image, (3, 3), 0)
        
        # Resize to consistent dimensions
        face_image = cv2.resize(face_image, (200, 200))
        
        return face_image

    def recognize_face(self, face_image):
        """Improved face recognition with preprocessing"""
        try:
            # Preprocess the face image
            processed_face = self.preprocess_face(face_image)
            
            # Predict with the recognizer
            label, confidence = self.face_recognizer.predict(processed_face)
            
            # Confidence threshold (lower is better for LBPH)
            if confidence < 70:  # More strict threshold
                return self.label_to_user.get(label), confidence
            return None, confidence
        except Exception as e:
            print(f"Recognition error: {str(e)}")
            return None, 0

    def recognize_faces_dnn(self, frame):
        """Use DNN for faster face detection"""
        (h, w) = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(
            cv2.resize(frame, (300, 300)), 1.0, (300, 300),
            (104.0, 177.0, 123.0), swapRB=False, crop=False)
        
        self.face_net.setInput(blob)
        detections = self.face_net.forward()
        
        faces = []
        for i in range(0, detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            if confidence > 0.7:  # Confidence threshold
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (x, y, x2, y2) = box.astype("int")
                faces.append((x, y, x2-x, y2-y))
        
        return faces

    # def recognize_face(self, face_image):
    #     """Recognize a face from an image"""
    #     with self._frame_lock:
    #         try:
    #             # Convert to grayscale
    #             gray = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY)
                
    #             # Resize to consistent size
    #             gray = cv2.resize(gray, (200, 200))
                
    #             # Predict
    #             label, confidence = self.face_recognizer.predict(gray)
                
    #             # Confidence threshold (lower is better for LBPH)
    #             if confidence < 80:  # Adjust this threshold as needed
    #                 return self.label_to_user.get(label), confidence
    #             return None, confidence
    #         except Exception as e:
    #             print(f"Recognition error: {str(e)}")
    #             return None, 0
