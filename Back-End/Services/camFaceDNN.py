import cv2
import time
import numpy as np
from threading import Lock, Thread
import os

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
            self.max_retries = 5
            self.vs = None
            self._initialized = True
            self._frame_lock = Lock()
            self.last_recognition_time = 0
            self.min_recognition_interval = 3  # seconds
            self.frame_buffer = None
            self.capture_thread = None
            self.running = False

            # Face detection
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            
            # Face recognition
            self.face_recognizer = cv2.face.LBPHFaceRecognizer_create()
            self.known_face_labels = []
            self.label_to_user = {}
            
            # DNN model initialization
            self.model_path = os.path.join(os.path.dirname(__file__), "models")
            self.dnn_net = None
            self.initialize_dnn_model()
            
            self.initialize_camera()
            self.start_capture_thread()
            
            self._initialized = True
    
    def flip_if_needed(self, frame):
        """Flip frame horizontally if configured to do so"""
        return cv2.flip(frame, 1) if self.flip else frame
    
    def train_recognizer(self, faces, labels):
        """Train the face recognizer with new data"""
        with self._frame_lock:
            try:
                if len(faces) > 0:
                    self.face_recognizer.train(faces, np.array(labels))
                    self.known_face_labels = labels
                    print(f"Recognizer trained with {len(faces)} faces")
            except Exception as e:
                print(f"Training error: {str(e)}")
    
    def initialize_dnn_model(self):
        """Initialize DNN model if files exist"""
        prototxt = os.path.join(self.model_path, "deploy.prototxt")
        caffemodel = os.path.join(self.model_path, "res10_300x300_ssd_iter_140000.caffemodel")
        
        if os.path.exists(prototxt) and os.path.exists(caffemodel):
            try:
                self.dnn_net = cv2.dnn.readNetFromCaffe(prototxt, caffemodel)
                print("DNN model loaded successfully")
            except Exception as e:
                print(f"Failed to load DNN model: {str(e)}")
                self.dnn_net = None
    
    def start_capture_thread(self):
        """Start a dedicated thread for frame capture"""
        if self.capture_thread is None:
            self.running = True
            self.capture_thread = Thread(target=self._capture_frames, daemon=True)
            self.capture_thread.start()
    
    def _capture_frames(self):
        """Continuous frame capture in background thread"""
        while self.running:
            try:
                ret, frame = self.vs.read()
                if ret:
                    with self._frame_lock:
                        self.frame_buffer = self.flip_if_needed(frame)
                else:
                    time.sleep(0.1)
            except Exception as e:
                print(f"Capture thread error: {str(e)}")
                time.sleep(1)
    
    def initialize_camera(self):
        """Initialize camera with optimized settings for Pi"""
        if self.vs is not None:
            self.vs.release()
            time.sleep(1)
        
        # Try simpler initialization for Pi
        self.vs = cv2.VideoCapture(self.cam_source)
        if not self.vs.isOpened():
            raise RuntimeError("Could not initialize camera")
            
        # Optimized settings for Raspberry Pi
        self.vs.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        self.vs.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        self.vs.set(cv2.CAP_PROP_FPS, 15)
        self.vs.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # Warm up camera
        for _ in range(5):
            self.vs.read()
        print("Camera initialized successfully")
    
    def get_frame_with_faces(self):
        """Get frame with face detection (optimized for Pi)"""
        if self.frame_buffer is None:
            return None, []
            
        with self._frame_lock:
            frame = self.frame_buffer.copy()
        
        # Convert to grayscale for faster processing
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Use either DNN or Haar cascade based on availability
        if self.dnn_net:
            faces = self.detect_faces_dnn(frame)
        else:
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
        
        recognized_users = []
        current_time = time.time()
        
        # Only process recognition if enough time has passed
        if (current_time - self.last_recognition_time) >= self.min_recognition_interval:
            for (x, y, w, h) in faces:
                face_roi = gray[y:y+h, x:x+w]
                label, confidence = self.face_recognizer.predict(face_roi)
                
                if confidence < 80:  # Confidence threshold
                    user_info = self.label_to_user.get(label)
                    if user_info:
                        recognized_users.append({
                            'user': user_info,
                            'confidence': float(100 - confidence),
                            'timestamp': current_time
                        })
                        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                        text = f"{user_info['name']} ({100 - confidence:.1f}%)"
                        cv2.putText(frame, text, (x, y-10), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
            if recognized_users:
                self.last_recognition_time = current_time
        
        # Encode frame with optimized settings
        ret, jpeg = cv2.imencode('.jpg', frame, [
            cv2.IMWRITE_JPEG_QUALITY, 70,
            cv2.IMWRITE_JPEG_OPTIMIZE, 1
        ])
        
        return (jpeg.tobytes() if ret else None, recognized_users)
    
    def detect_faces_dnn(self, frame):
        """DNN-based face detection"""
        (h, w) = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(
            cv2.resize(frame, (300, 300)), 1.0, (300, 300),
            (104.0, 177.0, 123.0), swapRB=False, crop=False)
        
        self.dnn_net.setInput(blob)
        detections = self.dnn_net.forward()
        
        faces = []
        for i in range(0, detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            if confidence > 0.7:  # Confidence threshold
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (x, y, x2, y2) = box.astype("int")
                faces.append((x, y, x2-x, y2-y))
        
        return faces
    
    def get_frame(self):
        """Get a single frame without face processing"""
        with self._frame_lock:
            if self.frame_buffer is None:
                return None
                
            frame = self.frame_buffer.copy()
        
        ret, jpeg = cv2.imencode('.jpg', frame, [
            cv2.IMWRITE_JPEG_QUALITY, 70,
            cv2.IMWRITE_JPEG_OPTIMIZE, 1
        ])
        return jpeg.tobytes() if ret else None
    
    def __del__(self):
        self.release()
    
    def release(self):
        """Clean up resources"""
        self.running = False
        if self.capture_thread:
            self.capture_thread.join(timeout=1)
        if self.vs is not None:
            self.vs.release()
            self.vs = None
        print("Camera resources released")