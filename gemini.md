# Flask 개발 및 테스트 가이드라인 (Gemini.md)

## 1. 프로젝트 개요 및 목적
- **목적:** 기존 PHP로 구현된 웹 애플리케이션을 Python Flask 프레임워크로 재개발.
- **주요 목표:** 성능, 확장성, 유지보수성 개선 및 RESTful API 서버 구축.

## 2. 기술 스택 및 버전
- **Framework:** Flask
- **Database Toolkit:** Flask-SQLAlchemy
- **Database Driver:** PyMySQL
- **Configuration:** python-dotenv
- **실행 환경:** WSL (Ubuntu)

## 3. 코딩 컨벤션 (Coding Convention)
- **프로젝트 구조:** 애플리케이션 팩토리(`create_app`)와 블루프린트(Blueprint) 패턴을 기본으로 사용합니다.
  - `app/routes/`: 블루프린트를 생성하고 URL과 처리 함수를 매핑하는 라우팅 파일을 위치시킵니다. (예: `user_routes.py`)
  - `app/apis/`: 클라이언트와 통신하며 JSON 데이터 응답을 처리하는 함수 파일을 위치시킵니다. (예: `user_api.py`)
  - `app/logics/`: 데이터베이스 처리, 외부 API 호출 등 핵심 비즈니스 로직을 담는 함수 파일을 위치시킵니다. (예: `user_logic.py`)
  - `app/templates/`: HTML 템플릿 파일을 관리합니다.
- **역할 분리:** URL 매핑(`routes`), 데이터 통신(`apis`), 비즈니스 로직(`logics`)의 역할을 명확히 분리하여 응집도를 높이고 결합도를 낮춥니다.
- **네이밍 규칙:**
  - 변수, 함수, 파일명: `snake_case` (예: `get_all_users`, `user_logic.py`)
  - 클래스명: `PascalCase` (예: `DevelopmentConfig`)
- **SQL 작성:** ORM 대신 Raw SQL을 사용할 경우, SQL Injection 방지를 위해 `sqlalchemy.text()`와 파라미터 바인딩(`:param`)을 반드시 사용합니다.

## 4. 환경 분리 및 설정 규칙
- **환경 설정:** 개발, 운영 등 환경별 설정은 `config.py` 파일에서 클래스로 분리하여 관리합니다.
- **민감 정보 관리:** 데이터베이스 접속 정보(`DATABASE_URL`), `SECRET_KEY` 등 민감한 정보는 `.env` 파일에 저장하고, `.gitignore`에 추가하여 버전 관리에서 제외합니다.
- **설정 로딩:** `python-dotenv` 라이브러리를 사용하여 `run.py`의 시작 지점에서 `.env` 파일을 로드합니다.

## 5. 테스트 및 검증 가이드
- **API 엔드포인트 테스트:** Postman, Insomnia 또는 `curl`을 사용하여 각 API 엔드포인트(GET, POST, PUT, DELETE)의 정상 동작과 예외 처리를 검증합니다.
- **단위 테스트:** 향후 `pytest`와 같은 테스트 프레임워크를 도입하여 비즈니스 로직(`*_logic.py`)에 대한 단위 테스트를 작성하는 것을 권장합니다.
- **데이터베이스 연결 테스트:** `/api/v1/db-test`와 같이 데이터베이스 연결 상태를 확인할 수 있는 간단한 헬스 체크(health check) API를 유지/활용합니다.

## 6. 에러 핸들링 및 로깅
- **예외 처리:** `try...except` 블록을 사용하여 데이터베이스 오류나 외부 API 호출 실패 등 예측 가능한 예외를 처리하고, 명확한 에러 메시지를 JSON 형식으로 반환합니다.
- **HTTP 상태 코드:** RESTful 원칙에 따라 상황에 맞는 HTTP 상태 코드를 반환합니다. (예: 성공 `200 OK`, 생성 `201 CREATED`, 클라이언트 오류 `400 Bad Request`, 서버 오류 `500 Internal Server Error`)
- **로깅:** Flask에 내장된 로깅 시스템이나 `logging` 모듈을 활용하여 주요 이벤트나 에러 발생 시 로그를 기록하여 디버깅 및 모니터링에 활용합니다.