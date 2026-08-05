# 온보딩 가이드

## 1. 프로젝트 개요

기존 PHP로 운영되던 웹 서비스를 Python **Flask**로 재개발한 프로젝트입니다.
설문/수집 데이터의 현황·통계 조회, 검색 키워드·단어·제외 단어 관리 등 **데이터 수집 관리자용 웹 애플리케이션**을 제공합니다.
기기 토큰 기반 자동 로그인, MySQL 연동, 서버 렌더링(Jinja2) 화면으로 구성되어 있습니다.

## 2. 디렉토리 구조와 각 폴더 역할

```
flask/
├── run.py                 # 앱 실행 진입점 (.env 로드 후 create_app 호출)
├── config.py               # 환경별 설정 클래스 (Config, DevelopmentConfig)
├── requirements.txt         # 의존 패키지 목록
├── .env                    # 민감 정보 (DB 접속정보, 로그인 계정 등, git 미포함)
├── app/
│   ├── __init__.py          # 애플리케이션 팩토리(create_app), 전역 인증 훅, 블루프린트 등록
│   ├── routes/              # URL ↔ 핸들러 매핑 (Blueprint 정의). 화면/요청 처리만 담당
│   ├── logics/               # DB 조회·저장 등 핵심 비즈니스 로직
│   ├── apis/                 # JSON 응답용 API 핸들러 (클라이언트 통신 전용)
│   ├── templates/            # Jinja2 HTML 템플릿 (base.html 상속 구조)
│   └── static/                # CSS 등 정적 파일 (bootstrap.css, style.css)
└── doc/readme.md             # 일자별 작업 로그 (변경 이력·이슈 기록)
```

역할 분리 원칙(`gemini.md` 컨벤션): **routes(URL 매핑) / apis(데이터 통신) / logics(비즈니스 로직)** 를 명확히 나눠서 응집도를 높이고 결합도를 낮춥니다. 새 기능을 추가할 때도 이 3계층 규칙을 따라주세요.

## 3. 핵심 파일 5개와 역할

| 파일 | 역할 |
|---|---|
| `app/__init__.py` | 앱 팩토리(`create_app`). Flask 앱 생성, CORS 설정, **`before_request`로 전역 기기 인증 검증**, 설정 로드, DB 초기화, 모든 블루프린트 등록을 담당하는 프로젝트의 중심 파일 |
| `run.py` | 실행 진입점. `.env` 로드 → `create_app()` 호출 → `0.0.0.0:5000`으로 서버 기동 |
| `config.py` | `Config`/`DevelopmentConfig` 클래스로 `SECRET_KEY`, `SQLALCHEMY_DATABASE_URI` 등 환경 설정 관리 |
| `app/routes/login.py` + `app/logics/login.py` | 로그인 처리와 기기 토큰 발급(`addDevice`). 로그인 성공 시 `device_token` 쿠키를 발급하고 DB에 저장 — 이후 모든 요청은 이 토큰으로 자동 인증됨 |
| `app/routes/home.py` + `app/logics/home.py` | 메인 대시보드(`/`). 최근 7일 수집 건수, 남은 수집 건수 등 홈 화면 데이터를 조회해 렌더링 |

## 4. 주요 코드 흐름

**요청 처리 흐름 (모든 요청 공통)**
1. 클라이언트 요청 → `app/__init__.py`의 `before_request` (`check_device_auth`) 실행
2. `/login`, 정적 파일 요청이 아니면 쿠키의 `device_token`을 `user_devices` 테이블과 대조 (만료시간 확인)
3. 유효하면 통과, 없거나 무효하면 `/login`으로 리다이렉트
4. 통과 후 요청된 블루프린트의 라우트 함수 실행 → 필요 시 `logics/`의 함수 호출 → DB 조회/처리 → `templates/`로 렌더링
5. 응답 시 `after_request`에서 `Referrer-Policy: no-referrer` 헤더 추가

**로그인 흐름**
1. `POST /login` → `.env`에 정의된 계정(`user0~3`, `password`)과 폼 입력값 비교
2. 일치하면 `secrets.token_hex(32)`로 랜덤 토큰 생성, 만료일 180일 지정
3. `logics/login.py`의 `addDevice()`로 `user_devices` 테이블에 저장
4. `HttpOnly`, `SameSite=Lax` 쿠키(`device_token`)를 응답에 설정 → 이후 요청은 위 전역 인증 흐름을 자동 통과

**대시보드(홈) 흐름**
- `GET /` → `logics/home.py`의 `get_remaining_collection_count()`, `get_last7_job_counts()` 호출 → `templates/home/app.html` 렌더링

**기타 도메인 라우트**: `/survey_join`, `/survey_info`, `/survey_words`, `/target_words`, `/exception_list`, `/job_log`(POST), `/nicon_sales` — 모두 동일 패턴(routes → logics → DB → template)을 따릅니다.

## 5. 개발 시작하기

### 5.1 설치

```bash
# 가상환경 생성 및 활성화
python3 -m venv .venv
source .venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 5.2 환경 변수 설정

프로젝트 루트에 `.env` 파일 생성 (git에는 포함되지 않으므로 담당자에게 값 요청):

```
SECRET_KEY=
DATABASE_URL=       # 예: mysql+pymysql://user:pw@host/dbname
user0=
user1=
user2=
user3=
password=            # 위 계정들의 공통 로그인 비밀번호
```

### 5.3 실행

```bash
source .venv/bin/activate
python run.py
# 또는 백그라운드 실행
nohup python run.py &
```

브라우저에서 `http://localhost:5000` 접속 → `/login`에서 `.env`의 계정으로 로그인 → 기기 토큰 쿠키 발급 후 대시보드 진입.

프로덕션 환경에서는 `gunicorn`(requirements.txt에 포함) 사용을 권장합니다.

### 5.4 테스트

- 현재 별도 자동화 테스트 스위트는 없습니다.
- API/화면 동작 확인은 `curl`, Postman 등으로 각 라우트를 직접 호출해 검증합니다 (`gemini.md` 가이드).
- 향후 `pytest` 도입 시 `app/logics/*.py`의 비즈니스 로직 단위 테스트부터 작성하는 것을 권장합니다 (아직 미착수).

---

### 참고: 알아두면 좋은 이슈

- `app/__init__.py`(`check_device_auth`)와 `app/logics/login.py`(`addDevice`)에서 SQL을 f-string으로 조합하는 부분이 있어 SQL 인젝션에 취약합니다. 인지하고 있는 이슈이며, 신규 코드 작성 시에는 반드시 파라미터 바인딩(`:param`)을 사용해주세요.
- `app/routes/user_views.py`에 `user_views_bp` 블루프린트가 정의되어 있지만 `app/__init__.py`에 등록되어 있지 않아 현재는 접근 불가능합니다.
