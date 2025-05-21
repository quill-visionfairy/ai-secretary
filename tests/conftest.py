import pytest
import os
from dotenv import load_dotenv

@pytest.fixture(autouse=True)
def load_env():
    """모든 테스트에서 자동으로 실행되는 픽스처"""
    # .env.test 파일 로드
    env_file = os.getenv('ENV_FILE', '.env.test')
    load_dotenv(env_file)
    
    # 테스트용 환경 변수 설정
    test_env = {
        'OPENAI_API_KEY': 'test_key',
        'GOOGLE_CLIENT_ID': 'test_client_id',
        'GOOGLE_PROJECT_ID': 'test_project_id',
        'GOOGLE_CLIENT_SECRET': 'test_client_secret'
    }
    
    # 기존 환경 변수 백업
    old_environ = dict(os.environ)
    
    # 테스트용 환경 변수 설정
    os.environ.update(test_env)
    
    yield
    
    # 테스트 후 환경 변수 복원
    os.environ.clear()
    os.environ.update(old_environ) 