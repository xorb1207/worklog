# Changelog — v3 → v4 (tweakable)

이 문서는 v3 디자인 핸드오프 이후 v4 (`templates/react_app.html`) 에서 발생한 모든 변경점을 정리합니다. 클로드 코드에서 통합 시 참고하세요.

---

## 새 기능

### 1. Tweaks 패널 (디자인 토글)
- 우측 하단 플로팅 패널 — 디자인 시스템을 런타임에 조정
- `data-density` (compact / normal / cozy), `data-voice` (default / soft / terminal) CSS 속성 토글
- localStorage에 영속화. **운영 배포 시에는 패널 자체를 제거하거나 어드민 only로 처리 가능**.
- 코드 진입점: 파일 하단 `TWEAK_DEFAULTS` 블록, `useTweaks()` 훅

### 2. 간트 ↔ 할일(Task) 자동 연동
- `deadline`이 있는 active Task (DONE/CANCELLED 제외)를 간트 아이템으로 자동 변환해 함께 표시
- 시작: `created_at` → 끝: `deadline` → 주 단위로 변환
- 간트 디테일 패널의 액션 버튼 2개:
  - **📝 일지에 기록**: 해당 Task의 `journal_date`(또는 오늘) 일지에 체크박스 라인 자동 추가 후 대시보드로 이동
  - **✕ 일정에서 제거**: Task 파생 항목은 숨김 처리(클라이언트 state), 시드 항목은 items에서 제거

### 3. 일지 외부 추가 브릿지
- 다른 뷰(간트, 추후 브리핑 등)에서 일지에 라인을 추가할 수 있는 커스텀 이벤트 시스템
- 이벤트: `worklog:append-journal`, detail: `{ date: 'YYYY-MM-DD', line: '...' }`
- Dashboard가 listener 등록 → `pendingAppendsRef` 큐 → 백엔드 latest fetch → 머지 → POST → setJournals
- **load와의 race condition 회피 설계** (큐잉 + 항상 backend latest 기준)

---

## 버그 수정

### 1. 오늘(TODAY) 날짜가 stale
- **이전**: 헤더의 "오늘 4/25" 라벨이 하드코딩, 간트의 today 위치가 고정 상수(`TODAY_WEEK = 3.6`)
- **수정**: `useToday()` 훅으로 매분 갱신, 간트의 todayWeekFloat는 실제 날짜에서 계산
- 영향 코드: `useToday`, `GanttView` 내 `todayWeekFloat` 계산, 헤더의 `formatKoreanDate(today)`

### 2. 간트 6/15 이후가 안 보임 (WEEKS 하드코딩)
- **이전**: 모듈 상수 `WEEKS = ['3/30', '4/6', ..., '6/15']` 12주로 고정 → 줌 아웃 / 먼 deadline 시 잘림
- **수정**: GanttView 내부에서 동적 생성. 규칙:
  - 기본 24주 (약 6개월)
  - 가장 먼 task `deadline` 까지 자동 확장
  - 가장 끝 `items[i].endWeek` 까지 자동 확장
  - **오늘 + 최소 8주**는 항상 보장
  - 끝에 +4주 패딩
- **추가**: 마운트 시 오늘 위치로 자동 스크롤 (화면 1/4 지점)
- 영향 코드: 모듈 상수 `WEEKS`, `TODAY_WEEK` 제거. `GanttView` 내 `WEEKS_BASE` + 동적 `WEEKS` + `chartScrollRef` + scroll-to-today useEffect

### 3. 간트 좌우 헤더 키(높이) 안 맞음
- **이전**: `data-density="compact"` 일 때 좌측 names-header 44px, 우측 헤더(월26 + 주30) 56px → **12px 어긋남**
- **수정**:
  - `.gantt-names-header { height: 56px }` (default)
  - `[data-density="compact"] .gantt-names-header { height: 56px }` (compact 오버라이드 제거)
- 영향 CSS: `.gantt-names-header`, `[data-density="compact"] .gantt-names-header`

### 4. "일지에 기록" 버튼이 작동 안 함 (race condition)
- **이전 #1**: 간트 액션 버튼이 onClick 핸들러 없음 (선언만)
- **이전 #2**: 핸들러 추가 후에도 GanttView가 `setSelectedDate`/`setView` props를 못 받아 화면 전환이 안 됨
- **이전 #3**: textarea DOM `value` 직접 수정 + `dispatchEvent('input')` 으로는 React controlled state가 안 바뀜
- **이전 #4**: 이벤트 핸들러가 `setJournals` 직후, Dashboard의 selectedDate-load `useEffect`가 늦게 도착해서 **추가한 줄을 backend 원본으로 덮어쓰는** race
- **수정**:
  - GanttView에 `tasks`, `setSelectedDate`, `setView`, `refreshTasks`, `bumpDataVersion` 모두 props로 전달
  - `pendingAppendsRef = useRef({ 'YYYY-MM-DD': [...lines] })` 큐 도입
  - `flushAppends(date)`: 백엔드 latest GET → 머지 → POST → setJournals + journalDates 갱신
  - 어떤 타이밍에 와도 데이터 손실 없음
- 영향 코드: `Dashboard` 의 `pendingAppendsRef` / `flushAppends` / `worklog:append-journal` listener, App 의 `<GanttView .../>` 호출

### 5. `/task` 슬래시 명령과 간트 추가 라인 포맷 불일치
- **이전**: 슬래시는 `- [ ] title 📌` (프로젝트 정보 없음), 간트는 `- [ ] title 📌 @project`
- **수정**: 둘 다 같은 포맷 사용 — `- [ ] title (~MM/DD) !A 📌 @project` (조건부 표시)
- 영향 코드: `onJournalKeyDown` 의 `replacement` 라인, `GanttView.logToJournal` 의 `line` 라인

---

## 제거된 항목

### 1. 주간 리포트 (`view === 'weekly'`) — Dashboard에 흡수
- **이유**: Dashboard 우측 "📊 이번 주" 컬럼이 동일 기능 제공 (stat 4종 + 완료율 바 + 8주 추이 + 4주 히트맵)
- 제거 대상:
  - 사이드바 nav item "📊 주간 리포트"
  - 헤더 분기 `view === 'weekly'`
  - 라우트 `view === 'weekly' && <WeeklyView ... />`
- **`WeeklyView` 함수 자체는 코드에 남아 있음** (호출되지 않음, dead code) — 통합 시 삭제 권장
- 보강: Dashboard "이번 주" 컬럼 헤더에 주 범위 라벨(`4/27–5/3`) 추가

### 2. 모듈 상수 `WEEKS`, `TODAY_WEEK`
- 동적 생성으로 대체 (위 버그 수정 #2 참조)

---

## 코드 위치 참조

주요 변경점의 파일 내 대략적 위치 (`templates/react_app.html` 기준):

| 변경 | 영역 |
|------|------|
| `useToday()` 훅 | 함수 정의부 (라인 ~735 근처) |
| `WEEKS` 동적 생성 | `GanttView` 내부 (라인 ~2300 근처) |
| `chartScrollRef` + scroll-to-today | `GanttView` 내부 |
| `pendingAppendsRef` + `flushAppends` | `Dashboard` 내부 (라인 ~1040 근처) |
| `worklog:append-journal` listener | `Dashboard` 내부 |
| Tweaks 패널 + `TWEAK_DEFAULTS` | 파일 하단 (`useTweaks` 훅) |
| `logToJournal` / `removeFromGantt` | `GanttView` 내부 |

---

## 백엔드 영향

- **신규 엔드포인트 불필요** — 기존 `/api/journal/<date>` GET, `/journal/save` POST 만으로 외부 추가 흐름 처리됨
- 단, 일지 본문에 `📌 @project` 마커가 자동 삽입되므로 백엔드가 일지 본문을 파싱하는 로직이 있다면 이 형식을 약속해두는 것을 권장

---

## 알려진 TODO (다음 작업자에게)

- `WeeklyView` 함수 dead code 정리
- 간트 자동 스크롤이 매번 마운트마다 발생 — 이미 스크롤 후 사용자가 이동한 위치를 기억하려면 ref 외 별도 sessionStorage 도입 필요
- Tweaks 패널은 디자인 탐색용 — 프로덕션에서는 빌드 시점에 제거하거나 `?tweaks=1` query로 가드 권장
