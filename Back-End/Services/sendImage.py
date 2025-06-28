import cv2
import imutils
import time
import numpy as np
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import ssl

# 邮箱配置
SMTP_SERVER = 'smtp.qq.com'
SMTP_PORT = 465
EMAIL_FROM = "charleswirantolgl@qq.com"
EMAIL_PASSWORD = "whopwummfcngbfbh"
EMAIL_TO = "2728642293@qq.com"  # 目标邮箱

def send_email_with_image(to_email, name, image_path):
    subject = "人脸识别通知"
    body = f"您好 {name}，我们已识别到您的人脸。识别时间: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = EMAIL_FROM
    msg['To'] = to_email
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    # 添加图片附件
    with open(image_path, 'rb') as f:
        mime = MIMEBase('image', 'jpg', filename=image_path.split('/')[-1])
        mime.add_header('Content-Disposition', 'attachment', filename=image_path.split('/')[-1])
        mime.set_payload(f.read())
        encoders.encode_base64(mime)
        msg.attach(mime)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context, timeout=20) as server:
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.sendmail(EMAIL_FROM, [to_email], msg.as_string())
        print(f" 邮件已发送，包含图片：{image_path}")

class VideoCamera(object):
    def __init__(self, flip = False):
        self.vs = cv2.VideoCapture(0)
        self.flip = flip
        time.sleep(2.0)
        if not self.vs.isOpened():
            raise Exception("无法打开摄像头")

    def __del__(self):
        if self.vs.isOpened():
            self.vs.release()

    def flip_if_needed(self, frame):
        if self.flip:
            return np.flip(frame, 0)
        return frame

    def get_frame(self):
        ret, frame = self.vs.read()
        if not ret:
            return None
        frame = self.flip_if_needed(frame)
        ret, jpeg = cv2.imencode('.jpg', frame)
        return jpeg.tobytes() if ret else None

    def get_object(self, classifier):
        found_objects = False
        ret, frame = self.vs.read()
        if not ret or frame is None:
            return None, found_objects
        
        # Process frame
        frame = self.flip_if_needed(frame).copy()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Face detection
        objects = classifier.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE
        )

        if len(objects) > 0:
            found_objects = True
            (x, y, w, h) = objects[0]
            face_img = frame[y:y+h, x:x+w]
            timestamp = int(time.time())
            save_path = f"/home/xiaobu/Desktop/test/final/Back-End/Services/face_{timestamp}.jpg"
            cv2.imwrite(save_path, face_img)

        # Draw rectangles
        for (x, y, w, h) in objects:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # Encode frame with error handling
        try:
            ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
            return (jpeg.tobytes(), found_objects) if ret else (None, found_objects)
        except Exception as e:
            print(f"Frame encoding error: {e}")
            return None, found_objects