#!/bin/bash
# WorkLog 실행 스크립트 (macOS / Linux)

cd "$(dirname "$0")"

echo ""
echo "  WorkLog 업무 자동화 앱 시작 중..."
echo "  브라우저에서 http://localhost:8080 으로 접속하세요."
echo "  종료하려면 Ctrl+C"
echo ""

# 가상환경이 있으면 활성화
if [ -d "venv" ]; then
  source venv/bin/activate
fi

python3 app.py
