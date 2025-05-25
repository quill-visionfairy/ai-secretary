from flask import request, jsonify
from . import gpt_bp
from gCalendar.gpt_calendar import process_calendar_query
from auth.constants import API_CONFIG
import logging

logger = logging.getLogger(__name__)

@gpt_bp.route('/ask', methods=['GET', 'POST', 'OPTIONS'])
def ask_gpt():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        # GET 요청 처리
        if request.method == 'GET':
            query = request.args.get('query')
            user_id = request.args.get('user_id')
            platform = request.args.get('platform', 'gpt')
            target = request.args.get('target', 'google')
        # POST 요청 처리
        else:
            data = request.get_json()
            query = data.get('query')
            user_id = data.get('user_id')
            platform = data.get('platform', 'gpt')
            target = data.get('target', 'google')

        if not query or not user_id:
            return jsonify({
                "status": "error",
                "message": "query와 user_id는 필수입니다."
            }), 400

        result = process_calendar_query(query, user_id=user_id, platform=platform)

        # 인증 필요 시
        if result.get("status") == "error" and "인증" in result.get("message", ""):
            return jsonify({
                "status": "unauthenticated",
                "message": "사용자 인증이 필요합니다.",
                "login_url": f"{API_CONFIG['authorize_url']}?platform={platform}&target={target}"
            }), 401

        return jsonify({
            "status": "success",
            "message": result.get("response"),
            "events": result.get("events", []),
            "query_info": result.get("query_info", {})
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@gpt_bp.route('/gizmos', methods=['GET', 'POST', 'OPTIONS'])
def gizmos():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        # gizmo_id 파라미터 확인
        gizmo_id = request.args.get('gizmo_id')
        if not gizmo_id:
            return jsonify({
                "detail": "gizmo_id is required"
            }), 400

        # POST 요청 처리
        if request.method == 'POST':
            data = request.get_json() or {}
            query = data.get('query')
            user_id = data.get('user_id')
            platform = data.get('platform', 'gpt')
            target = data.get('target', 'google')
        # GET 요청 처리
        else:
            query = request.args.get('query')
            user_id = request.args.get('user_id')
            platform = request.args.get('platform', 'gpt')
            target = request.args.get('target', 'google')

        if not query or not user_id:
            return jsonify({
                "detail": "query and user_id are required"
            }), 400

        result = process_calendar_query(query, user_id=user_id, platform=platform)

        # 인증 필요 시
        if result.get("status") == "error" and "인증" in result.get("message", ""):
            return jsonify({
                "id": gizmo_id,
                "status": "unauthenticated",
                "detail": "Authentication required",
                "login_url": f"{API_CONFIG['authorize_url']}?platform={platform}&target={target}"
            }), 401

        # CustomGPT 형식에 맞춰 응답
        return jsonify({
            "id": gizmo_id,
            "status": "success",
            "response": result.get("response"),
            "events": result.get("events", []),
            "query_info": result.get("query_info", {})
        })

    except Exception as e:
        return jsonify({
            "id": gizmo_id,
            "status": "error",
            "detail": str(e)
        }), 500 