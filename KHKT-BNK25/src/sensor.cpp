//NKHS-KHKT25 (@mahiru-chanVN)
#include <Arduino.h>
#include <Servo.h>
#define echoPin 9
#define trigPin 10 
#define button 2
typedef long long ll;
const ll latency = 15;
const ll DETECT_DISTANCE = 20;  // cm - distance to detect object - dev: Shouko Dev (@mahiru-chanVN)
const ll STOP_DISTANCE = 5;     // cm - distance to stop/close hand - dev: Shouko Dev (@mahiru-chanVN)

Servo servo_1;
ll duration;
ll distanceCm;
ll isHolding = 0;  // 0 = open, 1 = holding 

ll getDistance() {
    digitalWrite(trigPin, LOW); //Setup all in LOW - Shouko Dev (@mahiru-chanVN)
    delayMicroseconds(2); //cooldown
    digitalWrite(trigPin, HIGH); 
    delayMicroseconds(10);
    digitalWrite(trigPin, LOW);
    
    duration = pulseIn(echoPin, HIGH);
    distanceCm = duration * 0.034 / 2;
    return distanceCm;
}

void openHand() {
    for(ll i = 0; i <= 180; i++) {
        servo_1.write(i);
        delay(latency);
    }
    isHolding = 0;
}

void closeHand() {
    for(ll i = 180; i >= 0; i--) {
        servo_1.write(i);
        delay(latency);
    }
    isHolding = 1;
}

void setup() {
    Serial.begin(9600);
    pinMode(trigPin, OUTPUT);
    pinMode(echoPin, INPUT);
    pinMode(button, INPUT);
    
    servo_1.attach(3);
    
    // Initialize - open hand
    openHand();
}

void loop() {
    distanceCm = getDistance();
    ll buttonState = digitalRead(button);
    
    // Print distance for debugging
    Serial.print("Distance: ");
    Serial.print((int)distanceCm);
    Serial.print(" cm, Holding: ");
    Serial.println((int)isHolding);

    /*Use button to control (Disabled due to using FSRs) - dev: Shouko Dev (@mahiru-chanVN)
    if (buttonState == HIGH) {
        if (isHolding == 0) {
            closeHand();
        } else {
            openHand();
        }
        delay(500);  // Debounce
    }
    */
    // Auto-detect: close hand when object approaches (FSRs) - dev: Shouko Dev (@mahiru-chanVN)
    if (distanceCm < DETECT_DISTANCE && distanceCm > 0 && isHolding == 0) {
        closeHand();
    }
    
    // Auto-detect: open hand when object moves away (FSRs)- dev: Shouko Dev (@mahiru-chanVN)
    if (distanceCm > DETECT_DISTANCE + 5 && isHolding == 1) {
        openHand();
    }
    
    delay(100);
} 
    //Read button 
   /*doc_nut = digitalRead(button);
   if (doc_nut == HIGH) {
      for(ll i = 0; i <= 180; i++) {
        servo_1.write(i);
        delay(latency);
}
//main
 /*signed main()
{
  setup();
  loop();
}*/