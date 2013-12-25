
/* 
  HiveMind Arduino Sensor Monitor
  Developed by Trevor Stanhope
  DAQ controller for single-hive urban beekeepers.
*/

/* --- Libraries --- */
#include "stdio.h"
#include <DHT.h>
#include <SoftwareSerial.h>
//#include <SD.h>

/* --- Pins --- */
#define SD_PIN 10
#define DHT_INTERNAL_PIN A0
#define DHT_EXTERNAL_PIN A1
#define RPI_POWER_PIN A5

/* --- Values --- */
#define DHT_TYPE DHT11
#define BAUD 9600
#define CHARS 8
#define BUFFER 128
#define DIGITS 4
#define PRECISION 2
#define INTERVAL 1
#define UPTIME 600
#define DOWNTIME 3000

/* --- Functions --- */
float get_int_C(void);
float get_int_RH(void);
float get_ext_C(void);
float get_ext_RH(void);

/* --- Objects --- */
DHT internal(DHT_INTERNAL_PIN, DHT_TYPE);
DHT external(DHT_EXTERNAL_PIN, DHT_TYPE);
//Sd2Card card;
//SdVolume volume;
//SdFile root;

/* --- Strings --- */
char int_C[CHARS];
char int_RH[CHARS];
char ext_C[CHARS];
char ext_RH[CHARS];
char output[BUFFER];

/* --- State --- */
int counter = 0; // seconds on
boolean on = true; // start on

/* --- Setup --- */
void setup() {
  
  // Setup Serial
  Serial.begin(BAUD);
  
  // Setup Relay
  pinMode(RPI_POWER_PIN, OUTPUT);
  digitalWrite(RPI_POWER_PIN, LOW); // start on
  
  // Setup SD
//  pinMode(SD_PIN, OUTPUT);
//  while (!card.init(SPI_HALF_SPEED, SD_PIN)) {
//    continue; // connection failed
//  }
//  if (!volume.init(card)) {
//    return;
//  }
//  root.openRoot(volume);
  
  // Setup Sensors
  internal.begin();
  external.begin();
}

/* --- Loop --- */
void loop() {
  
  // Read Sensors
  dtostrf(get_ext_RH(), DIGITS, PRECISION, ext_RH); 
  dtostrf(get_ext_C(), DIGITS, PRECISION, ext_C);
  dtostrf(get_int_RH(), DIGITS, PRECISION, int_RH);
  dtostrf(get_int_C(), DIGITS, PRECISION, int_C);
  sprintf(output, "{'Internal_C':%s, 'External_C':%s, 'Internal_RH':%s, 'External_RH':%s}", int_C, ext_C, int_RH, ext_RH);
  
  // Log to file
//  File dataFile = SD.open("datalog.txt", FILE_WRITE);
//  dataFile.print(output);
//  dataFile.close();
  
  // Send to RaspberryPi
  Serial.println(output);
  delay(1000*INTERVAL);
  Serial.flush();
  
  // Set RaspberryPi State
  if (on) {
    if (counter <= UPTIME) {
      counter += INTERVAL;
    }
    else {
      counter = 0;
      on = false;
      digitalWrite(RPI_POWER_PIN, HIGH);
    }
  }
  else {
    if (counter <= DOWNTIME) {
      counter += INTERVAL;
    }
    else {
      counter = 0;
      on = true;
      digitalWrite(RPI_POWER_PIN, LOW);
    }
  }
}

/* --- Get Internal Humidity --- */
float get_int_RH() {
  float val = internal.readHumidity();
  if (isnan(val)) {
    return 0;
  }
  else {
    return val;
  }
}

/* --- Get Internal Temperature --- */
float get_int_C() {
  float val = internal.readTemperature(); //  Serial.println(val);
  if (isnan(val)) {
    return 0;
  }
  else {
    return val;
  }
}

/* --- Get External Humidity --- */
float get_ext_RH() {
  float val = external.readHumidity();
  if (isnan(val)) {
    return 0;
  }
  else {
    return val;
  }
}

/* --- Get External Temperature --- */
float get_ext_C() {
  float val = external.readTemperature();
  if (isnan(val)) {
    return 0;
  }
  else {
    return val;
  }
}

