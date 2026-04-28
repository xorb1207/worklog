"""
tray.py — WorkLog Quick Capture (시스템 트레이 상주 앱)

기능:
  - 시스템 트레이에 상주
  - 단축키 Ctrl+Shift+W (Windows) / Cmd+Shift+W (macOS) → 빠른 입력 팝업
  - 트레이 우클릭 메뉴 → 앱 열기 / 브라우저 / 종료

의존성:
  pip install pystray pillow keyboard   (Windows)
  pip install pystray pillow            (macOS — 단축키는 별도)

실행:
  python scripts/tray.py
  (부팅 시 자동 실행 등록은 setup_scheduler.bat / setup_scheduler_mac.sh 참조)
"""
import sys
import os
import threading
import tkinter as tk
from tkinter import ttk
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database as db
from config import APP_PORT

APP_URL = f"http://localhost:{APP_PORT}"


# ── Quick Capture 팝업 ────────────────────────────────────────────────────────

class QuickCapture:
    """단축키로 호출되는 경량 입력 팝업."""

    def __init__(self):
        self.win = None

    def show(self):
        if self.win and self.win.winfo_exists():
            self.win.lift()
            self.win.focus_force()
            return

        db.init_db()

        win = tk.Toplevel() if tk._default_root else tk.Tk()
        self.win = win
        win.title("WorkLog — 빠른 입력")
        win.geometry("420x200")
        win.resizable(False, False)
        win.attributes("-topmost", True)

        # 화면 중앙 배치
        win.update_idletasks()
        x = (win.winfo_screenwidth()  - 420) // 2
        y = (win.winfo_screenheight() - 200) // 2 - 80
        win.geometry(f"+{x}+{y}")

        # 배경색
        bg = "#1c1917"
        fg = "#f5f5f4"
        accent = "#818cf8"
        win.configure(bg=bg)

        tk.Label(win, text="💬  뭘 기록할까요?", bg=bg, fg=fg,
                 font=("Segoe UI", 11, "bold")).pack(pady=(16, 4), padx=20, anchor="w")

        entry = tk.Entry(win, font=("Segoe UI", 13), bg="#292524", fg=fg,
                         insertbackground=fg, relief="flat", bd=8)
        entry.pack(fill="x", padx=20, pady=4)
        entry.focus_set()

        # 옵션 행 (우선순위 + Task/메모 선택)
        opt_frame = tk.Frame(win, bg=bg)
        opt_frame.pack(fill="x", padx=20, pady=4)

        tk.Label(opt_frame, text="우선순위", bg=bg, fg="#a8a29e",
                 font=("Segoe UI", 9)).pack(side="left")
        priority_var = tk.StringVar(value="B")
        for p, label in [("A", "🔴 A"), ("B", "🟡 B"), ("C", "⚪ C")]:
            tk.Radiobutton(opt_frame, text=label, variable=priority_var, value=p,
                           bg=bg, fg=fg, selectcolor="#292524",
                           activebackground=bg, activeforeground=fg,
                           font=("Segoe UI", 9)).pack(side="left", padx=6)

        type_var = tk.StringVar(value="task")
        tk.Radiobutton(opt_frame, text="Task", variable=type_var, value="task",
                       bg=bg, fg=fg, selectcolor="#292524",
                       activebackground=bg, activeforeground=fg,
                       font=("Segoe UI", 9)).pack(side="right", padx=4)
        tk.Radiobutton(opt_frame, text="메모", variable=type_var, value="memo",
                       bg=bg, fg=fg, selectcolor="#292524",
                       activebackground=bg, activeforeground=fg,
                       font=("Segoe UI", 9)).pack(side="right", padx=4)

        status_var = tk.StringVar(value="")

        def submit(event=None):
            text = entry.get().strip()
            if not text:
                return
            try:
                if type_var.get() == "task":
                    db.add_task(title=text, priority=priority_var.get())
                    status_var.set(f"✅ Task 추가됨: {text[:30]}")
                else:
                    today = __import__("datetime").date.today().isoformat()
                    journal = db.get_or_create_journal(today)
                    existing = journal.get("content", "") or ""
                    new_content = existing + f"\n- {text}" if existing else f"- {text}"
                    db.update_journal(today, new_content)
                    status_var.set(f"📝 일지에 추가됨: {text[:30]}")
                entry.delete(0, "end")
                win.after(1200, win.destroy)
            except Exception as e:
                status_var.set(f"오류: {e}")

        btn_frame = tk.Frame(win, bg=bg)
        btn_frame.pack(fill="x", padx=20, pady=(4, 0))

        tk.Button(btn_frame, text="저장  (Enter)", command=submit,
                  bg=accent, fg="#fff", font=("Segoe UI", 10),
                  relief="flat", bd=0, padx=12, pady=6,
                  cursor="hand2").pack(side="left")
        tk.Button(btn_frame, text="취소  (Esc)", command=win.destroy,
                  bg="#292524", fg=fg, font=("Segoe UI", 10),
                  relief="flat", bd=0, padx=12, pady=6,
                  cursor="hand2").pack(side="left", padx=8)

        tk.Label(win, textvariable=status_var, bg=bg, fg="#a6e3a1",
                 font=("Segoe UI", 9)).pack(pady=(2, 0))

        entry.bind("<Return>", submit)
        win.bind("<Escape>", lambda e: win.destroy())
        win.protocol("WM_DELETE_WINDOW", win.destroy)
        win.mainloop()


# ── 트레이 아이콘 ─────────────────────────────────────────────────────────────

def make_icon():
    """16x16 트레이 아이콘 생성 (PIL)."""
    try:
        from PIL import Image, ImageDraw
        img  = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([4, 4, 60, 60], fill="#4f46e5")
        draw.text((20, 18), "W", fill="white")
        return img
    except ImportError:
        return None


def run_tray():
    """트레이 아이콘 실행. pystray 없으면 단순 tkinter 루프로 fallback."""
    qc = QuickCapture()

    try:
        import pystray
        from pystray import MenuItem, Menu

        icon_image = make_icon()
        if not icon_image:
            raise ImportError("PIL 없음")

        def open_app(_icon, _item):
            webbrowser.open(APP_URL)

        def quick_add(_icon, _item):
            threading.Thread(target=qc.show, daemon=True).start()

        def quit_app(icon, _item):
            icon.stop()

        menu = Menu(
            MenuItem("📋 WorkLog 열기", open_app, default=True),
            MenuItem("➕ 빠른 입력", quick_add),
            Menu.SEPARATOR,
            MenuItem("종료", quit_app),
        )

        icon = pystray.Icon("worklog", icon_image, "WorkLog", menu)

        # 단축키 등록 (keyboard 라이브러리, Windows 전용)
        try:
            import keyboard
            keyboard.add_hotkey("ctrl+shift+w", lambda: threading.Thread(target=qc.show, daemon=True).start())
            print("[tray] 단축키 등록: Ctrl+Shift+W")
        except Exception:
            print("[tray] 단축키 미등록 (keyboard 라이브러리 없음 — 트레이 메뉴로 사용하세요)")

        print(f"[tray] 트레이 상주 시작. {APP_URL}")
        icon.run()

    except ImportError:
        # pystray 없을 때 — tkinter 루프만 실행 (macOS 개발 환경 fallback)
        print("[tray] pystray 없음 — 빠른 입력 창만 표시합니다.")
        qc.show()


if __name__ == "__main__":
    run_tray()
