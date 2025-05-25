from flask import Flask, jsonify, request
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix
from auth.validator import validate_auth_setup
from authlib.integrations.flask_oauth2 import OAuth2Error
from flask_cors import CORS
from auth.storage import redis_client
import logging
import os
from __init__ import create_app

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 환경 변수 로드
load_dotenv()

# 인증 설정 검증
validation_result = validate_auth_setup()
if validation_result["status"] == "error":
    raise Exception("인증 설정 검증 실패: " + validation_result["error"])

# Flask 애플리케이션 초기화
app = Flask(__name__, static_url_path='', static_folder='static')
app.secret_key = os.getenv('SESSION_SECRET_KEY')
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Redis 세션 설정
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = redis_client
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1시간

# CORS 설정
CORS(app, supports_credentials=True, origins=[
    "http://localhost:3000",
    "http://localhost:8080",
    "https://chat.openai.com"
])

@app.before_request
def log_every_request():
    logger.info(f"Request to {request.path} method={request.method}")

@app.route('/')
def index():
    """메인 페이지"""
    return jsonify({'status': 'ok', 'message': 'Welcome to the API'})

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {str(error)}")
    return jsonify({"error": "서버 내부 오류 발생", "details": str(error)}), 500

@app.errorhandler(OAuth2Error)
def handle_oauth_error(error):
    """OAuth 에러 처리"""
    return jsonify({
        'error': error.error,
        'error_description': error.description
    }), error.status_code

@app.errorhandler(Exception)
def handle_error(error):
    """전역 에러 핸들러"""
    logger.error(f"Unhandled error: {str(error)}")
    return jsonify({
        'error': str(error),
        'message': 'An error occurred'
    }), 500

# Blueprint 등록
from routes import auth_bp, calendar_bp, gpt_bp
app.register_blueprint(auth_bp)
app.register_blueprint(calendar_bp)
app.register_blueprint(gpt_bp)

if __name__ == '__main__':
    app.run(debug=True)
