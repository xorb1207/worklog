from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
from datetime import date, timedelta
import database as db
from config import SECRET_KEY, APP_HOST, APP_PORT
import os, json

app = Flask(__name__)
app.secret_key = SECRET_KEY


# ── 메인 / React SPA ──────────────────────────────────────────────────────────

@app.route("/")
def index():
    # React SPA — Jinja2를 거치지 않고 직접 서빙 ({{ }} 충돌 방지)
    return send_from_directory(
        os.path.join(app.root_path, 'templates'),
        'react_app.html'
    )


@app.route("/classic")
def classic_index():
    today = date.today().isoformat()
    journal = db.get_or_create_journal(today)
    tasks   = db.get_active_tasks()
    stale   = db.get_stale_tasks()
    urgent  = db.get_deadline_soon_tasks(days=2)
    return render_template("journal.html",
        journal=journal,
        tasks=tasks,
        stale=stale,
        urgent=urgent,
        today=today,
        page="journal"
    )


@app.route("/api/journal/save", methods=["POST"])
@app.route("/journal/save", methods=["POST"])  # deprecated alias (TODO: remove ~6 months)
def save_journal():
    data = request.get_json() or {}
    target_date = data.get("date", date.today().isoformat())
    content     = data.get("content", "")
    db.update_journal(target_date, content)
    return jsonify({"ok": True})


@app.route("/journal/<target_date>")
def journal_date(target_date):
    journal = db.get_or_create_journal(target_date)
    tasks   = db.get_active_tasks()
    return render_template("journal.html",
        journal=journal,
        tasks=tasks,
        stale=[],
        urgent=[],
        today=date.today().isoformat(),
        page="journal"
    )


# ── Task 관리 ─────────────────────────────────────────────────────────────────

@app.route("/tasks")
def tasks():
    active    = db.get_active_tasks()
    done_list = db.get_tasks_by_status("DONE")
    stale     = db.get_stale_tasks()
    return render_template("tasks.html",
        active=active,
        done_list=done_list,
        stale=stale,
        today=date.today().isoformat(),
        page="tasks"
    )


@app.route("/api/tasks/add", methods=["POST"])
@app.route("/tasks/add", methods=["POST"])  # deprecated alias
def add_task():
    data  = request.get_json() or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"ok": False, "msg": "title is required"}), 400
    new_id = db.add_task(
        title        = title,
        priority     = data.get("priority", "B"),
        project      = data.get("project", ""),
        deadline     = data.get("deadline") or None,
        note         = data.get("note", ""),
        journal_date = data.get("journal_date", date.today().isoformat()),
        type         = data.get("type", "TASK"),
        waiting_for  = data.get("waiting_for") or None,
        source_text  = data.get("source_text") or None,
        confirmed    = data.get("confirmed", 1),
    )
    return jsonify({"ok": True, "id": new_id})


@app.route("/api/tasks/<int:task_id>/status", methods=["POST"])
@app.route("/tasks/<int:task_id>/status", methods=["POST"])  # deprecated alias
def set_task_status(task_id):
    data   = request.get_json() or {}
    status = data.get("status")
    if status in ("TODO", "DOING", "DONE", "CANCELLED"):
        db.update_task_status(task_id, status)
        return jsonify({"ok": True})
    return jsonify({"ok": False, "msg": "invalid status"}), 400


@app.route("/api/tasks/<int:task_id>/edit", methods=["POST"])
@app.route("/tasks/<int:task_id>/edit", methods=["POST"])  # deprecated alias
def edit_task(task_id):
    data = request.get_json() or {}
    db.update_task(task_id, **data)
    return jsonify({"ok": True})


@app.route("/api/tasks/<int:task_id>/delete", methods=["POST"])
@app.route("/tasks/<int:task_id>/delete", methods=["POST"])  # deprecated alias
def delete_task(task_id):
    db.delete_task(task_id)
    return jsonify({"ok": True})


# ── 주간 뷰 ───────────────────────────────────────────────────────────────────

@app.route("/weekly")
@app.route("/weekly/<week_start>")
def weekly(week_start=None):
    today = date.today()
    if week_start:
        start = date.fromisoformat(week_start)
    else:
        # 이번 주 월요일
        start = today - timedelta(days=today.weekday())
    end   = start + timedelta(days=6)

    journals = db.get_journals_range(start.isoformat(), end.isoformat())
    stats    = db.get_weekly_stats(start.isoformat(), end.isoformat())

    prev_week = (start - timedelta(days=7)).isoformat()
    next_week = (start + timedelta(days=7)).isoformat()

    heatmap = db.get_heatmap_data(days=35)

    return render_template("weekly.html",
        journals=journals,
        stats=stats,
        start=start.isoformat(),
        end=end.isoformat(),
        prev_week=prev_week,
        next_week=next_week,
        today=today.isoformat(),
        heatmap=heatmap,
        page="weekly"
    )


# ── 프로젝트 관리 ─────────────────────────────────────────────────────────────

@app.route("/api/projects")
def get_projects():
    projects = db.get_all_projects()
    return jsonify(projects)

@app.route("/api/projects/add", methods=["POST"])
def add_project():
    data  = request.get_json()
    name  = (data.get("name") or "").strip()
    color = data.get("color", "#6366f1")
    if not name:
        return jsonify({"ok": False, "msg": "이름을 입력해주세요"}), 400
    project = db.add_project(name, color)
    return jsonify({"ok": True, "project": project})


# ── API: 히트맵 데이터 ────────────────────────────────────────────────────────

@app.route("/api/heatmap")
def api_heatmap():
    days = int(request.args.get("days", 30))
    data = db.get_heatmap_data(days=days)
    return jsonify(data)


# ── API: 모닝 브리핑 데이터 (scheduler.py 에서도 사용) ────────────────────────

@app.route("/api/brief")
def api_brief():
    active = db.get_active_tasks()
    urgent = db.get_deadline_soon_tasks(days=2)
    stale  = db.get_stale_tasks()
    return jsonify({
        "date"   : date.today().isoformat(),
        "active" : active,
        "urgent" : urgent,
        "stale"  : stale,
    })


# ── React SPA 전용 API ────────────────────────────────────────────────────────

@app.route("/api/tasks/all")
def api_all_tasks():
    """전체 Task 반환 (status 파라미터로 필터 가능)"""
    status = request.args.get("status")
    conn = db.get_db()
    if status:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE status=? ORDER BY "
            "CASE priority WHEN 'A' THEN 1 WHEN 'B' THEN 2 ELSE 3 END, "
            "CASE WHEN deadline IS NULL THEN 1 ELSE 0 END, deadline, updated_at DESC",
            (status,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM tasks ORDER BY "
            "CASE status WHEN 'DOING' THEN 1 WHEN 'TODO' THEN 2 WHEN 'DONE' THEN 3 ELSE 4 END, "
            "CASE priority WHEN 'A' THEN 1 WHEN 'B' THEN 2 ELSE 3 END, "
            "CASE WHEN deadline IS NULL THEN 1 ELSE 0 END, deadline"
        ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/journal/<target_date>")
def api_journal_date(target_date):
    """특정 날짜 일지 JSON 반환"""
    journal = db.get_or_create_journal(target_date)
    return jsonify(journal)


@app.route("/api/journals/range")
def api_journals_range():
    """날짜 범위 일지 JSON 반환"""
    start = request.args.get("start")
    end   = request.args.get("end")
    if not start or not end:
        return jsonify({"error": "start, end 파라미터 필요"}), 400
    journals = db.get_journals_range(start, end)
    return jsonify(journals)


@app.route("/api/journals/dates")
def api_journal_dates():
    """특정 년월에 일지가 있는 날짜 목록"""
    year  = int(request.args.get("year",  date.today().year))
    month = int(request.args.get("month", date.today().month))
    dates = db.get_journal_dates(year, month)
    return jsonify(dates)


@app.route("/api/stats/weekly")
def api_stats_weekly():
    """주간 통계 JSON 반환"""
    start = request.args.get("start")
    end   = request.args.get("end")
    if not start or not end:
        return jsonify({"error": "start, end 파라미터 필요"}), 400
    stats = db.get_weekly_stats(start, end)
    return jsonify(stats)


@app.route("/api/projects/<int:project_id>/delete", methods=["POST"])
def api_delete_project(project_id):
    db.delete_project(project_id)
    return jsonify({"ok": True})


@app.route("/api/projects/<int:project_id>/color", methods=["POST"])
def api_update_project_color(project_id):
    data  = request.get_json()
    color = data.get("color", "#6366f1")
    db.update_project_color(project_id, color)
    return jsonify({"ok": True})


# ── 실행 ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    db.init_db()
    print(f"\n  업무 자동화 앱 실행 중 → http://{APP_HOST}:{APP_PORT}\n")
    app.run(host=APP_HOST, port=APP_PORT, debug=True)
