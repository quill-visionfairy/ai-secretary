import os
import redis
import json
from dotenv import load_dotenv

# .env 불러오기
load_dotenv()

# Redis 클라이언트 생성
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

def check_token_exists(user_id: str, platform: str = "google"):
    key = f"tokens:{platform}:{user_id}"
    token_data = redis_client.get(key)

    if token_data:
        print(f"✅ 토큰이 저장되어 있어요! key: {key}")
        print("내용 요약:")
        print(json.dumps(json.loads(token_data), indent=2, ensure_ascii=False))
    else:
        print(f"❌ 토큰이 없어요... key: {key}")
        print("아직 인증이 안 됐거나 저장이 안 된 것 같아요 ㅠㅠ")

if __name__ == "__main__":
    # 여기 user_id는 로그인 후 이메일 주소로 전달받는 값!
    user_id = input("확인할 user_id (이메일): ")
    check_token_exists(user_id)
