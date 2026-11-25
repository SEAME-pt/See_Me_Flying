import cv2
import numpy as np

SQ, COLS, ROWS = 80, 10, 7          # 10x7 squares = 9x6 inner corners
board = (np.indices((ROWS, COLS)).sum(axis=0) % 2) * 255
img = np.kron(board, np.ones((SQ, SQ))).astype(np.uint8)
img = cv2.copyMakeBorder(img, SQ, SQ, SQ, SQ, cv2.BORDER_CONSTANT, value=255)
cv2.imwrite('checkerboard_9x6.png', img)
print('wrote checkerboard_9x6.png')
