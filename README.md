# DWLLCH_BE

## 기술 스택
- Python
- Django
- Django REST Framework (DRF)

## 시작하기

### 1. 클론
```bash
git clone https://github.com/DWLLCH/DWLLCH_BE.git
cd DWLLCH_BE
```

### 2. 가상환경 생성 및 활성화
```
python -m venv myvenv
myvenv\Scripts\activate
```

### 3. 의존성 설치
```
pip install -r requirements.txt
```

### 4. 환경변수 설정
필요한 환경변수는 `.env` 파일에 작성

예시:
```
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
```

### 5. 데이터베이스 마이그레이션
```
python manage.py migrate
```

### 6. 개발 서버 실행
```
python manage.py runserver
```

## 개발 도구
- **Django + DRF** — 백엔드 API 개발
- **SQLite3** — 기본 로컬 개발 DB
- **APITestCase** — API 테스트 코드 작성
  - ```python manage.py test```
  - ```python manage.py test users```
- **CodeRabbit** — PR 생성 시 (draft 제외) GitHub에서 자동으로 코드 리뷰

## 폴더 구조
```text
DWLLCH_BE/
  config/                 # 프로젝트 설정
    settings.py
    urls.py
    asgi.py
    wsgi.py
  users/                  # 사용자 관련 앱
    models.py
    serializers.py
    views.py
    urls.py
    tests/
  manage.py
  requirements.txt
```

앱이 추가되면 `users/`와 같은 레벨로 확장합니다.

## 브랜치 전략
- `main` — 배포 브랜치. 직접 push 금지
- `develop` — 개발 통합 브랜치
- `feat/#이슈번호-기능명` — 기능 개발
- `fix/#이슈번호-버그명` — 버그 수정
- `chore/#이슈번호-작업명` — 설정, 빌드, 문서 등

## 이슈 규칙
- 작업 시작 전 이슈 먼저 생성 (`chore` 포함, 예외 없음)
- 이슈 제목 형식: `[FEAT] 기능명` / `[FIX] 버그명` / `[CHORE] 작업명`
- 이슈 템플릿(`.github/ISSUE_TEMPLATE`) 사용
  - 기능 요청 → `feature.md`
  - 버그 리포트 → `bug.md`
  - 설정/빌드 등 → `chore.md`

## PR 규칙
- PR 제목은 커밋 컨벤션과 동일한 형식
- 이슈 없이 PR 금지 (`closes #이슈번호` 필수)
- PR 템플릿(`.github/pull_request_template.md`) 양식에 맞춰 작성
- `feat` / `fix` / `chore` 브랜치 → develop으로 PR
- `develop` → `main`은 배포 시점에만 머지
- CodeRabbit 리뷰 확인 후, 필요한 피드백 반영 및 모든 리뷰 코멘트 resolve 후 merge

## 커밋 컨벤션
| 태그명 | 설명 |
| --- | --- |
| feat | 새로운 기능 추가 |
| fix | 버그 해결 |
| design | 응답 포맷, 문서 응답 구조 등 사용자 관점 변경 |
| !BREAKING CHANGE | 커다란 API 변경 |
| hotfix | 급하게 치명적인 버그를 고쳐야 하는 경우 |
| style | 코드 포맷 변경, 세미콜론 누락, 코드 수정이 없는 경우 |
| refactor | 프로덕션 코드 리팩토링 |
| comment | 필요한 주석 추가 및 변경 |
| docs | 문서를 수정 |
| test | 테스트 추가 |
| chore | 빌드, 테스트, 설정 업데이트 등 |
| rename | 파일 및 폴더명 수정, 옮기기 |
| remove | 파일 삭제만 진행 |