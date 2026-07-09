import cv2
import numpy as np

def detect_lane(frame):
    height, width = frame.shape[:2]
    roi = frame[int(height*0.5):height, :]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (9,9), 0)
    _, thresh = cv2.threshold(blurred, 85, 255, cv2.THRESH_BINARY_INV)
    kernel = np.ones((7,7), np.uint8)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=3)
    contours, _ = cv2.findContours(
        thresh,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    roi_center_x = roi.shape[1] // 2

    left_points = []
    right_contours = []
    for cnt in contours:

        area = cv2.contourArea(cnt)
        if area < 200:
            continue
        x,y,w,h = cv2.boundingRect(cnt)
        if h < 20:
            continue
        cx = x + w//2

        if cx < roi_center_x:
            for p in cnt:
                left_points.append(p[0])

        else:
            if area > 600:
                right_contours.append(cnt)

    left_line = None
    right_line = None

    if len(left_points) > 10:
        pts = np.array(left_points)
        vx,vy,x,y = cv2.fitLine(pts, cv2.DIST_L2,0,0.01,0.01)
        vx = vx[0]
        vy = vy[0]
        x = x[0]
        y = y[0]
        y1 = roi.shape[0]
        y2 = int(roi.shape[0]*0.3)
        if vy != 0:

            x1 = int(x + (y1 - y) * vx / vy)
            x2 = int(x + (y2 - y) * vx / vy)
            cv2.line(roi,(x1,y1),(x2,y2),(255,0,0),3)
            left_line = (x1,y1)



    if len(right_contours) > 0:
        right = max(right_contours, key=cv2.contourArea)
        x,y,w,h = cv2.boundingRect(right)
        right_line = (x+w//2, y+h)
        cv2.drawContours(roi,[right],-1,(0,255,0),3)
    error = None
    if left_line and right_line:
        center_x = (left_line[0] + right_line[0]) // 2
        error = center_x - roi_center_x
        cv2.circle(roi,(center_x,roi.shape[0]-10),6,(0,255,255),-1)
        cv2.putText(
            roi,
            f"Error: {error}",
            (10,30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0,0,255),
            2
        )
    cv2.line(roi, (roi_center_x, 0), (roi_center_x, roi.shape[0]), (0,0,255), 2)
    return error, roi, thresh