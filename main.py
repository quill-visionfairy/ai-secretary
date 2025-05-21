from __future__ import print_function
import os.path
import datetime
from datetime import timedelta
import json
from dotenv import load_dotenv
from flask import session, redirect, url_for

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

# .env 파일 로드
load_dotenv()

# Google Calendar에 접근하기 위한 권한 범위
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def create_flow():
    """OAuth 2.0 Flow 객체 생성"""
    client_config = {
        "web": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "project_id": os.getenv("GOOGLE_PROJECT_ID"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "redirect_uris": [
                "https://ai-secretary-148126309509.asia-northeast3.run.app/oauth2callback"
            ]
        }
    }
    
    return Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri="https://ai-secretary-148126309509.asia-northeast3.run.app/oauth2callback"
    )

def get_calendar_service():
    """Google Calendar API 서비스 객체 반환"""
    if 'credentials' not in session:
        return None

    creds = Credentials.from_authorized_user_info(session['credentials'], SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            session['credentials'] = credentials_to_dict(creds)
        else:
            return None

    return build('calendar', 'v3', credentials=creds)

def credentials_to_dict(credentials):
    """Credentials 객체를 딕셔너리로 변환"""
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

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

def check_calendar(start_date, end_date):
    """캘린더 일정 조회 메인 함수"""
    service = get_calendar_service()
    if not service:
        return {"error": "Authentication required"}
        
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

def main():
    # 기본값: 어제, 오늘, 내일 일정 확인
    today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = today - timedelta(days=1)  # 어제
    end_date = today + timedelta(days=2)    # 내일 끝
    check_calendar(start_date, end_date)

if __name__ == '__main__':
    main()
