"""
telegram_bot.py — WorkLog Telegram 봇

사용 전 설정:
  1. @BotFather 에서 봇 생성 → 토큰 복사
  2. config.py 의 TELEGRAM_TOKEN, TELEGRAM_CHAT_ID 채우기
  3. CHAT_ID 확인: https://api.telegram.org/bot<TOKEN>/getUpdates

실행:
  python scripts/telegram_bot.py          ← 봇 상시 실행 (polling)
  python scripts/telegram_bot.py send     ← 오늘 브리핑 즉시 전송 (스케줄러에서 호출)

지원 명령어:
  /start    — 환영 메시지
  /todo     — 오늘 TODO + DOING 목록
  /doing    — 현재 DOING 목록만
  /add <내용> [#프로젝트] [@마감일]  — Task 추가
  /done <번호>  — Task 완료 처리
  /brief    — 지금 즉시 브리핑 받기
  /weekly   — 이번 주 통계
"""
import sys
import os
import time
import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database as db
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, STALE_TASK_DAYS

# scheduler 메시지 빌더 재사용
from scheduler import (
    build_daily_brief,
    build_weekly_brief,
    _priority_label,
    _deadline_label,
    WEEKDAY_KO,
)

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


# ── Telegram API 래퍼 ─────────────────────────────────────────────────────────

def _request(method: str, data: dict = None) -> dict:
    url  = f"{BASE_URL}/{method}"
    body = json.dumps(data or {}).encode()
    req  = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"[telegram] HTTP {e.code}: {e.read().decode()}")
        return {}
    except Exception as e:
        print(f"[telegram] 요청 실패: {e}")
        return {}


def send_message(chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
    """텔레그램 메시지 전송. 4096자 초과 시 자동 분할."""
    MAX = 4000
    chunks = [text[i:i+MAX] for i in range(0, len(text), MAX)]
    ok = True
    for chunk in chunks:
        res = _request("sendMessage", {
            "chat_id":    chat_id,
            "text":       chunk,
            "parse_mode": parse_mode,
        })
        if not res.get("ok"):
            ok = False
    return ok


def get_updates(offset: int = 0) -> list:
    res = _request("getUpdates", {"offset": offset, "timeout": 30, "allowed_updates": ["message"]})
    return res.get("result", [])


# ── 명령어 핸들러 ─────────────────────────────────────────────────────────────

def cmd_start(chat_id: str, _args: str):
    send_message(chat_id, (
        "👋 <b>WorkLog 봇</b>이에요!\n\n"
        "업무 기록과 Task를 텔레그램에서 바로 관리할 수 있어요.\n\n"
        "<b>명령어</b>\n"
        "/todo — 오늘 할 일 목록\n"
        "/doing — 진행 중인 Task\n"
        "/add 할 일 내용 — Task 추가\n"
        "/done 번호 — Task 완료 처리\n"
        "/brief — 지금 브리핑 받기\n"
        "/weekly — 이번 주 통계\n\n"
        "← <i>더 자세한 건 localhost:8080 에서도 확인할 수 있어요</i>"
    ))


def cmd_todo(chat_id: str, _args: str):
    db.init_db()
    tasks = db.get_active_tasks()
    if not tasks:
        send_message(chat_id, "✅ 할 일이 없어요! 오늘도 홀가분하게 시작하세요 😊")
        return

    lines = [f"📌 <b>할 일 목록</b> ({len(tasks)}개)\n"]
    for t in tasks:
        status_icon = "▶" if t["status"] == "DOING" else "○"
        deadline = f"  <i>{t['deadline']}</i>" if t.get("deadline") else ""
        project  = f"  #{t['project']}" if t.get("project") else ""
        lines.append(f"{status_icon} <b>[{t['id']}]</b> {_priority_label(t['priority'])} {t['title']}{deadline}{project}")

    send_message(chat_id, "\n".join(lines))


def cmd_doing(chat_id: str, _args: str):
    db.init_db()
    tasks = db.get_doing_tasks()
    if not tasks:
        send_message(chat_id, "지금 진행 중인 Task가 없어요.\n/todo 로 전체 목록을 확인하고 오늘 할 것들을 DOING으로 옮겨보세요!")
        return

    lines = [f"▶ <b>진행 중</b> ({len(tasks)}개)\n"]
    for t in tasks:
        deadline = f"  <i>마감 {t['deadline']}</i>" if t.get("deadline") else ""
        lines.append(f"• <b>[{t['id']}]</b> {_priority_label(t['priority'])} {t['title']}{deadline}")

    if len(tasks) > 5:
        lines.append(f"\n💬 DOING이 {len(tasks)}개나 되네요. 오늘 집중할 것들만 추려보는 건 어떨까요?")

    send_message(chat_id, "\n".join(lines))


def cmd_add(chat_id: str, args: str):
    """
    /add 보고서 작성
    /add 보고서 작성 #프로젝트A @2026-04-30
    """
    db.init_db()
    if not args.strip():
        send_message(chat_id, "할 일 내용을 같이 입력해주세요!\n예) /add 보고서 작성 #프로젝트A @2026-04-30")
        return

    parts   = args.strip().split()
    project = ""
    deadline = None
    title_parts = []

    for part in parts:
        if part.startswith("#"):
            project = part[1:]
        elif part.startswith("@"):
            deadline = part[1:]
        else:
            title_parts.append(part)

    title = " ".join(title_parts).strip()
    if not title:
        send_message(chat_id, "제목이 빠진 것 같아요! 다시 한번 확인해볼게요.")
        return

    db.add_task(title=title, project=project, deadline=deadline)
    msg = f"✅ Task 추가했어요!\n\n📌 <b>{title}</b>"
    if project:
        msg += f"\n📁 {project}"
    if deadline:
        msg += f"\n📅 {deadline}"
    send_message(chat_id, msg)


def cmd_done(chat_id: str, args: str):
    db.init_db()
    task_id_str = args.strip()
    if not task_id_str.isdigit():
        send_message(chat_id, "Task 번호를 같이 알려주세요!\n예) /done 3\n\n번호는 /todo 에서 확인할 수 있어요.")
        return

    task_id = int(task_id_str)
    conn = db.get_db()
    task = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    conn.close()

    if not task:
        send_message(chat_id, f"번호 {task_id}인 Task를 찾지 못했어요 🤔\n/todo 로 목록을 확인해주세요.")
        return

    db.update_task_status(task_id, "DONE")
    send_message(chat_id, f"🎉 완료 처리했어요!\n\n✅ <b>{task['title']}</b>\n\n수고하셨어요!")


def cmd_brief(chat_id: str, _args: str):
    db.init_db()
    today     = date.today()
    is_monday = today.weekday() == 0

    promoted      = db.auto_promote_deadline_tasks()
    doing         = db.get_doing_tasks()
    stale         = db.get_stale_tasks(days=STALE_TASK_DAYS)
    yesterday_done = db.get_yesterday_done_count()

    if is_monday:
        message = build_weekly_brief(doing, stale)
    else:
        message = build_daily_brief(promoted, doing, yesterday_done, stale)

    send_message(chat_id, f"<pre>{message}</pre>")


def cmd_weekly(chat_id: str, _args: str):
    db.init_db()
    today      = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end   = week_start + timedelta(days=6)
    stats      = db.get_weekly_stats(week_start.isoformat(), week_end.isoformat())

    pct = int(stats["done"] / stats["total"] * 100) if stats["total"] else 0

    lines = [
        f"📊 <b>이번 주 통계</b>  ({week_start.isoformat()} ~ {week_end.isoformat()})",
        "",
        f"등록: {stats['total']}개",
        f"완료: {stats['done']}개",
        f"진행/대기: {stats['active']}개",
        f"완료율: {pct}%",
    ]
    send_message(chat_id, "\n".join(lines))


COMMANDS = {
    "/start":  cmd_start,
    "/todo":   cmd_todo,
    "/doing":  cmd_doing,
    "/add":    cmd_add,
    "/done":   cmd_done,
    "/brief":  cmd_brief,
    "/weekly": cmd_weekly,
}


# ── 봇 실행 루프 ──────────────────────────────────────────────────────────────

def handle_update(update: dict):
    msg = update.get("message", {})
    if not msg:
        return
    chat_id = str(msg.get("chat", {}).get("id", ""))
    text    = msg.get("text", "").strip()
    if not text or not chat_id:
        return

    # CHAT_ID 화이트리스트 (설정돼 있으면 본인만 허용)
    if TELEGRAM_CHAT_ID and chat_id != str(TELEGRAM_CHAT_ID):
        send_message(chat_id, "죄송해요, 이 봇은 개인용이에요 🙏")
        return

    # 명령어 파싱 (/add 할일내용 처럼 인자가 있는 경우)
    parts   = text.split(maxsplit=1)
    cmd     = parts[0].lower()
    args    = parts[1] if len(parts) > 1 else ""

    # @봇이름 suffix 제거 (/start@MyBot → /start)
    cmd = cmd.split("@")[0]

    handler = COMMANDS.get(cmd)
    if handler:
        try:
            handler(chat_id, args)
        except Exception as e:
            print(f"[telegram] 핸들러 오류 ({cmd}): {e}")
            send_message(chat_id, "앗, 처리 중에 문제가 생겼어요 😅 잠시 후 다시 시도해주세요.")
    else:
        send_message(chat_id, (
            f"'{text}' 는 모르는 명령어예요.\n\n"
            "/start 로 명령어 목록을 확인해보세요!"
        ))


def run_polling():
    """봇 상시 실행 — 폴링 방식"""
    if not TELEGRAM_TOKEN:
        print("[telegram] TELEGRAM_TOKEN 이 설정되지 않았어요.")
        print("config.py 에서 TELEGRAM_TOKEN 과 TELEGRAM_CHAT_ID 를 채워주세요.")
        return

    print("[telegram] 봇 시작! (Ctrl+C 로 종료)")
    offset = 0
    while True:
        try:
            updates = get_updates(offset)
            for update in updates:
                handle_update(update)
                offset = update["update_id"] + 1
        except KeyboardInterrupt:
            print("\n[telegram] 봇 종료")
            break
        except Exception as e:
            print(f"[telegram] 폴링 오류: {e}")
            time.sleep(5)


def send_brief_to_telegram():
    """스케줄러에서 호출: 브리핑을 텔레그램으로 전송"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[telegram] 토큰 또는 CHAT_ID 미설정, 전송 스킵")
        return

    db.init_db()
    today      = date.today()
    is_monday  = today.weekday() == 0
    promoted   = db.auto_promote_deadline_tasks()
    doing      = db.get_doing_tasks()
    stale      = db.get_stale_tasks(days=STALE_TASK_DAYS)
    yd         = db.get_yesterday_done_count()

    message = build_weekly_brief(doing, stale) if is_monday else build_daily_brief(promoted, doing, yd, stale)
    ok = send_message(str(TELEGRAM_CHAT_ID), f"<pre>{message}</pre>")
    print(f"[telegram] 브리핑 전송 {'성공' if ok else '실패'}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "poll"
    if cmd == "send":
        send_brief_to_telegram()
    else:
        run_polling()
