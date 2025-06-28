import cv2

cap = cv2.VideoCapture(
    "libcamerasrc ! video/x-raw,width=640,height=480 ! videoconvert ! appsink",
    cv2.CAP_GSTREAMER
)

if not cap.isOpened():
    print("❌ Failed to open camera via GStreamer")
else:
    print("✅ GStreamer pipeline working")
    cap.release()
