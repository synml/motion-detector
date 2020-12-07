import sys
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5 import uic

form_class = uic.loadUiType('main.ui')[0]



class MainWindow(QtWidgets.QMainWindow, form_class):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)

        pixmap = QtGui.QPixmap('res/1.jpg')
        self.label.setPixmap(pixmap)
        self.label.resize(pixmap.width(), pixmap.height())


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    thread = QtCore.QThread()
    thread.start()
    win = MainWindow()
    win.moveToThread(thread)
    win.show()
    app.exec_()
