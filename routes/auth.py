from flask import request, jsonify, redirect, session, url_for, current_app
from . import auth_bp
from auth.manager import AuthManager
from auth.storage import redis_client
from auth.utils import get_auth_manager
from functools import wraps
import logging
from typing import Optional, Dict, Any
from datetime import timedelta

logger = logging.getLogger(__name__)

class AuthError(Exception):
    """인증 관련 커스텀 예외"""
    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

def require_auth(f):
    """인증이 필요한 엔드포인트를 위한 데코레이터"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            logger.warning("[AUTH] Unauthorized access attempt", extra={
                'path': request.path,
                'method': request.method,
                'ip': request.remote_addr
            })
            raise AuthError('Unauthorized')
        
        # 세션 갱신
        session.modified = True
        return f(*args, **kwargs)
    return decorated

def handle_auth_error(f):
    """인증 관련 에러를 처리하는 데코레이터"""
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except AuthError as e:
            logger.error("[AUTH] Authentication error", extra={
                'error': str(e),
                'status_code': e.status_code,
                'path': request.path,
                'method': request.method
            })
            return jsonify({'error': e.message}), e.status_code
        except Exception as e:
            logger.error("[AUTH] Unexpected error", extra={
                'error': str(e),
                'path': request.path,
                'method': request.method
            }, exc_info=True)
            return jsonify({'error': 'Internal server error'}), 500
    return decorated

def setup_session(user_id: str) -> None:
    """세션 설정을 위한 헬퍼 함수"""
    session.clear()
    session['user_id'] = user_id
    session.permanent = True
    session.modified = True
    # 세션 ID 재생성
    session.regenerate()
    logger.info("[AUTH] Session setup completed", extra={'user_id': user_id})

@auth_bp.route('/authorize')
@handle_auth_error
def authorize():
    """OAuth2 인증 시작점"""
    auth_manager = get_auth_manager()
    auth_url = auth_manager.get_authorization_url()
    logger.info("[AUTH] Starting OAuth2 authorization flow", extra={
        'auth_url': auth_url
    })
    return redirect(auth_url)

@auth_bp.route('/callback')
@handle_auth_error
def oauth_callback():
    """OAuth2 콜백 처리"""
    code = request.args.get('code')
    if not code:
        logger.warning("[AUTH] OAuth callback received without code", extra={
            'query_params': dict(request.args)
        })
        raise AuthError('No code provided', 400)
        
    auth_manager = get_auth_manager()
    user = auth_manager.handle_oauth_callback(code)
    
    # 세션 설정
    setup_session(user['email'])
    
    logger.info("[AUTH] User successfully authenticated", extra={
        'user_id': user['email'],
        'provider': 'google'
    })
    return redirect(url_for('index'))

@auth_bp.route('/token')
@require_auth
@handle_auth_error
def get_token():
    """토큰 정보 조회"""
    user_id = session['user_id']
    auth_manager = get_auth_manager(user_id)
    token_info = auth_manager.get_token_info()
    logger.info("[AUTH] Token info retrieved", extra={
        'user_id': user_id,
        'token_type': token_info.get('token_type')
    })
    return jsonify(token_info)

@auth_bp.route('/userinfo')
@require_auth
@handle_auth_error
def get_user_info():
    """사용자 정보 조회"""
    user_id = session['user_id']
    auth_manager = get_auth_manager(user_id)
    user_info = auth_manager.get_user_info()
    logger.info("[AUTH] User info retrieved", extra={
        'user_id': user_id,
        'email': user_info.get('email')
    })
    return jsonify(user_info)

@auth_bp.route('/revoke')
@require_auth
@handle_auth_error
def revoke_token():
    """토큰 폐기"""
    user_id = session['user_id']
    auth_manager = get_auth_manager(user_id)
    
    # 토큰 폐기 전 검증
    if not auth_manager.get_token_info():
        logger.warning("[AUTH] Token revocation attempted with no valid token", extra={
            'user_id': user_id
        })
        raise AuthError('No valid token found')
    
    # 토큰 폐기
    auth_manager.revoke_credentials()
    
    # 세션 및 Redis 데이터 정리
    session.clear()
    redis_client.delete(f"tokens:google:{user_id}")
    
    logger.info("[AUTH] Token successfully revoked", extra={
        'user_id': user_id,
        'provider': 'google'
    })
    return jsonify({'message': 'Token revoked successfully'})

@auth_bp.route('/logout')
@handle_auth_error
def logout():
    """로그아웃"""
    user_id = request.args.get('user_id')
    if user_id:
        # Redis에서 토큰 삭제
        redis_client.delete(f"tokens:google:{user_id}")
    
    # 세션 무효화
    session.clear()
    session.modified = True
    
    logger.info("[AUTH] User logged out", extra={
        'user_id': user_id,
        'provider': 'google'
    })
    return redirect(url_for('index')) 