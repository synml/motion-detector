import cv2
import sys
import numpy as np
from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5 import QtGui
import time

error_index = []
subtract_frame_error = []
subtract_frame_percent_error = []
globalCount = 0


class ShowVideo(QtCore.QObject):
    camera = cv2.VideoCapture(0)

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
        self.frameCount = self.globalFrameCount  #
        self.total_frame = 0
        self.cycle = 0
        self.tempCycle = 0
        self.captureMode = False
        self.captureCount = 0
        self.motionCount = 0  #

    @QtCore.pyqtSlot()
    def startVideo(self):
        global image

        run_video = True
        while run_video:

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

                # shape[0] = 높이 , shape[1] = 너비
                cv2.startWindowThread()
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

                roi_frame = frame[self.default_y:roi_cols, self.default_x:roi_rows]
                buffer_frame_norm = 1 / (1 + np.exp(self.buffer_Frame))  # SIGMOID
                roi_frame_norm = 1 / (1 + np.exp(roi_frame))  # SIGMOID
                subtract_frame = np.sqrt(np.sum((buffer_frame_norm - roi_frame_norm) ** 2))  # L2 DISTANCE

                if self.total_frame == 1:
                    buff_error = subtract_frame

                # cv2.imshow('roi', self.buffer_Frame)
                if subtract_frame > buff_error * 1.3:

                    self.buffer_Frame = roi_frame

                    # 텍스트 브라우저 로그 남기기
                    now = time.localtime()
                    textBrowser.append(str(now.tm_year) + "년" + str(now.tm_mon) + "월" + str(now.tm_mday) + "일" + str(
                        now.tm_hour) + "시" + str(now.tm_min) + "분" + str(now.tm_sec) + "초")

                else:
                    self.buffer_Frame = roi_frame

                # 이전 오차값과 현재 오차값이 +-5퍼센트 이상이면 이상감지
                buff_error = subtract_frame
                #
                bbBoxFrame = frame.copy()
                output_frame = cv2.rectangle(bbBoxFrame, (self.default_x, self.default_y),
                                            (self.default_x + self.w, self.default_y + self.h), (0, 255, 0),
                                            thickness=3)
                qt_image1 = QtGui.QImage(output_frame.data,
                                         self.width,
                                         self.height,
                                         output_frame.strides[0],
                                         QtGui.QImage.Format_Grayscale8)

                h, w = roi_frame.shape
                roi_frame_cvt_mat = cv2.resize(roi_frame, (h, w))

                qt_image2 = QtGui.QImage(roi_frame_cvt_mat.data,
                                         h,
                                         w,
                                         roi_frame_cvt_mat.strides[0],
                                         QtGui.QImage.Format_Grayscale8)

                self.VideoSignal1.emit(qt_image1)
                self.VideoSignal2.emit(qt_image2)

                globalCount += 1

            loop = QtCore.QEventLoop()
            QtCore.QTimer.singleShot(500, loop.quit)
            loop.exec_()


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

    push_button1 = QtWidgets.QPushButton('Start')

    push_button1.clicked.connect(vid.startVideo)

    vertical_layout = QtWidgets.QVBoxLayout()
    horizontal_layout = QtWidgets.QHBoxLayout()

    horizontal_layout.addWidget(image_viewer1)
    horizontal_layout.addWidget(image_viewer2)
    textBrowser = QtWidgets.QTextBrowser()
    horizontal_layout.addWidget(textBrowser)

    vertical_layout.addLayout(horizontal_layout)
    vertical_layout.addWidget(push_button1)

    layout_widget = QtWidgets.QWidget()
    layout_widget.setLayout(vertical_layout)

    main_window = QtWidgets.QMainWindow()
    main_window.setCentralWidget(layout_widget)
    main_window.show()
    sys.exit(app.exec_())
