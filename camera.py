import multiprocessing as mp
import cv2

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

            elif rec_dat == 3:
                print("gpio 출력")





            elif rec_dat == 2:
                # 요청이 없는 경우
                cap.release()
                run = False

        conn.close()

    def get_frame(self, mode):
        # 카메라 연결 프로세스에서 프레임 수신하는데 사용
        # resize 값 50% 증가인 경우 1.5
        if mode == "capture":
            # send request
            self.parent_conn.send(1)
            frame = self.parent_conn.recv()

            # reset request
            self.parent_conn.send(0)

            return frame

            # resize if needed
        elif mode == "signal":
            self.parent_conn.send(3)

            # reset request
            self.parent_conn.send(0)
