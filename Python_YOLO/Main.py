import cv2
import serial
import time
import threading
import numpy as np

from DetectLane import detect_lane
from DetectSign import detect_sign

# ===== SERIAL =====
# Chạy trên Windows: COM5
# Chạy trên Raspberry Pi: đổi thành '/dev/ttyUSB0' hoặc '/dev/ttyACM0'
arduino = serial.Serial('COM5', 115200, timeout=1)
time.sleep(2)

# ===== CAMERA USB =====
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 480)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 320)

# ===== GLOBAL =====
current_frame = None
detected_sign = None
yolo_display = None
current_sign = 0

last_sign = None
sign_count = 0

left_speed = 0
base_speed = 0
right_speed = 0

# ===== RẼ PHẢI QUA NGÃ 3 =====
turn_right_mode = False
turn_right_start_time = 0

TURN_RIGHT_DURATION = 2.5   
TURN_RIGHT_ANGLE = 87         
TURN_RIGHT_SPEED_SIGN = 2    

# ===== YOLO THREAD =====
def yolo_thread():
    global current_frame, detected_sign, yolo_display
    global last_sign, sign_count

    while True:
        if current_frame is None:
            time.sleep(0.01)
            continue

        frame = current_frame.copy()

        sign, yolo_frame = detect_sign(frame)
        yolo_display = yolo_frame

        if sign is not None:
            if sign == last_sign:
                sign_count += 1
            else:
                sign_count = 0

            if sign_count >= 2:
                detected_sign = sign

            last_sign = sign

        time.sleep(0.03)


# ===== SERIAL READ THREAD =====
def serial_read_thread():
    global base_speed, left_speed, right_speed

    while True:
        try:
            if arduino.in_waiting > 0:
                data = arduino.readline().decode('utf-8', errors='ignore').strip()

                if data.startswith("FB,"):
                    parts = data.split(",")

                    if len(parts) == 4:
                        base_speed = int(parts[1])
                        left_speed = int(parts[2])
                        right_speed = int(parts[3])

                        print(
                            f"[ARDUINO] Base: {base_speed} | "
                            f"Left: {left_speed} | Right: {right_speed}"
                        )

        except Exception as e:
            print("Serial read error:", e)

        time.sleep(0.01)


# ===== START THREAD =====
threading.Thread(target=yolo_thread, daemon=True).start()
threading.Thread(target=serial_read_thread, daemon=True).start()


# ===== MAIN LOOP =====
while True:
    ret, frame = cap.read()

    if not ret:
        print("Camera lỗi!")
        continue

    frame = cv2.resize(frame, (720, 320))
    current_frame = frame.copy()

    error, roi, thresh = detect_lane(frame)

    now = time.time()

    # ===== XỬ LÝ BIỂN BÁO =====
    if detected_sign is not None:
        print("Detected:", detected_sign)

        if detected_sign == "Re Phai":
            # Gặp biển rẽ phải:
            # Giữ tốc độ như biển tăng tốc
            # Giữ góc lái 87 trong 3 giây
            turn_right_mode = True
            turn_right_start_time = now
            current_sign = TURN_RIGHT_SPEED_SIGN

            print("[MODE] Re Phai -> Angle 87 trong 3s, toc do Tang Toc")

        elif detected_sign == "Dung Lai":
            current_sign = 3

        elif detected_sign == "Tang Toc":
            current_sign = 4

        elif detected_sign == "Giam Toc":
            current_sign = 5

        print("Current Sign:", current_sign)

        detected_sign = None

    # ===== XỬ LÝ GÓC LÁI =====
    if turn_right_mode:
        # Trong 3 giây qua ngã 3:
        # Không dùng error của detect_lane
        steering_angle = TURN_RIGHT_ANGLE
        current_sign = TURN_RIGHT_SPEED_SIGN

        if now - turn_right_start_time >= TURN_RIGHT_DURATION:
            turn_right_mode = False
            current_sign = 0
            print("[MODE] Qua nga 3 xong -> quay lai bam lane binh thuong")

    else:
        # Bám line bình thường
        if error is not None:
            steering_angle = int(89 + 0.3 * error)
            steering_angle = max(60, min(120, steering_angle))
        else:
            steering_angle = 89

    # ===== HIỂN THỊ GÓC LÁI =====
    if steering_angle > 89:
        angle_color = (0, 0, 255)
    elif steering_angle < 89:
        angle_color = (255, 0, 0)
    else:
        angle_color = (0, 150, 0)

    cv2.putText(
        roi,
        f"Angle: {steering_angle}",
        (10, 60),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        angle_color,
        2
    )


    # ===== GỬI ARDUINO =====
    arduino.write(
        (str(steering_angle) + "," + str(current_sign) + "\n").encode()
    )

    print(
        f"[SEND] Angle: {steering_angle} | Sign: {current_sign} | "
        f"TurnRight: {turn_right_mode} | "
       )

    # ===== HIỂN THỊ ẢNH =====
    cv2.imshow("Lane ROI", roi)
    cv2.imshow("Threshold", thresh)

    if yolo_display is not None:
        cv2.imshow("YOLO Sign Detect", yolo_display)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    time.sleep(0.02)

arduino.close()
cap.release()
cv2.destroyAllWindows()