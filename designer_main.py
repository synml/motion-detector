import sys
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5 import uic
import cv2

form_class = uic.loadUiType('main.ui')[0]


class MainWindow(QtWidgets.QMainWindow, QtCore.QObject, form_class):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)

        camera = cv2.VideoCapture(1)
        ret, img = camera.read()
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w, c = img.shape
        qimg = QtGui.QImage(img.data, w, h, w * c, QtGui.QImage.Format_RGB888)
        pixmap = QtGui.QPixmap.fromImage(qimg)
        self.label.setPixmap(pixmap)
        self.label.resize(pixmap.width(), pixmap.height())


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    app.exec_()
