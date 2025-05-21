import unittest
from unittest.mock import patch, MagicMock
import datetime
from datetime import timedelta
import os
import json
from dotenv import load_dotenv

# 테스트할 모듈들 임포트
from main import (
    create_oauth_config,
    cleanup_temp_config,
    format_event_time,
    get_calendar_service
)

class TestCalendarFunctions(unittest.TestCase):
    def setUp(self):
        """각 테스트 전에 실행"""
        load_dotenv()
        self.sample_event = {
            'summary': '테스트 일정',
            'start': {
                'dateTime': '2024-03-20T10:00:00Z',
                'timeZone': 'Asia/Seoul'
            }
        }
        self.sample_all_day_event = {
            'summary': '종일 테스트 일정',
            'start': {
                'date': '2024-03-20'
            }
        }

    def test_format_event_time(self):
        """이벤트 시간 포맷팅 테스트"""
        # 일반 이벤트 테스트
        formatted_time = format_event_time(self.sample_event)
        self.assertEqual(formatted_time, '2024-03-20 10:00')

        # 종일 이벤트 테스트
        formatted_date = format_event_time(self.sample_all_day_event)
        self.assertEqual(formatted_date, '2024-03-20')

    def test_create_oauth_config(self):
        """OAuth 설정 파일 생성 테스트"""
        # 환경 변수 모의 설정
        test_env = {
            'GOOGLE_CLIENT_ID': 'test_client_id',
            'GOOGLE_PROJECT_ID': 'test_project_id',
            'GOOGLE_CLIENT_SECRET': 'test_client_secret'
        }
        
        with patch.dict(os.environ, test_env):
            config_file = create_oauth_config()
            
            # 파일이 생성되었는지 확인
            self.assertTrue(os.path.exists(config_file))
            
            # 파일 내용 확인
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            self.assertEqual(config['installed']['client_id'], 'test_client_id')
            self.assertEqual(config['installed']['project_id'], 'test_project_id')
            self.assertEqual(config['installed']['client_secret'], 'test_client_secret')
            
            # 테스트 후 파일 정리
            cleanup_temp_config(config_file)

    def test_cleanup_temp_config(self):
        """임시 설정 파일 정리 테스트"""
        # 테스트 파일 생성
        test_file = 'test_config.json'
        with open(test_file, 'w') as f:
            f.write('{}')
        
        # 파일 정리
        cleanup_temp_config(test_file)
        
        # 파일이 삭제되었는지 확인
        self.assertFalse(os.path.exists(test_file))

    @patch('main.build')
    @patch('main.InstalledAppFlow')
    @patch('main.Credentials')
    @patch('builtins.open', create=True)
    def test_get_calendar_service(self, mock_open, mock_creds_class, mock_flow, mock_build):
        """캘린더 서비스 객체 생성 테스트"""
        # 케이스 1: 토큰이 없는 경우
        mock_open.side_effect = FileNotFoundError
        mock_creds = MagicMock()
        mock_flow.from_client_secrets_file.return_value.run_local_server.return_value = mock_creds
        mock_build.return_value = MagicMock()

        service = get_calendar_service()
        mock_flow.from_client_secrets_file.assert_called_once()
        mock_build.assert_called_with('calendar', 'v3', credentials=mock_creds)

        # 케이스 2: 토큰이 만료된 경우
        mock_open.side_effect = None
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "refresh_token"
        mock_creds_class.from_authorized_user_file.return_value = mock_creds

        service = get_calendar_service()
        mock_creds.refresh.assert_called_once()
        mock_build.assert_called_with('calendar', 'v3', credentials=mock_creds)

        # 케이스 3: 유효한 토큰이 있는 경우
        mock_creds.valid = True
        mock_creds.expired = False
        service = get_calendar_service()
        mock_build.assert_called_with('calendar', 'v3', credentials=mock_creds)

    def test_get_calendar_service_error_handling(self):
        """캘린더 서비스 생성 시 에러 처리 테스트"""
        with patch('main.build') as mock_build:
            # API 빌드 실패 케이스
            mock_build.side_effect = Exception("API 빌드 실패")
            with self.assertRaises(Exception):
                get_calendar_service()

class TestCalendarIntegration(unittest.TestCase):
    """통합 테스트"""
    
    def setUp(self):
        """각 테스트 전에 실행"""
        load_dotenv()
        
    def test_env_variables(self):
        """환경 변수 설정 테스트"""
        required_vars = [
            'GOOGLE_CLIENT_ID',
            'GOOGLE_PROJECT_ID',
            'GOOGLE_CLIENT_SECRET',
            'OPENAI_API_KEY'
        ]
        
        for var in required_vars:
            self.assertIsNotNone(os.getenv(var), f'{var} 환경 변수가 설정되지 않았습니다.')

if __name__ == '__main__':
    unittest.main() 