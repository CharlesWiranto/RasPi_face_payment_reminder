import cv2
import time
import numpy as np

class VideoCamera(object):
    def __init__(self, flip=False, cam_source=0):
        """
        Initialize the camera.
        
        Args:
            flip (bool): Whether to flip the image vertically
            cam_source (int/str): Camera source (0 for default camera)
        """
        self.vs = None
        self.flip = flip
        self.cam_source = cam_source
        self.retry_count = 0
        self.max_retries = 5
        self.camera_source = self.determine_camera_source()
        self.initialize_camera()

    # def initialize_camera(self):
    #     """Initialize or reinitialize the camera."""
    #     if self.vs is not None:
    #         self.vs.release()
    #         time.sleep(0.5)
            
    #     self.vs = cv2.VideoCapture(self.cam_source)
    #     if not self.vs.isOpened():
    #         self.retry_count += 1
    #         if self.retry_count <= self.max_retries:
    #             print(f"Camera initialization failed. Retrying ({self.retry_count}/{self.max_retries})...")
    #             time.sleep(1)
    #             self.initialize_camera()
    #         else:
    #             raise Exception("Could not open camera after multiple attempts")
    #     else:
    #         # Set camera properties
    #         self.vs.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    #         self.vs.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    #         self.retry_count = 0
    #         print("Camera initialized successfully")
    
    def determine_camera_source(self):
        """Determine the correct camera source for Raspberry Pi"""
        try:
            # Check if this is a Raspberry Pi
            with open('/proc/device-tree/model', 'r') as f:
                if 'Raspberry Pi' in f.read():
                    # Try different camera backends
                    if self.test_camera_source('libcamera'):
                        return 'libcamera'
                    elif self.test_camera_source(0):  # Try default index
                        return 0
        except:
            pass
        return 0  # Fallback to default

    def test_camera_source(self, source):
        """Test if a camera source works"""
        try:
            cap = cv2.VideoCapture(source)
            if cap.isOpened():
                cap.release()
                return True
        except:
            pass
        return False

    # def initialize_camera(self):
    #     """Initialize or reinitialize the camera."""
    #     if self.vs is not None:
    #         self.vs.release()
    #         time.sleep(0.5)
            
    #     # For libcamera on Raspberry Pi
    #     if self.camera_source == 'libcamera':
    #         self.vs = cv2.VideoCapture('libcamerasrc ! video/x-raw,width=640,height=480 ! videoconvert ! appsink', 
    #                                   cv2.CAP_GSTREAMER)
    #     else:
    #         self.vs = cv2.VideoCapture(self.camera_source)
            
    #     if not self.vs.isOpened():
    #         self.retry_count += 1
    #         if self.retry_count <= self.max_retries:
    #             print(f"Camera initialization failed. Retrying ({self.retry_count}/{self.max_retries})...")
    #             time.sleep(1)
    #             self.initialize_camera()
    #         else:
    #             raise Exception("Could not open camera after multiple attempts")
    #     else:
    #         # Set camera properties (only works with V4L2)
    #         if isinstance(self.camera_source, int):
    #             self.vs.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    #             self.vs.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    #         self.retry_count = 0
    #         print(f"Camera initialized successfully with source: {self.camera_source}")

    def initialize_camera(self):
        if self.vs is not None:
            self.vs.release()
            time.sleep(0.5)

        for attempt in range(1, self.max_retries + 1):
            print(f"Camera initialization attempt ({attempt}/{self.max_retries})")
            
            if self.camera_source == "gstreamer":
                self.vs = cv2.VideoCapture("libcamerasrc ! video/x-raw,width=640,height=480 ! videoconvert ! appsink", cv2.CAP_GSTREAMER)
            else:
                self.vs = cv2.VideoCapture(self.camera_source)

            if self.vs.isOpened():
                if isinstance(self.camera_source, int):
                    self.vs.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    self.vs.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                print(f"Camera initialized successfully with source: {self.camera_source}")
                return
            else:
                time.sleep(1)
        
        raise Exception("Could not open camera after multiple attempts")

    def __del__(self):
        """Release camera resources."""
        if self.vs is not None:
            self.vs.release()

    def flip_if_needed(self, frame):
        """Flip frame if needed."""
        return np.flip(frame, 0) if self.flip else frame

    def get_frame(self):
        """Get current frame from camera."""
        try:
            ret, frame = self.vs.read()
            if not ret:
                print("Failed to read frame from camera")
                self.initialize_camera()
                return None
                
            frame = self.flip_if_needed(frame)
            ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            return jpeg.tobytes() if ret else None
        except Exception as e:
            print(f"Error getting frame: {str(e)}")
            self.initialize_camera()
            return None

    def get_object(self, classifier):
        """Detect objects using the given classifier."""
        found_objects = False
        try:
            ret, frame = self.vs.read()
            if not ret:
                return None, found_objects
                
            frame = self.flip_if_needed(frame).copy()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            objects = classifier.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30),
                flags=cv2.CASCADE_SCALE_IMAGE
            )

            if len(objects) > 0:
                found_objects = True

            # Draw rectangles around detected objects
            for (x, y, w, h) in objects:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            ret, jpeg = cv2.imencode('.jpg', frame)
            return (jpeg.tobytes() if ret else None, found_objects)
        except Exception as e:
            print(f"Error in get_object: {str(e)}")
            return None, False