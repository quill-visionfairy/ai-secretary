import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import json
from unittest.mock import patch, MagicMock
from main import get_calendar_service, get_events
from auth_manager import AuthManager

# 1️⃣ 개선된 SCOPES 구조 반영
mock_token_data = {
    'token': 'ya29.fake-token',
    'refresh_token': 'refresh-token',
    'token_uri': 'https://oauth2.googleapis.com/token',
    'client_id': 'test-client-id',
    'client_secret': 'test-secret',
    'scopes': [
        'https://www.googleapis.com/auth/calendar.readonly',
        'https://www.googleapis.com/auth/userinfo.email'
    ]
}

# 2️⃣ load_tokens 테스트
@patch('auth_manager.redis_client.get')
def test_load_tokens(mock_get):
    mock_get.return_value = '{"token": "ya29.fake-token"}'
    auth = AuthManager('google')
    tokens = auth.load_tokens('issackiss518@gmail.com')
    assert tokens is not None
    assert 'token' in tokens

# 3️⃣ get_calendar_service 개선 (platform 명시)
@patch('main.Credentials.from_authorized_user_info')
@patch('main.build')
@patch('auth_manager.redis_client.get')
def test_get_calendar_service(mock_redis_get, mock_build, mock_creds):
    mock_redis_get.return_value = json.dumps(mock_token_data)
    mock_creds.return_value = MagicMock(valid=True)
    mock_build.return_value = "service_obj"
    
    service = get_calendar_service("issackiss518@gmail.com", "google")
    assert service == "service_obj"

# 4️⃣ get_events 테스트
def test_get_events():
    mock_service = MagicMock()
    mock_service.events().list().execute.return_value = {
        'items': [
            {'summary': 'Test Event', 'start': {'dateTime': '2025-05-23T10:00:00Z'}}
        ]
    }
    import datetime
    now = datetime.datetime.now()
    events = get_events(mock_service, now, now)
    assert isinstance(events, list)
    assert len(events) > 0
    assert 'summary' in events[0]
