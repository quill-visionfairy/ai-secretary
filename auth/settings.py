import os
from typing import Dict, Any

# OAuth 및 인증 관련 상수/설정만 정의하는 파일
SCOPES = {
    'google': [
        'openid', #반드시 포함 
        'https://www.googleapis.com/auth/calendar.readonly',
        'https://www.googleapis.com/auth/userinfo.email'
    ],
    ('gpt', 'google'): [
        'openid',
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/userinfo.email'
    ],
    # 'notion': [...],
    # 'slack': [...],
}

# Redis 연결 설정
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# OAuth2 설정
OAUTH_REDIRECT_URI = os.getenv('OAUTH_REDIRECT_URI', 'http://localhost:8080/oauth2callback')
CLIENT_SECRETS_FILE = 'client_secrets.json'

# 기타 설정
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
PORT = int(os.getenv('PORT', '8080'))

def load_config() -> Dict[str, Any]:
    """
    애플리케이션 설정을 로드합니다.
    
    Returns:
        Dict[str, Any]: 설정 값들을 포함하는 딕셔너리
    """
    return {
        'SCOPES': SCOPES,
        'REDIS_URL': REDIS_URL,
        'OAUTH_REDIRECT_URI': OAUTH_REDIRECT_URI,
        'CLIENT_SECRETS_FILE': CLIENT_SECRETS_FILE,
        'DEBUG': DEBUG,
        'PORT': PORT
    } 