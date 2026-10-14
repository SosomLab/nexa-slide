# 운영

아래 명령의 `-W <ws>` 는 `--workspace <작업 공간>` 의 줄임이다(실행기를 쓰면 생략).

## 작업 흐름

```bash
python3 studio/build_deck.py   -W <ws> ch00            # content/ch00.json → decks/ch00.json (덱이 있으면 멈춤)
python3 studio/build_deck.py   -W <ws> ch00 --force    # 덮어쓰기(기존 덱은 .history 백업)
python3 studio/build_deck.py   -W <ws> book [--chapters ch00 ch18]   # 통합본
python3 studio/export_pptx.py  -W <ws> ch00            # → out/ch00.pptx
python3 studio/render_mermaid.py -W <ws> ch18 [--all]  # content 의 mermaid → PNG (바뀐 것만)
pwsh -File studio/render_pptx.ps1 -Pptx <ws>/out/ch00.pptx -OutDir <ws>/out/ch00   # PowerPoint 렌더 PNG
python3 studio/compare.py      -W <ws> ch00 [--slides 1,5] [--port 5600]   # 브라우저 vs PowerPoint 픽셀 비교
python3 studio/check_parity.py -W <ws> [ch00 …]        # render.js ↔ common.py 결과 동일 확인(node 필요)
python3 studio/gen_tokens_css.py -W <ws> [--write]     # 템플릿 tokens.json ↔ 템플릿 design/tokens.css 값 일치 확인/갱신
python3 studio/set_fonts.py    -W <ws> [default|modern]   # 글꼴 프리셋
python3 studio/check_layout.py -W <ws> [ch00 …] [--json]  # 레이아웃 검사(ERROR 가 있으면 종료 코드 1)
```

## 레이아웃 검사

편집기 "검사" 탭이 저장할 때마다 자동으로 다시 검사한다(썸네일 ⚠ 배지 = 그 슬라이드 건수, 빨강 = ERROR 포함). 항목을 누르면 그 슬라이드·요소로 가고 해당 영역을 점선으로 표시한다.

| 규칙 | 등급 | 내용 |
|---|---|---|
| `t1.overlap.text-text` | ERROR(작은 쪽 10% 이상)/WARNING | 글자가 있는 두 요소의 실제 글자 영역이 겹침 |
| `t1.overlap.text-crosses-border` | WARNING | 글자 영역이 다른 도형의 경계에 걸침(시퀀스 다이어그램 이름표처럼 의도일 수 있음 — 눈으로 확인) |
| `t2.cutoff.spill` | ERROR(15% 이상)/WARNING | 글자가 자기 상자보다 높음(줄 수 추정) · 줄바꿈 없는 줄이 폭을 넘음 · 코드/실행계획 줄 수가 상자보다 김 |
| `t2.cutoff.container` | WARNING | 글자 영역이 그것을 담은 도형 밖으로 나감 |
| `t3.offslide` | ERROR | 요소가 1280×720 밖으로 나감 |
| `t4.font.min` | ERROR | 글자 크기 < 역할별 최소 pt(pt = px × 0.75). 기본 `default` 9pt · `footnotes` 7pt |
| `t5.mono.align` | WARNING | 실행계획의 `\|` 열 위치가 줄마다 다름(강조 표시를 뺀 원문 기준) |

규칙 id 는 Genspark `check_slide_layout` 형식(t1 겹침·t2 잘림 계층)을 본떴고, 최소 글자·고정폭 정렬·요소로 이동은 nexa-slide 에만 있다.
기준값(역할별 최소 pt)은 **템플릿** `check.minFontPt` 에 있다([templates.md](templates.md)). 작업 공간은 뺄 것만 고른다:

```json
"check": {"ignore": ["t1.overlap.text-crosses-border"], "ignoreSlides": {"ch00": ["s12"]}}
```

줄바꿈은 어절 단위로 글꼴 폭을 재서 흉내 내는 추정이다(Pillow 가 있으면 실제 글꼴). 최종 확인은 `compare.py`(PowerPoint 렌더 대조).

- **build 보호**: `--force` 여도 마지막 빌드 뒤 편집기에서 고친 슬라이드가 있으면 멈추고 번호·종류를 알려 준다.
  고친 내용을 content 에 옮긴 뒤 다시 빌드하거나, 버려도 되면 `--discard-edits`. 비교 기준 = `decks/.history/<id>/last-build.json`.
- 공통 슬라이드(`content/_common.json`)를 바꾸면 각 장을 `--force` 로 다시 빌드한다.

## 여러 작업 공간

엔진은 한 벌, 서비스 구성은 각 작업 공간(`nexa-slide.json` + `nexa.py`)에 둔다. 서버는 작업 공간마다 프로세스 하나다.

### 단독 — 작업 공간마다 포트

```bash
python3 <작업 공간>/nexa.py start      # 그 작업 공간의 설정 포트로 백그라운드 실행(이미 떠 있으면 주소만 알림)
python3 <작업 공간>/nexa.py status     # 작업 공간·덱·서버(포트·pid)·세션 연결·대기/처리 중 요청
python3 <작업 공간>/nexa.py url        # 접속 주소
python3 <작업 공간>/nexa.py stop       # 그 작업 공간 서버만 종료
```

### 허브 중계 — 포트 하나(5599)로 여러 Studio

```bash
python3 studio/service.py start        # 허브(시작 페이지) → http://127.0.0.1:5599/
#   시작 페이지 "최근 작업"·"폴더·저장소 열기"·"새 슬라이드 만들기" → http://127.0.0.1:5599/w/<이름>/  (그 작업 공간의 Studio)
#   최근 작업의 포트 배지 = 그 서버로 바로 가는 주소(새 탭) · 시작/중지 = 그 작업 공간 서버만
python3 studio/service.py stop         # 허브만 끈다 - 작업 공간 서버들은 그대로 돈다(각각 nexa.py stop, 또는 시작 페이지 "중지")
```

- 허브는 `/w/<이름>/…` 를 그 작업 공간 서버로 넘긴다. 서버가 꺼져 있으면 첫 요청 때 띄운다(`--port auto` — 설정 포트가 쓰는 중이면 다음 빈 포트).
- `<이름>` 은 폴더 이름 + 경로 해시 6자(예 `신제품-소개-3fa9c1`). 시작 페이지에서 열거나 만든 작업 공간(최근 작업)만 중계한다.
- 두 방식을 섞어도 된다 — 작업 공간당 서버는 하나이므로 `nexa.py start` 로 띄운 서버가 있으면 허브는 그 서버로 넘기고, 허브가 띄운 서버는 `nexa.py status`·`stop` 으로 다룬다.
  Claude 세션(`watch_requests`)은 서버가 어느 쪽으로 떴든 그 작업 공간의 파일만 보므로 영향이 없다.
- 끄는 방법: 시작 페이지 "중지"(그 작업 공간 서버만) · `nexa.py stop` · 허브 자체는 `service.py stop`. 허브를 끄면 `/w/…` 주소만 끊기고 각 서버의 직접 주소는 그대로다.
- 시작 페이지 메뉴 "기준 폴더 설정"의 **중계** 토글(사용자 설정 `hubProxy`)을 끄면 전처럼 열기·만들기가 작업 공간 서버의 포트로 바로 간다.
  자세한 동작은 [home.md](home.md#한-주소로-중계--허브-포트-하나로-여러-studio), 두 방식 비교는 [server.md](server.md#두-가지-운용-방식).

| 원칙 | 이유 |
|---|---|
| 작업 공간마다 `port` 를 다르게 | 단독으로 함께 띄우기. 겹치면 뒤에 띄운 쪽이 "포트를 쓸 수 없다"로 멈춘다(허브가 띄울 때는 빈 포트로 비켜 간다) |
| 작업 공간당 서버 하나 | 두 번째 시작은 거부(기존 주소 안내). 허브 중계도 떠 있는 서버를 그대로 쓴다. 동시 시작은 `out/.studio/start.lock` 으로 줄을 세운다 |
| 작업 공간당 요청 감시 하나 | 살아 있는 감시가 있으면 새 감시는 `{"event":"refused"}` 한 줄을 내고 끝난다 |
| Claude 세션은 그 작업 공간의 저장소에서 연다 | 세션의 작업 폴더·규칙(CLAUDE.md)·git 이 그 저장소이므로 요청 처리·커밋이 그 저장소에 남는다 |

## 인증 · 계정 (허브)

허브는 로컬이어도 로그인이 필요하다. 자세한 규칙·저장 위치·API 는 [auth.md](auth.md).
처음 띄우기·인증 판으로 올리기·사용자 관리·복구·자동 시작·백업을 순서대로 따라 하려면 [server-admin.md](server-admin.md)(운영자용).

```bash
# 처음 — 허브에 접속하면 최초 관리자 설정 페이지. 이미 밖에 열어 둔 허브를 새 판으로 올릴 때는 재시작 "전에" 터미널에서 관리자를 만든다
python3 studio/auth.py add <아이디> --admin
python3 studio/service.py restart
# 운영
python3 studio/auth.py list                      # 사용자·역할
python3 studio/auth.py reset-password <아이디>    # 비밀번호 초기화(이 PC 에서만 - 원격 불가). 그 사용자의 로그인은 모두 끊긴다
python3 studio/auth.py role <아이디> admin        # 관리자 지정(웹 /account 에서도)
```

- 계정 `users.json`·세션·공유 비밀·접근 로그는 **사용자 설정 폴더**에만 있다(`%APPDATA%\nexa-slide` 등). 저장소에 들어가지 않으므로 clone 한 PC 마다 따로 만든다.
- 관리자를 모두 잃었으면 `users.json` 을 지우고(터널은 먼저 끊거나 `add --admin` 으로 바로 만든다) 다시 접속한다.
- 접근 로그 `hub/logs/access-YYYY-MM-DD.log` — `deny` 줄(`login.fail`·`login.locked`·위조 헤더·Host 변조)을 가끔 본다. 보관 `accessLogDays`(30일).
- 밖에 열 때는 **허브 포트만** 터널에 연결한다. 작업 공간 서버 포트(5600~)에는 로그인이 없다.

## 백업 · 복원

| 대상 | 위치 | 보존 |
|---|---|---|
| 편집기 저장 전 덱 | `decks/.history/<id>/<시각>.json` | 최근 50개 |
| build 덮어쓰기 전 덱 | `decks/.history/<id>/<시각>-build.json` | 50개에 포함 |
| 밖에서 바뀌기 직전 덱 | `decks/.history/<id>/<시각>-ext.json` | 50개에 포함 |
| 마지막 빌드 결과 | `decks/.history/<id>/last-build.json` | 1개 |
| **변경 원장**(누가 언제 어느 장·요소를) | `decks/.history/<id>/changes.jsonl` | 덱당 1,000줄(`ledger.keep`) - [change-ledger.md](change-ledger.md) |
| 원장 잠금 | `out/.studio/ledger-<id>.lock` | 상태 파일(내용 없음) |

복원 = 편집기 기록 탭·변경 탭 "직전으로"(원장에 `restore` 로 남는다), 또는 백업 파일을 `decks/<id>.json` 으로 복사(원장에는 "외부" 로 남는다). 편집기가 2초 안에 다시 불러온다(편집 중이면 충돌 선택).
`.history` 와 `out/` 은 git 에서 제외한다 — 덱 JSON 자체는 작업 공간 저장소에서 git 으로 관리한다.

## 포트·프로세스 점검

```powershell
# Windows — 5600 을 쓰는 프로세스와 명령줄
Get-NetTCPConnection -LocalPort 5600 -State Listen | % { Get-CimInstance Win32_Process -Filter "ProcessId=$($_.OwningProcess)" } | select ProcessId, CommandLine
# 요청 감시 프로세스
Get-CimInstance Win32_Process -Filter "Name like 'python%'" | ? CommandLine -like '*watch_requests*' | select ProcessId, CommandLine
Stop-Process -Id <PID> -Force
```

```bash
# macOS / Linux
lsof -iTCP:5600 -sTCP:LISTEN
pgrep -fl watch_requests
```

- 같은 작업 공간에 감시를 둘 이상 띄우지 않는다 — 같은 요청이 두 세션에 전달된다. 하트비트 파일(`out/.studio/session.json`)은 마지막에 쓴 감시의 것만 남는다.
- Windows Git Bash 의 `kill` 은 래퍼만 끝내고 python 이 남을 수 있다 — `Stop-Process`/`taskkill /F` 를 쓴다.

## 문제 해결

| 증상 | 확인 |
|---|---|
| 편집기 "덱 없음" | 작업 공간이 맞는지(`/api/config` 의 `workspace`), `decks/` 에 덱이 있는지 — 없으면 build_deck |
| 로고가 안 보임 | `nexa-slide.json` `brand.logo` 경로가 `assetRoot` 기준인지 |
| 그림이 깨짐(404) | 덱의 `src` 가 `assetRoot` 기준 상대 경로인지 |
| "포트를 쓸 수 없다" | 다른 작업 공간이 그 포트를 쓰는 중 — `nexa-slide.json` 의 `port` 를 바꾸거나 `--port auto`(허브 중계로 열면 자동) |
| "이미 실행 중" | 그 작업 공간 서버가 떠 있다 — `nexa.py url` 로 주소 확인 |
| `/w/<이름>/` 이 404 "모르는 작업 공간" | 최근 작업에 없는 작업 공간 — 시작 페이지에서 "폴더·저장소 열기"로 한 번 열면 목록에 올라 중계된다. 폴더를 옮겼으면 이름(해시)이 바뀐다 |
| 허브가 401 또는 로그인 페이지만 보여 줌 | 정상 — 허브는 로그인 필수. 비밀번호를 잊었으면 `python3 studio/auth.py reset-password <아이디>`([auth.md](auth.md)) |
| 로그인이 429 "잠겼다" | 5회 실패 → 15분 잠금. 허브 재시작으로도 풀린다(`service.py restart`) |
| 허브가 400 "허용되지 않은 Host" | 루프백·Cloudflare 경유가 아닌 호스트로 들어왔다 — 사용자 설정 `publicHosts` 에 그 호스트를 적는다 |
| 허브 `service.py start` 가 "응답이 없다"로 끝남 | 구 판 `common.py`(`/api/config` 로 확인)와 새 서버가 섞였다 — 엔진을 같은 판으로 맞춘다(새 판은 `/api/auth/state` 로 확인) |
| `/w/<이름>/` 이 502 "연결할 수 없다" | 허브가 그 서버를 띄우지 못했다 — 그 작업 공간에서 `nexa.py start` 로 직접 띄워 오류를 본다(`out/.studio/server.log`) |
| 중계로 연 Studio 에서 그림·글꼴이 404 | 편집기 코드가 옛 판(접두 미지원)일 수 있다 — 브라우저 강제 새로 고침(Ctrl+F5) 후에도 그러면 엔진을 최신으로 |
| 시작 페이지의 포트 배지와 `nexa-slide.json` 의 `port` 가 다름 | 설정 포트가 쓰는 중이어서 허브가 빈 포트로 띄웠다(정상). 배지의 포트가 실제 포트, `server.json` 과 같다 |
| `start` 하면 빈 콘솔 창이 뜨고 닫으면 서버가 꺼짐(Windows venv) | 0.13.3 이하 `service.py` 문제 - 0.13.4 이상으로 올린 뒤 `restart` |
| "세션 연결 없음" | 세션이 감시를 실행 중인지([claude-session.md](claude-session.md)). Monitor 는 최대 30분 — 만료되면 다시 건다 |
| PPT 렌더 실패 | PowerPoint 설치·`pwsh` 경로, 이전 렌더가 진행 중이면 429 |
| PPT 와 화면 글자 위치가 다름 | 글꼴을 바꿨다면 `compare.py` 로 다시 재서 `pptTextShift` 수정 |
| 저장 충돌이 반복 | 같은 덱을 다른 브라우저 탭에서 열었는지 |
