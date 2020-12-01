import sys
import time

import cv2
import numpy as np
from PyQt5 import QtCore, QtWidgets, QtGui


class ShowVideo(QtCore.QObject):
    VideoSignal1 = QtCore.pyqtSignal(QtGui.QImage)
    VideoSignal2 = QtCore.pyqtSignal(QtGui.QImage)

    def __init__(self, parent=None):
        super(ShowVideo, self).__init__(parent)
        self.camera = cv2.VideoCapture(0)
        self.height, self.width, _ = self.camera.read()[1].shape

        self.default_x, self.default_y, self.w, self.h = -1, -1, -1, -1
        self.blue = (255, 0, 0)
        self.yellow = (0, 255, 255)
        self.buffer_frame = None
        self.motion_count = 0
        self.total_frame = 0

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
        ret, frame = self.camera.read()

        # shape[0] = 높이 , shape[1] = 너비
        cv2.startWindowThread()
        cv2.imshow('video', frame)
        cv2.setMouseCallback("video", self.onMouse, param=frame)
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
                self.buffer_frame = frame[self.default_y:roi_cols, self.default_x:roi_rows]

            roi_frame = frame[self.default_y:roi_cols, self.default_x:roi_rows]
            buffer_frame_norm = 1 / (1 + np.exp(-self.buffer_frame, dtype=np.float64))  # SIGMOID
            roi_frame_norm = 1 / (1 + np.exp(-roi_frame, dtype=np.float64))  # SIGMOID
            subtract_frame = np.sqrt(np.sum((buffer_frame_norm - roi_frame_norm) ** 2))  # L2 DISTANCE

            if self.total_frame == 1:
                buff_error = subtract_frame

            # cv2.imshow('roi', self.buffer_Frame)
            if subtract_frame > buff_error * 1.3:

                self.buffer_frame = roi_frame

                # textBrowser에 로그 기록
                now = time.strftime('%y%m%d_%H%M%S', time.localtime(time.time()))
                textBrowser.append(now + ', count=' + str(self.motion_count))

            else:
                self.buffer_frame = roi_frame

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

            h, w = roi_frame.shape
            roi_frame_cvt_mat = cv2.resize(roi_frame, (h, w))

            qt_image2 = QtGui.QImage(roi_frame_cvt_mat.data,
                                     h,
                                     w,
                                     roi_frame_cvt_mat.strides[0],
                                     QtGui.QImage.Format_Grayscale8)

            self.VideoSignal1.emit(qt_image1)
            self.VideoSignal2.emit(qt_image2)

            self.motion_count += 1

            loop = QtCore.QEventLoop()
            QtCore.QTimer.singleShot(33, loop.quit)
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

    textBrowser = QtWidgets.QTextBrowser()
    horizontal_layout = QtWidgets.QHBoxLayout()
    horizontal_layout.addWidget(image_viewer1)
    horizontal_layout.addWidget(image_viewer2)
    horizontal_layout.addWidget(textBrowser)

    push_button1 = QtWidgets.QPushButton('Start')
    push_button1.clicked.connect(vid.startVideo)
    vertical_layout = QtWidgets.QVBoxLayout()
    vertical_layout.addLayout(horizontal_layout)
    vertical_layout.addWidget(push_button1)

    layout_widget = QtWidgets.QWidget()
    layout_widget.setLayout(vertical_layout)

    main_window = QtWidgets.QMainWindow()
    main_window.setCentralWidget(layout_widget)
    main_window.show()
    app.exec_()
