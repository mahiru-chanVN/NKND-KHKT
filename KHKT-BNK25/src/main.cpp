//KHKT25-NKHS (@mahiru-chanVN)
#include <Arduino.h>
#include <Servo.h>
#define FSR1_NGON_CAI A0
#define FSR2_NGON_TRO A1
#define FSR3_NGON_GIUA A2
#define FSR4_NGON_UT A3
typedef void aaaa;
typedef long long ll;
Servo servo_1, servo_2, servo_3, servo_4;
ll readcai_a = 0, readtro_a = 0, readgiua_a = 0, readut_a = 0;
ll cai_a, tro_a, giua_a, ut_a;
aaaa setup() {
  pinMode(FSR1_NGON_CAI, INPUT);
  pinMode(FSR2_NGON_TRO, INPUT);
  pinMode(FSR3_NGON_GIUA, INPUT);
  pinMode(FSR4_NGON_UT, INPUT);

  servo_1.attach(9);
  servo_2.attach(6);
  servo_3.attach(5);
  servo_4.attach(3);

  Serial.begin(9600);
}

aaaa loop() {
   readcai_a = digitalRead(FSR1_NGON_CAI);
   readtro_a = digitalRead(FSR2_NGON_TRO);
   readgiua_a = digitalRead(FSR3_NGON_GIUA);
   readut_a = digitalRead(FSR4_NGON_UT);
   
   cai_a = map(readcai_a, 0, 1023, 0, 180);
   tro_a = map(readtro_a, 0, 1023, 0, 180);
   giua_a = map(readgiua_a, 0, 1023,  0, 180);
   ut_a = map(readut_a, 0, 1023, 0, 180);

  servo_1.write(cai_a);
  servo_2.write(tro_a);
  servo_3.write(giua_a);
  servo_4.write(ut_a);

   
}

/*signed main()
{
  setup();
  loop();
}*/
  