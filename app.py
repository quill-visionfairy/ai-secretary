from flask import Flask, request, jsonify, redirect, session, url_for
from datetime import datetime
from main import check_google_calendar, get_calendar_service, create_flow, credentials_to_dict
from gpt_calendar import process_calendar_query
import os
import json
import traceback
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix
from auth_manager import AuthManager, redis_client

print("🔥 Flask 서버 실행 시작됨!")


# 환경 변수 로딩 디버깅
print("현재 작업 디렉토리:", os.getcwd())
print(".env 파일 존재 여부:", os.path.exists('.env'))

# .env 파일 내용 확인
try:
    with open('.env', 'r', encoding='utf-8') as f:
        env_content = f.read()
    print("\n.env 파일 구조:")
    for line in env_content.splitlines():
        if line.strip() and not line.startswith('#'):
            key = line.split('=')[0]
            print(f"- {key}: {'값이 있음' if '=' in line else '값이 없음'}")
except Exception as e:
    print(".env 파일 읽기 실패:", str(e))

# .env 파일 로드
load_dotenv(verbose=True)

app = Flask(__name__)
app.secret_key = os.urandom(24)  # 세션을 위한 비밀키 설정
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

def check_env_vars():
    """환경 변수 체크"""
    required_vars = [
        'GOOGLE_CLIENT_ID',
        'GOOGLE_PROJECT_ID',
        'GOOGLE_CLIENT_SECRET',
        'OPENAI_API_KEY'
    ]
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        print(f"환경 변수 {var}: {'설정됨' if value else '설정되지 않음'}")
        if not value:
            missing_vars.append(var)
    return missing_vars

@app.route('/')
def index():
    return "AI Secretary API Server"

@app.route('/auth_status')
def auth_status():
    """Google Calendar 인증 상태 확인"""
    try:
        # 환경 변수 직접 확인
        env_vars = {
            'GOOGLE_CLIENT_ID': os.getenv('GOOGLE_CLIENT_ID'),
            'GOOGLE_PROJECT_ID': os.getenv('GOOGLE_PROJECT_ID'),
            'GOOGLE_CLIENT_SECRET': os.getenv('GOOGLE_CLIENT_SECRET'),
            'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY')
        }
        
        print("\n환경 변수 상태:")
        for key, value in env_vars.items():
            print(f"{key}: {'설정됨 (길이: ' + str(len(value)) + ')' if value else '설정되지 않음'}")

        # 환경 변수 체크
        missing_vars = check_env_vars()
        if missing_vars:
            return jsonify({
                "status": "error",
                "message": f"Missing environment variables: {', '.join(missing_vars)}"
            }), 400

        user_id = request.args.get('user_id')
        platform = request.args.get('platform', 'google')
        if not user_id:
            return jsonify({
                "status": "error",
                "message": "user_id가 필요합니다. 인증 상태 확인 불가"
            }), 400

        service = get_calendar_service(user_id, platform)
        if service:
            return jsonify({"status": "ok", "message": "Authentication successful"})
        return jsonify({"status": "error", "message": "Authentication failed"}), 401
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": "JSON parsing error", "details": str(e)}), 500
    except Exception as e:
        print(f"Error in auth_status endpoint: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e), "type": type(e).__name__}), 500

@app.route('/calendar', methods=['GET'])
def calendar():
    try:
        # 환경 변수 체크
        missing_vars = check_env_vars()
        if missing_vars:
            return jsonify({
                "status": "error",
                "message": f"Missing environment variables: {', '.join(missing_vars)}"
            }), 400

        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        user_id = request.args.get('user_id')
        platform = request.args.get('platform', 'google')

        if not start_date or not end_date or not user_id:
            return jsonify({'error': 'start_date, end_date, user_id are required'}), 400

        # 서비스 객체가 있는지 확인
        service = get_calendar_service(user_id, platform)
        if not service:
            return jsonify({'error': 'Calendar service not authenticated'}), 401

        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        events = route_calendar_service(user_id, start, end, platform)
        return jsonify({
            'status': 'ok',
            'events': events
        })
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": "JSON parsing error", "details": str(e)}), 500
    except Exception as e:
        print(f"Error in calendar endpoint: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e), "type": type(e).__name__}), 500

@app.route('/query_calendar', methods=['POST'])
def query_calendar():
    try:
        # 환경 변수 체크
        missing_vars = check_env_vars()
        if missing_vars:
            return jsonify({
                "status": "error",
                "message": f"Missing environment variables: {', '.join(missing_vars)}"
            }), 400

        data = request.get_json()
        if not data or 'start_time' not in data or 'end_time' not in data or 'user_id' not in data:
            return jsonify({
                'status': 'error',
                'message': 'start_time, end_time, user_id are required'
            }), 400

        try:
            # ISO 8601 형식의 시간을 datetime 객체로 변환
            start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))
        except ValueError as e:
            return jsonify({
                'status': 'error',
                'message': f'Invalid datetime format: {str(e)}'
            }), 400

        platform = data.get('platform', 'google')
        # 서비스 객체 가져오기
        service = get_calendar_service(data['user_id'], platform)
        if not service:
            return jsonify({
                'status': 'error',
                'message': 'Calendar service not authenticated'
            }), 401

        # 캘린더 이벤트 조회
        events = route_calendar_service(data['user_id'], start_time, end_time, platform)
        
        return jsonify({
            'status': 'success',
            'events': events
        })

    except Exception as e:
        print(f"Error in query_calendar endpoint: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/login')
def login():
    """Google OAuth 로그인 (플랫폼/사용자 ID 지원)"""
    platform = request.args.get('platform', 'google')
    # user_id는 인증 후 콜백에서 추출
    auth = AuthManager(platform)
    flow = auth.create_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    # state는 필요시 Redis에 저장 가능 (여기선 생략)
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    """OAuth 콜백 처리 (세션 대신 Redis 사용)"""
    platform = request.args.get('platform', 'google')
    auth = AuthManager(platform)
    flow = auth.create_flow()
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    # 사용자 이메일 추출 (id_token에서)
    user_id = auth.get_user_id_from_credentials(credentials)
    if not user_id:
        return jsonify({'status': 'error', 'message': '사용자 이메일 추출 실패'}), 400
    # Redis에 토큰 저장
    auth.save_tokens(user_id, credentials)
    print(f"✅ Redis에 토큰 저장 완료! user_id={user_id}")
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    """로그아웃 (Redis에서 토큰 삭제)"""
    platform = request.args.get('platform', 'google')
    user_id = request.args.get('user_id')
    if user_id:
        key = f"tokens:{platform}:{user_id}"
        redis_client.delete(key)
        print(f"🧹 Redis 로그아웃 완료: {key}")
    return redirect(url_for('index'))

@app.route('/ask_gpt', methods=['POST'])
def ask_gpt():
    try:
        # 환경 변수 체크
        missing_vars = check_env_vars()
        if missing_vars:
            return jsonify({
                "status": "error",
                "message": f"Missing environment variables: {', '.join(missing_vars)}"
            }), 400

        # 요청 데이터 확인
        data = request.get_json()
        if not data or 'query' not in data or 'user_id' not in data:
            return jsonify({
                'status': 'error',
                'message': 'query, user_id are required'
            }), 400

        platform = data.get('platform', 'google')
        # GPT 처리 및 캘린더 조회 (user_id, platform 전달)
        result = process_calendar_query(data['query'], user_id=data['user_id'], platform=platform)

        # 최종 응답 포맷 별도 구성
        return jsonify({
            'status': 'success',
            'message': result.get("response"),
            'events': result.get("events", []),
            'query_info': result.get("query_info", {})
        })

    except Exception as e:
        print(f"Error in ask_gpt endpoint: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# 디버그 모드에서만 세션 상태를 확인할 수 있는 라우트
@app.route('/debug_session')
def debug_session():
    from flask import session
    return {
        "has_credentials": 'credentials' in session,
        "credentials": session.get('credentials', '없음 😢')
    }

if __name__ == '__main__':
    # Cloud Run은 PORT 환경 변수를 사용
    port = int(os.environ.get('PORT', 8080))
    # 모든 인터페이스에서 수신 대기
    app.run(host='0.0.0.0', port=port, debug=False)
