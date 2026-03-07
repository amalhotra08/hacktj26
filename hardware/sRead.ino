#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BMP280.h>
#include <Adafruit_BNO055.h>
#include <utility/imumaths.h>

Adafruit_BMP280 bmp;
Adafruit_BNO055 bno = Adafruit_BNO055(55);
int analogPin = 7;   

void setup() {
  Serial.begin(115200);
  Wire.begin(41, 42);

  Serial.println("Starting sensors...");

  // BMP280
  if (!bmp.begin(0x77)) {
    Serial.println("BMP280 not found");
    while (1);
  }

  // BNO055
  if (!bno.begin()) {
    Serial.println("BNO055 not detected");
    while (1);
  }

  delay(1000);
  bno.setExtCrystalUse(true);

  Serial.println("Sensors ready");
}

void loop() {

  // -------- Analog AQI --------

  int analogValue = analogRead(analogPin);

  Serial.println("Analog Sensor");

  Serial.print("ADC Value: ");
  Serial.println(analogValue);


  // -------- BMP280 --------
  float temp = bmp.readTemperature();
  float pressure = bmp.readPressure() / 100.0;
  float altitude = bmp.readAltitude(1013.25);

  Serial.println("BMP280");
  Serial.print("Temperature: ");
  Serial.print(temp);
  Serial.println(" C");

  Serial.print("Pressure: ");
  Serial.print(pressure);
  Serial.println(" hPa");

  Serial.print("Altitude: ");
  Serial.print(altitude);
  Serial.println(" m");


  // -------- BNO055 --------
  imu::Vector<3> euler = bno.getVector(Adafruit_BNO055::VECTOR_EULER);
  imu::Vector<3> accel = bno.getVector(Adafruit_BNO055::VECTOR_ACCELEROMETER);

  Serial.println("BNO055");

  Serial.print("Yaw: ");
  Serial.print(euler.x());
  Serial.print("  Pitch: ");
  Serial.print(euler.y());
  Serial.print("  Roll: ");
  Serial.println(euler.z());

  Serial.print("Accel X: ");
  Serial.print(accel.x());
  Serial.print("  Y: ");
  Serial.print(accel.y());
  Serial.print("  Z: ");
  Serial.println(accel.z());

  Serial.println("-------------------------");

  delay(500);
}
