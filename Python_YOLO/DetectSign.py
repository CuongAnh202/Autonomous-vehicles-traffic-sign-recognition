import cv2
from ultralytics import YOLO

# load model
model = YOLO("best.pt")

def detect_sign(frame):

    sign = None

    results = model(frame, imgsz=320, conf=0.75, verbose=False)

    for r in results:

        boxes = r.boxes
        if boxes is None:
            continue

        for box in boxes:

            x1, y1, x2, y2 = box.xyxy[0]

            x1 = int(x1)
            y1 = int(y1)
            x2 = int(x2)
            y2 = int(y2)

            conf = float(box.conf[0])
            cls = int(box.cls[0])

            label = model.names[cls]

            sign = label

            cv2.rectangle(frame, (x1,y1), (x2,y2), (0,0,255), 2)

            text = f"{label} {conf:.2f}"

            cv2.putText(frame,
                        text,
                        (x1, y1-10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0,255,0),
                        2)

    return sign, frame