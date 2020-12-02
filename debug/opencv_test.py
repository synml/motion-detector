import cv2

img = cv2.imread('../res/1.jpg')
cv2.imshow('image', img)
cv2.imshow('image2', img)
cv2.waitKey(0)
