import time
import cv2
import numpy as np
from camera import VideoCamera

def main():
    # Load face detection classifier
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    
    # Initialize camera with error handling
    try:
        cam = VideoCamera()
    except Exception as e:
        print(f"Camera initialization failed: {e}")
        return

    try:
        while True:
            # Get frame data
            frame_bytes, found = cam.get_object(face_cascade)
            
            # Skip if no frame received
            if frame_bytes is None:
                print("No frame data received")
                time.sleep(0.1)
                continue

            try:
                # Convert to numpy array with verification
                nparr = np.frombuffer(frame_bytes, np.uint8)
                if nparr.size == 0:
                    print("Received empty frame data")
                    continue

                # Decode image
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if img is None:
                    print("Failed to decode image")
                    continue

                # Save to file (headless operation)
                timestamp = int(time.time())
                output_path = f"/home/pi/Documents/final/output_{timestamp}.jpg"
                cv2.imwrite(output_path, img)
                print(f"Saved frame to {output_path}")

            except Exception as e:
                print(f"Frame processing error: {e}")

            time.sleep(0.1)  # Reduce CPU usage

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        # Cleanup resources
        if 'cam' in locals():
            del cam

if __name__ == "__main__":
    main()