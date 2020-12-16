import cv2
import numpy as np


camera = cv2.VideoCapture('1230.avi')
i=0

print(np.abs(1)-np.abs(10))
while True:
    i+=1
    ret, frame = camera.read()
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    np.savetxt('nparray/test'+str(i), frame, fmt='%.18e')
    cv2.imshow('video', frame)

    cv2.waitKey(0)

