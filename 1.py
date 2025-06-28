import cv2
import imutils  #图像处理工具包,也可用于视频的处理，如摄像头、本地文件等
import time
import numpy as np  #运行速度非常快的数学库，主要用于数组计算

class VideoCamera(object):
    def __init__(self, flip = False):   #类初始化，self指向类实例对象本身
        self.vs = cv2.VideoCapture(0)  # 用OpenCV打开默认摄像头
        self.flip = flip
        time.sleep(2.0)
        if not self.vs.isOpened():
            raise Exception("无法打开摄像头")

    def __del__(self):  #对象销毁时调用，用于释放资源
        if self.vs.isOpened():
            self.vs.release()  # 释放摄像头资源

    def flip_if_needed(self, frame):    #翻转当前这帧的图片， frame：帧
        if self.flip:
            return np.flip(frame, 0)    #np.flip用于翻转数组，NumPy的np.flip()函数允许沿着某一个轴翻转数组的内容。当使                                        用np.flip时，指定要反转的数组和轴。如果不指定轴将沿着输入数组的所有轴反转内容。
        return frame                    #np.flip(frame,0)，0：按行翻转，1：按列翻转，不指定：按行按列翻转

    def get_frame(self):                    #得到当前帧
        ret, frame = self.vs.read()
        if not ret:
            return None
        frame = self.flip_if_needed(frame)
        ret, jpeg = cv2.imencode('.jpg', frame)     #cv2.imencode()函数是将图片格式转换(编码)成流数据，赋值到内存缓                                                    存中;主要用于图像数据格式的压缩，方便网络传输。
        return jpeg.tobytes() if ret else None                       #image.tobytes（）函数，以字节对象的形式返回图像

    def get_object(self, classifier):               #调用分类器识别人脸，返回识别到的人脸图片
        found_objects = False
        ret, frame = self.vs.read()
        if not ret:
            return None, found_objects
        frame = self.flip_if_needed(frame).copy()      #复制视频流采集到的帧，用于进行人脸判断
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)          #将读取到的帧进行颜色空间转换，有些图像可能在 RGB 颜                                                                    色空间信息不如转换到其它颜色空间更清晰

        objects = classifier.detectMultiScale(      #调整函数的参数使检测结果更加精确
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE
        )

        if len(objects) > 0:                        #如果有识别到人脸
            found_objects = True

        # Draw a rectangle around the objects       #在人脸周围画一个矩形框
        for (x, y, w, h) in objects:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        ret, jpeg = cv2.imencode('.jpg', frame)
        return (jpeg.tobytes() if ret else None, found_objects)      #如果识别到人脸，就将其图片转换成流数据并返回