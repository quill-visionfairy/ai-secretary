from flask import Flask, request, jsonify, redirect, session, url_for
from datetime import datetime
from main import check_calendar, get_calendar_service, create_flow, credentials_to_dict
from gpt_calendar import process_calendar_query
import os
import json
import traceback
from dotenv import load_dotenv

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

@app.route('/auth')
def auth():
    """Google Calendar 인증"""
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

        service = get_calendar_service()
        if service:
            return jsonify({"status": "ok", "message": "Authentication successful"})
        return jsonify({"status": "error", "message": "Authentication failed"}), 401
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": "JSON parsing error", "details": str(e)}), 500
    except Exception as e:
        print(f"Error in auth endpoint: {str(e)}")
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

        if not start_date or not end_date:
            return jsonify({'error': 'start_date and end_date are required'}), 400

        # 서비스 객체가 있는지 확인
        service = get_calendar_service()
        if not service:
            return jsonify({'error': 'Calendar service not authenticated'}), 401

        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        events = check_calendar(start, end)
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

@app.route('/query', methods=['POST'])
def query_calendar():
    try:
        data = request.json
        if not data or 'start_time' not in data or 'end_time' not in data:
            return jsonify({'error': 'start_time and end_time are required'}), 400

        try:
            # ISO 8601 형식의 시간을 datetime 객체로 변환
            start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))
        except ValueError as e:
            return jsonify({
                'error': 'Invalid datetime format. Please use ISO 8601 format (e.g., 2024-05-21T00:00:00Z)'
            }), 400

        result = check_calendar(start_time, end_time)
        return jsonify({
            'status': 'ok',
            'result': {
                'data': result,
                'status': 'success'
            }
        })
    except Exception as e:
        print(f"Error in query endpoint: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/login')
def login():
    """Google OAuth 로그인"""
    flow = create_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['state'] = state
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    """OAuth 콜백 처리"""
    state = session['state']
    flow = create_flow()
    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials
    session['credentials'] = credentials_to_dict(credentials)

    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    """로그아웃"""
    if 'credentials' in session:
        del session['credentials']
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Cloud Run은 PORT 환경 변수를 사용
    port = int(os.environ.get('PORT', 8080))
    # 모든 인터페이스에서 수신 대기
    app.run(host='0.0.0.0', port=port, debug=False)
