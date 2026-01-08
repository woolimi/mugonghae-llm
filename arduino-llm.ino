#include <LiquidCrystal.h>

// LCD 핀 연결 설정 (RS, E, D4, D5, D6, D7)
// 필요에 따라 아래 핀 번호를 실제 연결한 핀에 맞게 수정하세요
LiquidCrystal lcd(8, 9, 4, 5, 6, 7);

// 시리얼 입력을 읽는 함수 (asdf.c 참고)
String readLine() {
  static String buf = "";
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n') {
      String line = buf;
      buf = "";
      line.trim();
      return line;
    } else if (c != '\r') {
      buf += c;
    }
  }
  return "";
}

// 감정에 따라 LCD에 이모티콘 표시
void displayEmotion(String emotion) {
  emotion.toUpperCase();
  lcd.clear();
  
  if (emotion == "HAPPY") {
    lcd.setCursor(0, 0);
    lcd.print("Emotion: Happy");
    lcd.setCursor(0, 1);
    lcd.print("(^v^)");
  } else if (emotion == "SAD") {
    lcd.setCursor(0, 0);
    lcd.print("Emotion: Sad");
    lcd.setCursor(0, 1);
    lcd.print("(T_T)");
  } else if (emotion == "SOSO") {
    lcd.setCursor(0, 0);
    lcd.print("Emotion: Soso");
    lcd.setCursor(0, 1);
    lcd.print("(-_-)");
  } else {
    // 알 수 없는 명령
    lcd.setCursor(0, 0);
    lcd.print("Unknown cmd:");
    lcd.setCursor(0, 1);
    lcd.print(emotion);
  }
}

void setup() {
  // 시리얼 통신 초기화
  Serial.begin(9600);
  delay(200);
  
  // LCD 초기화 전 충분한 대기 시간
  delay(100);
  
  // LCD 초기화 (16자, 2줄)
  lcd.begin(16, 2);
  
  // 초기화 후 추가 대기
  delay(100);
  
  // 화면 지우기
  lcd.clear();
  delay(50);
  
  // 첫 번째 줄에 메시지 출력
  lcd.setCursor(0, 0);
  lcd.print("LCD Ready");
  
  // 두 번째 줄에 상태 표시
  lcd.setCursor(0, 1);
  lcd.print("Waiting...");
  
  Serial.println("READY");
}

void loop() {
  String cmd = readLine();
  if (cmd.length() > 0) {
    displayEmotion(cmd);
    Serial.print("OK:");
    Serial.println(cmd);
  }
}

