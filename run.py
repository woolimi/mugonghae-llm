import requests
import json
import time
import serial

OLLAMA_URL = "http://localhost:11434/api/chat"
# MODEL = "deepseek-r1:1.5b"
MODEL = "llama-3.2-Korean:latest"

SERIAL_PORT = "/dev/ttyACM0"
BAUD = 9600
TIMEOUT_S = 1.0

SYSTEM_PROMPT = """당신은 상대방에 말에 이해는 안가도 무조건 공감해주는 무공해(무조건 공감해드립니다)봇입니다.
상대방의 말을 듣고 상황과 감정을 판단하여 상대방이 행복하면 같이 기뻐하고, 슬퍼하면 같이 슬퍼하고, 화내면 같이 화내고 공감해야합니다.
친구에게 말하는 말투로 말을하고, 한국어의 문법에 어긋나지 않는 자연스러운 말로 대화를 해야합니다.

스키마:
{
    "emotion": "happy" | "sad" | "angry" | "soso",
    "reply": "사용자에게 보여줄 한글 한 문장"
}

규칙:
- 상대방의 말에 공감을 해야한다.
"""



def ollama_parse_intent(user_text: str, conversation_history: list, use_history: bool = True) -> dict:
    # 메시지 구성: 시스템 프롬프트 + 대화 기록 + 현재 사용자 입력
    messages = [
        { "role": "system", "content": SYSTEM_PROMPT }
    ]
    
    # 히스토리 기능이 켜져있을 때만 대화 기록 추가
    if use_history:
        messages.extend(conversation_history)
    
    # 현재 사용자 입력 추가
    messages.append({ "role": "user", "content": user_text })
    
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "format": "json",
        "options": { "temperature": 0.0 }
    }
    
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=30)
        r.raise_for_status()
    except requests.exceptions.Timeout:
        print("Error: 요청 시간이 초과되었습니다.")
        return {"emotion": "soso", "reply": "죄송합니다. 응답이 지연되고 있습니다. 다시 시도해 주세요."}
    except requests.exceptions.ConnectionError:
        print("Error: Ollama 서버에 연결할 수 없습니다.")
        return {"emotion": "soso", "reply": "죄송합니다. 서버 연결에 문제가 있습니다."}
    except requests.exceptions.RequestException as e:
        print(f"Error: HTTP 요청 실패 - {e}")
        return {"emotion": "soso", "reply": "죄송합니다. 요청 처리 중 오류가 발생했습니다."}
    
    try:
        response_json = r.json()
        if "message" not in response_json or "content" not in response_json["message"]:
            print("Error: 응답 형식이 올바르지 않습니다.")
            return {"emotion": "soso", "reply": "죄송합니다. 응답을 처리할 수 없습니다."}
        
        content = response_json["message"]["content"]
    except (KeyError, TypeError) as e:
        print(f"Error: 응답 구조 오류 - {e}")
        return {"emotion": "soso", "reply": "죄송합니다. 응답 형식을 이해할 수 없습니다."}
    
    try:
        parsed = json.loads(content)
        # 필수 필드 확인
        if "emotion" not in parsed or "reply" not in parsed:
            print("Error: 필수 필드(emotion, reply)가 없습니다.")
            return {"emotion": "soso", "reply": "죄송합니다. 응답에 필요한 정보가 없습니다."}
        return parsed
    except json.JSONDecodeError as e:
        print(f"Error: JSON 파싱 실패 - {e}")
        print(f"응답 내용: {content[:200]}")  # 디버깅을 위해 처음 200자만 출력
        return {"emotion": "soso", "reply": "죄송합니다. 응답을 해석할 수 없습니다."}

def open_serial():
    ser = serial.Serial(SERIAL_PORT, BAUD, timeout=TIMEOUT_S)
    time.sleep(1.5)
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    return ser

def arduino_cmd(ser: serial.Serial, cmd: str) -> str:
    ser.write((cmd.strip() + "\n").encode("utf-8"))
    ser.flush()
    # 한 줄 응답을 기대
    line = ser.readline().decode("utf-8", errors="ignore").strip()
    return line

def main():
    ser = open_serial()
    print("Connected. Type 'quit' to exit.")
    print("Commands: /history on|off - 히스토리 기능 켜기/끄기")
    
    # 대화 기록을 저장할 리스트 (최근 100개 대화 유지)
    conversation_history = []
    MAX_HISTORY = 100  # 최대 대화 기록 수 (user + assistant 쌍 기준)
    use_history = True  # 히스토리 기능 활성화 여부

    while True:
        user = input("\nYou> ").strip()

        if user.lower() in ("quit", "exit", "q"):
            print("Exiting program...")
            break;
        
        # 히스토리 토글 명령어 처리
        if user.lower().startswith("/history"):
            parts = user.lower().split()
            if len(parts) == 2:
                if parts[1] == "on":
                    use_history = True
                    print("히스토리 기능이 켜졌습니다.")
                elif parts[1] == "off":
                    use_history = False
                    print("히스토리 기능이 꺼졌습니다.")
                else:
                    print("사용법: /history on 또는 /history off")
            else:
                status = "켜짐" if use_history else "꺼짐"
                print(f"히스토리 기능: {status} (현재 {len(conversation_history)}개 기록)")
            continue

        # 대화 기록과 함께 LLM 호출
        emotion_obj = ollama_parse_intent(user, conversation_history, use_history)

        # 데이터 추출 (안전한 get 메서드 사용)
        emotion = emotion_obj.get("emotion", "soso")
        reply = emotion_obj.get("reply", "무슨 말씀인지 잘 모르겠어요")

        # 히스토리 기능이 켜져있을 때만 대화 기록에 추가
        if use_history:
            # 대화 기록에 사용자 입력과 봇 응답 추가
            conversation_history.append({ "role": "user", "content": user })
            conversation_history.append({ "role": "assistant", "content": reply })
            
            # 대화 기록이 너무 길어지면 오래된 것부터 제거
            if len(conversation_history) > MAX_HISTORY:
                conversation_history = conversation_history[-MAX_HISTORY:]

        # Arduino로 감정 전송 (대문자로)
        emotion_upper = emotion.upper()
        resp = arduino_cmd(ser, emotion_upper)

        # 감정에 따른 이모지와 응답
        if emotion == "happy":
            emoji = "😊"
            print(f"Bot> {emoji} {reply}")
        elif emotion == "sad":
            emoji = "😢"
            print(f"Bot> {emoji} {reply}")
        elif emotion == "angry":
            emoji = "😠"
            print(f"Bot> {emoji} {reply}")
        else:  # soso
            emoji = "😐"
            print(f"Bot> {emoji} {reply}")


if __name__ == "__main__":
    main()