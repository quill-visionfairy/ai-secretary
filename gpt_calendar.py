from openai import OpenAI
import datetime
import os
from main import get_calendar_service, get_events, route_calendar_service
from datetime import timedelta
from dotenv import load_dotenv
import json

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
        raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
    return OpenAI(api_key=api_key)

def extract_date_range(query: str) -> dict:
    """자연어 쿼리에서 날짜 범위 추출"""
    client = init_openai_client()
    
    system_message = """당신은 사용자의 자연어 쿼리에서 날짜 범위를 추출하는 AI 비서입니다.
다음 규칙을 따라주세요:
1. 시작 시간과 종료 시간을 ISO 8601 형식으로 반환
2. "오늘", "내일", "다음 주" 등의 상대적 표현을 실제 날짜로 변환
3. 특정 날짜만 언급된 경우 해당 날의 00:00:00부터 23:59:59까지로 설정
4. 시간이 명시되지 않은 경우 하루 전체를 범위로 설정
5. 날짜가 명시되지 않은 경우 오늘을 기준으로 설정"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": query}
        ],
        response_format={"type": "json_object"}
    )

    result = response.choices[0].message.content
    return json.loads(result)

def process_calendar_query(query: str, user_id: str = None, platform: str = 'google'):
    """사용자 쿼리 처리 (user_id, platform 지원)"""
    try:
        if not user_id:
            print("[API ERROR] user_id가 없음 - 인증 필요")
            return {
                "status": "error",
                "message": "사용자 인증이 필요합니다. 먼저 로그인 해주세요."
            }
        # 1. 자연어에서 날짜 범위 추출
        try:
            date_range = extract_date_range(query)
            start_time = date_range.get("start_time")
            end_time = date_range.get("end_time")
        except Exception as e:
            print(f"[GPT ERROR] 날짜 범위 추출 실패: {str(e)}")
            return {
                "status": "error",
                "message": f"GPT 호출 중 오류 발생: 날짜 범위 추출 실패 - {str(e)}"
            }

        if not start_time or not end_time:
            print("[API ERROR] 날짜 범위 추출 결과 없음")
            return {
                "status": "error",
                "message": "날짜 범위를 추출할 수 없습니다."
            }

        # 2. 캘린더 조회 (user_id, platform 활용)
        try:
            start = datetime.datetime.fromisoformat(start_time)
            end = datetime.datetime.fromisoformat(end_time)
            service = get_calendar_service(user_id, platform)
            if not service:
                print(f"[API ERROR] 캘린더 서비스 인증 실패: user_id={user_id}, platform={platform}")
                events = []
            else:
                events = get_events(service, start, end)
        except Exception as e:
            print(f"[API ERROR] 캘린더 조회 실패: {str(e)}")
            return {
                "status": "error",
                "message": f"API 호출 중 오류 발생: 캘린더 조회 실패 - {str(e)}"
            }

        # 3. GPT에게 일정 정보 전달하여 응답 생성
        try:
            client = init_openai_client()
            events_description = "조회된 일정:\n"
            if events:
                for event in events:
                    events_description += f"- {event['start']}: {event['summary']}\n"
            else:
                events_description += "해당 기간에 예정된 일정이 없습니다.\n"

            system_message = f"""당신은 {platform.title()} Calendar 일정 관리를 돕는 AI 비서입니다.\n사용자의 일정 관련 질문에 친절하게 답변해주세요.\n일정이 있다면 시간과 제목을 명확하게 알려주시고, \n일정이 없다면 그 날이 비어있다고 알려주세요.\n답변은 한국어로 해주세요."""

            final_response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": query},
                    {"role": "system", "content": f"조회한 기간: {start_time} ~ {end_time}"},
                    {"role": "system", "content": events_description}
                ]
            )
        except Exception as e:
            print(f"[GPT ERROR] GPT 응답 생성 실패: {str(e)}")
            return {
                "status": "error",
                "message": f"GPT 호출 중 오류 발생: 응답 생성 실패 - {str(e)}"
            }

        return {
            "status": "success",
            "user_id": user_id,
            "query_info": {
                "original_query": query,
                "start_time": start_time,
                "end_time": end_time
            },
            "events": events,
            "response": final_response.choices[0].message.content
        }

    except Exception as e:
        print(f"[API ERROR] process_calendar_query 전체 예외: {str(e)}")
        return {
            "status": "error",
            "message": f"API 호출 중 알 수 없는 오류 발생: {str(e)}"
        }

if __name__ == "__main__":
    # 테스트 쿼리
    query = input("어떤 일정을 확인하시겠습니까? (예: 이번 주 일정 알려줘): ")
    result = process_calendar_query(query)
    print(f"결과: {result}")
