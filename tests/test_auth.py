import pytest
from unittest.mock import patch, MagicMock
from auth.manager import AuthManager
from auth.constants import OAUTH_CONFIG
import time
import fakeredis
import json

@pytest.fixture
def mock_redis():
    """Mock Redis 서버 생성"""
    server = fakeredis.FakeServer()
    redis_client = fakeredis.FakeRedis(server=server)
    return redis_client

@pytest.fixture
def auth_manager(mock_redis):
    """Redis Mock을 사용하는 AuthManager 생성"""
    with patch('auth.storage.redis_client', mock_redis):
        return AuthManager()

@pytest.fixture
def mock_token():
    return {
        'access_token': 'test_access_token',
        'refresh_token': 'test_refresh_token',
        'expires_in': 3600,
        'expires_at': time.time() + 3600
    }

@pytest.fixture
def mock_user_info():
    return {
        'id': 'test_user_id',
        'email': 'test@example.com',
        'name': 'Test User'
    }

def test_get_auth_url(auth_manager):
    """인증 URL 생성 테스트"""
    auth_url = auth_manager.get_auth_url()
    assert OAUTH_CONFIG['authorize_url'] in auth_url
    assert f"client_id={OAUTH_CONFIG['client_id']}" in auth_url
    assert f"redirect_uri={OAUTH_CONFIG['redirect_uri']}" in auth_url

@patch('requests.post')
def test_exchange_code_for_token(mock_post, auth_manager, mock_token):
    """토큰 교환 테스트"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_token
    mock_post.return_value = mock_response

    result = auth_manager._exchange_code_for_token('test_code')
    assert result == mock_token
    mock_post.assert_called_once()

@patch('requests.get')
def test_get_user_info(mock_get, auth_manager, mock_user_info):
    """사용자 정보 조회 테스트"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_user_info
    mock_get.return_value = mock_response

    result = auth_manager._get_user_info('test_access_token')
    assert result == mock_user_info
    mock_get.assert_called_once()

@patch('requests.post')
def test_refresh_access_token(mock_post, auth_manager, mock_token):
    """토큰 갱신 테스트"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_token
    mock_post.return_value = mock_response

    result = auth_manager._refresh_access_token('test_refresh_token')
    assert result == mock_token
    mock_post.assert_called_once()

def test_is_token_expired(auth_manager, mock_token):
    """토큰 만료 확인 테스트"""
    # 만료되지 않은 토큰
    assert not auth_manager._is_token_expired(mock_token)
    
    # 만료된 토큰
    expired_token = mock_token.copy()
    expired_token['expires_at'] = time.time() - 1
    assert auth_manager._is_token_expired(expired_token)

@patch('auth.manager.AuthManager._refresh_access_token')
@patch('auth.manager.AuthManager._is_token_expired')
def test_refresh_token(mock_is_expired, mock_refresh, auth_manager, mock_token, mock_redis):
    """토큰 갱신 프로세스 테스트"""
    # Redis에 토큰 저장 (올바른 키 형식 사용)
    mock_redis.set(f"auth:google:calendar:test_user_id", json.dumps(mock_token))
    
    mock_is_expired.return_value = True
    mock_refresh.return_value = mock_token

    result = auth_manager.refresh_token('test_user_id')
    assert result == mock_token
    mock_refresh.assert_called_once()

@patch('auth.manager.AuthManager._get_user_info')
@patch('auth.manager.AuthManager._exchange_code_for_token')
def test_handle_callback(mock_exchange, mock_get_user_info, auth_manager, mock_token, mock_user_info, mock_redis):
    """OAuth 콜백 처리 테스트"""
    mock_exchange.return_value = mock_token
    mock_get_user_info.return_value = mock_user_info

    result = auth_manager.handle_callback('test_code')
    assert result == mock_user_info
    mock_exchange.assert_called_once_with('test_code')
    mock_get_user_info.assert_called_once_with(mock_token['access_token']) 