# Python 3.9 베이스 이미지 사용
FROM python:3.9-slim

# 작업 디렉토리 설정
WORKDIR /app


# requirements 먼저 복사
COPY requirements.txt ./

# 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt && pip show Flask && pip freeze > /installed.txt

# 전체 프로젝트 복사
COPY . .

# 포트 8080 노출
EXPOSE 8080

# 환경 변수 설정
ENV PORT=8080

# 애플리케이션 실행
CMD ["python", "app.py"] 