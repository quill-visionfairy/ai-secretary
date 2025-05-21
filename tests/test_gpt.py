import unittest
from unittest.mock import patch, MagicMock
import os
from dotenv import load_dotenv
from gpt_calendar import (
    init_openai_client,
    get_calendar_function_spec,
    process_calendar_query
)

class TestGPTFunctions(unittest.TestCase):
    def setUp(self):
        """각 테스트 전에 실행"""
        load_dotenv()

    def test_init_openai_client(self):
        """OpenAI 클라이언트 초기화 테스트"""
        # API 키가 설정된 경우
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test_key'}):
            client = init_openai_client()
            self.assertIsNotNone(client)

        # API 키가 없는 경우
        with patch.dict(os.environ, {'OPENAI_API_KEY': ''}, clear=True):
            with self.assertRaises(ValueError):
                init_openai_client()

    def test_get_calendar_function_spec(self):
        """함수 스펙 정의 테스트"""
        spec = get_calendar_function_spec()
        
        # 스펙 형식 확인
        self.assertIsInstance(spec, list)
        self.assertEqual(len(spec), 1)
        
        func_spec = spec[0]
        self.assertEqual(func_spec['name'], 'check_calendar')
        self.assertIn('parameters', func_spec)
        self.assertIn('start_date', func_spec['parameters']['properties'])
        self.assertIn('end_date', func_spec['parameters']['properties'])

    @patch('gpt_calendar.OpenAI')
    def test_process_calendar_query(self, mock_openai):
        """GPT 쿼리 처리 테스트"""
        # 환경 변수 설정
        test_env = {
            'OPENAI_API_KEY': 'test_key',
            'GOOGLE_CLIENT_ID': 'test_client_id',
            'GOOGLE_PROJECT_ID': 'test_project_id',
            'GOOGLE_CLIENT_SECRET': 'test_client_secret'
        }
        
        with patch.dict(os.environ, test_env):
            # 모의 응답 설정
            mock_response = MagicMock()
            mock_response.choices[0].message.tool_calls[0].function.name = 'check_calendar'
            mock_response.choices[0].message.tool_calls[0].function.arguments = '''
            {
                "start_date": "2024-03-20T00:00:00",
                "end_date": "2024-03-21T00:00:00"
            }
            '''
            
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            # 테스트 실행
            with patch('gpt_calendar.check_calendar') as mock_check_calendar:
                process_calendar_query("오늘 일정 알려줘")
                
                # check_calendar가 호출되었는지 확인
                self.assertTrue(mock_check_calendar.called)

    def test_error_handling(self):
        """에러 처리 테스트"""
        # OpenAI API 오류
        with patch('gpt_calendar.OpenAI') as mock_openai:
            mock_openai.side_effect = Exception("API 오류")
            process_calendar_query("오늘 일정")  # 예외가 잡혀서 처리되어야 함

class TestGPTIntegration(unittest.TestCase):
    """통합 테스트"""
    
    def setUp(self):
        """각 테스트 전에 실행"""
        load_dotenv()

    @unittest.skipIf(not os.getenv('RUN_INTEGRATION_TESTS'), "통합 테스트 건너뛰기")
    def test_real_api_call(self):
        """실제 API 호출 테스트"""
        response = process_calendar_query("내일 일정 알려줘")
        # 응답 형식만 확인 (실제 내용은 매번 다를 수 있음)
        self.assertIsNotNone(response)

if __name__ == '__main__':
    unittest.main() 