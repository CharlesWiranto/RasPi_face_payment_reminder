import cv2
cap = cv2.VideoCapture(0)
print(f"Camera opened: {cap.isOpened()}")
ret, frame = cap.read()
print(f"Frame captured: {ret}, Shape: {frame.shape if ret else 'N/A'}")
cap.release()