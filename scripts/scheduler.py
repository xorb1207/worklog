"""
scheduler.py — WorkLog 자동화 엔진 (고도화 버전)

실행 방법:
  python scheduler.py morning   ← 매일 09:00  (월요일은 주간 브리핑으로 자동 전환)
  python scheduler.py evening   ← 매일 17:30
  python scheduler.py stale     ← 매일 09:05

CLAUDE.md 설계 원칙:
  - 자동 상태 전환은 D-0 TODO → DOING 하나만
  - 나머지는 전부 제안, 사용자가 최종 결정
  - 메시지 톤: 친절한 동료처럼, 단정하지 말고 물어보는 형식
"""
import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database as db
from notifier import notify
from config import STALE_TASK_DAYS

WEEKDAY_KO = ["월", "화", "수", "목", "금", "토", "일"]


# ── 메시지 빌더 ───────────────────────────────────────────────────────────────

def _priority_label(p: str) -> str:
    return {"A": "🔴", "B": "🟡", "C": "⚪"}.get(p, "⚪")


def _deadline_label(deadline: str) -> str:
    if not deadline:
        return ""
    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    if deadline == today:
        return "  ← 오늘 마감!"
    if deadline == tomorrow:
        return "  ← 내일 마감"
    return f"  ← {deadline}"


def build_daily_brief(promoted: list, doing: list, yesterday_done: int, stale: list) -> str:
    today    = date.today()
    weekday  = WEEKDAY_KO[today.weekday()]
    lines    = []

    lines.append(f"📅 {today.isoformat()} ({weekday}) 모닝 브리핑")
    lines.append("─" * 32)

    # 1. 오늘 마감으로 자동 전환된 항목
    if promoted:
        lines.append("")
        lines.append("🔥 오늘 마감이라 DOING으로 옮겨뒀어요")
        for t in promoted:
            lines.append(f"   {_priority_label(t['priority'])} {t['title']}")

    # 2. 오늘 포커스 (DOING 목록)
    lines.append("")
    if doing:
        over = len(doing) > 5
        lines.append(f"📌 오늘 포커스 ({len(doing)}개{'  ⚠️ 좀 많은 것 같아요, 집중할 것만 추려보는 건 어떨까요?' if over else ''})")
        for t in doing[:7]:
            lines.append(f"   {_priority_label(t['priority'])} {t['title']}{_deadline_label(t.get('deadline',''))}")
        if len(doing) > 7:
            lines.append(f"   … 외 {len(doing)-7}개 더")
    else:
        lines.append("📌 오늘 포커스")
        lines.append("   아직 진행 중인 Task가 없어요.")
        lines.append("   오늘 할 일을 DOING으로 옮겨보는 건 어떨까요? 👉 localhost:8080")

    # 3. 어제 통계
    lines.append("")
    if yesterday_done > 0:
        lines.append(f"✅ 어제 완료: {yesterday_done}개  수고하셨어요! 👏")
    else:
        lines.append("✅ 어제 완료: 0개  (기록을 빠뜨렸을 수도 있어요)")

    # 4. 방치 Task 제안 (강제 아님)
    if stale:
        lines.append("")
        lines.append(f"💬 혹시 이 Task들, 아직 진행 중인가요? ({STALE_TASK_DAYS}일 이상 그대로예요)")
        for t in stale[:3]:
            days_stale = (date.today() - date.fromisoformat(t["updated_at"][:10])).days
            lines.append(f"   · {t['title']}  ({days_stale}일째)")
        if len(stale) > 3:
            lines.append(f"   … 외 {len(stale)-3}개 더")
        lines.append("   계속하실 거면 괜찮고, 아니면 완료나 취소로 정리해두시면 깔끔해져요 😊")

    lines.append("")
    lines.append("→ http://localhost:8080")
    return "\n".join(lines)


def build_weekly_brief(doing: list, stale: list) -> str:
    today      = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end   = week_start + timedelta(days=6)
    last_start = week_start - timedelta(days=7)
    last_end   = week_start - timedelta(days=1)

    last_done  = db.get_week_done_count(last_start.isoformat(), last_end.isoformat())
    last_total = db.get_week_total_count(last_start.isoformat(), last_end.isoformat())
    pct        = int(last_done / last_total * 100) if last_total else 0

    lines = []
    lines.append(f"📊 이번 주 브리핑  ({week_start.isoformat()} ~ {week_end.isoformat()})")
    lines.append("─" * 32)

    # 지난 주 회고
    lines.append("")
    if last_total:
        lines.append(f"지난 주 완료율: {pct}%  ({last_done}/{last_total}개)")
        if pct >= 80:
            lines.append("지난 주도 열심히 하셨네요! 이번 주도 파이팅 💪")
        elif pct >= 50:
            lines.append("절반 이상 해내셨어요. 이번 주는 조금 더 해봐요!")
        else:
            lines.append("생각보다 바빴던 한 주였나요? 이번 주는 욕심을 조금 줄여보는 건 어떨까요 😊")
    else:
        lines.append("지난 주 Task 기록이 없어요. 이번 주부터 시작해봐요!")

    # 이번 주 마감 Task
    week_deadline = db.get_deadline_soon_tasks(days=7)
    if week_deadline:
        lines.append("")
        lines.append(f"📅 이번 주 마감 ({len(week_deadline)}개)")
        for t in week_deadline:
            lines.append(f"   {_priority_label(t['priority'])} {t['title']}{_deadline_label(t.get('deadline',''))}")

    # 지금 DOING
    if doing:
        lines.append("")
        lines.append(f"📌 현재 진행 중 ({len(doing)}개)")
        for t in doing[:5]:
            lines.append(f"   {_priority_label(t['priority'])} {t['title']}")

    # 방치 Task 점검 제안
    if stale:
        lines.append("")
        lines.append(f"💬 오래된 Task들, 이번 주에 한번 점검해보는 건 어떨까요?")
        for t in stale[:4]:
            days_stale = (date.today() - date.fromisoformat(t["updated_at"][:10])).days
            lines.append(f"   · {t['title']}  ({days_stale}일째)")

    lines.append("")
    lines.append("좋은 한 주 보내세요! → http://localhost:8080")
    return "\n".join(lines)


def build_evening_message(has_content: bool, doing: list) -> str:
    today   = date.today().isoformat()
    lines   = []

    if not has_content:
        lines.append("퇴근 전 잠깐만요 ✋")
        lines.append("")
        lines.append(f"오늘({today}) 일지가 아직 비어있어요.")
        lines.append("5분만 투자해서 오늘 한 일을 기록해두면")
        lines.append("내일 아침 브리핑이 훨씬 알차게 나와요 😊")
        if doing:
            lines.append("")
            lines.append(f"오늘 진행한 Task ({len(doing)}개)")
            for t in doing[:4]:
                lines.append(f"   · {t['title']}")
            lines.append("완료한 것들은 DONE으로 체크해두시는 거 잊지 마세요!")
    else:
        undone = [t for t in doing if t["status"] in ("TODO", "DOING")]
        if undone:
            lines.append("오늘도 수고하셨어요 🙌")
            lines.append("")
            lines.append(f"아직 못 끝낸 게 {len(undone)}개 있어요.")
            for t in undone[:4]:
                lines.append(f"   · {t['title']}")
            lines.append("")
            lines.append("오늘 안에 마무리할 건지, 내일로 넘길 건지 체크해두시면 좋아요!")
        else:
            lines.append("오늘 할 일 다 끝내셨네요! 고생하셨습니다 🎉")

    lines.append("")
    lines.append("→ http://localhost:8080")
    return "\n".join(lines)


def build_stale_message(stale: list) -> str:
    lines = []
    lines.append(f"💬 오래된 Task들, 한번 점검해보실래요?")
    lines.append("")
    for t in stale:
        days_stale = (date.today() - date.fromisoformat(t["updated_at"][:10])).days
        lines.append(f"   · {t['title']}  ({days_stale}일 동안 그대로예요)")
    lines.append("")
    lines.append("계속 진행 중이면 괜찮아요 😊")
    lines.append("완료됐거나 필요없어진 것들은 정리해두시면 브리핑이 더 깔끔해져요.")
    lines.append("")
    lines.append("→ http://localhost:8080")
    return "\n".join(lines)


# ── 실행 함수 ─────────────────────────────────────────────────────────────────

def morning_brief():
    db.init_db()
    today    = date.today()
    is_monday = today.weekday() == 0

    # D-0 자동 전환 (유일하게 허용된 자동 상태 변경)
    promoted = db.auto_promote_deadline_tasks()

    doing         = db.get_doing_tasks()
    stale         = db.get_stale_tasks(days=STALE_TASK_DAYS)
    yesterday_done = db.get_yesterday_done_count()

    if is_monday:
        title   = "WorkLog — 이번 주 브리핑 📊"
        message = build_weekly_brief(doing, stale)
    else:
        title   = "WorkLog — 모닝 브리핑 📅"
        message = build_daily_brief(promoted, doing, yesterday_done, stale)

    # OS 알림 발송
    notify(title, message, duration=12)

    # 오늘 일지 생성 + 브리핑 내용 상단 삽입
    db.get_or_create_journal(today.isoformat())
    db.prepend_to_journal(today.isoformat(), message)

    # 텔레그램 브리핑 전송 (토큰 설정된 경우에만)
    try:
        from telegram_bot import send_brief_to_telegram
        send_brief_to_telegram()
    except Exception as e:
        print(f"[morning] 텔레그램 전송 스킵: {e}")

    print(f"[morning] 브리핑 완료 ({'주간' if is_monday else '일일'})")
    print(message)


def evening_check():
    db.init_db()
    today   = date.today().isoformat()
    journal = db.get_or_create_journal(today)
    content = (journal.get("content") or "").strip()
    doing   = db.get_doing_tasks()

    # 브리핑 텍스트만 있고 실제 기록이 없는 경우도 "미작성"으로 처리
    # (브리핑은 "📅"로 시작하므로 그것만 있으면 빈 것과 동일)
    real_content = "\n".join(
        line for line in content.splitlines()
        if line.strip() and not line.startswith("📅") and not line.startswith("─")
        and not line.startswith("🔥") and not line.startswith("📌")
        and not line.startswith("✅") and not line.startswith("💬")
        and not line.startswith("→")
    ).strip()

    has_content = bool(real_content)
    message     = build_evening_message(has_content, doing)
    notify("WorkLog — 퇴근 전 체크 ✋", message, duration=12)
    print(f"[evening] 알림 발송 (일지 작성: {'O' if has_content else 'X'})")


def stale_check():
    db.init_db()
    stale = db.get_stale_tasks(days=STALE_TASK_DAYS)
    if not stale:
        print("[stale] 방치된 Task 없음 — 깔끔해요! ✅")
        return
    message = build_stale_message(stale)
    notify("WorkLog — Task 점검 알림 💬", message, duration=10)
    print(f"[stale] {len(stale)}개 방치 Task 알림 발송")
    print(message)


# ── 진입점 ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "morning"
    runners = {
        "morning": morning_brief,
        "evening": evening_check,
        "stale":   stale_check,
    }
    if cmd in runners:
        runners[cmd]()
    else:
        print(f"알 수 없는 명령: {cmd}")
        print("사용법: python scheduler.py [morning|evening|stale]")
