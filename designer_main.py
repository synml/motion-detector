import sys
import time

import cv2
import numpy as np
import pygame
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


class Camera(QtCore.QObject):
    def __init__(self, label, textBrowser):
        super(Camera, self).__init__()
        self.camera = cv2.VideoCapture(0)
        self.label = label

        self.textBrowser = textBrowser
        # self.width = self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)
        # self.height = self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
        self.label.resize(label_w, label_h)

        self.logic = True  # 반복 루프 제어

        self.default_x, self.default_y, self.w, self.h = -1, -1, -1, -1
        self.buffer_frame = None
        print(self.default_x, self.default_y, self.w, self.h)
        self.total_frame = 0
        self.loop_time = 100  # 프레임 처리 간격 (100 = 0.1초)
        self.buffError = 0  # 이전 프레임 기준 오차율
        self.idleMode = False  # Flag변수, 이상 감지 후 유휴 상태 돌입
        self.maxIdleCount = 5000  # (1000 = 1s ) idleMode가 True일 때 이상 감지를 몇 초 간 안할것인가
        self.idleCount = 0  # idleMode가 True일 때 이상 감지 누적 시간( idelCount == maxIdelCount 가 되면 idleMode = False )

        # 첫 프레임 gui 라벨 이미지 설정
        ret, firstFrame = self.camera.read()
        firstFrame = cv2.cvtColor(firstFrame, cv2.COLOR_BGR2GRAY)
        firstFrame = cv2.resize(firstFrame, dsize=(800, 600), interpolation=cv2.INTER_AREA)
        qimg = QtGui.QImage(firstFrame.data, firstFrame.shape[1], firstFrame.shape[0],
                            firstFrame.strides[0], QtGui.QImage.Format_Grayscale8)
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
                print(self.default_x, self.default_y, self.w, self.h)

    def startVideo(self):
        now = time.localtime()
        # textBrowser 이벤트 처리
        self.textBrowser.append("감지 시작: " + str(now.tm_year) + "년" + str(now.tm_mon) + "월" + str(now.tm_mday) +
                                "일" + str(now.tm_hour) + "시" + str(now.tm_min) + "분" + str(now.tm_sec) + "초")
        # ROI 처리
        ret, firstFrame = self.camera.read()
        # firstFrame= cv2.cvtColor(firstFrame, cv2.COLOR_BGR2GRAY)
        firstFrame = cv2.resize(firstFrame, dsize=(800, 600), interpolation=cv2.INTER_AREA)
        cv2.startWindowThread()
        cv2.imshow('video', firstFrame)
        cv2.setMouseCallback("video", self.onMouse, param=firstFrame)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        print(self.default_x, self.default_y, self.w, self.h)
        while self.logic:
            ret, frame = self.camera.read()
            if not ret:  # 카메라 인식 안될경우
                print('camera read error')
                return

            self.total_frame += 1
            roi_cols = self.default_y + self.h
            roi_rows = self.default_x + self.w

            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            frame = cv2.resize(frame, dsize=(800, 600), interpolation=cv2.INTER_AREA)
            if self.buffer_frame is None:
                firstFrame = cv2.cvtColor(firstFrame, cv2.COLOR_BGR2GRAY)
                self.buffer_frame = firstFrame[self.default_y:roi_cols, self.default_x:roi_rows]

            self.roi_frame = frame[self.default_y:roi_cols, self.default_x:roi_rows]
            subtract_frame = np.round(np.sqrt(np.sum((self.buffer_frame - self.roi_frame) ** 2)))  # L2 DISTANCE

            if self.total_frame == 1:
                self.buffError = subtract_frame

            # cv2.imshow('roi', self.buffer_Frame)
            # print(subtract_frame)
            print(self.default_x, self.default_y, self.w, self.h)
            # 유휴 상태
            if self.idleMode:
                if rasp:
                    GPIO.output(idle, GPIO.HIGH)  # rasp인 경우 GPIO 출력
                self.idleCount += self.loop_time  # 유휴상태 경과 시간 += 루프 간격

                if self.idleCount == self.maxIdleCount:  # 유휴상태 경과시간이 유휴시간 임계값에 도달한 경우
                    if rasp:
                        GPIO.output(idle, GPIO.LOW)  # RASP인 경우 GPIO OFF
                    self.idleCount = 0  # 유휴상태 경과시간 초기화
                    self.idleMode = False  # 유휴상태 해제

            # 일반 감지 모드
            else:
                threshold = self.buffError * 1.5
                if subtract_frame > threshold:
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
                else:
                    if rasp:
                        GPIO.output(alert, GPIO.LOW)

            self.buffer_frame = self.roi_frame  # 손실 계산을 위해 현재 프레임을 버퍼에 넣고 다음 루프 때 비교
            # 이전 오차값과 현재 오차값이 +-5% 이상이면 모션 감지
            self.buffError = subtract_frame
            bounding_box_frame = frame.copy()
            output_frame = cv2.rectangle(bounding_box_frame, (self.default_x, self.default_y),
                                         (self.default_x + self.w, self.default_y + self.h), (0, 255, 0),
                                         thickness=3)

            # img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            # h, w, c = img.shape
            qimg = QtGui.QImage(output_frame.data, label_w, label_h,
                                output_frame.strides[0], QtGui.QImage.Format_Grayscale8)
            pixmap = QtGui.QPixmap.fromImage(qimg)
            self.label.setPixmap(pixmap)
            loop = QtCore.QEventLoop()
            QtCore.QTimer.singleShot(self.loop_time, loop.quit)  # 이벤트 루트 간격
            loop.exec_()
            # cv2.waitKey(33)

    def quit(self):
        self.logic = False  # 메인로직 반복 종료
        if rasp:
            GPIO.cleanup()
        win.thread.quit()
        win.thread.wait(5000)
        app.quit()  # 앱 최종 종료


class SubWindow(QtWidgets.QDialog, QtCore.QObject, setOptionDialogUi):
    def __init__(self):
        super(SubWindow, self).__init__()
        self.setupUi(self)

    # def showDialog(self):
    #     print("다이얼로그 오픈")
    #     # QtWidgets.QDialog.setWindowModality(self, QtCore.Qt.NonModal)

    #     self.initUI()
    #
    # def initUI(self):
    #     self.setWindowTitle('Sub Window')
    #     self.setGeometry(100, 100, 200, 100)
    #     layout = QtWidgets.QVBoxLayout()
    #     layout.addStretch(1)
    #     edit = QtWidgets.QLineEdit()
    #     font = edit.font()
    #     font.setPointSize(20)
    #     edit.setFont(font)
    #     self.edit = edit
    #     subLayout = QtWidgets.QHBoxLayout()
    #
    #     btnOK = QtWidgets.QPushButton("확인")
    #     btnOK.clicked.connect(self.onOKButtonClicked)
    #     btnCancel = QtWidgets.QPushButton("취소")
    #     btnCancel.clicked.connect(self.onCancelButtonClicked)
    #     layout.addWidget(edit)
    #
    #     subLayout.addWidget(btnOK)
    #     subLayout.addWidget(btnCancel)
    #     layout.addLayout(subLayout)
    #     layout.addStretch(1)
    #     self.setLayout(layout)


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

        self.exitButton.clicked.connect(self.camera.quit)


if __name__ == "__main__":
    pygame.init()
    pygame.mixer.init()
    pygame.mixer.music.load("res/alert.mp3")

    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    app.exec_()
