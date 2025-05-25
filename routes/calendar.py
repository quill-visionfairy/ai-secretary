from flask import request, jsonify, session
from . import calendar_bp
from auth.manager import AuthManager
import logging

logger = logging.getLogger(__name__)

def get_auth_manager(user_id=None):
    """AuthManager 인스턴스를 생성하는 헬퍼 함수"""
    return AuthManager('google', 'calendar', user_id)

@calendar_bp.route('/')
def get_calendar():
    """캘린더 정보 조회"""
    try:
        auth_manager = get_auth_manager(session.get('user_id'))
        if not auth_manager.is_authenticated():
            logger.warning(f"Unauthenticated calendar access attempt by {session.get('user_id')}")
            return jsonify({'error': 'Not authenticated'}), 401
        calendar_info = auth_manager.get_calendar_info()
        logger.info(f"Calendar info retrieved for user {session.get('user_id')}")
        return jsonify(calendar_info)
    except Exception as e:
        logger.error(f"Calendar info retrieval error: {str(e)}")
        return jsonify({'error': 'Failed to get calendar info'}), 500

@calendar_bp.route('/events')
def get_calendar_events():
    """캘린더 이벤트 조회"""
    try:
        auth_manager = get_auth_manager(session.get('user_id'))
        if not auth_manager.is_authenticated():
            logger.warning(f"Unauthenticated events access attempt by {session.get('user_id')}")
            return jsonify({'error': 'Not authenticated'}), 401
        events = auth_manager.get_calendar_events()
        logger.info(f"Calendar events retrieved for user {session.get('user_id')}")
        return jsonify(events)
    except Exception as e:
        logger.error(f"Calendar events retrieval error: {str(e)}")
        return jsonify({'error': 'Failed to get calendar events'}), 500 