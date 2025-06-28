import re
import cv2
import numpy as np
import pigpio
import time
from PIL import Image
import tflite_runtime.interpreter as tflite  

CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
DETECTION_THRESHOLD = 0.4    
MIN_MOVE_THRESH = 5         
TARGET_CLASSES = [16, 17]   

HORIZON_PIN = 17           
SERVO_FREQ = 50            
ANGLE_RANGE = (-90, 90)    
INITIAL_ANGLE = 0          

def angle_to_duty(angle):
    # 将角度(-90°~90°)转换为占空比（2.5%~12.5%）
    angle = np.clip(angle, *ANGLE_RANGE)
    return 2.5 + (angle + 90) * 10 / 180

def update_servo(pi, pin, current_angle, target_angle):
    # 更新舵机角度（带角度限制和步长控制）
    target_angle = np.clip(target_angle, *ANGLE_RANGE)
    delta = np.sign(target_angle - current_angle) * min(15, abs(target_angle - current_angle))
    new_angle = current_angle + delta
    duty = angle_to_duty(new_angle)
    pi.set_PWM_dutycycle(pin, duty)
    return new_angle

def load_labels(label_path):
    with open(label_path, 'r') as f:
        return {int(m.group(1)): m.group(2) for m in [re.match(r"(\d+)\s+(\w+)", line.strip()) for line in f if line.strip()] if m}

def load_model(model_path):
    return tflite.Interpreter(model_path=model_path)

if __name__ == "__main__":
    model_path = 'data/detect.tflite'
    label_path = 'data/coco_labels.txt'

    # 初始化摄像头和舵机
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    pi = pigpio.pi()
    pi.set_PWM_frequency(HORIZON_PIN, SERVO_FREQ)
    pi.set_PWM_dutycycle(HORIZON_PIN, angle_to_duty(INITIAL_ANGLE))

    interpreter = load_model(model_path)
    interpreter.allocate_tensors()
    labels = load_labels(label_path)
    input_details = interpreter.get_input_details()
    input_index = input_details[0]['index']
    input_shape = input_details[0]['shape']

    current_angle = INITIAL_ANGLE

    try:
        while True:
            ret, frame = cap.read()
            if not ret: continue

            # 图像预处理
            image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).resize((input_shape[2], input_shape[1]))
            input_data = np.expand_dims(image, axis=0).astype(np.uint8)

            # 目标检测
            interpreter.set_tensor(input_index, input_data)
            interpreter.invoke()
            boxes, classes, scores, _ = [interpreter.get_tensor(d['index']) for d in interpreter.get_output_details()]

            # 过滤有效目标
            valid_idx = np.where((scores[0] > DETECTION_THRESHOLD) & np.isin(classes[0].astype(int), TARGET_CLASSES))[0]
            if valid_idx.size == 0:
                cv2.imshow('Tracking', frame)
                if cv2.waitKey(1) == 27: break
                continue

            # 取最大置信度目标
            best_idx = valid_idx[np.argmax(scores[0][valid_idx])]
            box = boxes[0][best_idx]
            x_center = (box[1] + box[3])/2 * CAMERA_WIDTH

            # 计算角度偏移
            center_x = CAMERA_WIDTH // 2
            dx = x_center - center_x  # 像素偏移量
            angle_offset = (dx / center_x) * 45  # 转换为角度偏移
            target_angle = current_angle + angle_offset

            if abs(dx) >= MIN_MOVE_THRESH:
                current_angle = update_servo(pi, HORIZON_PIN, current_angle, target_angle)

            # 绘制检测框
            x1, y1 = int(box[1]*CAMERA_WIDTH), int(box[0]*CAMERA_HEIGHT)
            x2, y2 = int(box[3]*CAMERA_WIDTH), int(box[2]*CAMERA_HEIGHT)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"{labels[classes[0][best_idx].astype(int)]}: {scores[0][best_idx]:.2f}", 
                       (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            cv2.imshow('Tracking', frame)
            if cv2.waitKey(1) == 27: break

    except KeyboardInterrupt:
        pass
    finally:
        pi.set_PWM_dutycycle(HORIZON_PIN, 0)
        pi.stop()
        cap.release()
        cv2.destroyAllWindows()