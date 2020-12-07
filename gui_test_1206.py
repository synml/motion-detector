"""
1206 ROI 새창 띄우기 테스트 코드

"""

import sys
import time

import cv2
import numpy as np
import pygame
from PyQt5 import QtCore, QtWidgets, QtGui
try:
    import RPi.GPIO as GPIO
    rasp = True
    idle = 25
    alert = 24
except ModuleNotFoundError:
    rasp = False
    idle = 25
    alert = 24




class ShowVideo(QtCore.QObject):
    VideoSignal1 = QtCore.pyqtSignal(QtGui.QImage)
    VideoSignal2 = QtCore.pyqtSignal(QtGui.QImage)



    def __init__(self, parent=None):
        super(ShowVideo, self).__init__(parent)
        self.roiDialog = QtWidgets.QDialog()
        self.camera = cv2.VideoCapture(0)
        self.logic = True
        self.height, self.width, _ = self.camera.read()[1].shape

        self.default_x, self.default_y, self.w, self.h = -1, -1, -1, -1
        self.buffer_frame = None

        self.total_frame = 0
        self.loop_time = 100 # 프레임 처리 간격 (100 = 0.1초)
        self.buffError = 0 # 이전 프레임 기준 오차율
        self.idleMode = False # Flag변수, 이상 감지 후 유휴 상태 돌입
        self.maxIdleCount = 5000 # (1000 = 1s ) idleMode가 True일 때 이상 감지를 몇 초 간 안할것인가
        self.idleCount = 0 # idleMode가 True일 때 이상 감지 누적 시간( idelCount == maxIdelCount 가 되면 idleMode = False )




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




    @QtCore.pyqtSlot()
    def startVideo(self):
        now = time.localtime()
        start_button.hide()
        textBrowser.append("시작 시간: " + str(now.tm_year) + "년" + str(now.tm_mon) + "월" + str(now.tm_mday) + "일" +
                           str(now.tm_hour) + "시" + str(now.tm_min) + "분" + str(now.tm_sec) + "초")

        ret, firstFrame = self.camera.read()

        # shape[0] = 높이 , shape[1] = 너비
        cv2.startWindowThread()
        cv2.imshow('video', firstFrame)
        cv2.setMouseCallback("video", self.onMouse, param=firstFrame)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

        while self.logic:
            ret, image = self.camera.read()

            # 처리 로직
            self.total_frame += 1
            roi_cols = self.default_y + self.h
            roi_rows = self.default_x + self.w
            frame = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            if self.buffer_frame is None:
                firstFrame = cv2.cvtColor(firstFrame, cv2.COLOR_BGR2GRAY)
                self.buffer_frame = firstFrame[self.default_y:roi_cols, self.default_x:roi_rows]

            self.roi_frame = frame[self.default_y:roi_cols, self.default_x:roi_rows]
            subtract_frame = np.round(np.sqrt(np.sum((self.buffer_frame - self.roi_frame) ** 2)))  # L2 DISTANCE

            if self.total_frame == 1:
                self.buffError = subtract_frame

            # cv2.imshow('roi', self.buffer_Frame)
            print(subtract_frame)

            # 유휴 상태
            if self.idleMode :
                if rasp:
                    GPIO.output(idle, GPIO.HIGH) # rasp인 경우 GPIO 출력
                self.idleCount += self.loop_time # 유휴상태 경과 시간 += 루프 간격

                if self.idleCount  == self.maxIdleCount: # 유휴상태 경과시간이 유휴시간 임계값에 도달한 경우
                    if rasp:
                        GPIO.output(idle, GPIO.LOW) # RASP인 경우 GPIO OFF
                    self.idleCount = 0 # 유휴상태 경과시간 초기화
                    self.idleMode = False # 유휴상태 해제

            # 일반 감지 모드
            else :
                threshold = self.buffError * 1.5
                if subtract_frame > threshold:
                    if rasp:
                        GPIO.output(alert, GPIO.HIGH)
                    pygame.mixer.music.play()
                    #self.buffer_frame = roi_frame

                    # textBrowser에 로그 기록
                    now = time.localtime()
                    textBrowser.append("이상 감지: " + str(now.tm_year) + "년" + str(now.tm_mon) + "월" + str(now.tm_mday) +
                                       "일" + str(now.tm_hour) + "시" + str(now.tm_min) + "분" + str(now.tm_sec) + "초")

                    self.idleMode = True
                else:
                    if rasp:
                        GPIO.output(alert, GPIO.LOW)
                    #self.buffer_frame = roi_frame

            self.buffer_frame = self.roi_frame # 손실 계산을 위해 현재 프레임을 버퍼에 넣고 다음 루프 때 비교
            # 이전 오차값과 현재 오차값이 +-5% 이상이면 모션 감지
            self.buffError = subtract_frame
            bounding_box_frame = frame.copy()
            output_frame = cv2.rectangle(bounding_box_frame, (self.default_x, self.default_y),
                                         (self.default_x + self.w, self.default_y + self.h), (0, 255, 0),
                                         thickness=3)
            qt_image1 = QtGui.QImage(output_frame.data,
                                     self.width,
                                     self.height,
                                     output_frame.strides[0],
                                     QtGui.QImage.Format_Grayscale8)

            self.VideoSignal1.emit(qt_image1)


            h, w = self.roi_frame.shape
            self.roi_frame_cvt_mat = cv2.resize(self.roi_frame, (h, w))

            qt_image2 = QtGui.QImage(self.roi_frame_cvt_mat.data,
                                     h,
                                     w,
                                     self.roi_frame_cvt_mat.strides[0],
                                     QtGui.QImage.Format_Grayscale8)
            self.VideoSignal2.emit(qt_image2)




            loop = QtCore.QEventLoop()
            QtCore.QTimer.singleShot(self.loop_time, loop.quit) # 이벤트 루트 간격
            loop.exec_() # 이벤트 루프 호출

    def activeRoI(self):
        print("roi")
        self.roiDialog.setWindowTitle('test')
        self.roiDialog.setWindowModality(QtCore.Qt.NonModal)
        self.roiDialog.resize(300, 200)
        # self.roiDialog.show()


    def quit(self):
        self.logic = False # 메인로직 반복 종료
        if rasp:
            GPIO.cleanup()
        thread.quit() # 쓰레드 반환
        thread.wait(5000) # 쓰레드 반환 데드라인 5초
        app.quit() # 앱 최종 종료




class ImageViewer(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(ImageViewer, self).__init__(parent)
        self.image = QtGui.QImage()
        self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.drawImage(0, 0, self.image)
        self.image = QtGui.QImage()

    @QtCore.pyqtSlot(QtGui.QImage)
    def setImage(self, image):
        if image.isNull():
            print("Viewer Dropped frame!")

        self.image = image
        if image.size() != self.size():
            self.setFixedSize(image.size())
        self.update()


# class TestVideo():
#     print("testvideo 객체 호출")
#
#     # roiWidget = QtWidgets.QWidget()
#     # roiLayout = QtWidgets.QVBoxLayout()
#     # image_viewer3 = ImageViewer()
#     # roiLayout.addWidget(image_viewer3)
#     # roiWidget.setLayout(roiLayout)
#     #roiWidget.show()
#
#
#
#     def __init__(self, roiWidget):
#           # roi영역 출력 화면
#         self.roiWidget = QtWidgets.QWidget()
#         self.roiLayout = QtWidgets.QVBoxLayout()
#
#
#         image_viewer3 = ImageViewer()
#         self.roiLayout.addWidget(image_viewer3)
#         #
#         test = ShowVideo
#         test.VideoSignal2.connect(image_viewer2.setImage)
#         self.roiWidget.setLayout(self.roiLayout)
#
#
#     def activateRoI(self):
#         self.roiWidget.show()


if __name__ == '__main__':
    pygame.init()
    pygame.mixer.init()
    pygame.mixer.music.load("res/alert.mp3")

    if rasp:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(alert, GPIO.OUT)
        GPIO.setup(idle, GPIO.OUT)

    app = QtWidgets.QApplication(sys.argv)

    thread = QtCore.QThread()

    thread.start()

    vid = ShowVideo()
    vid.moveToThread(thread)


    # vid2.moveToThread(thread)



    image_viewer1 = ImageViewer()
    image_viewer2 = ImageViewer()
    image_viewer3 = ImageViewer()


    vid.VideoSignal1.connect(image_viewer1.setImage) # 감지 카메라 출력 전체 화면
    vid.VideoSignal2.connect(image_viewer2.setImage) # roi영역 출력 화면
    vid.VideoSignal2.connect(image_viewer3.setImage) # roi영역 출력 화면




    textBrowser = QtWidgets.QTextBrowser()
    horizontal_layout = QtWidgets.QHBoxLayout()
    horizontal_layout.addWidget(image_viewer1)





    horizontal_layout.addWidget(image_viewer2)

    horizontal_layout.addWidget(textBrowser)

    #############
    # roi 창 테스트
    roiWidget = QtWidgets.QWidget()
    roiLayout = QtWidgets.QVBoxLayout()
    roiLayout.addWidget(image_viewer3)
    roiWidget.setLayout(roiLayout)
    def create():
        roiWidget.show()


    roiButton = QtWidgets.QPushButton('Dialog Button')

    roiButton.clicked.connect(create)
    roiButton.setGeometry(10, 10, 200, 50)
    horizontal_layout.addWidget(roiButton)

    # roiDialog = QtWidgets.QDialog()
    # roiDialog.setWindowTitle('test')
    # roiDialog.setWindowModality(QtCore.Qt.NonModal)
    # roiDialog.resize(300, 200)
    # roiDialog.show()




    ###############

    # horizontal_layout.addWidget(showRoi_button)
    # horizontal_layout.addWidget(closeRoi_button)

    start_button = QtWidgets.QPushButton('시작')
    start_button.clicked.connect(vid.startVideo)
    quit_button = QtWidgets.QPushButton("종료")
    quit_button.clicked.connect(vid.quit)

    vertical_layout = QtWidgets.QVBoxLayout()
    vertical_layout.addLayout(horizontal_layout)
    vertical_layout.addWidget(start_button)

    layout_widget = QtWidgets.QWidget()
    layout_widget.setLayout(vertical_layout)
    vertical_layout.addWidget(quit_button)

    main_window = QtWidgets.QMainWindow()
    main_window.setWindowTitle('Motion Detector')
    main_window.setWindowIcon(QtGui.QIcon('res/icon.png'))
    main_window.setCentralWidget(layout_widget)
    main_window.setGeometry(100, 100, 1280, 400)
    main_window.show()
    app.exec_()
