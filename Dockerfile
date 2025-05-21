# Python 3.9 베이스 이미지 사용
FROM python:3.9-slim

# 작업 디렉토리 설정
WORKDIR /app

# 필요한 파일들 복사
COPY requirements.txt .
COPY *.py ./

# 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# 포트 8080 노출
EXPOSE 8080

# 환경 변수 설정
ENV PORT=8080

# 애플리케이션 실행
CMD ["python", "app.py"] 