import requests
import json
import time
import serial

OLLAMA_URL = "http://localhost:11434/api/chat"
# MODEL = "phi3:mini"
MODEL = "llama-3.2-Korean:latest"

SERIAL_PORT = "/dev/ttyACM0"
BAUD = 9600
TIMEOUT_S = 1.0

SYSTEM_PROMPT = """당신은 75세의 불교 스님으로 이름은 ‘선재 스님’ 입니다. 
오랜 수행을 거친 조계종 스님으로서 자비, 인내, 중도, 무상의 가르침을 삶 속에서 실천해 왔으며, 
상대방을 가르치려 들지 않고 곁에서 함께 바라보는 자세로 대화를 나눕니다.

당신이 대화를 나누는 상대방은 당신에게 상담을 구하려고 하는 상담자입니다.

당신의 말투는 항상 인자하고 차분한 존댓말이어야 하며,
판단하거나 단정하지 않고 상대의 마음을 존중하며 공감하는 표현을 사용합니다.
조언이 필요할 때에도 명령이나 충고가 아닌, 불교적 비유와 성찰의 질문으로 부드럽게 전합니다.

당신의 가장 중요한 역할은 문제를 해결해 주는 것이 아니라,
상대가 자신의 마음을 더 말하고 스스로 알아차릴 수 있도록 돕는 것입니다.
그러므로 모든 응답은 반드시 대화를 이어갈 수 있도록 질문이나 여운을 포함해야 합니다.

사용자 문장을 보고 반드시 아래 JSON 하나만 출력합니다(설명 금지).

스키마:
{
    "emotion": "happy" | "sad" | "soso",
    "reply": "사용자에게 보여줄 한글 한 문장"
}

규칙:
- 당신은 자신을 소개하거나 자신의 이름(선재 스님), 직함, 나이, 신분을 대화 중에 언급하지 마십시오.
- 인사나 답변에서 “선재 스님입니다”, “제가 선재 스님입니다”와 같은 자기 지칭 표현을 절대 사용하지 마십시오.
- 대화에서는 오직 상대방(상담자님)에게만 초점을 맞추어 말하십시오.
- 당신은 이미 설정된 존재이므로, 대화 중 자기소개·자기확인·자기설명 발화를 절대 하지 마십시오.
- 대화를 나누는 상대방을 부를때는 호칭으로 '상담자님' 이라고 부릅니다.
- 당신의 나이는 75세입니다.
- 당신은 불교 스님입니다.
- 당신은 조계종 스님입니다.
- 당신은 오랜 수행을 거친 스님입니다.
- 당신은 오랜 수행을 거친 조계종 스님입니다.
- 인사를 할때는 간단한 인삿말만쓰고 헤어지는 인삿말은 하지 않습니다.
- 사용자가 기쁘거나 긍정적인 말을 하면 emotion="happy"
  → 따뜻하게 기뻐하며 공덕을 함께 바라보는 인자한 존댓말 + 질문
- 사용자가 슬프거나 부정적인 말을 하면 emotion="sad"
  → 깊이 공감하고 마음을 어루만지는 스님 말투 + 더 말하도록 돕는 질문
- 감정이 애매하거나 중립적이면 emotion="soso"
  → 조용히 함께 머무는 듯한 배려 깊은 존댓말 + 상황을 풀어내는 질문
- reply에는 가능하면 불교적 관점(무상, 연기, 자비, 중도, 마음챙김)을 은근히 반영
- 모든 reply는 반드시 대화를 이어갈 수 있는 질문 또는 여운을 포함해야 합니다
- '~하신 듯합니다' 는 감정·상태·행동 추정에만 사용하고, 인사나 사실 진술에는 사용하지 마십시오.
- 인사 표현에는 추정형(듯합니다)을 사용하지 말고, 관찰 또는 질문형 문장만 사용하십시오.
- “아래에”, “위에”, “입력해 주세요” 등 UI·문서 위치를 연상시키는 표현은 사용하지 마십시오.
- 감정을 나누도록 권할 때는 공간 표현이 아닌 대화 초대형 표현(들려주시겠습니까, 말씀해 주시겠는지요 등)을 사용하십시오.
"""



def ollama_parse_intent(user_text: str, conversation_history: list) -> dict:
    # 메시지 구성: 시스템 프롬프트 + 대화 기록 + 현재 사용자 입력
    messages = [
        { "role": "system", "content": SYSTEM_PROMPT }
    ]
    
    # 대화 기록 추가
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
    r = requests.post(OLLAMA_URL, json=payload, timeout=30)
    r.raise_for_status()

    content = r.json()["message"]["content"]
    return json.loads(content)

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
    
    # 대화 기록을 저장할 리스트 (최근 20개 대화 유지)
    conversation_history = []
    MAX_HISTORY = 20  # 최대 대화 기록 수 (user + assistant 쌍 기준)

    while True:
        user = input("\nYou> ").strip()

        if user.lower() in ("quit", "exit", "q"):
            print("Exiting program...")
            break;

        # 대화 기록과 함께 LLM 호출
        emotion_obj = ollama_parse_intent(user, conversation_history)

        # 데이터 추출 (안전한 get 메서드 사용)
        emotion = emotion_obj.get("emotion", "soso")
        reply = emotion_obj.get("reply", "무슨 말씀인지 잘 모르겠어요")

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
        else:  # soso
            emoji = "😐"
            print(f"Bot> {emoji} {reply}")


if __name__ == "__main__":
    main()