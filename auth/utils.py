from typing import Optional
from auth.manager import AuthManager

def get_auth_manager(user_id: Optional[str] = None) -> AuthManager:
    """AuthManager 인스턴스를 생성하는 헬퍼 함수
    
    Args:
        user_id (Optional[str]): 사용자 ID. 기본값은 None
        
    Returns:
        AuthManager: AuthManager 인스턴스
    """
    return AuthManager('google', 'calendar', user_id) 