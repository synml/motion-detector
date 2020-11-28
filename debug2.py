import sys
from PyQt5 import QtWidgets

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    window = QtWidgets.QWidget()
    window.resize(289, 170)
    window.setWindowTitle("FIrst Qt Program")

    label = QtWidgets.QLabel('Hello Qt', window)
    label.move(110, 80)

    window.show()
    app.exec_()
