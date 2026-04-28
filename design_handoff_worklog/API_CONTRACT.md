# API Contract — WorkLog v3

프론트엔드(`templates/react_app.html`)가 호출하는 모든 엔드포인트와 페이로드 스펙. `app.py`의 라우팅과 1:1로 맞춰야 합니다.

## ⚠️ 경로 prefix 주의

GET은 `/api/...` 로 일관되어 있는데, **일부 POST는 `/api/` prefix가 없음**:
- `POST /tasks/add`, `/tasks/<id>/status`, `/tasks/<id>/edit`, `/tasks/<id>/delete`
- `POST /journal/save`

`app.py`가 이미 prefix 없이 라우팅돼 있으므로 현 상태에선 동작합니다. 다만 일관성을 위해 향후 `/api/` 로 통일을 권장 (DEBUG_FINDINGS.md #1).

---

## Tasks

### `GET /api/tasks/all`
모든 Task 반환. 정렬: status(DOING→TODO→DONE) → priority(A→B→C) → deadline(없으면 뒤로).

**Query**: `?status=TODO|DOING|DONE|CANCELLED` (옵션)

**Response** (200):
```json
[
  {
    "id": 1,
    "title": "Q2 기획서 제출",
    "status": "DOING",
    "priority": "A",
    "project": "보고서",
    "deadline": "2026-04-29",
    "note": "",
    "created_at": "2026-04-20 09:30:00",
    "updated_at": "2026-04-25 14:10:00",
    "journal_date": "2026-04-25"
  }
]
```
프론트는 `normalizeTask()`로 snake → camel 변환 (`createdAt`, `updatedAt`, `journalDate`).

### `POST /tasks/add`
Task 생성 — 항상 status=TODO로 INSERT.

**Body**:
```json
{
  "title": "string (required)",
  "priority": "A|B|C",
  "project": "string",
  "deadline": "YYYY-MM-DD | null",
  "note": "string",
  "journal_date": "YYYY-MM-DD"
}
```
**Response**: `{"ok": true}` — ⚠️ id를 반환하지 않음. DOING으로 즉시 승격하려면 직후 `/api/tasks/all`로 재조회해서 매칭해야 함 (race condition 위험).

### `POST /tasks/<id>/status`
**Body**: `{"status": "TODO|DOING|DONE|CANCELLED"}`
**Response**: `{"ok": true}` 또는 400 `{"ok": false, "msg": "invalid status"}`

### `POST /tasks/<id>/edit`
**Body**: 변경할 필드만 (예: `{"title": "...", "deadline": "...", "note": "..."}`)
**Response**: `{"ok": true}`

### `POST /tasks/<id>/delete`
**Body**: `{}`
**Response**: `{"ok": true}`

---

## Journals

### `GET /api/journal/<YYYY-MM-DD>`
특정 날짜 일지 (없으면 빈 일지 생성 후 반환).

**Response**:
```json
{ "date": "2026-04-25", "content": "- 보고서 작성 #보고서\n- 코드 리뷰 #개발" }
```

### `POST /journal/save`
**Body**:
```json
{ "date": "2026-04-25", "content": "..." }
```
**Response**: `{"ok": true}`

프론트: 600ms 디바운스 자동저장 + 수동 저장 버튼 + ⌘S(향후).

### `GET /api/journals/range?start=YYYY-MM-DD&end=YYYY-MM-DD`
범위 내 모든 일지. 검색 모달이 90일치 사전로딩에 사용.

**Response**: `[{date, content}, ...]`

### `GET /api/journals/dates?year=YYYY&month=M`
해당 월에 일지가 있는 날짜 목록. 미니 캘린더 도트용.

**Response**: `["2026-04-21", "2026-04-22", ...]`

---

## Projects

### `GET /api/projects`
**Response**:
```json
[
  { "id": 1, "name": "보고서", "color": "#2563eb" },
  { "id": 2, "name": "개발",   "color": "#7c3aed" }
]
```

### `POST /api/projects/add`
**Body**: `{"name": "string", "color": "#hex (옵션, 기본 #6366f1)"}`
**Response**: `{"ok": true, "project": {...}}` 또는 400 `{"ok": false, "msg": "이름을 입력해주세요"}`

### `POST /api/projects/<id>/delete`
**Body**: `{}`
**Response**: `{"ok": true}`

### `POST /api/projects/<id>/color`
**Body**: `{"color": "#hex"}`
**Response**: `{"ok": true}`

---

## Stats / Heatmap / Brief

### `GET /api/heatmap?days=35`
**Response**: `[{ "date": "YYYY-MM-DD", "count": N }, ...]`

### `GET /api/stats/weekly?start=&end=`
주간 통계 (현재 v3 프론트는 직접 호출 안 함, 백엔드는 이미 구현됨).

### `GET /api/brief`
모닝 브리핑 데이터. scheduler.py 도 함께 사용.
**Response**: `{ date, active: [...], urgent: [...], stale: [...] }`

---

## 호출 패턴 요약

**App 마운트 시 (병렬):**
```
GET /api/tasks/all
GET /api/projects
GET /api/heatmap?days=35
GET /api/journals/range?start=<-90d>&end=<today>
GET /api/journals/dates?year=&month= (전월/당월/익월 3회)
```

**선택 날짜 변경 시:**
```
GET /api/journal/<date> (캐시 미스 시만)
```

**저널 편집 시:**
```
POST /journal/save (600ms 디바운스)
```

**Task CRUD:**
```
낙관적 업데이트 → POST → 실패 시 GET /api/tasks/all 으로 롤백
```
