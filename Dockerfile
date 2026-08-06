# 로컬 개발환경(.venv)이 Python 3.14.4를 사용 중이므로 동일한 메이저 버전을 사용합니다.
FROM python:3.14-slim

WORKDIR /app

# 파이썬 출력 버퍼링 비활성화 및 .pyc 파일 생성 방지
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# 의존성만 먼저 복사해 Docker 레이어 캐시를 최대한 활용합니다.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 나머지 소스 복사 (.env, .venv 등은 .dockerignore로 제외됨)
COPY . .

EXPOSE 5000

# 운영 환경에서는 Flask 내장 서버 대신 gunicorn을 사용합니다.
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "run:app"]
