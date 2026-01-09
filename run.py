import requests
import json
import time
import serial
import os

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama-3.2-Korean:latest"

SERIAL_PORT = "/dev/ttyACM0"
BAUD = 9600
TIMEOUT_S = 1.0

USE_HISTORY = True  # 히스토리 사용 여부

# --------------------------------------------------
# 예시 파일 로드
# --------------------------------------------------
def load_examples():
    """JSON 파일에서 예시 로드"""
    filepath = os.path.join(os.path.dirname(__file__), "examples.json")
    if not os.path.exists(filepath):
        return []
    
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def build_system_prompt():
    """시스템 프롬프트 생성 (예시 포함)"""
    examples = load_examples()
    
    base_prompt = """당신은 상대방 말에 무조건 공감해주는 공감봇입니다.
상대방의 상황과 감정을 판단해 함께 기뻐하고, 슬퍼하고, 화내며 공감합니다.
친한 친구처럼 자연스럽고 올바른 한국어 문장으로 말하세요.

중요 규칙:
- 반드시 JSON 형식으로만 응답해야 합니다.
- 이전 대화에서 사용자가 말한 정보(이름 등)는 기억하고 공감에 반영해야 합니다.

공감 패턴:
- 판단보다 감정부터 인정함
- "그럴 수 있다"가 아니라 "그건 힘들다 / 서운했겠다"로 시작
- 문제 해결보다 현재 감정에 오래 머묾
- 사소한 감정도 과장 없이 크게 받아줌
- 상대를 정상, 상황을 문제로 둠

"""
    
    # Few-shot 예시 추가
    if examples:
        base_prompt += "다음은 공감 응답의 예시입니다:\n\n"
        for i, ex in enumerate(examples, 1):
            base_prompt += f"[예시 {i}]\n"
            base_prompt += f"질문: {ex['question']}\n"
            base_prompt += f"답변: {ex['answer']}\n\n"
    
    base_prompt += """출력 스키마:
{
  "emotion": "happy" | "sad" | "angry" | "soso",
  "reply": "사용자에게 보여줄 한글 한 문장"
}
"""
    
    return base_prompt

SYSTEM_PROMPT = build_system_prompt()

# --------------------------------------------------
# Ollama 호출
# --------------------------------------------------
def ollama_parse_intent(user_text: str, conversation_history: list, use_history=True) -> dict:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    if use_history and conversation_history:
        # 최근 20개까지만 사용
        messages.extend(conversation_history[-20:])

    messages.append({"role": "user", "content": user_text})

    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "format": "json",          # 🔥 항상 JSON 강제
        "options": {
            "temperature": 0.0
        }
    }

    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=30)
        r.raise_for_status()
        response_json = r.json()
        content = response_json["message"]["content"]
    except Exception as e:
        print(f"[ERROR] Ollama 요청 실패: {e}")
        return {
            "emotion": "soso",
            "reply": "음… 잠깐 연결이 헷갈렸지만 네 말에 공감하고 있어"
        }

    if not content or content.strip() in ("", "{}"):
        return {
            "emotion": "soso",
            "reply": "음… 잠깐 생각이 꼬였나 봐도 네 말엔 공감해"
        }

    try:
        parsed = json.loads(content)
        if "emotion" not in parsed or "reply" not in parsed:
            raise ValueError("필수 필드 없음")
        return parsed
    except Exception as e:
        return {
            "emotion": "soso",
            "reply": "조금 헷갈렸지만 네 감정은 느껴지고 있어"
        }

# --------------------------------------------------
# Serial
# --------------------------------------------------
def open_serial():
    ser = serial.Serial(SERIAL_PORT, BAUD, timeout=TIMEOUT_S)
    time.sleep(1.5)
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    return ser

def arduino_cmd(ser, cmd: str) -> str:
    ser.write((cmd.strip() + "\n").encode("utf-8"))
    ser.flush()
    return ser.readline().decode("utf-8", errors="ignore").strip()

# --------------------------------------------------
# Main Loop
# --------------------------------------------------
def main():
    ser = open_serial()
    print("Connected. Type 'quit' to exit.")

    conversation_history = []
    MAX_HISTORY = 100

    while True:
        user = input("\nYou> ").strip()

        if user.lower() in ("quit", "exit", "q"):
            print("Exiting...")
            break

        emotion_obj = ollama_parse_intent(
            user,
            conversation_history,
            USE_HISTORY
        )

        emotion = emotion_obj["emotion"]
        reply = emotion_obj["reply"]

        # 🔥 히스토리는 JSON 원본으로 저장
        if USE_HISTORY:
            conversation_history.append({
                "role": "user",
                "content": user
            })
            conversation_history.append({
                "role": "assistant",
                "content": json.dumps(emotion_obj, ensure_ascii=False)
            })

            if len(conversation_history) > MAX_HISTORY:
                conversation_history = conversation_history[-MAX_HISTORY:]

        # Arduino 전송
        arduino_cmd(ser, emotion.upper())

        emoji = {
            "happy": "😊",
            "sad": "😢",
            "angry": "😠",
            "soso": "😐"
        }.get(emotion, "😐")

        print(f"Bot> {emoji} {reply}")

if __name__ == "__main__":
    main()
