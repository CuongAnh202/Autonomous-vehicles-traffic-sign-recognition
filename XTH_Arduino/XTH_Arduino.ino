#include <Servo.h>

Servo steering;
const int servoPin = 10;
const int steeringCenter = 90;   // Góc trung tâm của servo (xe đi thẳng)

// Khai báo chân điều khiển động cơ
const int ENA = 6, IN1 = 11, IN2 = 12;  // Trái
const int ENB = 5, IN3 = 3, IN4 = 4;    // Phải

int baseSpeed = 100;            // Tốc độ cơ bản
const int diffFactor = 110;     // Hệ số chênh lệch giữa hai bánh khi rẽ (giá trị càng lớn xe quay càng gắt)

unsigned long lastCommandTime = 0;
const unsigned long timeout = 600;    // Quá 600ms ko nhận tín hiệu -> dừng xe

unsigned long lastSendTime = 0;
const unsigned long sendInterval = 50;   // Gửi dữ liệu mỗi 50ms

int targetAngle = 88;         // Góc mong muốn
float currentAngle = 88;      // Góc thực tế

int check = 0;      // Trạng thái nhận từ Serial

void smoothServoTo(int target, float factor) {
  currentAngle = factor * target + (1 - factor) * currentAngle;
  steering.write((int)currentAngle);
}

void check_Sign(int &leftSpeed, int &rightSpeed) {
  switch (check) {
    case 2:
      baseSpeed = 150;
      break;
    case 4:
      baseSpeed = 170;
      break;
    case 5:
      baseSpeed = 120;
      break;
    case 3:
      baseSpeed = 0;
      leftSpeed = 0;
      rightSpeed = 0;
      return;
    default:
      baseSpeed = 100;
      break;
  }
}

// Tính toán tốc độ quay khi rẽ
void calculateMotorSpeed(int angle, int &leftSpeed, int &rightSpeed) {
  int diff = angle - steeringCenter;    // Sai lệch góc

  leftSpeed = baseSpeed;
  rightSpeed = baseSpeed;

  int delta = (abs(diff) * diffFactor) / 45;    // Chênh lệch tốc độ

  if (diff > 0) {         // Rẽ phải
    leftSpeed += delta;
    rightSpeed -= delta;
  } 
  else if (diff < 0) {    // Rẽ trái
    rightSpeed += delta;
    leftSpeed -= delta;
  }

  if (abs(diff) > 20) {   // Giảm tốc khi cua gắt
    float scale = constrain(1 - (abs(diff) / 150.0), 0.4, 1.0);
    leftSpeed *= scale;
    rightSpeed *= scale;
  }

  leftSpeed = constrain(leftSpeed, 0, 255);
  rightSpeed = constrain(rightSpeed, 0, 255);
}

// Thiết lập chiều quay ( quay tiến )
void runForward(int leftSpeed, int rightSpeed) {
  digitalWrite(IN1, HIGH); 
  digitalWrite(IN2, LOW);

  digitalWrite(IN3, HIGH); 
  digitalWrite(IN4, LOW);
  // Xuất PWM (0-255)
  analogWrite(ENA, leftSpeed);
  analogWrite(ENB, rightSpeed);
}

// Dừng động cơ
void stopMotors() {
  analogWrite(ENA, 0);
  analogWrite(ENB, 0);

  digitalWrite(IN1, LOW); 
  digitalWrite(IN2, LOW);

  digitalWrite(IN3, LOW); 
  digitalWrite(IN4, LOW);
}

// Gửi dữ liệu phản hồi
void sendSpeedData(int baseSpeed, int leftSpeed, int rightSpeed) {
  if (millis() - lastSendTime >= sendInterval) {
    lastSendTime = millis();

    Serial.print("FB,");
    Serial.print(baseSpeed);
    Serial.print(",");
    Serial.print(leftSpeed);
    Serial.print(",");
    Serial.println(rightSpeed);
  }
}

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(5);   // Giảm delay khi đọc Serial

  // Động cơ
  pinMode(ENA, OUTPUT); 
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(ENB, OUTPUT); 
  pinMode(IN3, OUTPUT); 
  pinMode(IN4, OUTPUT);

  // Servo
  steering.attach(servoPin);
  steering.write(steeringCenter);

  lastCommandTime = millis();     // Thời gian nhận lệnh cuối

  stopMotors();
}

void loop() {
  // Đọc dữ liệu từ Serial
  if (Serial.available() > 0) {
    String data = Serial.readStringUntil('\n');   
    data.trim();    // Xóa khoảng trắng

    int commaIndex = data.indexOf(',');   // Tìm dấu phẩy

    if (commaIndex > 0) {
      int angle = data.substring(0, commaIndex).toInt();    // Tách góc
      check = data.substring(commaIndex + 1).toInt();       // Tách dữ liệu biển báo

      if (angle > 0) {
        targetAngle = constrain(angle, 30, 150);    // Giới hạn góc
        lastCommandTime = millis();   // Cập nhật thời gian nhận lệnh
      }
    }
  }

  int leftSpeed = baseSpeed;
  int rightSpeed = baseSpeed;

  // ===== TIMEOUT =====
  if (millis() - lastCommandTime > timeout) {
    baseSpeed = 0;
    leftSpeed = 0;
    rightSpeed = 0;

    stopMotors();
    smoothServoTo(steeringCenter, 0.3);  
    sendSpeedData(baseSpeed, leftSpeed, rightSpeed);
    return;
  }

  check_Sign(leftSpeed, rightSpeed);

  // ===== DỪNG XE =====
  if (baseSpeed == 0) {
    leftSpeed = 0;
    rightSpeed = 0;

    stopMotors();
    smoothServoTo(steeringCenter, 0.3);
    sendSpeedData(baseSpeed, leftSpeed, rightSpeed);
    return;
  }

  float diffServo = abs(targetAngle - currentAngle);
  float factor = (diffServo > 20) ? 0.75 : 0.45;

  smoothServoTo(targetAngle, factor);

  calculateMotorSpeed(targetAngle, leftSpeed, rightSpeed); 

  runForward(leftSpeed, rightSpeed);

  sendSpeedData(baseSpeed, leftSpeed, rightSpeed);
}

