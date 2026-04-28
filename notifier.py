"""
크로스플랫폼 알림 모듈
- Windows : PowerShell Toast (설치 불필요)
- macOS   : osascript (기본 내장)
- Linux   : notify-send fallback
"""
import subprocess
import sys


def notify_windows(title: str, message: str, duration: int = 8):
    """Windows Toast 알림 — PowerShell 방식"""
    msg = message.replace("'", "`'").replace('"', '`"').replace('\n', '`n')
    ttl = title.replace("'", "`'")
    ps_script = f"""
Add-Type -AssemblyName System.Windows.Forms
$n = New-Object System.Windows.Forms.NotifyIcon
$n.Icon = [System.Drawing.SystemIcons]::Information
$n.Visible = $true
$n.ShowBalloonTip({duration * 1000}, '{ttl}', '{msg}', [System.Windows.Forms.ToolTipIcon]::Info)
Start-Sleep -Seconds {duration}
$n.Dispose()
"""
    try:
        subprocess.Popen(
            ["powershell", "-WindowStyle", "Hidden", "-Command", ps_script],
            creationflags=subprocess.CREATE_NO_WINDOW
        )
    except Exception as e:
        print(f"[notifier] Windows 알림 실패: {e}")


def notify_macos(title: str, message: str, **_):
    """macOS 알림 — osascript (설치 불필요, 기본 내장)"""
    # 첫 줄만 subtitle로, 나머지는 본문으로
    lines = message.strip().split('\n')
    subtitle = lines[0] if lines else ""
    body     = '\n'.join(lines[1:]).strip() if len(lines) > 1 else ""

    # 특수문자 이스케이프
    def esc(s): return s.replace('\\', '\\\\').replace('"', '\\"')

    script = f'display notification "{esc(body or subtitle)}" with title "{esc(title)}"'
    if body:
        script = f'display notification "{esc(body)}" with title "{esc(title)}" subtitle "{esc(subtitle)}"'

    try:
        subprocess.run(["osascript", "-e", script], check=True)
    except Exception as e:
        print(f"[notifier] macOS 알림 실패: {e}")


def notify_linux(title: str, message: str, duration: int = 8):
    """Linux fallback — notify-send"""
    try:
        subprocess.run(["notify-send", "-t", str(duration * 1000), title, message])
    except Exception:
        print(f"\n[알림] {title}\n{message}\n")


def notify(title: str, message: str, duration: int = 8):
    """플랫폼 자동 감지 후 알림 발송"""
    if sys.platform == "win32":
        notify_windows(title, message, duration)
    elif sys.platform == "darwin":
        notify_macos(title, message)
    else:
        notify_linux(title, message, duration)
    # 터미널에도 항상 출력 (로그용)
    print(f"\n[알림] {title}\n{message}\n")


if __name__ == "__main__":
    notify("WorkLog 테스트", "알림이 정상 동작합니다!\n플랫폼: " + sys.platform)
