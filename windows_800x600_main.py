import multiprocessing as mp
import sys
import time
import os
import cv2
import numpy as np
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5 import uic

try:
    import RPi.GPIO as GPIO

    GPIO.setMode(GPIO.BCM)
    rasp = True
    #idle = 25
    alert = 24
    GPIO.setup(alert, GPIO.OUT)
except ModuleNotFoundError:
    rasp = False
    #idle = 25
    alert = 24

"""
전역 설정란

라벨 크기 : 800(w 너비)  600(h 높이)

"""
idleTime = 10 # second
threshold = 1.6

label_w = 800
label_h = 600
#
def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


mainUI = resource_path(r'C:\Users\hoi\Desktop\motion-detector\main.ui')
setOptionDialogUI = resource_path(r'C:\Users\hoi\Desktop\motion-detector\setOptionDialog.ui')
infoDialogUI = resource_path(r'C:\Users\hoi\Desktop\motion-detector\infoDialog.ui')

mainUi = uic.loadUiType(mainUI)[0]
setOptionDialogUi = uic.loadUiType(setOptionDialogUI)[0]
infoDialogUi = uic.loadUiType(os.path.abspath(infoDialogUI))[0]


class IPCamera:
    def __init__(self, rtsp_url: str):
        # 데이터 프로세스 전송 파이프
        self.rtsp_url = rtsp_url
        self.parent_conn, child_conn = mp.Pipe()
        # load process
        self.p = mp.Process(target=self.update, args=(child_conn, rtsp_url))
        # start process
        self.p.daemon = True
        self.p.start()

    def get_first_frame(self):
        _, frame = cv2.VideoCapture(self.rtsp_url).read()
        return frame

    def end(self):
        # 프로세스 종료 요청
        self.parent_conn.send(2)

    def update(self, conn, rtsp_url: str):
        # load cam into separate process
        cap = cv2.VideoCapture(rtsp_url)

        run = True
        while run:
            # 버퍼에서 카메라 데이터 수신
            cap.grab()

            # 입력 데이터 수신
            rec_dat = conn.recv()

            if rec_dat == 1:
                # 프레임 수신 완료했을 경우
                ret, frame = cap.read()
                conn.send(frame)

            elif rec_dat == 2:
                # 요청이 없는 경우
                cap.release()
                run = False

        conn.close()

    def get_frame(self, resize=None):
        # 카메라 연결 프로세스에서 프레임 수신하는데 사용
        # resize 값 50% 증가인 경우 1.5

        # send request
        self.parent_conn.send(1)
        frame = self.parent_conn.recv()

        # reset request
        self.parent_conn.send(0)

        # resize if needed
        if resize is None:
            return frame
        else:
            return cv2.resize(frame, None, fx=resize, fy=resize)

def setUrl(cameraProtocol, cameraID, cameraPassword, cameraIP, cameraPort, cameraProfileName):
    return  cameraProtocol + '://' + cameraID + ':' \
    + cameraPassword + '@' + cameraIP + ':' + cameraPort + '/' + cameraProfileName + '/media.smp'


class MotionDetector(QtCore.QObject):
    idleTime = 5

    def __init__(self, label, textBrowser):
        super(MotionDetector, self).__init__()

        self.cameraProtocol = 'rtsp'
        self.cameraID = 'admin'
        self.cameraPassword = '1q2w3e4r5t'
        self.cameraIP = '192.168.0.4'
        self.cameraPort = '554'
        self.cameraProfileName = 'test'

        self.label = label
        self.textBrowser = textBrowser
        self.label.resize(label_w, label_h)
        self.logic = True  # 반복 루프 제어
        self.default_x, self.default_y, self.w, self.h = -1, -1, -1, -1
        self.loopFlag = False
        self.buffer_frame = None
        #self.total_frame = 0
        self.buffError = None  # 이전 프레임 기준 오차율
        self.idleMode = False  # Flag변수, 이상 감지 후 유휴 상태 돌입
        global idleTime, threshold
        self.idleTime = idleTime
        self.threshold = threshold
        self.fps = 1


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
                cv2.imshow('Set RoI', img_draw)

    def setRoI(self, frame):
        cv2.startWindowThread()
        cv2.imshow('Set RoI', frame)
        cv2.setMouseCallback("Set RoI", self.onMouse, param=frame)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    def write_log(self, message: str):
        now = time.localtime()
        self.textBrowser.append(message + ': ' + str(now.tm_year) + "년 " + str(now.tm_mon) + "월 "
                                + str(now.tm_mday) + "일 " + str(now.tm_hour) + "시 "
                                + str(now.tm_min) + "분 " + str(now.tm_sec) + "초")

    def loop(self):
        if self.loopFlag:return
        self.loopFlag = True

        self.ip_camera = IPCamera(setUrl(self.cameraProtocol, self.cameraID, self.cameraPassword,
                                         self.cameraIP, self.cameraPort, self.cameraProfileName))
        self.frame = cv2.cvtColor(self.ip_camera.get_first_frame(), cv2.COLOR_BGR2GRAY)
        self.frame = cv2.resize(self.frame, dsize=(800, 600), interpolation=cv2.INTER_AREA)

        # textBrowser 이벤트 처리
        self.write_log('감지 시작')
        # ROI 처리
        if self.default_x == -1:
            self.setRoI(self.frame)

        #첫 프레임 로드 받은 후 연산 처리 작업
        if self.buffer_frame is None:  # 첫 프레임인 경우에
            self.frame = self.ip_camera.get_frame()
            self.frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)
            self.frame = cv2.resize(self.frame, dsize=(800, 600), interpolation=cv2.INTER_AREA)
            self.buffer_frame = self.frame[self.default_y:self.default_y + self.h,
                                self.default_x:self.default_x + self.w]
            subtract_frame = np.round(
                np.sqrt(np.sum(np.abs(self.buffer_frame - self.buffer_frame) ** 2)))  # L2 DISTANCE
            self.buffError = subtract_frame
            # 수정사항 -----------------
            bounding_box_frame = self.frame.copy()

            output_frame = cv2.rectangle(bounding_box_frame, (self.default_x, self.default_y),
                                         (self.default_x + self.w, self.default_y + self.h), (0, 255, 0),
                                         thickness=5)

            qimg = QtGui.QImage(output_frame.data, label_w, label_h,
                                output_frame.strides[0], QtGui.QImage.Format_Grayscale8)
            pixmap = QtGui.QPixmap.fromImage(qimg)
            self.label.setPixmap(pixmap)

        # 두 번째 프레임 처리

        self.frame = self.ip_camera.get_frame()
        self.frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)

        self.roi_frame = self.frame[self.default_y:self.default_y + self.h, self.default_x:self.default_x + self.w]
        subtract_frame = np.round(np.sqrt(np.sum(np.abs(self.buffer_frame - self.roi_frame) ** 2)))

        self.buffer_frame = self.roi_frame
        self.buffError = subtract_frame
        bounding_box_frame = self.frame.copy()
        output_frame = cv2.rectangle(bounding_box_frame, (self.default_x, self.default_y),
                                     (self.default_x + self.w, self.default_y + self.h), (0, 255, 0),
                                     thickness=5)
        output_frame = cv2.resize(output_frame, dsize=(800, 600), interpolation=cv2.INTER_AREA)
        qimg = QtGui.QImage(output_frame.data, label_w, label_h,
                            output_frame.strides[0], QtGui.QImage.Format_Grayscale8)
        pixmap = QtGui.QPixmap.fromImage(qimg)

        self.label.setPixmap(pixmap)

        previous_time = time.time()

        while self.logic:
            self.frame = self.ip_camera.get_frame()
            self.frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)
            self.frame = cv2.resize(self.frame, dsize=(800, 600), interpolation=cv2.INTER_AREA)
            current_time = time.time() - previous_time

            if current_time > 1. / self.fps:
                previous_time = time.time()


                if self.buffer_frame is None:  # 첫 프레임인 경우에
                    self.buffer_frame = self.frame[self.default_y:self.default_y + self.h,
                                        self.default_x:self.default_x + self.w]

                self.roi_frame = self.frame[self.default_y:self.default_y + self.h,
                                 self.default_x:self.default_x + self.w]


                subtract_frame = np.round(
                    np.sqrt(np.sum(np.abs(self.buffer_frame - self.roi_frame) ** 2)))  # L2 DISTANCE

                if self.buffError is None:
                    self.buffError = subtract_frame

                # 유휴 상태
                if self.idleMode:
                    win.statusLabel.setText("유휴 상태")
                    win.idleTimeLcd.display((self.idleInitTime + self.idleTime) - time.time())

                    if self.idleInitTime + self.idleTime <= time.time():
                        self.idleMode = False  # 유휴상태 해제
                        # self.discount = 0

                # 일반 감지 모드
                else:
                    self.idleInitTime = time.time()
                    win.statusLabel.setText("일반 감지 상태")
                    win.idleTimeLcd.display(0)

                    if subtract_frame > self.buffError * self.threshold:
                        if rasp:
                            GPIO.output(alert, GPIO.HIGH)

                        self.write_log('이상 감지')
                        self.idleMode = True


                    else:
                        if rasp:
                            GPIO.output(alert, GPIO.LOW)

                self.buffer_frame = self.roi_frame

                self.buffError = subtract_frame
            bounding_box_frame = self.frame.copy()

            output_frame = cv2.rectangle(bounding_box_frame, (self.default_x, self.default_y),
                                         (self.default_x + self.w, self.default_y + self.h), (0, 255, 0),
                                         thickness=5)
            output_frame = cv2.resize(output_frame, dsize=(800, 600), interpolation=cv2.INTER_AREA)

            qimg = QtGui.QImage(output_frame.data, label_w, label_h,
                                output_frame.strides[0], QtGui.QImage.Format_Grayscale8)
            pixmap = QtGui.QPixmap.fromImage(qimg)
            self.label.setPixmap(pixmap)



class InfoDialog(QtWidgets.QDialog, infoDialogUi):
    def __init__(self):
        super(InfoDialog, self).__init__()
        self.setupUi(self)


class SetOptionDialog(QtWidgets.QDialog, setOptionDialogUi):
    def __init__(self):
        super(SetOptionDialog, self).__init__()
        self.setupUi(self)

        self.cameraID.setText(str('admin'))
        self.cameraPW.setText(str('1q2w3e4r5t'))
        self.cameraIP.setText(str('192.168.0.4'))
        self.cameraProfile.setText(str('test'))

        self.cameraID.textChanged.connect(self.cameraidValueChanged)
        self.cameraPW.textChanged.connect(self.camerapwValueChanged)
        self.cameraIP.textChanged.connect(self.cameraipValueChanged)
        self.cameraProfile.textChanged.connect(self.cameraprofileValueChanged)


        self.idleTimeSpinBox.setValue(idleTime)
        self.thresholdSlider.setSliderPosition(int((threshold - 1) / 0.05) + 1)
        self.thresholdLCD.display((threshold - 1) / 0.05)

        self.idleTimeSpinBox.valueChanged.connect(self.idleTimeValueChanged)
        self.thresholdSlider.valueChanged.connect(self.thresholdValueChanged)
        self.fpsSlider.valueChanged.connect(self.fpsValueChanged)

    def cameraidValueChanged(self):
        win.motionDetector.cameraID = self.cameraID.text()

    def camerapwValueChanged(self):
        win.motionDetector.cameraPassword = self.cameraPW.text()

    def cameraipValueChanged(self):
        win.motionDetector.cameraIP = self.cameraIP.text()

    def cameraprofileValueChanged(self):
        win.motionDetector.cameraProfileName = self.cameraProfile.text()

    def idleTimeValueChanged(self):
        win.motionDetector.idleTime = self.idleTimeSpinBox.value()

    def thresholdValueChanged(self):
        win.motionDetector.threshold = 1 + (0.05 * self.thresholdSlider.value())
        self.thresholdLCD.display(self.thresholdSlider.value())

    def fpsValueChanged(self):
        win.motionDetector.fps = self.fpsSlider.value()
        self.fpsLCD.display(self.fpsSlider.value())


class MainWindow(QtWidgets.QMainWindow, mainUi):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)

        self.thread = QtCore.QThread()
        self.thread2 = QtCore.QThread()
        self.thread.start()
        self.thread2.start()

        self.motionDetector = MotionDetector(self.label, self.textBrowser)
        self.motionDetector.moveToThread(self.thread)
        self.setOptionDialog = SetOptionDialog()
        self.setOptionDialog.moveToThread(self.thread2)
        self.infoDialog = InfoDialog()

        self.startButton.clicked.connect(self.motionDetector.loop)
        self.setOptionButton.clicked.connect(self.setOptionDialog.show)
        self.exitButton.clicked.connect(self.quit)
        self.actionQuit.triggered.connect(self.quit)
        self.actionSetOption.triggered.connect(self.setOptionDialog.show)
        self.actionInfo.triggered.connect(self.infoDialog.show)

    def quit(self):
        self.motionDetector.logic = False  # 메인로직 반복 종료
        try:
            self.motionDetector.ip_camera.end()
        except:
            print("local")
            pass

        if rasp:
            GPIO.cleanup()
        app.instance().quit()
        app.quit()
        win.thread.exit()
        win.thread.quit()
        win.thread.wait(5000)


if __name__ == "__main__":
    mp.freeze_support() # for windows
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    app.exec_()