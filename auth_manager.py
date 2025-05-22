import os
import redis
import json
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# Redis 연결 (환경 변수 또는 기본값 사용)
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

SCOPES = {
    'google': ['https://www.googleapis.com/auth/calendar.readonly'],
    # 확장: 'notion': [...], 'slack': [...]
}

class AuthManager:
    def __init__(self, platform: str):
        self.platform = platform
        self.scopes = SCOPES.get(platform, [])

    def create_flow(self):
        """플랫폼별 OAuth Flow 객체 생성 (Google 예시)"""
        if self.platform == 'google':
            client_config = {
                "web": {
                    "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                    "project_id": os.getenv("GOOGLE_PROJECT_ID"),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                    "redirect_uris": [
                        os.getenv("GOOGLE_REDIRECT_URI", "https://ai-secretary-148126309509.asia-northeast3.run.app/oauth2callback")
                    ]
                }
            }
            return Flow.from_client_config(
                client_config,
                scopes=self.scopes,
                redirect_uri=client_config["web"]["redirect_uris"][0]
            )
        # TODO: Notion, Slack 등 추가
        raise NotImplementedError(f"플랫폼 {self.platform}의 OAuth는 아직 지원되지 않습니다.")

    def save_tokens(self, user_id: str, credentials):
        """토큰을 Redis에 저장 (credentials는 dict 또는 Credentials 객체)"""
        if isinstance(credentials, Credentials):
            data = self.credentials_to_dict(credentials)
        else:
            data = credentials
        key = f"tokens:{self.platform}:{user_id}"
        redis_client.set(key, json.dumps(data))

    def load_tokens(self, user_id: str):
        """Redis에서 토큰 로드 (딕셔너리 반환, 없으면 None)"""
        key = f"tokens:{self.platform}:{user_id}"
        value = redis_client.get(key)
        if value:
            return json.loads(value)
        return None

    def credentials_to_dict(self, credentials):
        """Credentials 객체를 딕셔너리로 변환"""
        return {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }

    def get_user_id_from_credentials(self, credentials):
        """Google Credentials에서 이메일 추출 (id_token 사용)"""
        if hasattr(credentials, 'id_token') and credentials.id_token:
            return credentials.id_token.get('email')
        # id_token이 없으면 API 호출 필요 (생략)
        return None 