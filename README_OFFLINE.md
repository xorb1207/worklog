# WorkLog — 폐쇄망 배포 가이드 (Windows)

타겟 환경: **Windows Pro / Python 3.12**

---

## 1. 개발 PC에서 (외부망 가능)

### 의존성·정적 자산 미러링은 이미 커밋돼 있음

이 레포의 다음 디렉터리는 git에 **포함**되어 있습니다 (폐쇄망에서 그대로 사용):

- `wheels/` — pip wheel 11개 (~3.2MB), Windows x86_64 / Python 3.12 전용
- `static/vendor/` — React 18.3.1 + Babel 7.29.0 production UMD (~3.2MB)

### wheel 재미러링 (의존성 추가 시에만)

`requirements.txt` 수정 후:

```cmd
rmdir /s /q wheels
mkdir wheels

REM 각 패키지를 --no-deps로 받음 (pystray의 darwin 전용 marker dep 회피)
pip download flask==<ver> blinker==<ver> click==<ver> itsdangerous==<ver> jinja2==<ver> markupsafe==<ver> werkzeug==<ver> ^
  --platform win_amd64 --python-version 3.12 --only-binary=:all: --no-deps -d wheels\

pip download pystray==<ver> six==<ver> ^
  --platform win_amd64 --python-version 3.12 --only-binary=:all: --no-deps -d wheels\

pip download pillow==<ver> ^
  --platform win_amd64 --python-version 3.12 --only-binary=:all: --no-deps -d wheels\

pip download keyboard==<ver> ^
  --platform win_amd64 --python-version 3.12 --only-binary=:all: --no-deps -d wheels\
```

> **주의**: `pip download -r requirements.txt --platform win_amd64` 한 줄로는 안 됩니다. pystray가 darwin 전용 conditional dep(`pyobjc-framework-Quartz`)를 명세하는데 pip resolver가 platform marker를 무시하고 그것까지 받으려 하기 때문. 위처럼 `--no-deps`로 패키지별로 나눠 받고, transitive dep도 명시 다운로드.

### vendor 재미러링 (React/Babel 버전 변경 시에만)

```cmd
curl -o static\vendor\react.production.min.js https://unpkg.com/react@18.3.1/umd/react.production.min.js
curl -o static\vendor\react-dom.production.min.js https://unpkg.com/react-dom@18.3.1/umd/react-dom.production.min.js
curl -o static\vendor\babel.min.js https://unpkg.com/@babel/standalone@7.29.0/babel.min.js
```

### git push

```cmd
git add .
git commit -m "..."
git push
```

---

## 2. 폐쇄망 PC에서

### 2-1. 최초 설치

```cmd
git clone <사내 git URL>
cd work-automation

REM Python 3.12가 PATH에 있어야 함
install_offline.bat
```

`install_offline.bat`이 하는 일:
1. Python 3.12 확인
2. `venv\` 생성
3. `pip install --no-index --find-links wheels\ -r requirements.txt` (오프라인)

### 2-2. 실행

```cmd
run.bat
```

- 브라우저 자동 오픈: `http://localhost:8080`
- 첫 실행 시 `data\worklog.db` 자동 생성

### 2-3. 일일 백업 자동화 (선택)

`backup_db.bat`을 Windows **작업 스케줄러**에 등록:

1. 작업 스케줄러 → 작업 만들기
2. 트리거: 매일 00:00
3. 동작: `<프로젝트경로>\backup_db.bat` 시작
4. "가장 높은 권한으로 실행" 체크 권장

이 스크립트는:
- `data\worklog.db` → `backups\YYYY-MM-DD.db` SQLite 온라인 백업 (앱 실행 중에도 안전)
- 30일 넘은 백업은 자동 삭제

### 2-4. 업데이트

개발 PC에서 push 후 폐쇄망에서:

```cmd
git pull
REM 의존성이 추가됐으면 install_offline.bat 다시 실행
REM 코드만 변경됐으면 run.bat 재시작
```

---

## 3. 트러블슈팅

| 증상 | 원인 / 해결 |
|---|---|
| `pip install` 시 `Could not find a version that satisfies` | `wheels\`에 해당 wheel이 없음. requirements.txt에 새 패키지가 추가됐다면 외부망에서 wheel 다시 받아 push 필요 |
| 화면 흰색, 콘솔에 React 에러 | `static\vendor\*.js` 3개 파일이 다 있는지 확인. F12 → Network 탭에서 200인지 |
| 노란 "백엔드 미연결" 배너 | `python app.py`가 안 돌고 있음. 또는 포트 8080이 막혀 있음. `netstat -ano \| findstr :8080`로 확인 |
| DB 락 오류 | `data\worklog.db-journal` 또는 `*-wal` 파일이 비정상 종료로 남았는지 확인. WAL+timeout=10s 적용돼 있어 단일 사용자에선 거의 발생 안 함 |
| 폰트가 fallback (Noto Sans KR)으로 보임 | 폐쇄망에서 fonts.googleapis.com 차단 → 정상 동작. 사내 폰트 미러가 있으면 `react_app.html`의 `<link href="...googleapis.com...">`을 교체 |

---

## 4. 폴더 구조 요약

```
work-automation/
├── app.py, database.py, config.py, notifier.py     ← 코드
├── requirements.txt                                  ← 잠금된 의존성
├── wheels/*.whl                                      ← 폐쇄망 설치용 (커밋됨, ~3.2MB)
├── static/vendor/{react,react-dom,babel}.*.js       ← 로컬 미러 (커밋됨, ~3.2MB)
├── templates/react_app.html                          ← React SPA
├── data/worklog.db                                   ← 폐쇄망에서 자동 생성 (gitignore)
├── backups/YYYY-MM-DD.db                             ← 일일 백업 (gitignore)
├── install_offline.bat                               ← 1회 설치
├── run.bat                                           ← 매일 실행
└── backup_db.bat                                     ← 작업 스케줄러용 일일 백업
```

---

## 5. 보안·운영 체크리스트

- [ ] `config.py`의 `SECRET_KEY = "change-this-in-production"` → 임의 문자열로 교체
- [ ] `APP_HOST = "127.0.0.1"` 유지 (다른 PC에서 접근 불가하게)
- [ ] 작업 스케줄러에 `backup_db.bat` 등록
- [ ] `backups/` 폴더를 별도 디스크/네트워크 드라이브로 미러링하면 더 안전
- [ ] Windows Defender의 폴더 액세스 제어에서 `data\` 디렉터리에 `python.exe` 쓰기 권한 허용
