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
        self.camera = cv2.VideoCapture(1)
        self.height, self.width, _ = self.camera.read()[1].shape

        self.default_x, self.default_y, self.w, self.h = -1, -1, -1, -1
        self.blue = (255, 0, 0)
        self.yellow = (0, 255, 255)
        self.buffer_frame = None
        self.motion_count = 0
        self.total_frame = 0
        self.loop_time = 500

        self.idleMode = False # Flag변수, 이상 감지 후 유휴 상태 돌입
        self.maxIdleCount = 5000 # (1000 = 1s ) idleMode가 True일 때 이상 감지를 몇 초 간 안할것인가
        self.idleCount = 0 # idleMode가 True일 때 이상 감지 누적 시간( idelCount == maxIdelCount 가 되면 idleMode = False )

        self.roiMode = False


        self.roiDialog = QtWidgets.QDialog()



    def onMouse(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.default_x = x
            self.default_y = y

        elif event == cv2.EVENT_LBUTTONUP:
            self.w = x - self.default_x
            self.h = y - self.default_y

            if self.w > 0 and self.h > 0:
                img_draw = param.copy()
                cv2.rectangle(img_draw, (self.default_x, self.default_y), (x, y), self.yellow, 2)
                cv2.imshow('video', img_draw)

                # roi = frame[self.default_y:roi_cols, self.default_x:roi_rows]
                # threshhold = np.shape(np.ravel(roi))[0]
            print(self.default_x, self.default_y, self.w, self.h)

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

        while True:
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
            buffer_frame_norm = self.buffer_frame
            roi_frame_norm = self.roi_frame
            #buffer_frame_norm = 1 / (1 + np.exp(-self.buffer_frame, dtype=np.float64))  # SIGMOID
            #roi_frame_norm = 1 / (1 + np.exp(-roi_frame, dtype=np.float64))  # SIGMOID
            subtract_frame = np.round(np.sqrt(np.sum((buffer_frame_norm - roi_frame_norm) ** 2)))  # L2 DISTANCE

            if self.total_frame == 1:
                buff_error = subtract_frame

            # cv2.imshow('roi', self.buffer_Frame)
            print(subtract_frame)

            if self.idleMode :
                GPIO.output(idle, GPIO.HIGH)
                self.idleCount += self.loop_time
                now = time.localtime()
                #textBrowser.append("유휴 상태: " + str(now.tm_year) + "년" + str(now.tm_mon) + "월" + str(now.tm_mday) +
                #                   "일" + str(now.tm_hour) + "시" + str(now.tm_min) + "분" + str(now.tm_sec) + "초")

                #print("유휴")
                if self.idleCount  == self.maxIdleCount:
                    GPIO.output(idle, GPIO.LOW)
                    self.idleCount = 0
                    self.idleMode = False
                    #print("유휴상태 끝")
                    # now = time.localtime()
                    # textBrowser.append("정상 모드: " + str(now.tm_year) + "년" + str(now.tm_mon) + "월" + str(now.tm_mday) +
                    #                    "일" + str(now.tm_hour) + "시" + str(now.tm_min) + "분" + str(now.tm_sec) + "초")

            else :
                threshold = buff_error * 1.5
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
            buff_error = subtract_frame
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

            self.motion_count += 1

            loop = QtCore.QEventLoop()
            QtCore.QTimer.singleShot(self.loop_time, loop.quit)
            loop.exec_()

    # def showRoI(self):
    #     self.roiMode = True
    #     # NewWindow(self)
    #
    #
    # # 버튼 이벤트 함수
    # def dialog_open(self):
    #     # 버튼 추가
    #     #btnDialog = QtWidgets.QPushButton("OK", self.roiDialog)
    #     #btnDialog.move(100, 100)
    #     #btnDialog.clicked.connect(self.dialog_close)
    #
    #     # QDialog 세팅
    #     self.roiDialog.setWindowTitle('Dialog')
    #     self.roiDialog.setWindowModality(QtCore.Qt.NonModal)
    #     self.roiDialog.resize(300, 200)
    #     self.roiDialog.show()


    # # Dialog 닫기 이벤트
    # def dialog_close(self):
    #     self.roiDialog.close()

    def quit(self):
        if rasp:
            GPIO.cleanup()
        app.quit()

    # def catch_exceptions(t, val, tb):
    #     QtWidgets.QMessageBox.critical(None,
    #                                    "An exception was raised",
    #                                    "Exception type: {}".format(t))

# class NewWindow(QtWidgets.QMainWindow):
#     def __init__(self, parent=None):
#         super(NewWindow, self).__init__(parent)
#         self.label = QtWidgets.QLabel('New Window!')
#         centralWidget = QtWidgets.QWidget()
#         self.setCentralWidget(centralWidget)
#         self.layout = QtWidgets.QGridLayout(centralWidget)
#         self.layout.addWidget(self.label)



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

    image_viewer1 = ImageViewer()
    image_viewer2 = ImageViewer()

    vid.VideoSignal1.connect(image_viewer1.setImage)
    vid.VideoSignal2.connect(image_viewer2.setImage)

    textBrowser = QtWidgets.QTextBrowser()
    horizontal_layout = QtWidgets.QHBoxLayout()
    horizontal_layout.addWidget(image_viewer1)

    # RoI
    showRoi_button = QtWidgets.QPushButton('Show RoI') #ROI 버튼 보기


    # showRoi_button.clicked.connect(vid.dialog_open)


    horizontal_layout.addWidget(image_viewer2)

    horizontal_layout.addWidget(textBrowser)


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
