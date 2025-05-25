import os

# OAuth2 설정
OAUTH_CONFIG = {
    'client_id': os.getenv('GOOGLE_CLIENT_ID'),
    'client_secret': os.getenv('GOOGLE_CLIENT_SECRET'),
    'authorize_url': 'https://accounts.google.com/o/oauth2/v2/auth',
    'token_url': 'https://oauth2.googleapis.com/token',
    'userinfo_url': 'https://www.googleapis.com/oauth2/v3/userinfo',
    'revoke_url': 'https://oauth2.googleapis.com/revoke',
    'redirect_uri': os.getenv('OAUTH_REDIRECT_URI', 'http://localhost:5000/oauth/callback'),
    'scopes': [
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile'
    ]
}

# OAuth2 스코프
SCOPES = OAUTH_CONFIG['scopes']

# OAuth2 리다이렉트 URI
OAUTH_REDIRECT_URI = OAUTH_CONFIG['redirect_uri']

# 클라이언트 시크릿 파일 경로
CLIENT_SECRETS_FILE = os.getenv('CLIENT_SECRETS_FILE', 'client_secrets.json')

# Redis 설정
REDIS_CONFIG = {
    'host': os.getenv('REDIS_HOST', 'localhost'),
    'port': int(os.getenv('REDIS_PORT', 6379)),
    'db': int(os.getenv('REDIS_DB', 0)),
    'url': os.getenv('REDIS_URL', 'redis://localhost:6379/0')
}

# Redis URL (이전 버전 호환성)
REDIS_URL = REDIS_CONFIG['url']

# 세션 설정
SESSION_CONFIG = {
    'secret_key': os.getenv('SESSION_SECRET_KEY', os.urandom(24)),
    'session_type': 'redis',
    'permanent': True,
    'session_lifetime': 3600  # 1시간
}

# API 설정
API_CONFIG = {
    'calendar_api_url': 'https://www.googleapis.com/calendar/v3',
    'userinfo_api_url': 'https://www.googleapis.com/oauth2/v3/userinfo',
    'base_url': os.getenv('API_BASE_URL', 'http://localhost:5000'),
    'authorize_url': os.getenv('AUTHORIZE_URL', 'https://ai-secretary-148126309509.asia-northeast3.run.app/oauth/authorize')
}

__all__ = [
    'OAUTH_CONFIG', 'REDIS_CONFIG', 'SESSION_CONFIG', 'API_CONFIG',
    'SCOPES', 'OAUTH_REDIRECT_URI', 'CLIENT_SECRETS_FILE', 'REDIS_URL'
] 