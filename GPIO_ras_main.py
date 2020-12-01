import cv2
import sys
import numpy as np
from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5 import QtGui
import time


raspMode = False
if raspMode :
    import RPi.GPIO as GPIO
# 반복 횟수
globalCount = 0

# 프레임 연산 처리 간격
loopTime = 500
#GPIO.setmode(GPIO.BOARD)
#GPIO.setup(17, GPIO.OUT)


class ShowVideo(QtCore.QObject):


    camera = cv2.VideoCapture(1)

    ret, image = camera.read()
    height, width = image.shape[:2]

    VideoSignal1 = QtCore.pyqtSignal(QtGui.QImage)
    VideoSignal2 = QtCore.pyqtSignal(QtGui.QImage)


    def __init__(self, parent=None):
        super(ShowVideo, self).__init__(parent)
        # main logic variable
        self.drag = False
        self.default_x, self.default_y, self.w, self.h = -1, -1, -1, -1
        self.blue, self.yellow = (255, 0, 0), (0, 255, 255)
        self.first_frame = True
        self.buffer_Frame = None

        self.threshhold = 0
        self.globalFrameCount = 7
        self.frameCount = self.globalFrameCount #
        # 프레임 반복 횟수
        self.total_frame = 0
        # 이상 감지 후 남은 유휴 시간
        self.idleTime = 0



    @QtCore.pyqtSlot()
    def startVideo(self):
        # 메인로직 시작 시 시작버튼 숨기기




        now = time.localtime()
        push_button1.hide()
        textBrowser.append("Start Time : " +
            str(now.tm_year) + "년" + str(now.tm_mon) + "월" + str(now.tm_mday) + "일" + str(now.tm_hour) + "시" + str(
                now.tm_min) + "분" + str(now.tm_sec) + "초")
        # 카메라 캡쳐해서 받아온 이미지 정보 전역 함수 불러오기
        global image

        # 메인 로직 반복
        while True:

            #  ?? 레??
            if self.first_frame is True:

                ret, frame = self.camera.read()
                def onMouse(event, x, y, flags, param):

                    if event == cv2.EVENT_LBUTTONDOWN:
                        self.drag = True
                        self.default_x = x
                        self.default_y = y

                    elif event == cv2.EVENT_LBUTTONUP:
                        if self.drag:
                            drag = False
                            self.w = x - self.default_x
                            self.h = y - self.default_y

                            if self.w > 0 and self.h > 0:
                                img_draw = frame.copy()
                                cv2.rectangle(img_draw, (self.default_x, self.default_y), (x, y), self.yellow, 2)
                                cv2.imshow('video', img_draw)

                                roi_cols = self.default_y + self.h
                                roi_rows = self.default_x + self.w

                                # roi = frame[self.default_y:roi_cols, self.default_x:roi_rows]
                                # threshhold = np.shape(np.ravel(roi))[0]
                            print(self.default_x, self.default_y, self.w, self.h)

                #shape[0] = 높이 , shape[1] = 너비


                cv2.imshow('video', frame)
                cv2.setMouseCallback("video", onMouse, param=frame)
                cv2.waitKey(0)
                cv2.destroyAllWindows()
                self.first_frame = False



            else:

                global globalCount
                ret, image = self.camera.read()

                # 처리 로직
                self.total_frame += 1
                roi_cols = self.default_y + self.h
                roi_rows = self.default_x + self.w
                frame = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                if self.buffer_Frame is None:
                    self.buffer_Frame = frame[self.default_y:roi_cols, self.default_x:roi_rows]




                roi_Frame = frame[self.default_y:roi_cols, self.default_x:roi_rows]
                buffer_Frame_norm = 1 / (1 + np.exp(self.buffer_Frame)) # SIGMOID
                roi_Frame_norm = 1 / (1 + np.exp(roi_Frame)) # SIGMOID
                subtract_frame = np.sqrt(np.sum((buffer_Frame_norm - roi_Frame_norm) ** 2)) # L2 DISTANCE


                if self.total_frame == 1 :
                    buff_error = subtract_frame




                # cv2.imshow('roi', self.buffer_Frame)

                print(subtract_frame)
                if subtract_frame > buff_error*1.7:
                    #GPIO.output(17, GPIO.HIGH)
                    self.buffer_Frame = roi_Frame

                    # 텍스트 브라우저 로그 남기기
                    now = time.localtime()
                    textBrowser.append("이상 감지 : " + str(now.tm_year)+"년" + str(now.tm_mon)+"월" + str(now.tm_mday)+"일" + str(now.tm_hour)+"시" + str(now.tm_min)+"분" + str(now.tm_sec)+"초")

                else:
                    #GPIO.output(17, GPIO.LOW)
                    self.buffer_Frame = roi_Frame

                # 이전 오차값과 현재 오차값이 +-5퍼센트 이상이면 이상감지
                buff_error = subtract_frame
                #
                bbBoxFrame = frame.copy()
                outputFrame = cv2.rectangle(bbBoxFrame, (self.default_x, self.default_y), (self.default_x + self.w, self.default_y + self.h), (0, 255, 0), thickness=3)
                qt_image1 = QtGui.QImage(outputFrame.data,
                                        self.width,
                                        self.height,
                                        outputFrame.strides[0],
                                        QtGui.QImage.Format_Grayscale8)


                h, w = roi_Frame.shape
                roiFrameCvtMat = cv2.resize(roi_Frame,(h,w))


                qt_image2 = QtGui.QImage(roiFrameCvtMat.data,
                                        h,
                                        w,
                                        roiFrameCvtMat.strides[0],
                                        QtGui.QImage.Format_Grayscale8)

                self.VideoSignal1.emit(qt_image1)
                self.VideoSignal2.emit(qt_image2)

                globalCount +=1



            loop = QtCore.QEventLoop()
            QtCore.QTimer.singleShot(loopTime, loop.quit) #
            loop.exec_()

    def quit(self):
        GPIO.cleanup()
        app.quit()

class ImageViewer(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(ImageViewer, self).__init__(parent)
        self.image = QtGui.QImage()
        self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.drawImage(0, 0, self.image)
        self.image = QtGui.QImage()

    def initUI(self):
        self.setWindowTitle('Test')

    @QtCore.pyqtSlot(QtGui.QImage)
    def setImage(self, image):
        if image.isNull():
            print("Viewer Dropped frame!")

        self.image = image
        if image.size() != self.size():
            self.setFixedSize(image.size())
        self.update()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)


    thread = QtCore.QThread()
    thread.start()
    vid = ShowVideo()
    vid.moveToThread(thread)

    image_viewer1 = ImageViewer()
    image_viewer2 = ImageViewer()

    vid.VideoSignal1.connect(image_viewer1.setImage)
    vid.VideoSignal2.connect(image_viewer2.setImage)

    # 시작 버튼
    push_button1 = QtWidgets.QPushButton('시작')
    # 버튼 클릭 시 vid class의 startVideo 호출
    push_button1.clicked.connect(vid.startVideo)


    vertical_layout = QtWidgets.QVBoxLayout()
    horizontal_layout = QtWidgets.QHBoxLayout()

    horizontal_layout.addWidget(image_viewer1)
    horizontal_layout.addWidget(image_viewer2)
    textBrowser = QtWidgets.QTextBrowser()
    horizontal_layout.addWidget(textBrowser)

    vertical_layout.addLayout(horizontal_layout)
    vertical_layout.addWidget(push_button1)

    # 종료 버튼
    quit_button = QtWidgets.QPushButton("종료")
    # 버튼 클릭 시 vid class의 quit 함수 호출(app.quit 호출)
    quit_button.clicked.connect(vid.quit)
    # 종료 버튼 열 추가
    vertical_layout.addWidget(quit_button)

    layout_widget = QtWidgets.QWidget()
    layout_widget.setLayout(vertical_layout)
    #
    main_window = QtWidgets.QMainWindow()
    main_window.setCentralWidget(layout_widget)
    # 윈도우 전체 크기 설정(x축, y축 , 창 가로 너비, 창 세로 너비 )
    main_window.setGeometry(100,100,1200,400)
    main_window.show()
    sys.exit(app.exec_())