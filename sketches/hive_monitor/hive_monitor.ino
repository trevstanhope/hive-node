/* 
  Hive Monitor ("Power Cycle" Version)
  Developed by Trevor Stanhope
  DAQ controller for hive sensor monitoring.
*/

/* --- Libraries --- */
#include "stdio.h"
#include <Wire.h>
#include <Adafruit_BMP085.h>
#include <DHT.h>

/* --- Definitions --- */
#define DHT_INTERNAL_PIN 4
#define DHT_EXTERNAL_PIN 5
#define VOLTS_PIN A0
#define AMPS_PIN A1
#define RESET_PIN A2
#define RPI_POWER_PIN A3
#define DHT_TYPE DHT22

/* --- Constants --- */
const unsigned int BAUD = 9600;
const unsigned int CHARS = 8;
const unsigned int BUFFER = 128;
const unsigned int DIGITS = 4;
const unsigned int PRECISION = 2;
const unsigned int ON_WAIT = 500;
const unsigned int OFF_WAIT = 1000;
const unsigned int BOOT_WAIT = 5000;
const unsigned int RESET_WAIT = 500; //
const unsigned int PIN_WAIT = 200; // wait for pin to initialize
const unsigned int SERIAL_WAIT = 1000; // wait for serial connection to start
const unsigned int SHUTDOWN_WAIT = 5000; // wait for pi to shutdown
const unsigned int ON_CYCLES = 60; // counter value when it will turn off
const unsigned int OFF_CYCLES = 1200; // counter value when it will back turn on

/* --- Functions --- */
float get_int_temp(void);
float get_int_humidity(void);
float get_ext_temp(void);
float get_ext_humidity(void);
float get_volts(void);
float get_amps(void);

/* --- Objects --- */
DHT int_dht(DHT_INTERNAL_PIN, DHT_TYPE);
DHT ext_dht(DHT_EXTERNAL_PIN, DHT_TYPE);
Adafruit_BMP085 bmp;

/* --- Variables --- */
char INT_TEMPERATURE[CHARS];
char INT_HUMIDITY[CHARS];
char EXT_TEMPERATURE[CHARS];
char EXT_HUMIDITY[CHARS];
char VOLTS[CHARS];
char AMPS[CHARS];
char PASCALS[CHARS];
char JSON[BUFFER];
int CYCLES = 0;
int INCOMING = 0;

/* --- Setup --- */
void setup() {
  digitalWrite(RESET_PIN, HIGH);
  digitalWrite(RPI_POWER_PIN, HIGH);
  delay(PIN_WAIT);
  pinMode(RESET_PIN, OUTPUT);
  pinMode(RPI_POWER_PIN, OUTPUT);
  delay(BOOT_WAIT); // Serial cannot be on during RPi boot
  Serial.begin(BAUD);
  delay(SERIAL_WAIT); // wait for serial to establish
  int_dht.begin();
  ext_dht.begin();
  bmp.begin();
}

/* --- Loop --- */
void loop() {
  // Flush incoming serial buffer to prevent mem leaks
  while (Serial.available() > 0) {
    INCOMING = Serial.read();
  }
  if (CYCLES < ON_CYCLES) {
    dtostrf(get_ext_temp(), DIGITS, PRECISION, EXT_TEMPERATURE); 
    dtostrf(get_ext_humidity(), DIGITS, PRECISION, EXT_HUMIDITY);
    dtostrf(get_int_temp(), DIGITS, PRECISION, INT_TEMPERATURE);
    dtostrf(get_int_humidity(), DIGITS, PRECISION, INT_HUMIDITY);
    dtostrf(get_pressure(), DIGITS, PRECISION, PASCALS);
    dtostrf(get_volts(), DIGITS, PRECISION, VOLTS);
    dtostrf(get_amps(), DIGITS, PRECISION, AMPS);
    sprintf(JSON, "{'cycles':%d,'int_t':%s,'ext_t':%s,'int_h':%s,'ext_h':%s,'volts':%s,'amps':%s, 'bars':%s}", CYCLES, INT_TEMPERATURE, EXT_TEMPERATURE, INT_HUMIDITY, EXT_HUMIDITY, VOLTS, AMPS, PASCALS);
    Serial.println(JSON);
    delay(ON_WAIT);
  }
  else if (CYCLES == ON_CYCLES) {
    Serial.flush();
    Serial.end();
    delay(SHUTDOWN_WAIT);
    digitalWrite(RPI_POWER_PIN, LOW);
  }
  else if (CYCLES < (ON_CYCLES + OFF_CYCLES)) {
    delay(OFF_WAIT);
  }
  else {
    digitalWrite(RESET_PIN, LOW);
  }
  CYCLES++;
}

/* --- Sensor Functions --- */
// Internal Humidity
float get_int_humidity() {
  float val = int_dht.readHumidity();
  if (isnan(val)) {
    return 0;
  }
  else {
    return val;
  }
}

// Internal Temperature
float get_int_temp() {
  float val = int_dht.readTemperature(); //  Serial.println(val);
  if (isnan(val)) {
    return 0;
  }
  else {
    return val;
  }
}

// Get External Humidity
float get_ext_humidity() {
  float val = ext_dht.readHumidity();
  if (isnan(val)) {
    return 0;
  }
  else {
    return val;
  }
}

// Get External Temperature
float get_ext_temp() {
  float val = ext_dht.readTemperature();
  if (isnan(val)) {
    return 0;
  }
  else {
    return val;
  }
}

// Barometric Pressure
float get_pressure() {
  float val = bmp.readPressure();
  return val;
}

// Amperage
float get_amps() {
  float val = (512 - analogRead(AMPS_PIN)) / 30.0;
  return val;
}

// Voltage
float get_volts() {
  float val = analogRead(VOLTS_PIN) / 40.96;
  return val;
}
