import sys
import time

import cv2
import numpy as np
import pygame

import multiprocessing as mp

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5 import uic

try:
    import RPi.GPIO as GPIO

    rasp = True
    idle = 25
    alert = 24
except ModuleNotFoundError:
    rasp = False
    idle = 25
    alert = 24

"""
전역 설정란

라벨 크기 : 800(w 너비)  600(h 높이)

"""

label_w = 800
label_h = 600

mainUi = uic.loadUiType('main.ui')[0]
setOptionDialogUi = uic.loadUiType('setOptionDialog.ui')[0]


class camera():

    def __init__(self, rtsp_url):
        # 데이터 프로세스 전송 파이프
        self.rtsp_url = rtsp_url
        self.parent_conn, child_conn = mp.Pipe()
        # load process
        self.p = mp.Process(target=self.update, args=(child_conn, rtsp_url))
        # start process
        self.p.daemon = True
        self.p.start()

    def get_first_frame(self):
        firstFrameCap = cv2.VideoCapture(self.rtsp_url)
        _, frame = firstFrameCap.read()
        return frame

    def end(self):
        # 프로세스 종료 요청
        self.parent_conn.send(2)

    def update(self, conn, rtsp_url):
        # load cam into seperate process
        print("카메라 로드 중")
        # cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        cap = cv2.VideoCapture(rtsp_url)

        # 버퍼 지정
        # cap.set(cv2.CAP_PROP_BUFFERSIZE , 30)

        print("카메라 로드 완료")
        run = True

        while run:
            # 버퍼에서 카메라 데이터 수신
            cap.grab()

            # 입력 데이터 수신
            rec_dat = conn.recv()

            if rec_dat == 1:
                # 프레임 수신 완료했을 경우
                ret, frame = cap.read()
                conn.send(frame)

            elif rec_dat == 2:
                # 요청이 없는 경우
                cap.release()
                run = False

        print("Camera Connection Closed")
        conn.close()

    def get_frame(self, resize=None):
        #카메라 연결 프로세스에서 프레임 수신하는데 사용
        # resize 값 50% 증가인 경우 1.5

        # send request
        self.parent_conn.send(1)
        frame = self.parent_conn.recv()

        # reset request
        self.parent_conn.send(0)

        # resize if needed
        if resize == None:
            return frame
        else:
            print("리사이즈")
            return self.rescale_frame(frame, resize)

    def rescale_frame(self, frame, percent=65):

        return cv2.resize(frame, None, fx=percent, fy=percent)


class Camera(QtCore.QObject):
    def __init__(self, label, textBrowser):
        super(Camera, self).__init__()
        # self.camera = cv2.VideoCapture(0)
        self.firstCamera = cv2.VideoCapture('rtsp://admin:1q2w3e4r5t@192.168.0.5:554/fhd/media.smp')
        self.camera = camera('rtsp://admin:1q2w3e4r5t@192.168.0.5:554/fhd/media.smp')
        self.rescale_value = None

        self.label = label

        self.textBrowser = textBrowser
        self.label.resize(label_w, label_h)

        self.logic = True  # 반복 루프 제어

        self.default_x, self.default_y, self.w, self.h = -1, -1, -1, -1
        self.buffer_frame = None

        self.total_frame = 0

        self.buffError = 0  # 이전 프레임 기준 오차율
        self.idleMode = False  # Flag변수, 이상 감지 후 유휴 상태 돌입
        self.idleTime = 5 # second
        self.discount = 0


        # 첫 프레임 gui 라벨 이미지 설정
        ret, self.firstFrame = self.firstCamera.read()
        self.firstFrame = cv2.cvtColor(self.firstFrame, cv2.COLOR_BGR2GRAY)
        self.firstFrame = cv2.resize(self.firstFrame, dsize=(800, 600), interpolation=cv2.INTER_AREA)
        qimg = QtGui.QImage(self.firstFrame.data, self.firstFrame.shape[1], self.firstFrame.shape[0],
                            self.firstFrame.strides[0], QtGui.QImage.Format_Grayscale8)
        pixmap = QtGui.QPixmap.fromImage(qimg)
        self.label.setPixmap(pixmap)

    def onMouse(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.default_x = x
            self.default_y = y

        elif event == cv2.EVENT_LBUTTONUP:
            self.w = x - self.default_x
            self.h = y - self.default_y

            if self.w > 0 and self.h > 0:
                img_draw = param.copy()
                cv2.rectangle(img_draw, (self.default_x, self.default_y), (x, y), (0, 255, 255), 2)
                cv2.imshow('video', img_draw)

    def startVideo(self):
        now = time.localtime()
        # textBrowser 이벤트 처리
        self.textBrowser.append("감지 시작: " + str(now.tm_year) + "년" + str(now.tm_mon) + "월" + str(now.tm_mday) +
                                "일" + str(now.tm_hour) + "시" + str(now.tm_min) + "분" + str(now.tm_sec) + "초")
        # ROI 처리
        ret, self.firstFrame = self.firstCamera.read()
        self.firstFrame = cv2.cvtColor(self.firstFrame, cv2.COLOR_BGR2GRAY)
        self.firstFrame = cv2.resize(self.firstFrame, dsize=(800, 600), interpolation=cv2.INTER_AREA)
        cv2.startWindowThread()
        cv2.imshow('video', self.firstFrame)
        cv2.setMouseCallback("video", self.onMouse, param=self.firstFrame)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

        while self.logic:
            # ret, frame = self.camera.read()
            self.frame = self.camera.get_frame()
            if not ret:  # 카메라 인식 안될경우
                print('camera read error')
                return

            self.total_frame += 1
            roi_cols = self.default_y + self.h
            roi_rows = self.default_x + self.w

            self.frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)
            self.frame = cv2.resize(self.frame, dsize=(800, 600), interpolation=cv2.INTER_AREA)
            if self.buffer_frame is None:
                # self.firstFrame = cv2.cvtColor(self.firstFrame, cv2.COLOR_BGR2GRAY)
                self.buffer_frame = self.firstFrame[self.default_y:roi_cols, self.default_x:roi_rows]

            self.roi_frame = self.frame[self.default_y:roi_cols, self.default_x:roi_rows]


            subtract_frame = np.round(np.sqrt(np.sum((self.buffer_frame - self.roi_frame) ** 2)))  # L2 DISTANCE
            # subtract_frame = np.round(np.sqrt(np.sum((self.buffer_frame - self.roi_frame))))  # L2 DISTANCE

            if self.total_frame == 1:
                self.buffError = subtract_frame

            print(subtract_frame)
            # 유휴 상태
            if self.idleMode:
                print("유휴")
                win.statusLabel.setText("유휴 상태")
                win.idleTimeLcd.display((self.idleInitTime + self.idleTime ) - time.time())
                self.discount += 1

                if rasp:
                    GPIO.output(idle, GPIO.HIGH)  # rasp인 경우 GPIO 출력
                print("유휴상태 현재시간", time.time())

                if self.idleInitTime + self.idleTime <= time.time():
                    if rasp:
                        GPIO.output(idle, GPIO.LOW)  # RASP인 경우 GPIO OFF
                    self.idleMode = False  # 유휴상태 해제
                    self.discount = 0

            # 일반 감지 모드
            else:
                print("일반감지모드")
                self.idleInitTime = time.time()
                win.statusLabel.setText("일반 감지 상태")
                win.idleTimeLcd.display(0)
                threshold = self.buffError * 1.2
                if subtract_frame > threshold and self.total_frame >= 3:


                    print("이상감지")
                    if rasp:
                        GPIO.output(alert, GPIO.HIGH)
                    pygame.mixer.music.play()
                    # self.buffer_frame = roi_frame

                    # textBrowser에 로그 기록
                    now = time.localtime()
                    self.textBrowser.append(
                        "이상 감지: " + str(now.tm_year) + "년" + str(now.tm_mon) + "월" + str(now.tm_mday) +
                        "일" + str(now.tm_hour) + "시" + str(now.tm_min) + "분" + str(now.tm_sec) + "초")

                    self.idleMode = True

                    print("진입시간",self.idleInitTime)
                else:
                    if rasp:
                        GPIO.output(alert, GPIO.LOW)

            self.buffer_frame = self.roi_frame  # 손실 계산을 위해 현재 프레임을 버퍼에 넣고 다음 루프 때 비교
            # 이전 오차값과 현재 오차값이 +-5% 이상이면 모션 감지
            self.buffError = subtract_frame
            bounding_box_frame = self.frame.copy()
            output_frame = cv2.rectangle(bounding_box_frame, (self.default_x, self.default_y),
                                         (self.default_x + self.w, self.default_y + self.h), (0, 255, 0),
                                         thickness=3)


            qimg = QtGui.QImage(output_frame.data, label_w, label_h,
                                output_frame.strides[0], QtGui.QImage.Format_Grayscale8)
            pixmap = QtGui.QPixmap.fromImage(qimg)
            self.label.setPixmap(pixmap)
            # loop = QtCore.QEventLoop()
            # QtCore.QTimer.singleShot(33, loop.quit)  # 이벤트 루트 간격
            # loop.exec_()



class SubWindow(QtWidgets.QDialog, QtCore.QObject, setOptionDialogUi):
    def __init__(self):
        super(SubWindow, self).__init__()
        self.setupUi(self)
        self.textEdit.setText("33")
        self.buttonBox.clicked.connect(self.idleTimeEditChanged)

    def idleTimeEditChanged(self):
        self.textEdit.setText("qq")



class MainWindow(QtWidgets.QMainWindow, mainUi):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)

        self.thread = QtCore.QThread()
        self.thread.start()
        self.thread2 = QtCore.QThread()
        self.thread2.start()

        self.camera = Camera(self.label, self.textBrowser)
        self.camera.moveToThread(self.thread)

        self.setOptionDialog = SubWindow()
        self.setOptionDialog.moveToThread(self.thread)

        self.startButton.clicked.connect(self.camera.startVideo)
        self.setOptionButton.clicked.connect(self.setOptionDialog.show)
        self.exitButton.clicked.connect(self.quit)

        # 메뉴바 시그널 연결
        self.actionStart.triggered.connect(self.camera.startVideo)
        self.actionQuit.triggered.connect(self.quit)

    def quit(self):
        self.camera.logic = False  # 메인로직 반복 종료
        print("종료")
        if rasp:
            GPIO.cleanup()
        win.thread.quit()
        win.thread.wait(5000)
        app.quit()  # 앱 최종 종료


if __name__ == "__main__":
    pygame.init()
    pygame.mixer.init()
    pygame.mixer.music.load("res/alert.mp3")

    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    app.exec_()
