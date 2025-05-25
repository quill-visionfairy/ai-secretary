from typing import Optional, Dict, Any
from authlib.oauth2.rfc6749.errors import OAuth2Error
from auth.storage import AuthStorage
from auth.constants import OAUTH_CONFIG, API_CONFIG
import logging
import time
import requests

logger = logging.getLogger(__name__)

class AuthManager:
    def __init__(self):
        self.storage = AuthStorage()
        logger.info("AuthManager initialized")

    def get_auth_url(self, state: str = None) -> str:
        """인증 URL을 생성합니다."""
        try:
            params = {
                'client_id': OAUTH_CONFIG['client_id'],
                'redirect_uri': OAUTH_CONFIG['redirect_uri'],
                'scope': ' '.join(OAUTH_CONFIG['scopes']),
                'response_type': 'code',
                'access_type': 'offline',
                'prompt': 'consent'
            }
            if state:
                params['state'] = state

            auth_url = f"{OAUTH_CONFIG['authorize_url']}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
            logger.info("Generated auth URL", extra={'state': state})
            return auth_url
        except Exception as e:
            logger.error("Failed to generate auth URL", extra={'error': str(e)})
            raise OAuth2Error("인증 URL 생성 실패")

    def handle_callback(self, code: str, state: str = None) -> Dict[str, Any]:
        """OAuth 콜백을 처리합니다."""
        try:
            # 토큰 교환
            token_data = self._exchange_code_for_token(code)
            if not token_data:
                raise OAuth2Error("토큰 교환 실패")

            # 사용자 정보 조회
            user_info = self._get_user_info(token_data['access_token'])
            if not user_info:
                raise OAuth2Error("사용자 정보 조회 실패")

            # 토큰 저장
            self.storage.save_token(
                user_info['id'],
                token_data,
                platform='google',
                target='calendar'
            )

            logger.info("Successfully handled OAuth callback", extra={
                'user_id': user_info['id'],
                'state': state
            })
            return user_info
        except Exception as e:
            logger.error("Failed to handle OAuth callback", extra={
                'error': str(e),
                'state': state
            })
            raise OAuth2Error("인증 처리 실패")

    def get_token(self, user_id: str) -> Optional[Dict[str, Any]]:
        """사용자의 토큰을 조회합니다."""
        try:
            token = self.storage.get_token(user_id)
            if not token:
                logger.warning(f"No token found for user {user_id}")
                return None

            # 토큰 만료 확인
            if self._is_token_expired(token):
                logger.info(f"Token expired for user {user_id}")
                return None

            logger.info(f"Retrieved token for user {user_id}")
            return token
        except Exception as e:
            logger.error(f"Failed to get token for user {user_id}", extra={'error': str(e)})
            raise OAuth2Error("토큰 조회 실패")

    def refresh_token(self, user_id: str) -> Optional[Dict[str, Any]]:
        """토큰을 갱신합니다."""
        try:
            old_token = self.storage.get_token(user_id)
            if not old_token or 'refresh_token' not in old_token:
                logger.warning(f"Cannot refresh token for user {user_id}: No refresh token available")
                return None

            # 토큰 갱신 요청
            new_token = self._refresh_access_token(old_token['refresh_token'])
            if not new_token:
                logger.error(f"Failed to refresh token for user {user_id}")
                return None

            # 새 토큰 저장
            self.storage.refresh_token(user_id, new_token)
            logger.info(f"Successfully refreshed token for user {user_id}")
            return new_token
        except Exception as e:
            logger.error(f"Failed to refresh token for user {user_id}", extra={'error': str(e)})
            raise OAuth2Error("토큰 갱신 실패")

    def _is_token_expired(self, token: Dict[str, Any]) -> bool:
        """토큰 만료 여부를 확인합니다."""
        if 'expires_at' not in token:
            return True
        return time.time() >= token['expires_at']

    def _exchange_code_for_token(self, code: str) -> Optional[Dict[str, Any]]:
        """인증 코드를 토큰으로 교환합니다."""
        try:
            token_data = {
                'code': code,
                'client_id': OAUTH_CONFIG['client_id'],
                'client_secret': OAUTH_CONFIG['client_secret'],
                'redirect_uri': OAUTH_CONFIG['redirect_uri'],
                'grant_type': 'authorization_code'
            }
            
            response = requests.post(OAUTH_CONFIG['token_url'], data=token_data)
            if response.status_code != 200:
                logger.error("Token exchange failed", extra={
                    'status_code': response.status_code,
                    'response': response.text
                })
                return None
                
            token = response.json()
            token['expires_at'] = time.time() + token.get('expires_in', 3600)
            return token
            
        except Exception as e:
            logger.error("Failed to exchange code for token", extra={'error': str(e)})
            return None

    def _get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """사용자 정보를 조회합니다."""
        try:
            headers = {'Authorization': f"Bearer {access_token}"}
            response = requests.get(OAUTH_CONFIG['userinfo_url'], headers=headers)
            
            if response.status_code != 200:
                logger.error("Failed to get user info", extra={
                    'status_code': response.status_code,
                    'response': response.text
                })
                return None
                
            return response.json()
            
        except Exception as e:
            logger.error("Failed to get user info", extra={'error': str(e)})
            return None

    def _refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """액세스 토큰을 갱신합니다."""
        try:
            token_data = {
                'client_id': OAUTH_CONFIG['client_id'],
                'client_secret': OAUTH_CONFIG['client_secret'],
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token'
            }
            
            response = requests.post(OAUTH_CONFIG['token_url'], data=token_data)
            if response.status_code != 200:
                logger.error("Token refresh failed", extra={
                    'status_code': response.status_code,
                    'response': response.text
                })
                return None
                
            token = response.json()
            token['expires_at'] = time.time() + token.get('expires_in', 3600)
            token['refresh_token'] = refresh_token  # 리프레시 토큰 유지
            return token
            
        except Exception as e:
            logger.error("Failed to refresh access token", extra={'error': str(e)})
            return None

    def get_user_info(self) -> Dict[str, Any]:
        """사용자 정보를 반환합니다."""
        if not self.token:
            raise ValueError("인증되지 않은 사용자입니다.")

        if self._is_token_expired():
            self._refresh_token()

        headers = {'Authorization': f"Bearer {self.token['access_token']}"}
        response = requests.get(OAUTH_CONFIG['userinfo_url'], headers=headers)
        if response.status_code != 200:
            raise OAuth2Error('Failed to get user info')
            
        return response.json()

    def revoke_credentials(self) -> None:
        """사용자 인증 정보를 삭제합니다."""
        if self.user_id:
            self.token_storage.delete_token(self.user_id)
        self.token = None

    def get_token_info(self) -> Dict[str, Any]:
        """토큰 정보를 반환합니다."""
        if not self.token:
            raise ValueError("인증되지 않은 사용자입니다.")

        if self._is_token_expired():
            self._refresh_token()

        return {
            'access_token': self.token['access_token'],
            'token_type': self.token.get('token_type', 'Bearer'),
            'expires_in': self.token.get('expires_in'),
            'scope': self.token.get('scope', ' '.join(OAUTH_CONFIG['scopes']))
        }

    def get_calendar_info(self) -> Dict[str, Any]:
        """캘린더 정보를 반환합니다."""
        if not self.token:
            raise ValueError("인증되지 않은 사용자입니다.")

        if self._is_token_expired():
            self._refresh_token()

        headers = {'Authorization': f"Bearer {self.token['access_token']}"}
        response = requests.get(
            f"{API_CONFIG['calendar_api_url']}/users/me/calendarList",
            headers=headers
        )
        if response.status_code != 200:
            raise OAuth2Error('Failed to get calendar info')
            
        return response.json()

    def get_calendar_events(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """캘린더 이벤트를 반환합니다."""
        if not self.token:
            raise ValueError("인증되지 않은 사용자입니다.")

        if self._is_token_expired():
            self._refresh_token()

        headers = {'Authorization': f"Bearer {self.token['access_token']}"}
        params = {
            'timeMin': start_date,
            'timeMax': end_date,
            'singleEvents': True,
            'orderBy': 'startTime'
        }
        
        response = requests.get(
            f"{API_CONFIG['calendar_api_url']}/calendars/primary/events",
            headers=headers,
            params=params
        )
        if response.status_code != 200:
            raise OAuth2Error('Failed to get calendar events')
            
        return response.json()

__all__ = ['AuthManager']