import os
import json
import redis
from typing import List, Dict, Any
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from auth.constants import (
    SCOPES,
    OAUTH_REDIRECT_URI,
    CLIENT_SECRETS_FILE,
    REDIS_URL,
    OAUTH_CONFIG,
    API_CONFIG,
    REDIS_CONFIG
)

class AuthValidationError(Exception):
    """인증 설정 검증 중 발생하는 예외"""
    pass

def validate_env_vars() -> List[str]:
    """필수 환경 변수 검증"""
    required_vars = [
        'GOOGLE_CLIENT_ID',
        'GOOGLE_PROJECT_ID',
        'GOOGLE_CLIENT_SECRET',
        'OPENAI_API_KEY'
    ]
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
    return missing_vars

def validate_client_secrets() -> Dict[str, Any]:
    """client_secrets.json 파일 검증"""
    if not os.path.exists(CLIENT_SECRETS_FILE):
        raise AuthValidationError(f"Client secrets file not found: {CLIENT_SECRETS_FILE}")
    
    try:
        with open(CLIENT_SECRETS_FILE, 'r') as f:
            secrets = json.load(f)
            
        # 필수 필드 검증
        required_fields = ['web', 'installed']
        if not any(field in secrets for field in required_fields):
            raise AuthValidationError("Client secrets must contain 'web' or 'installed' configuration")
            
        # client_id와 client_secret 검증
        config = secrets.get('web', secrets.get('installed', {}))
        if not config.get('client_id') or not config.get('client_secret'):
            raise AuthValidationError("Client secrets must contain client_id and client_secret")
            
        # redirect_uris 검증
        if 'web' in secrets and 'redirect_uris' in secrets['web']:
            if OAUTH_REDIRECT_URI not in secrets['web']['redirect_uris']:
                raise AuthValidationError(f"OAuth redirect URI {OAUTH_REDIRECT_URI} not found in client secrets")
                
        return secrets
    except json.JSONDecodeError:
        raise AuthValidationError("Invalid JSON in client secrets file")

def validate_redis_connection() -> bool:
    """Redis 연결 검증"""
    try:
        client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        client.ping()
        return True
    except redis.ConnectionError as e:
        raise AuthValidationError(f"Failed to connect to Redis: {str(e)}")

def validate_oauth_flow() -> bool:
    """OAuth Flow 설정 검증"""
    try:
        # Flow 객체 생성 시도
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=OAUTH_REDIRECT_URI
        )
        return True
    except Exception as e:
        raise AuthValidationError(f"Failed to create OAuth flow: {str(e)}")

def validate_auth_setup() -> Dict[str, Any]:
    """전체 인증 설정 검증"""
    validation_results = {
        "status": "success",
        "details": {}
    }
    
    try:
        # 1. 환경 변수 검증
        missing_vars = validate_env_vars()
        if missing_vars:
            raise AuthValidationError(f"Missing environment variables: {', '.join(missing_vars)}")
        validation_results["details"]["env_vars"] = "valid"
        
        # 2. client_secrets.json 검증
        secrets = validate_client_secrets()
        validation_results["details"]["client_secrets"] = "valid"
        
        # 3. Redis 연결 검증
        if validate_redis_connection():
            validation_results["details"]["redis"] = "connected"
            
        # 4. OAuth Flow 검증
        if validate_oauth_flow():
            validation_results["details"]["oauth_flow"] = "valid"
            
        return validation_results
        
    except AuthValidationError as e:
        validation_results["status"] = "error"
        validation_results["error"] = str(e)
        return validation_results

if __name__ == "__main__":
    # 테스트 실행
    result = validate_auth_setup()
    print(json.dumps(result, indent=2)) 