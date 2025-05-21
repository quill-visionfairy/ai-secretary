from openai import OpenAI
import datetime
import os
from main import check_calendar
from datetime import timedelta
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class GPTError(Exception):
    """GPT 관련 커스텀 예외"""
    def __init__(self, message, error_type=None):
        self.message = message
        self.error_type = error_type
        super().__init__(self.message)

def init_openai_client():
    """OpenAI 클라이언트 초기화"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise GPTError(
            "OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.\n"
            "1. .env 파일을 생성하세요.\n"
            "2. OPENAI_API_KEY=your_api_key_here 형식으로 API 키를 추가하세요.",
            "api_key_missing"
        )
    return OpenAI(api_key=api_key)

def get_calendar_function_spec():
    """캘린더 함수 스펙 정의"""
    return [{
        "name": "check_calendar",
        "description": "Google 캘린더 일정 확인",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "ISO 8601 형식 시작일 (예: 2025-05-20)"
                },
                "end_date": {
                    "type": "string",
                    "description": "ISO 8601 형식 종료일 (예: 2025-05-22)"
                }
            },
            "required": ["start_date", "end_date"]
        }
    }]

def process_calendar_query(query: str):
    """사용자 쿼리 처리"""
    try:
        # OpenAI 클라이언트 초기화
        client = init_openai_client()

        # API 호출
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "당신은 Google Calendar 일정 관리를 돕는 AI 비서입니다."},
                    {"role": "user", "content": query}
                ],
                tools=[{
                    "type": "function",
                    "function": get_calendar_function_spec()[0]
                }],
                tool_choice={"type": "function", "function": {"name": "check_calendar"}}
            )
        except Exception as api_error:
            if "insufficient_quota" in str(api_error):
                raise GPTError(
                    "OpenAI API 할당량이 초과되었습니다. 다음을 확인해주세요:\n"
                    "1. OpenAI 계정의 결제 상태\n"
                    "2. API 사용량 제한\n"
                    "3. 현재 청구 주기의 사용량",
                    "quota_exceeded"
                )
            raise GPTError(f"OpenAI API 호출 중 오류 발생: {str(api_error)}", "api_error")

        # 응답 처리
        tool_call = response.choices[0].message.tool_calls[0]
        if tool_call.function.name == "check_calendar":
            import json
            args = json.loads(tool_call.function.arguments)
            
            try:
                start = datetime.datetime.fromisoformat(args["start_date"])
                end = datetime.datetime.fromisoformat(args["end_date"])
                return {
                    "status": "success",
                    "data": check_calendar(start, end)
                }
            except ValueError as e:
                return {
                    "status": "error",
                    "error": f"날짜 형식 오류: {str(e)}"
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"캘린더 조회 중 오류 발생: {str(e)}"
                }

    except GPTError as e:
        return {
            "status": "error",
            "error": e.message,
            "error_type": e.error_type
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"예상치 못한 오류 발생: {str(e)}"
        }

if __name__ == "__main__":
    # 사용자 입력 받기
    user_query = input("어떤 일정을 확인하시겠습니까? (예: 이번 주 일정 알려줘): ")
    result = process_calendar_query(user_query)
    print(f"결과: {result}")
