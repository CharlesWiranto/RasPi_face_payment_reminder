import cv2

import numpy as np
from camera11 import VideoCamera

def main():
    face_cascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")
    cam = VideoCamera()
    while True:
        frame_bytes, found = cam.get_object(face_cascade)
        if frame_bytes is not None:
            nparr = np.frombuffer(frame_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            cv2.imshow('Face Detection Test', img)
        if found:
            print("检测到人脸，正在发送邮件...")
        if hasattr(cam, 'last_email_sent') and cam.last_email_sent:
            print("邮件发送成功！")
            cam.last_email_sent = False  # 重置，避免重复输出
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()