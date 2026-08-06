#!/usr/bin/env bash
# Docker로 프로젝트 전체를 설치/실행하는 스크립트
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v docker &> /dev/null; then
    echo "오류: docker 명령을 찾을 수 없습니다. Docker를 먼저 설치해 주세요." >&2
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "오류: 'docker compose' 플러그인을 찾을 수 없습니다." >&2
    exit 1
fi

if [ ! -f .env ]; then
    echo "오류: .env 파일이 없습니다. SECRET_KEY, DATABASE_URL 등을 담은 .env 파일을 먼저 만들어 주세요." >&2
    exit 1
fi

echo "[1/2] 이미지 빌드 중..."
docker compose build

echo "[2/2] 컨테이너 실행 중..."
docker compose up -d

echo
echo "완료되었습니다. http://localhost:5000 에서 확인하세요."
echo "로그 확인: docker compose logs -f"
echo "중지: docker compose down"
