# Handoff: WorkLog — 업무 자동화 앱

## Overview

**WorkLog**은 매일의 업무 일지(Markdown 기반)와 Task 관리, 주간/월간 리포트, Gantt 형태의 전체 일정, 모닝 브리핑을 한 화면에서 다루는 1인용 폐쇄망 데스크톱 웹 앱입니다. Flask + SQLite 백엔드 위에 React(SPA, Babel-in-browser) 프론트엔드가 올라가 있는 구조이고, 본 핸드오프는 **프론트엔드 디자인 v3와 백엔드 API 계약**을 클로드 코드(Claude Code)에서 이어 개발할 수 있도록 정리한 패키지입니다.

핵심 가치:
- 매일 일지 한 곳에 쓰고 자동저장 (날짜별 캐시)
- Task는 우선순위(A/B/C) × 상태(TODO/DOING/DONE/CANCELLED) × 프로젝트로 관리, DOING은 5개 한도
- 좌측 미니 캘린더로 날짜 점핑, 일지 있는 날짜는 도트 표시
- 키보드 단축키 중심(⌘K 검색, ⌘N 빠른추가, ⌘J 저널, ⌘←/→ 날짜이동, ⌘D 다크모드, ?도움말)
- 폐쇄망 환경에서 단독 실행 (외부 의존성 최소화)

## About the Design Files

이 번들의 HTML 파일들은 **디자인 레퍼런스(프로토타입)** 입니다. 실제 프로덕션 코드로 그대로 복사하기 위한 것이 아니라 **의도한 화면, 인터랙션, 카피, 상태 전이를 보여주는 명세** 로 받아들여 주세요.

본 프로젝트의 타겟 환경은 이미 정해져 있습니다:
- **백엔드**: Python Flask + SQLite (`app.py`, `database.py`, `config.py` 이미 존재)
- **프론트엔드**: 단일 HTML(React UMD + Babel standalone) — Flask가 `templates/react_app.html` 로 서빙
- **실행**: `python app.py` → `http://localhost:8080`

따라서 클로드 코드의 작업은 **이 디자인 HTML을 그대로 `templates/react_app.html`에 배치**하고, 백엔드와의 **API 계약 정합성**을 맞추고, **폐쇄망 배포 가이드**를 정리하는 방향입니다. 프레임워크를 바꾸거나 빌드 도구를 도입할 필요는 없습니다 (단일 파일 + UMD 스크립트로 폐쇄망에 wheel/CDN 미러만 두면 동작).

## Fidelity

**High-fidelity (hifi)** — v3 HTML은 픽셀 단위로 색·타이포·여백·인터랙션이 모두 확정된 상태입니다. 그대로 사용 가능하며, 클로드 코드는 이 파일을 `templates/react_app.html`에 배치한 뒤 백엔드 정합성·버그·배포 이슈 위주로 작업하면 됩니다.

## Files in this Bundle

```
design_handoff_worklog/
├── README.md                        ← 본 문서
├── CHANGELOG.md                     ← v3 → v4 변경점 (최신, 우선 확인)
├── API_CONTRACT.md                  ← 프론트가 호출하는 모든 엔드포인트 명세
├── DEBUG_FINDINGS.md                ← 코드 리뷰로 발견한 디버깅 포인트
├── NEXT_STEPS.md                    ← 클로드 코드에서 이어서 할 작업 체크리스트
├── templates/
│   └── react_app.html               ← 메인 SPA v4 (Flask가 이 파일을 / 라우트에서 서빙)
└── reference/
    ├── WorkLog App.html             ← v1 (참고)
    ├── WorkLog App v2.html          ← v2 (참고)
    ├── WorkLog App v2 wired.html    ← v2 wired (참고)
    ├── Excel Import.html            ← 엑셀 임포트 모달 단독 디자인
    └── wireframes.html              ← 초기 와이어프레임
```

> **⚠️ v4 사용 시 반드시 `CHANGELOG.md` 먼저 읽으세요.** v3 대비 다음이 바뀌었습니다:
> - WEEKS 하드코딩 제거 (간트 동적 확장 + 오늘 자동 스크롤)
> - 주간 리포트 뷰 제거 (대시보드 흡수)
> - 간트 ↔ Task 자동 연동 + "일지에 기록"/"일정에서 제거" 액션
> - Tweaks 패널 추가 (디자인 토글)
> - 다수 race condition / 정렬 버그 수정

## Screens / Views

상위 라우팅은 React 내부 state(`view`)로 처리하며 5개의 메인 뷰가 있습니다.

### 1. Dashboard (`view='dashboard'`)
- **목적**: 오늘 집중할 Task + 일지 작성 + 주간 통계 한눈에
- **레이아웃**: 좌측 사이드바(176px) + 메인(헤더 + 3컬럼)
- **3컬럼 구성** (드래그 리오더, 숨김 가능, 너비 리사이즈):
  - `📌 오늘 집중`: DOING / TODO / DONE 섹션, 빠른추가, 우선순위 칩, 마감일
  - `📝 오늘 기록`: 마크다운 저널 textarea, 자동저장, 태그 자동완성, 체크박스 토글, 들여쓰기
  - `📊 이번 주`: stat 카드, 진행률 바, 35일 히트맵
- **컬럼 순서/숨김 상태는 localStorage(`worklog.colOrder`, `worklog.hiddenCols`)에 저장**

### 2. Briefing (`view='briefing'`)
- **목적**: 모닝 브리핑 — 오늘 시작 시 봐야 할 핵심
- 마감 임박, DOING, 방치 Task 요약

### 3. Gantt (`view='gantt'`)
- **목적**: 12주 단위 전체 일정 시각화
- 프로젝트 필터 칩, Today 라인, 진행률 오버레이
- Excel Import 진입점 (3-step 모달)

### 4. Weekly (`view='weekly'`)
- **목적**: 주간 리포트 — 한 주 일지 모아보기 + 통계
- 이전/다음 주 네비게이션

### 5. Cleanup (`view='cleanup'`)
- **목적**: 7일 이상 방치된 Task와 CANCELLED 정리
- 일괄 완료/진행/취소/복구/삭제

### 추가 모달
- **SearchModal** (⌘K): 90일 일지 + 전체 Task 통합 검색, 태그 칩, 날짜 점프
- **ProjectManager**: 프로젝트 CRUD + 색상 팔레트 (18색)
- **ExcelModal**: 3-step 엑셀 업로드 (드롭존 → 미리보기 → 완료)
- **ShortcutsModal** (?): 키보드 단축키 도움말

## Interactions & Behavior

### 일지(Journal) Textarea — 핵심 UX
- **자동저장**: 600ms 디바운스 → `POST /journal/save`
- **마크다운 리스트 자동 이어쓰기**: `- `, `* `, `- [ ] `, `- [x] ` 패턴 자동 prefix; 빈 항목 Enter는 종료
- **들여쓰기**: Tab/Shift+Tab (멀티라인 선택 지원)
- **체크박스 토글**: `⌘/Ctrl + Click`
- **태그 자동완성**: `#` 입력 시 빈도순 상위 6개 노출, Enter/Tab 삽입, Esc 닫기
- **IME 안전**: `e.isComposing`, `e.keyCode !== 229` 체크

### Task 추가
- DOING이 5개 이상이면 새 Task는 자동으로 TODO로 들어감(토스트 안내)
- 백엔드 `POST /tasks/add`는 항상 TODO로 INSERT → 즉시 DOING으로 승격해야 하면 별도 status 호출
  - ⚠️ **알려진 race condition**: 같은 제목 task가 여러 개면 잘못된 것을 잡을 수 있음 → DEBUG_FINDINGS.md 참조

### 토스트
- 성공/실패 모두 토스트로; 삭제는 5초간 "↩ 실행 취소" 액션 제공

### 다크모드
- `data-dark="true"` 속성으로 전환, localStorage 저장
- ⌘D 토글

### 백엔드 미연결 감지
- 첫 fetch 실패 시 `__NO_BACKEND__` 플래그 + 상단에 노란 배너 표시
- 콘솔 스팸 방지 (이후 호출은 즉시 throw)

## State Management

React `useState` + `useCallback` + `useEffect` 만 사용 (외부 라이브러리 없음).

**App 레벨 상태:**
- `dark`, `view`, `tasks`, `projFilter`, `projects`, `projectsRaw`, `selectedDate`
- 모달 토글: `showExcel`, `showProjMgr`, `showSearch`, `showShortcuts`
- `dataVersion` — `ALL_JOURNALS`/`HEATMAP_DATA` 갱신 트리거
- `journalDates` — `{ 'YYYY-MM-DD': true }` 미니 캘린더 도트용

**모듈 레벨 가변 상태 (let):**
- `ALL_JOURNALS` (90일치), `TAG_FREQ`, `HEATMAP_DATA`, `WEEKLY_JOURNALS`, `PROJECTS`, `PROJ_COLORS`
- 백엔드 fetch 결과로 교체됨, `bumpDataVersion()`으로 리렌더 트리거

**낙관적 업데이트 패턴:**
- 상태 변경 → setState 즉시 반영 → POST → 실패 시 `refreshTasks()` 롤백

## Design Tokens

### Colors (Light)
```
--bg: #f5f1ec
--surface: #ffffff
--surface-2: #faf8f5
--border: #ebe5dc
--border-2: #dfd9d2
--text: #1e1b18
--text-2: #5c564f
--text-3: #8b857d
--text-4: #a39d96
--accent: #4f46e5
--accent-light: #eef2ff
--accent-text: #4338ca
--red: #dc2626  / --red-light: #fee2e2
--amber: #d97706 / --amber-light: #fef3c7
--green: #16a34a / --green-light: #dcfce7
--blue: #2563eb / --blue-light: #dbeafe
--prio-a: #dc2626 (긴급)
--prio-b: #d97706 (보통)
--prio-c: #78716c (낮음)
```

### Colors (Dark) — `[data-dark="true"]`
```
--bg: #0f0e0d / --surface: #1e1c1a / --surface-2: #2a2724
--border: #373330 / --border-2: #4a4542
--text: #f5f3f0 / --text-2: #d4cfc9 / --text-3: #9e9890 / --text-4: #6b6560
--accent: #4f8ef7 / --accent-light: #1a2f52 / --accent-text: #7eb0fa
```

### Project Color Swatches (18색)
```
#6366f1 #2563eb #0ea5e9 #06b6d4 #10b981 #16a34a
#84cc16 #eab308 #f59e0b #f97316 #ef4444 #dc2626
#ec4899 #d946ef #a855f7 #7c3aed #64748b #475569
```

### Spacing & Layout
- Sidebar width: `176px`
- Border radius: `--radius: 6px`, `--radius-sm: 4px`
- Shadows: 3단계 (`--shadow`, `--shadow-md`, `--shadow-lg`)

### Typography
- Font: `Inter`, `Noto Sans KR` (sans), `JetBrains Mono` (mono — 저널)
- Base size: `14px`, line-height `1.5`
- 저널 textarea: mono, line-height `1.9`
- 헤더 타이틀: `15px / 700`
- 카드 타이틀: `13px / 500`
- 메타: `11px`
- 라벨: `10px / 600 / uppercase / letter-spacing 0.5px`

## Assets

이 디자인은 외부 이미지/아이콘 의존이 없습니다. 모든 아이콘은 이모지(🏠 📋 📅 📊 🧹 📁 🔴 🟡 ⚪ ✓ ✕ ↩ 🔥 ⏱ 등)로 처리됩니다. 폐쇄망 환경에서도 OS 기본 이모지 폰트로 렌더링되므로 별도 자산 패키징 불필요.

**Google Fonts** 의존:
```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+KR:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
```
폐쇄망에선 fallback 폰트(`'Noto Sans KR', sans-serif`)가 이미 잡혀 있으므로 동작은 합니다. 사내 폰트 미러가 있으면 교체 권장.

**React UMD + Babel Standalone** 의존:
```
react@18.3.1 (umd/react.development.js)
react-dom@18.3.1 (umd/react-dom.development.js)
@babel/standalone@7.29.0
```
폐쇄망 배포 시 이 3개 파일을 `static/vendor/`에 미러링하고 `<script src>` 경로 교체 필요. SRI integrity 해시는 v3 HTML에 이미 박혀 있음.

## Open Questions for Claude Code

1. `database.py`, `config.py` 의 현재 구현이 `app.py`의 호출 시그니처와 일치하는지 확인
2. POST 경로의 `/api/` prefix 정합성 (DEBUG_FINDINGS.md #1 참조)
3. 폐쇄망 배포: pip wheel 번들, React/Babel 로컬 미러, Google Fonts 처리
4. 동시성: SQLite 단일 파일에서 동시 쓰기 시 락 동작 확인
5. 백업 전략: `worklog.db` 일일 스냅샷 정책

자세한 내용은 `NEXT_STEPS.md` 참조.
