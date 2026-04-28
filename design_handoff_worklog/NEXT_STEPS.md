# Next Steps for Claude Code

이 문서는 클로드 코드(터미널 에이전트)에서 이어서 진행할 작업 체크리스트입니다. **순서대로** 진행하면 폐쇄망 1인 운용까지 도달합니다.

---

## Phase 0 — 환경 확인 (15분)

- [ ] 현재 폴더 구조 점검
  ```
  ls -la
  # app.py / database.py / config.py / templates/ / static/ 존재 여부
  ```
- [ ] `python app.py` 실행 → `http://localhost:8080` 접속 → 기본 동작 확인
- [ ] `worklog.db` (SQLite) 생성 위치/스키마 확인
  ```
  sqlite3 worklog.db ".schema"
  ```
- [ ] `database.py`가 다음 함수를 모두 export 하는지 확인:
  - `init_db()`, `get_db()`
  - `get_or_create_journal(date)`, `update_journal(date, content)`, `get_journals_range(start, end)`, `get_journal_dates(year, month)`
  - `get_active_tasks()`, `get_tasks_by_status(status)`, `get_stale_tasks()`, `get_deadline_soon_tasks(days)`
  - `add_task(...)`, `update_task_status(id, status)`, `update_task(id, **kw)`, `delete_task(id)`
  - `get_all_projects()`, `add_project(name, color)`, `delete_project(id)`, `update_project_color(id, color)`
  - `get_heatmap_data(days)`, `get_weekly_stats(start, end)`

---

## Phase 1 — 디자인 통합 (30분)

- [ ] `templates/react_app.html` 위치에 본 핸드오프의 `templates/react_app.html` 배치
- [ ] 브라우저에서 정적 렌더 확인 (백엔드 없이도 노란 "백엔드 미연결" 배너 + UI는 표시되어야 함)
- [ ] 백엔드 띄운 상태에서 다시 접속 → 배너 사라지고 데이터 채워지는지 확인
- [ ] 콘솔 에러 0개 목표

---

## Phase 2 — API 정합성 (1~2시간)

`API_CONTRACT.md` 와 `app.py` 비교하면서 한 줄씩 점검:

- [ ] `GET /api/tasks/all` 응답에 모든 필드 (`id, title, status, priority, project, deadline, note, created_at, updated_at, journal_date`) 포함 확인
- [ ] `POST /tasks/add` — 빈 title 거절 / 기본값 적용 / `created_at` 자동 채움
- [ ] `POST /tasks/<id>/edit` 가 임의의 부분 업데이트(`{"title": "..."}` 만 보내도 OK) 처리되는지
- [ ] `GET /api/journals/dates?year=&month=` — 빈 일지(content 공백)는 제외하는지
- [ ] `GET /api/heatmap` `count` 가 실제로 무엇을 카운트하는지 정의 (작성한 일지 수? Task 변경 수? bytes?)
- [ ] `__NO_BACKEND__` 배너가 정상 환경에서 뜨지 않는지 (네트워크 hiccup 시 false positive 확인)

### 디버깅 #1 적용
- [ ] POST 경로 `/api/` prefix 통일 (deprecation alias 유지)
- [ ] 프론트 fetch URL 동기화

### 디버깅 #2 적용
- [ ] `db.add_task()` → 새 id 반환
- [ ] `app.py /api/tasks/add` 응답에 `id` 포함
- [ ] 프론트 `addTask()` 의 race-condition fallback 제거

### 디버깅 #3 적용
- [ ] `@app.before_request setup()` 제거, `__main__` 가드에서만 init

---

## Phase 3 — 폐쇄망 패키징 (2~3시간)

### 의존성 미러링
- [ ] `requirements.txt` 잠금
  ```
  pip freeze > requirements.txt
  ```
- [ ] 외부망에서 wheel 다운로드
  ```
  pip download -r requirements.txt -d wheels/ --platform <target> --python-version <ver>
  ```
- [ ] 폐쇄망 설치 가이드 작성 (`pip install --no-index --find-links wheels/ -r requirements.txt`)

### 프론트 정적 자산 미러
- [ ] `static/vendor/` 디렉터리 생성, 다음 파일 복사:
  - `react.development.js` (또는 `react.production.min.js`)
  - `react-dom.development.js`
  - `babel.min.js`
- [ ] `templates/react_app.html` 의 `<script src="https://unpkg.com/...">` 를 `{{ url_for('static', filename='vendor/...') }}` 로 교체
  - SRI integrity 해시도 함께 갱신 또는 제거
- [ ] **Babel standalone 대신 빌드 타임 컴파일 도입 검토** — 프로덕션에선 babel-in-browser 비추 (시작 1~2초 지연). 다만 폐쇄망 1인용이면 그대로 둬도 OK.

### Google Fonts
- [ ] `static/fonts/` 에 Inter / Noto Sans KR / JetBrains Mono woff2 미러
- [ ] `<link href="...fonts.googleapis.com...">` 를 `@font-face` 로 교체 (또는 그대로 두고 fallback에 의존)

---

## Phase 4 — 데이터 안정성 (1시간)

- [ ] **백업 스크립트** — 매일 00:00 `worklog.db` → `backups/YYYY-MM-DD.db` 복사 (cron 또는 Windows 작업 스케줄러)
- [ ] **WAL 모드** — `PRAGMA journal_mode=WAL;` 적용해서 동시 읽기/쓰기 안정화
- [ ] **외래키 제약** — `PRAGMA foreign_keys=ON;` (Python sqlite3는 기본 OFF)
- [ ] **프로젝트 삭제 정책** 확정 (CASCADE vs SET NULL)

---

## Phase 5 — 운영 편의 (선택, 1~2시간)

- [ ] **launcher.bat / launcher.sh** — 더블클릭으로 venv 활성화 + 서버 기동 + 브라우저 자동 오픈
- [ ] **시스템 트레이 앱화** (선택) — `pystray` 로 트레이 아이콘 + 종료 메뉴
- [ ] **모닝 브리핑 알림** — `scheduler.py` 가 이미 있다면 Windows 토스트(plyer) 또는 단순 로그

---

## Phase 6 — 테스트 (선택)

- [ ] `pytest` + `pytest-flask` 로 API 스모크 테스트
  - 모든 GET이 200 반환
  - Task CRUD 라운드트립
  - 일지 저장/로드 라운드트립
- [ ] 한국어 검색(태그 `#보고서`)이 모달에서 정상 동작하는지 수동 테스트

---

## 관찰 결과 메모 — 디자인 의도

다음은 디자이너(Claude)가 의도한 부분이라 변경 시 주의:

- **DOING 5개 한도** — 인지 부하 관리. 한도 초과 시 자동 TODO 강등 + 토스트는 "한계 보호" UX
- **저널 mono 폰트 + 1.9 line-height** — 마크다운 가독성 우선
- **Toast 실행 취소** — 5초 윈도우, 삭제는 항상 복구 가능 (실수 방지)
- **백엔드 미연결 노란 배너** — 사용자가 "왜 안 되지?" 헤매지 않게
- **컬럼 순서/숨김 영속화** — 사용자가 자기 워크플로우에 맞게 커스터마이즈

기능 추가 시 위 톤을 유지해주세요.

---

## 막혔을 때

- `app.py` 라우팅 미스: `flask routes` 명령으로 등록된 라우트 전체 확인
- SQLite 락: `worklog.db-journal` 파일 남아 있나 확인 (비정상 종료 흔적)
- React 화면 흰색: 콘솔 → Babel 트랜스파일 에러 (대부분 JSX 문법 실수) 확인
- 폰트가 fallback으로 떨어짐: 네트워크 탭에서 fonts.googleapis.com 차단 여부 확인
