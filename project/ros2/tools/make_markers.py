import cv2

d = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
for i in range(4):
    if hasattr(cv2.aruco, 'generateImageMarker'):   # OpenCV >= 4.7
        img = cv2.aruco.generateImageMarker(d, i, 600)
    else:                                         # OpenCV 4.6 (Ubuntu 24.04)
        img = cv2.aruco.drawMarker(d, i, 600)
    img = cv2.copyMakeBorder(img, 80, 80, 80, 80, cv2.BORDER_CONSTANT, value=255)
    cv2.imwrite(f'aruco_4x4_{i}.png', img)
print('wrote aruco_4x4_0..3.png')
