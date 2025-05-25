import json
from typing import Optional, Dict, Any
import redis
import os
from google.auth.credentials import Credentials
from authlib.oauth2.rfc6749 import TokenMixin
import time
from redis import Redis
from auth.constants import REDIS_CONFIG
import logging

logger = logging.getLogger(__name__)

class RedisClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.client = redis.Redis.from_url(
                REDIS_CONFIG['url'],
                decode_responses=True
            )
        return cls._instance

    @property
    def redis_client(self):
        return self.client

# Redis 클라이언트 싱글톤 인스턴스
redis_client = RedisClient().redis_client

class AuthStorage:
    def __init__(self):
        self.redis = redis_client
        logger.info("AuthStorage initialized with Redis client")

    def _get_key(self, user_id: str, platform: str = 'google', target: str = 'calendar') -> str:
        """Redis 키를 생성합니다."""
        return f"auth:{platform}:{target}:{user_id}"

    def save_token(self, user_id: str, token: Dict[str, Any], platform: str = 'google', target: str = 'calendar') -> None:
        """토큰을 저장합니다."""
        if not user_id or not token:
            logger.warning("Attempted to save token with missing user_id or token")
            return

        key = self._get_key(user_id, platform, target)
        # 토큰 만료 시간 설정
        if 'expires_in' in token:
            token['expires_at'] = time.time() + token['expires_in']
        
        try:
            self.redis.set(key, json.dumps(token), ex=3600)  # 1시간 후 만료
            logger.info(f"Token saved for user {user_id}", extra={
                'platform': platform,
                'target': target,
                'expires_at': token.get('expires_at')
            })
        except Exception as e:
            logger.error(f"Failed to save token for user {user_id}", extra={
                'error': str(e),
                'platform': platform,
                'target': target
            })
            raise

    def get_token(self, user_id: str, platform: str = 'google', target: str = 'calendar') -> Optional[Dict[str, Any]]:
        """토큰을 조회합니다."""
        if not user_id:
            logger.warning("Attempted to get token with missing user_id")
            return None

        key = self._get_key(user_id, platform, target)
        try:
            data = self.redis.get(key)
            if data:
                token = json.loads(data)
                logger.info(f"Token retrieved for user {user_id}", extra={
                    'platform': platform,
                    'target': target,
                    'expires_at': token.get('expires_at')
                })
                return token
            logger.warning(f"No token found for user {user_id}", extra={
                'platform': platform,
                'target': target
            })
            return None
        except Exception as e:
            logger.error(f"Failed to get token for user {user_id}", extra={
                'error': str(e),
                'platform': platform,
                'target': target
            })
            raise

    def delete_token(self, user_id: str, platform: str = 'google', target: str = 'calendar') -> None:
        """토큰을 삭제합니다."""
        if not user_id:
            logger.warning("Attempted to delete token with missing user_id")
            return

        key = self._get_key(user_id, platform, target)
        try:
            self.redis.delete(key)
            logger.info(f"Token deleted for user {user_id}", extra={
                'platform': platform,
                'target': target
            })
        except Exception as e:
            logger.error(f"Failed to delete token for user {user_id}", extra={
                'error': str(e),
                'platform': platform,
                'target': target
            })
            raise

    def refresh_token(self, user_id: str, new_token: Dict[str, Any], platform: str = 'google', target: str = 'calendar') -> None:
        """토큰 갱신"""
        if not user_id or not new_token:
            logger.warning("Attempted to refresh token with missing user_id or token")
            return

        try:
            self.save_token(user_id, new_token, platform, target)
            logger.info(f"Token refreshed for user {user_id}", extra={
                'platform': platform,
                'target': target,
                'expires_at': new_token.get('expires_at')
            })
        except Exception as e:
            logger.error(f"Failed to refresh token for user {user_id}", extra={
                'error': str(e),
                'platform': platform,
                'target': target
            })
            raise

__all__ = ['AuthStorage', 'redis_client'] 