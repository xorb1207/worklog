# Debug Findings — Code Review 결과

v3 HTML과 `app.py`를 함께 검토하면서 발견한 이슈/개선점입니다. 우선순위 순 정렬.

---

## 🔴 P1 — 즉시 확인 필요

### #1. POST 경로의 `/api/` prefix 누락
**증상**: GET은 모두 `/api/...`인데 POST는 일부가 prefix 없이 호출됨.
- 프론트 호출: `POST /tasks/add`, `/tasks/<id>/status|edit|delete`, `/journal/save`
- `app.py`도 동일하게 prefix 없이 라우팅돼 있어서 **현재는 동작함**

**문제점**:
- 일관성 부족 — 신규 개발자가 헷갈림
- nginx/리버스 프록시에서 `/api/*` 만 백엔드로 라우팅하는 일반적 패턴과 충돌
- `/journal/<date>` 는 GET 라우트(템플릿 반환)와 `/journal/save` POST가 섞여 있어 정리 필요

**제안**:
```python
# app.py 변경
@app.route("/api/tasks/add", methods=["POST"])           # was: /tasks/add
@app.route("/api/tasks/<int:task_id>/status", methods=["POST"])
@app.route("/api/tasks/<int:task_id>/edit",   methods=["POST"])
@app.route("/api/tasks/<int:task_id>/delete", methods=["POST"])
@app.route("/api/journal/save", methods=["POST"])        # was: /journal/save
```
프론트도 동일하게 변경. 기존 라우트는 6개월 정도 alias로 유지 후 deprecate.

### #2. `addTask()` race condition
**위치**: `react_app.html` Dashboard.addTask
**증상**: `POST /tasks/add` 가 id를 반환하지 않아서, DOING으로 즉시 승격해야 할 때 `/api/tasks/all`을 재조회 후 `title === t.title && status === 'TODO'` 로 매칭. **같은 제목 task가 여러 개면 잘못된 것을 잡음.**

**제안**: `add_task()`가 새 row id를 반환하도록 수정.
```python
# database.py
def add_task(...) -> int:
    cur = conn.execute("INSERT INTO tasks ... RETURNING id", ...)
    return cur.fetchone()[0]

# app.py
@app.route("/api/tasks/add", methods=["POST"])
def add_task():
    ...
    new_id = db.add_task(...)
    return jsonify({"ok": True, "id": new_id})
```
프론트는 응답의 `id`를 받아 바로 status 업데이트.

### #3. `@app.before_request setup()` 매 요청 init
**위치**: `app.py` line ~13
**증상**: 모든 요청마다 `db.init_db()` 호출. SQLite가 재진입 가능하긴 하지만 낭비이고, 동시 쓰기 시 락 윈도우가 늘어남.

**제안**: 앱 시작 시 1회만:
```python
# 제거: @app.before_request setup()

if __name__ == "__main__":
    db.init_db()  # 여기서만
    app.run(...)
```

---

## 🟡 P2 — 가까운 시일 내

### #4. `/api/projects/add` 가 중복 검사를 안 함
프론트는 `projects.includes(name)` 으로 클라이언트 검사만 함. 동시 추가 시 중복 가능. DB UNIQUE 제약 또는 백엔드 검사 필요.

### #5. 프로젝트 삭제 시 해당 Task 처리 미정의
`/api/projects/<id>/delete` 가 단순 DELETE면, 그 프로젝트를 참조하는 Task는 어떻게 되나? FK CASCADE? 아니면 `project=NULL`로? 정책 확정 필요.

### #6. 일지 저장 디바운스 + 페이지 종료 시점
600ms 디바운스 중 사용자가 탭을 닫으면 마지막 입력이 유실됨. `beforeunload` 시 동기 flush 또는 `navigator.sendBeacon` 사용 권장.

### #7. `__NO_BACKEND__` 배너 — 폐쇄망 환경에서 정상인데도 뜰 수 있음
첫 fetch가 네트워크 단절(짧은 hiccup)로 실패하면 영구 데모 모드 진입. 재시도 로직 또는 사용자 수동 해제 버튼 필요.

### #8. `data-dark` 속성을 `documentElement` 에 설정
CSS는 `[data-dark="true"]` 셀렉터인데 React가 `setAttribute('data-dark', dark)` 로 boolean을 주면 `data-dark="false"` 가 되어 어트리뷰트가 *존재함*. CSS 매칭은 정확히 `"true"` 일 때만 되니 동작은 OK이지만, 명시적으로 토글이 더 깨끗:
```js
document.documentElement.setAttribute('data-dark', dark ? 'true' : 'false');
```
(현재 코드도 사실상 동일하게 동작함, 단지 가독성 개선)

---

## 🟢 P3 — 개선/리팩토링

### #9. 모듈 레벨 `let` 가변 상태 (`ALL_JOURNALS`, `PROJECTS` 등)
React 트리 밖에서 변경되는 모듈 변수에 의존하는 컴포넌트가 있어 리렌더가 `dataVersion`에 의존. Context 또는 Zustand 같은 작은 store로 정리하면 안전.

### #10. `getISOWeek()` 표준 검증
ISO 8601 주차 계산 로직이 자체 구현. 한국 표기와 어긋나는 경계(연말/연초) 케이스 테스트 필요.

### #11. `INIT_TASKS = []` 인데 `WEEKLY_JOURNALS = []`, `HEATMAP_DATA = (() => ... 35일 0)()` 처럼 시드 패턴이 일관되지 않음
모두 빈 배열로 시작하고 fetch 후 채우는 게 일관성 있음.

### #12. 검색 모달 — 90일치 사전 로딩
모달 열 때 90일 일지 전체 fetch. 폐쇄망 1인용이라 데이터 양 적어 OK이지만, 향후 검색 인덱스 서버사이드 필요할 수 있음.

### #13. Excel Import — 현재 모달은 100% 더미
`ExcelModal`이 step 1→2→3을 클릭으로만 넘김. 실제 파일 파싱/업로드 백엔드(`/api/excel/import`) 미구현. 우선순위에 따라 구현 결정.

---

## ✅ 잘된 점

- API 정규화 헬퍼(`normalizeTask`)로 snake/camel 경계 깔끔
- `__NO_BACKEND__` 가드로 미리보기/배포 분리
- 낙관적 업데이트 + 실패 시 refresh 롤백 일관
- 키보드 단축키 + IME 안전 처리(`isComposing`, `keyCode 229`) 잘 됨
- localStorage 영속 (다크모드, 컬럼 순서/숨김) 챙김
- Toast의 실행 취소 액션 — UX 좋음
