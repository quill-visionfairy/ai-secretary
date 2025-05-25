from flask import Flask
from flask_cors import CORS
from auth.settings import load_config
from auth.storage import redis_client
import logging

def create_app():
    """Flask 애플리케이션 팩토리"""
    app = Flask(__name__)
    
    # 설정 로드
    config = load_config()
    app.config.update(config)
    
    # CORS 설정
    CORS(app, supports_credentials=True, origins=[
        "http://localhost:3000",
        "http://localhost:8080",
        "https://chat.openai.com"
    ])
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Redis 세션 설정
    app.config['SESSION_TYPE'] = 'redis'
    app.config['SESSION_REDIS'] = redis_client
    app.config['SESSION_PERMANENT'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600
    
    # 블루프린트 등록
    from routes.auth import auth_bp
    from routes.calendar import calendar_bp
    from routes.gpt import gpt_bp
    
    app.register_blueprint(auth_bp, url_prefix='/oauth')
    app.register_blueprint(calendar_bp, url_prefix='/calendar')
    app.register_blueprint(gpt_bp, url_prefix='/gpt')
    
    # 에러 핸들러 등록
    from auth.validator import validate_auth_setup
    from authlib.integrations.flask_oauth2 import OAuth2Error
    
    @app.errorhandler(500)
    def internal_error(error):
        logging.error(f"Internal error: {str(error)}")
        return {"error": "서버 내부 오류 발생", "details": str(error)}, 500

    @app.errorhandler(OAuth2Error)
    def handle_oauth_error(error):
        """OAuth 에러 처리"""
        return {
            'error': error.error,
            'error_description': error.description
        }, error.status_code

    @app.errorhandler(Exception)
    def handle_error(error):
        """전역 에러 핸들러"""
        logging.error(f"Unhandled error: {str(error)}")
        return {
            'error': str(error),
            'message': 'An error occurred'
        }, 500
    
    return app
