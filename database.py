import sqlite3
import os
import calendar
from datetime import date, datetime, timedelta
from config import DB_PATH


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)  # 락 발생 시 10초 대기 (단일 사용자라 충분)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")     # 동시 읽기/쓰기 안정화
    conn.execute("PRAGMA foreign_keys=ON")      # FK 제약 활성화 (Python sqlite3는 기본 OFF)
    conn.execute("PRAGMA synchronous=NORMAL")   # WAL+NORMAL — 데이터 손실 위험 거의 없으면서 쓰기 빠름
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS journals (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            date       TEXT    NOT NULL UNIQUE,   -- YYYY-MM-DD
            content    TEXT    DEFAULT '',
            created_at TEXT    DEFAULT (datetime('now','localtime')),
            updated_at TEXT    DEFAULT (datetime('now','localtime'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            title        TEXT    NOT NULL,
            status       TEXT    DEFAULT 'TODO',  -- TODO | DOING | DONE | CANCELLED
            priority     TEXT    DEFAULT 'B',     -- A | B | C
            project      TEXT    DEFAULT '',
            deadline     TEXT    DEFAULT NULL,    -- YYYY-MM-DD
            note         TEXT    DEFAULT '',
            created_at   TEXT    DEFAULT (datetime('now','localtime')),
            updated_at   TEXT    DEFAULT (datetime('now','localtime')),
            journal_date TEXT    DEFAULT NULL     -- 어느 날짜에 등록됐는지
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL UNIQUE,
            color      TEXT    DEFAULT '#6366f1',
            created_at TEXT    DEFAULT (datetime('now','localtime'))
        )
    """)

    conn.commit()
    conn.close()


# ── Journal ───────────────────────────────────────────────────────────────────

def get_or_create_journal(target_date: str = None):
    """오늘(또는 지정일) 일지 반환. 없으면 생성."""
    if target_date is None:
        target_date = date.today().isoformat()
    conn = get_db()
    row = conn.execute("SELECT * FROM journals WHERE date=?", (target_date,)).fetchone()
    if not row:
        conn.execute("INSERT INTO journals (date, content) VALUES (?,?)", (target_date, ""))
        conn.commit()
        row = conn.execute("SELECT * FROM journals WHERE date=?", (target_date,)).fetchone()
    conn.close()
    return dict(row)


def update_journal(target_date: str, content: str):
    """일지 저장 — 없으면 생성, 있으면 업데이트 (UPSERT)"""
    conn = get_db()
    conn.execute("""
        INSERT INTO journals (date, content, updated_at)
        VALUES (?, ?, datetime('now','localtime'))
        ON CONFLICT(date) DO UPDATE
          SET content    = excluded.content,
              updated_at = excluded.updated_at
    """, (target_date, content))
    conn.commit()
    conn.close()


def get_journals_range(start: str, end: str):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM journals WHERE date BETWEEN ? AND ? ORDER BY date DESC",
        (start, end)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Tasks ─────────────────────────────────────────────────────────────────────

def get_active_tasks():
    """TODO + DOING 상태의 모든 Task (우선순위·마감일 순)"""
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM tasks
        WHERE status IN ('TODO','DOING')
        ORDER BY
            CASE priority WHEN 'A' THEN 1 WHEN 'B' THEN 2 ELSE 3 END,
            CASE WHEN deadline IS NULL THEN 1 ELSE 0 END,
            deadline
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_tasks_by_status(status: str):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM tasks WHERE status=? ORDER BY updated_at DESC", (status,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stale_tasks(days: int = 7):
    """N일 이상 DOING 상태로 방치된 Task"""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM tasks WHERE status='DOING' AND updated_at <= ?", (cutoff,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_deadline_soon_tasks(days: int = 2):
    """N일 이내 마감인 미완료 Task"""
    today = date.today().isoformat()
    limit = (date.today() + timedelta(days=days)).isoformat()
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM tasks
        WHERE status IN ('TODO','DOING')
          AND deadline IS NOT NULL
          AND deadline BETWEEN ? AND ?
        ORDER BY deadline
    """, (today, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_task(title, priority="B", project="", deadline=None, note="", journal_date=None) -> int:
    if journal_date is None:
        journal_date = date.today().isoformat()
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO tasks (title,priority,project,deadline,note,journal_date) VALUES (?,?,?,?,?,?)",
        (title, priority, project, deadline, note, journal_date)
    )
    new_id = cur.lastrowid
    conn.commit()
    conn.close()
    return new_id


def update_task_status(task_id: int, status: str):
    conn = get_db()
    conn.execute(
        "UPDATE tasks SET status=?, updated_at=datetime('now','localtime') WHERE id=?",
        (status, task_id)
    )
    conn.commit()
    conn.close()


def update_task(task_id: int, **kwargs):
    allowed = {"title", "status", "priority", "project", "deadline", "note"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    set_clause = ", ".join(f"{k}=?" for k in fields)
    values = list(fields.values()) + [task_id]
    conn = get_db()
    conn.execute(
        f"UPDATE tasks SET {set_clause}, updated_at=datetime('now','localtime') WHERE id=?",
        values
    )
    conn.commit()
    conn.close()


def delete_task(task_id: int):
    conn = get_db()
    conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()


# ── 브리핑 엔진용 함수 ────────────────────────────────────────────────────────

def auto_promote_deadline_tasks() -> list:
    """D-0 (오늘 마감) TODO Task를 자동으로 DOING으로 전환.
    전환된 Task 목록을 반환 (브리핑 메시지에 표시용).
    이 함수는 하루에 한 번 모닝 브리핑 시점에만 호출한다.
    """
    today = date.today().isoformat()
    conn  = get_db()
    rows  = conn.execute(
        "SELECT * FROM tasks WHERE status='TODO' AND deadline=?", (today,)
    ).fetchall()
    promoted = [dict(r) for r in rows]
    if promoted:
        conn.execute(
            "UPDATE tasks SET status='DOING', updated_at=datetime('now','localtime') "
            "WHERE status='TODO' AND deadline=?",
            (today,)
        )
        conn.commit()
    conn.close()
    return promoted


def get_yesterday_done_count() -> int:
    """어제 완료 처리된 Task 수 (브리핑 통계용)."""
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    conn  = get_db()
    count = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE status='DONE' "
        "AND date(updated_at) = ?", (yesterday,)
    ).fetchone()[0]
    conn.close()
    return count


def get_doing_tasks() -> list:
    """DOING 상태 Task만 반환 (우선순위·마감일 순)."""
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM tasks
        WHERE status = 'DOING'
        ORDER BY
            CASE priority WHEN 'A' THEN 1 WHEN 'B' THEN 2 ELSE 3 END,
            CASE WHEN deadline IS NULL THEN 1 ELSE 0 END,
            deadline
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_week_done_count(start: str, end: str) -> int:
    """해당 주 완료 Task 수."""
    conn  = get_db()
    count = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE status='DONE' "
        "AND date(updated_at) BETWEEN ? AND ?", (start, end)
    ).fetchone()[0]
    conn.close()
    return count


def get_week_total_count(start: str, end: str) -> int:
    """해당 주 등록된 전체 Task 수 (완료 포함)."""
    conn  = get_db()
    count = conn.execute(
        "SELECT COUNT(*) FROM tasks "
        "WHERE status != 'CANCELLED' AND journal_date BETWEEN ? AND ?",
        (start, end)
    ).fetchone()[0]
    conn.close()
    return count


def prepend_to_journal(target_date: str, prefix: str):
    """일지 상단에 텍스트를 추가한다. 기존 내용은 그대로 보존."""
    conn    = get_db()
    current = conn.execute(
        "SELECT content FROM journals WHERE date=?", (target_date,)
    ).fetchone()
    if current is None:
        conn.execute(
            "INSERT INTO journals (date, content) VALUES (?,?)",
            (target_date, prefix)
        )
    else:
        existing = current["content"] or ""
        # 이미 오늘 브리핑이 삽입돼 있으면 덮어쓰지 않음
        if existing.startswith(prefix[:30]):
            conn.close()
            return
        new_content = prefix + ("\n\n" if existing else "") + existing
        conn.execute(
            "UPDATE journals SET content=?, updated_at=datetime('now','localtime') WHERE date=?",
            (new_content, target_date)
        )
    conn.commit()
    conn.close()


# ── Weekly stats ──────────────────────────────────────────────────────────────

def get_weekly_stats(start: str, end: str):
    conn = get_db()
    total  = conn.execute("SELECT COUNT(*) FROM tasks WHERE journal_date BETWEEN ? AND ?", (start, end)).fetchone()[0]
    done   = conn.execute("SELECT COUNT(*) FROM tasks WHERE status='DONE' AND journal_date BETWEEN ? AND ?", (start, end)).fetchone()[0]
    active = conn.execute("SELECT COUNT(*) FROM tasks WHERE status IN ('TODO','DOING') AND journal_date BETWEEN ? AND ?", (start, end)).fetchone()[0]
    conn.close()
    return {"total": total, "done": done, "active": active}


# ── 프로젝트 ──────────────────────────────────────────────────────────────────

def get_all_projects() -> list:
    conn = get_db()
    rows = conn.execute("SELECT * FROM projects ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_project(name: str, color: str = "#6366f1") -> dict:
    conn = get_db()
    try:
        conn.execute("INSERT INTO projects (name, color) VALUES (?,?)", (name, color))
        conn.commit()
    except Exception:
        pass  # 중복이면 무시
    row = conn.execute("SELECT * FROM projects WHERE name=?", (name,)).fetchone()
    conn.close()
    return dict(row)


def delete_project(project_id: int):
    """프로젝트 삭제 정책: tasks.project 는 TEXT(이름)이라 FK 없음.
    삭제 후에도 task의 project 이름은 그대로 보존되고 색상 매핑만 잃음.
    동일 이름으로 재추가하면 색상까지 복구됨 (= 무손실)."""
    conn = get_db()
    conn.execute("DELETE FROM projects WHERE id=?", (project_id,))
    conn.commit()
    conn.close()


def update_project_color(project_id: int, color: str):
    conn = get_db()
    conn.execute("UPDATE projects SET color=? WHERE id=?", (color, project_id))
    conn.commit()
    conn.close()


def get_journal_dates(year: int, month: int) -> list:
    """특정 년월에 일지가 있는 날짜 목록 반환 (미니 캘린더 has-log 표시용)"""
    last_day = calendar.monthrange(year, month)[1]
    start = f"{year}-{month:02d}-01"
    end   = f"{year}-{month:02d}-{last_day:02d}"
    conn  = get_db()
    rows  = conn.execute(
        "SELECT date FROM journals "
        "WHERE date BETWEEN ? AND ? AND content IS NOT NULL AND content != ''",
        (start, end)
    ).fetchall()
    conn.close()
    return [r["date"] for r in rows]


# ── 히트맵 ────────────────────────────────────────────────────────────────────

def get_heatmap_data(days: int = 35) -> list:
    """최근 N일의 날짜별 완료(DONE) Task 수 반환. [{date, count}, ...]
    count 의미: 그 날짜에 status가 DONE으로 변경된 task 개수
    (updated_at 기준 — 같은 task를 여러 번 DONE 토글하면 마지막 날에만 잡힘).
    프론트 히트맵 tooltip "완료 N개" 와 정합."""
    end   = date.today()
    start = end - timedelta(days=days - 1)
    conn  = get_db()
    rows  = conn.execute("""
        SELECT date(updated_at) as d, COUNT(*) as cnt
        FROM tasks
        WHERE status = 'DONE'
          AND date(updated_at) BETWEEN ? AND ?
        GROUP BY date(updated_at)
    """, (start.isoformat(), end.isoformat())).fetchall()
    conn.close()

    counts = {r["d"]: r["cnt"] for r in rows}
    result = []
    for i in range(days):
        d = (start + timedelta(days=i)).isoformat()
        result.append({"date": d, "count": counts.get(d, 0)})
    return result
