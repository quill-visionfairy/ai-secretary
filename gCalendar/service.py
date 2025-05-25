import os.path
import datetime
import json
import logging
from dotenv import load_dotenv
from flask import session, redirect, url_for
from datetime import timedelta
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from py.config import SCOPES

# logging 설정
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(asctime)s %(message)s')
logger = logging.getLogger(__name__)

# .env 파일 로드
load_dotenv()

def create_flow(platform='gpt', target='google'):
    """플랫폼/타겟별 OAuth Flow 객체 생성 (AuthManager 사용)"""
    return get_auth(platform, target).create_flow()

def get_calendar_service(user_id, platform='gpt', target='google', auth=None):
    """Redis 기반 토큰으로 Google Calendar API 서비스 객체 반환"""
    if auth is None:
        auth = get_auth(platform, target)
    tokens = auth.load_tokens(user_id)
    if not tokens:
        logger.warning(f"tokens= {tokens}")
        return None
    try:
        creds = Credentials.from_authorized_user_info(tokens, auth.scopes)
    except Exception as e:
        logger.error(f"Credentials.from_authorized_user_info 예외 발생: {e}")
        return None
    # refresh_token이 없으면 access_token을 revoke하고 None 반환
    if not getattr(creds, 'refresh_token', None):
        # access_token 철회 시도
        auth.revoke_token(creds.token)
        # 토큰 삭제
        key = f"tokens:{platform}:{target}:{user_id}"
        auth.redis_client.delete(key)
        logger.error("[ERROR] refresh_token이 없어 토큰을 철회하고 재인증 필요")
        return None
    if not creds or not creds.valid:
        logger.warning("❌ token not valid!")
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                auth.save_tokens(user_id, creds)
            except Exception as e:
                logger.error(f"토큰 refresh 중 예외 발생: {e}")
                return None
        else:
            logger.warning("❌ token not valid!")
            return None
    return build('calendar', 'v3', credentials=creds)

def credentials_to_dict(credentials):
    """Credentials 객체를 딕셔너리로 변환 (AuthManager 사용)"""
    return get_auth('gpt', 'google').credentials_to_dict(credentials)

def get_events(service, start_date, end_date):
    """지정된 기간의 일정을 가져옴"""
    # 한국 시간 (UTC+9)으로 조정
    time_min = start_date.astimezone().isoformat()
    time_max = end_date.astimezone().isoformat()

    print(f"Fetching events from {time_min} to {time_max}")  # 디버깅용 로그

    events_result = service.events().list(
        calendarId='primary',
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])
    print(f"Found {len(events)} events")  # 디버깅용 로그
    
    return events

def format_event_time(event):
    """이벤트 시작 시간 포맷팅"""
    start = event['start'].get('dateTime', event['start'].get('date'))
    if 'T' in start:  # dateTime 형식일 경우
        start_time = datetime.datetime.fromisoformat(start.replace('Z', '+00:00'))
        return start_time.strftime('%Y-%m-%d %H:%M')
    else:  # date 형식일 경우
        return start

def print_events_by_date(events):
    """일정을 날짜별로 출력"""
    if not events:
        print('일정이 없습니다.')
        return

    current_date = None
    for event in events:
        event_date = format_event_time(event)[:10]  # YYYY-MM-DD 부분만 추출
        
        # 날짜가 바뀌면 구분선 출력
        if event_date != current_date:
            current_date = event_date
            today = datetime.datetime.now().date()
            event_datetime = datetime.datetime.strptime(event_date, '%Y-%m-%d').date()
            
            if event_datetime == today:
                print(f'\n[오늘 - {event_date}]')
            elif event_datetime == today - timedelta(days=1):
                print(f'\n[어제 - {event_date}]')
            elif event_datetime == today + timedelta(days=1):
                print(f'\n[내일 - {event_date}]')
            else:
                print(f'\n[{event_date}]')
            
        # 이벤트 정보 출력
        start_time = format_event_time(event)
        if 'T' in event['start'].get('dateTime', ''):  # 시간이 있는 경우
            print(f"⏰ {start_time[11:]} - {event['summary']}")
        else:  # 종일 일정인 경우
            print(f"📌 종일 - {event['summary']}")

def check_google_calendar(user_id, start_date, end_date, platform='google'):
    """구글 캘린더 일정 조회 메인 함수 (user_id, platform 기반)"""
    service = get_calendar_service(user_id, platform)
    if not service:
        return {"error": "Authentication required"}
    # refresh_token 없음 등으로 dict 에러 반환 시
    if isinstance(service, dict) and service.get("error"):
        return {"error": service["error"]}
    events = get_events(service, start_date, end_date)
    # 이벤트 데이터 가공
    formatted_events = []
    for event in events:
        formatted_event = {
            'summary': event['summary'],
            'start': format_event_time(event),
            'is_all_day': 'T' not in event['start'].get('dateTime', '')
        }
        formatted_events.append(formatted_event)
    return formatted_events

def route_calendar_service(user_id, start_date, end_date, platform=None):
    """
    user_id와 platform을 받아 연결된 서비스에 따라 캘린더 조회 함수를 라우팅
    platform이 명시되지 않으면, 기본 연결(google)로 처리
    추후 Notion, Slack 등 확장 가능
    """
    # 실제 서비스 연결 정보는 DB/Redis 등에서 조회해야 함 (여기선 platform 인자 우선)
    if not platform:
        platform = 'google'  # 기본값
    if platform == 'google':
        return check_google_calendar(user_id, start_date, end_date, platform)
    
    # TODO: Notion 연동 시 notion_client를 사용해 일정 조회 구현 예정
    # elif platform == 'notion':
    #     return check_notion_calendar(user_id, start_date, end_date)
    # TODO: Slack 연동 시 slash command 기반 회의 관리 예정
    # elif platform == 'slack':
    #     return check_slack_calendar(user_id, start_date, end_date)
    else:
        return {"error": f"지원하지 않는 플랫폼입니다: {platform}"}

def main():
    user_id = "testuser@gmail.com"
    platform = "google"

    today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = today - timedelta(days=1)
    end_date = today + timedelta(days=2)

    result = route_calendar_service(user_id, start_date, end_date, platform)
    print(result)

if __name__ == '__main__':
    main()
