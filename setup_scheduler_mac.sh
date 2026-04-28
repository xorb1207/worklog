#!/bin/bash
# macOS 자동 알림 등록 — launchd (cron 대신 macOS 표준 방식)
# 실행: bash setup_scheduler_mac.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$(which python3)"
PLIST_DIR="$HOME/Library/LaunchAgents"
mkdir -p "$PLIST_DIR"

# ── 모닝 브리핑 (매일 09:00) ─────────────────────────────────────────────────
cat > "$PLIST_DIR/com.worklog.morning.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>             <string>com.worklog.morning</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON</string>
    <string>$SCRIPT_DIR/scripts/scheduler.py</string>
    <string>morning</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>   <integer>9</integer>
    <key>Minute</key> <integer>0</integer>
  </dict>
  <key>StandardOutPath</key> <string>$SCRIPT_DIR/data/morning.log</string>
  <key>StandardErrorPath</key><string>$SCRIPT_DIR/data/morning.log</string>
</dict>
</plist>
EOF
launchctl load "$PLIST_DIR/com.worklog.morning.plist" 2>/dev/null
launchctl unload "$PLIST_DIR/com.worklog.morning.plist" 2>/dev/null
launchctl load "$PLIST_DIR/com.worklog.morning.plist"
echo "✅ 모닝 브리핑 등록 완료 (매일 09:00)"

# ── 퇴근 전 체크 (매일 17:30) ────────────────────────────────────────────────
cat > "$PLIST_DIR/com.worklog.evening.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>             <string>com.worklog.evening</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON</string>
    <string>$SCRIPT_DIR/scripts/scheduler.py</string>
    <string>evening</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>   <integer>17</integer>
    <key>Minute</key> <integer>30</integer>
  </dict>
  <key>StandardOutPath</key> <string>$SCRIPT_DIR/data/evening.log</string>
  <key>StandardErrorPath</key><string>$SCRIPT_DIR/data/evening.log</string>
</dict>
</plist>
EOF
launchctl unload "$PLIST_DIR/com.worklog.evening.plist" 2>/dev/null
launchctl load "$PLIST_DIR/com.worklog.evening.plist"
echo "✅ 퇴근 전 체크 등록 완료 (매일 17:30)"

# ── 방치 Task 알림 (매일 09:05) ───────────────────────────────────────────────
cat > "$PLIST_DIR/com.worklog.stale.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>             <string>com.worklog.stale</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON</string>
    <string>$SCRIPT_DIR/scripts/scheduler.py</string>
    <string>stale</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>   <integer>9</integer>
    <key>Minute</key> <integer>5</integer>
  </dict>
  <key>StandardOutPath</key> <string>$SCRIPT_DIR/data/stale.log</string>
  <key>StandardErrorPath</key><string>$SCRIPT_DIR/data/stale.log</string>
</dict>
</plist>
EOF
launchctl unload "$PLIST_DIR/com.worklog.stale.plist" 2>/dev/null
launchctl load "$PLIST_DIR/com.worklog.stale.plist"
echo "✅ 방치 Task 알림 등록 완료 (매일 09:05)"

echo ""
echo "등록된 작업 확인:"
launchctl list | grep worklog
echo ""
echo "제거하려면: launchctl unload ~/Library/LaunchAgents/com.worklog.*.plist"
