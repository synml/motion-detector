import sys
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5 import uic
import cv2

form_class = uic.loadUiType('main.ui')[0]


class Camera(QtCore.QObject):
    def __init__(self):
        super(Camera, self).__init__()
        self.cam = cv2.VideoCapture(0)

    def start(self):
        while True:
            ret, img = self.cam.read()
            if not ret:
                print('camera read error')
                return

            h, w, c = img.shape
            qimg = QtGui.QImage(img.data, w, h, w * c, QtGui.QImage.Format_RGB888)
            pixmap = QtGui.QPixmap.fromImage(qimg)
            self.label.setPixmap(pixmap)
            self.label.resize(pixmap.width(), pixmap.height())
            cv2.waitKey(60)


class MainWindow(QtWidgets.QMainWindow, form_class):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)

        self.thread = QtCore.QThread()
        self.thread.start()
        self.camera = Camera()
        self.camera.moveToThread(self.thread)

        self.startButton.clicked.connect(self.camera.start)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    app.exec_()
