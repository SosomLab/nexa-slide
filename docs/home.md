# 시작 페이지와 기본 메뉴

nexa-slide 는 **제작 도구(엔진)와 만든 슬라이드를 물리적으로 나눈다.** 엔진 폴더에는 슬라이드 내용을 저장하지 않는다.
제작마다 작업 공간 폴더를 하나 두고, 그 폴더에 내용(`content/`·`decks/`·`assets/`)과 서버 실행 정보(`nexa-slide.json`·`nexa.py`)를 넣는다.
시작 페이지는 **작업 공간을 정하는 일**을 먼저 하고, 정한 뒤에는 Studio(편집기)로 넘긴다.

## 띄우기

```bash
python3 studio/service.py start        # 작업 공간 밖에서 → 시작 페이지(허브) http://127.0.0.1:5599/
python3 studio/server.py               # 앞에서 실행(Ctrl+C 로 종료)
python3 <작업 공간>/nexa.py start      # 작업 공간 서버 → 덱이 있으면 바로 Studio
```

| 상황 | `/` 를 열면 |
|---|---|
| 작업 공간 없이 띄움(허브) | 시작 페이지 `/studio/home.html` |
| 작업 공간 서버, 덱 있음 | Studio `/studio/` (작성한 문서로 바로) |
| 작업 공간 서버, 덱 없음 | 시작 페이지 |
| 엔진 폴더 안의 작업 공간(예: `example/`) | 열지 않고 허브로 뜬다. 예제는 "데모"로 복사해 연다 |

- 허브 포트는 5599(사용자 설정 `hubPort` 로 바꿀 수 있다). 허브의 실행 정보·로그는 사용자 설정 폴더의 `hub/.studio/` 에 둔다. 엔진이나 현재 폴더에는 아무것도 쓰지 않는다.
- 작업 공간 서버에서도 시작 페이지(`/studio/home.html`)와 기본 메뉴를 그대로 쓸 수 있다.

## 한 주소로 중계 — 허브 포트 하나로 여러 Studio

허브는 `/w/<이름>/…` 를 **그 작업 공간 서버로 넘겨 준다**(중계). 작업 공간마다 서버 프로세스 하나라는 구조는 그대로지만, 브라우저는 포트 하나(5599)만 쓴다.

```
브라우저 ──► 127.0.0.1:5599                (허브)
               ├─ /                      시작 페이지 (허브가 직접)
               ├─ /w/신제품-소개-3fa9c1/…  → 127.0.0.1:5600  (작업 공간 A 서버)
               └─ /w/교육자료-slides-9b2e…/ → 127.0.0.1:5604  (작업 공간 B 서버)
```

- **이름**(`<이름>`) = 작업 공간 폴더 이름 + 경로 해시 6자(`hub.ws_id`). 폴더가 `slides` 면 저장소 이름을 앞에 붙인다. 최근 작업(열기·만들기를 거친 작업 공간)만 중계한다 — 모르는 이름은 404.
- **대상 서버**: 떠 있으면 그 서버로(`nexa.py start` 로 띄운 것도 같다 — 작업 공간당 서버 하나). 꺼져 있으면 첫 요청 때 `--port auto` 로 띄운다 — 설정 포트가 비어 있으면 그 포트, 다른 작업 공간이 쓰고 있으면 다음 빈 포트(실제 포트는 `out/.studio/server.json`). 대상이 응답하지 않으면 다시 찾아 한 번 더 시도한다(꺼졌으면 다시 띄움).
- **편집기**(`studio.js`·`menu.js`·`slide.html`)는 주소의 `/w/<이름>` 접두를 보고 `/api`·`/out`·그림 경로(`RENDER_BASE`) 앞에 붙인다. 작업 공간 서버로 바로 열면 접두가 빈 값이라 전과 같다. 메뉴의 홈·새로 만들기·열기는 접두 없이 허브로, Studio 항목만 접두를 붙인다.
- 중계로 열면 여러 작업 공간이 한 origin 의 `localStorage` 를 같이 쓴다 — 화면 배치 같은 편집기 설정은 공유되고(브라우저 설정으로 봄), 아직 보내지 않은 요청 입력(`nexa-typed-*`)은 작업 공간 이름을 앞에 붙여 섞이지 않게 한다.
- **설정 `hubProxy`**(기본 켬, 시작 페이지 메뉴 "기준 폴더 설정"): 켜면 열기·만들기·데모가 중계 주소(`/w/<이름>/`)로 가고 최근 작업의 포트 배지가 그 서버로 바로 가는 링크(새 탭)가 된다. 끄면 전처럼 작업 공간 서버의 포트로 바로 이동한다. `nexa.py start` 로 직접 띄우는 방식은 둘 다 그대로다.
- 응답에 `url`(이동할 곳) 과 `direct`(그 작업 공간 서버 주소), `id`, `hubUrl` 이 함께 온다. `/api/home` 의 최근 작업에도 `id`·`hubUrl` 이 있고, `proxy` 로 설정값을 알 수 있다.

## 기준 폴더

특별히 정하지 않으면 **운영체제의 기본 문서 폴더** 아래 `NexaSlide/` 가 기준 폴더이고, 제작마다 그 아래에 폴더를 하나씩 만든다.

| 운영체제 | 문서 폴더 |
|---|---|
| Windows | 알려진 폴더 Documents(`SHGetKnownFolderPath`). OneDrive·다른 드라이브로 옮겼으면 그 위치 |
| macOS | `~/Documents` |
| Linux | `xdg-user-dir DOCUMENTS`(한국어 환경이면 `~/문서`일 수 있다). 없으면 `~/Documents` |

우선순위: 환경변수 `NEXA_SLIDE_PROJECTS` > 사용자 설정 `projectsRoot`(시작 페이지 메뉴 "기준 폴더 설정") > 문서 폴더/`NexaSlide`.
현재 값 확인: `python3 studio/paths.py`

**만드는 폴더는 저장소 관리 기준 폴더(루트)**다: 사용자가 기초 자료를 모아 정리하고 필요하면 관련 소스도 개발하는 곳(구조 자유).
슬라이드(최종 산출물)는 그 아래 **`slides/` 작업 공간**에 만든다 — nexa-slide 가 만드는 폴더는 이것 하나뿐이고, 루트에는 md 파일만 둔다
(`SLIDES.md` 개념·구조·서버 실행, 없을 때만 `CLAUDE.md`·`AGENTS.md`). 이미 있는 파일은 건드리지 않는다([new-project.md](new-project.md#2-작업-공간-만들기)).

**폴더·저장소를 지정하면** 기준 폴더 대신 그 폴더(또는 하위 폴더)를 루트로 만든다. 하위 폴더는 제목(폴더 이름으로 바꾼 것)으로 자동으로 채우고, git 저장소를 고르면 비운다(그 저장소가 루트).
제목을 바꾸면 따라 바뀌지만, 사용자가 하위 폴더를 직접 고치면 그 뒤로는 건드리지 않는다(비우면 고른 폴더가 루트).

**작업 공간 폴더**(저장 위치 아래, 기본 `slides`)는 저장소 루트 아래 슬라이드를 만들 폴더 이름이다 — 위치 선택과 따로 정한다.
예: `ppt` 로 바꾸면 작업 공간은 `<폴더>/ppt`, 실행은 `python3 <폴더>/ppt/nexa.py start`(명령에는 `--slides-dir ppt` 가 붙는다).
열기는 저장소 루트를 골라도 바로 아래의 작업 공간 폴더를 찾아 연다.
기본 위치로 돌아가면 지정한 폴더·하위 폴더는 비운다.
엔진 폴더 안은 고를 수 없다.

## 사용자 설정

엔진·작업 공간 밖의 사용자 설정 폴더에 `settings.json` 하나로 둔다. 슬라이드 내용은 없다.

| 운영체제 | 위치 |
|---|---|
| Windows | `%APPDATA%\nexa-slide\settings.json` |
| macOS | `~/Library/Application Support/nexa-slide/settings.json` |
| Linux | `$XDG_CONFIG_HOME/nexa-slide/settings.json`(기본 `~/.config`) |

환경변수 `NEXA_SLIDE_USER_DIR` 로 폴더를 바꿀 수 있다(시험용).

| 키 | 내용 |
|---|---|
| `projectsRoot` | 기준 폴더(없으면 문서 폴더/NexaSlide) |
| `hubPort` | 허브 포트(기본 5599) |
| `hubProxy` | 열기·만들기를 중계 주소 `/w/<이름>/` 로(기본 `true`). `false` 면 작업 공간 서버 포트로 바로 이동 |
| `sessionDays` · `publicHosts` · `accessLogDays` · `accessLogStatic` | 로그인 유지 일수(7) · 허용 공개 호스트 · 접근 로그 보관 일수(30) · 정적 승인 줄 기록 — [auth.md](auth.md) |
| `shareMaxDays` · `shareCreate` | 보기 전용 공유 링크의 최대 만료 일수(90) · 만들 수 있는 사람 `any`(기본)/`admin` — [auth.md](auth.md#보기-전용-공유-링크-02225) |
| `sessionAgent` · `sessionModel` · `sessionModels` · `sessionIdleMinutes` · `sessionTurnMinutes` · `sessionMax` · `sessionMaxTurns` · `sessionBudgetUsd` · `engineMaxTurns` · `engineTurnMinutes` · `engineContinue` · `agentPaths` | AI 웹 세션 전역 기본(에이전트 `claude`/`codex` · 모델 · 모델 목록 `{claude: […], codex: […]}` · 유휴 60분 · 턴 20분 · 동시 3 · 턴당 도구 반복 40 · 예산 · 실행 파일 경로). 엔진 세션(서버 요청 개발)은 따로 턴당 도구 반복 `engineMaxTurns` 150 · 턴 `engineTurnMinutes` 60분 · 도구 한도에 걸렸을 때 같은 대화로 이어 하기 `engineContinue` 2번(0.22.34~, 설정 파일·API). **관리자만** — 시작 페이지 메뉴 "기준 폴더 설정" 아래 "AI 세션 전역 기본". 작업 공간 설정 `sessionAgent`·`sessionModel`(`nexa-slide.local.json`/`nexa-slide.json`)과 세션 시작 창의 선택이 이보다 우선 |

계정(`users.json`)·세션·접근 로그도 이 폴더에 있다. 허브는 로컬이어도 로그인이 필요하다 — [auth.md](auth.md).
| `sessionAllowWeb` | **웹 세션에 웹 검색 허용 스위치**(기본 꺼짐, 관리자만). 켜면 세션 시작 창에 "이 세션에 웹 검색 허용" 체크가 생기고(관리자만 체크 가능, claude 만) 그 세션의 권한에서 `WebSearch`·`WebFetch` 가 열린다 - 다른 외부 접근(curl·wget·powershell·mcp)은 여전히 막힌다. 보안 주의는 [server-admin.md](server-admin.md) |
| `sessionAllowGit` · `sessionAllowPush` · `sessionRepoRoot` | **웹 세션 git·저장소 권한 스위치**(기본 꺼짐, 관리자만, claude 만). 켜면 세션 시작 창에 "이 세션에 git 기록 / push / 저장소 루트 접근 허용" 체크가 생긴다(관리자만 체크). git 기록 = `add`·`commit`·`branch`·`switch`/`checkout`·`merge`·`stash`·`tag`(+조회), push = `push`·`pull`·`fetch`(git 기록을 함께 켬), 저장소 루트 = 작업 공간을 품은 저장소 루트 아래 파일 읽기·쓰기(`--add-dir`, `.git/` 직접 수정 금지). 작업 공간 설정에 같은 키를 `false` 로 두면 그 작업 공간에서는 꺼진다(켜는 것은 전역만). 보안 주의는 [server-admin.md](server-admin.md) |
| `recent` | 최근 작업 `[{path, title, opened}]` - 최대 30개 |
| `samples` | 등록한 샘플 사이트 `[{name, url, note}]` |

## 시작 페이지 구성

머리의 **ⓘ 설정 안내**(최근 작업 카드의 ⓘ 도 같은 창, 그 작업 공간이 골라진 채): 엔진·작업 공간 저장소를 받은 뒤 이 PC 에서 할 일을 **실제 경로가 채워진 명령**(엔진 clone·`pip`·`server.py`·`git pull`·`/nexa-slide-server`, 작업 공간 `nexa.py engine <엔진>`·`update_launcher`·`start`·`/nexa-slide-session`·`/nexa-slide-server`)과 복사 단추로 보여 준다 — [install.md — clone 이후](install.md#저장소를-받은-뒤-할-일-clone-이후).

| 탭 | 내용 |
|---|---|
| 시작 | **새 슬라이드 만들기**(① 제목·템플릿·시작용 내용 ② 목적·대상·작성 방향·참고 자료 ③ 저장 위치), **폴더·저장소 열기**, **서버 작업**(nexa-slide 엔진 개발 — 엔진 요청 큐·개발 세션, 아래), **최근 작업**(실행 상태·포트 · 서버 시작/중지 · 세션) |
| 튜토리얼 | 작업 공간 정하기 → 템플릿·방향 → Studio 편집 → Claude 세션 요청 → 발표·내보내기 → 최근 추가된 기능(요청 기록 창·덱 복제·그림 효과·정리·보관·표시 언어·PowerPoint 기능 보강 0.22.11~13) |
| 데모 | 엔진 예제(`example/`)를 기준 폴더의 `nexa-slide-demo/` 로 처음 한 번 복사해 연다 |
| 템플릿 | 맨 앞 **＋ 회사 템플릿 만들기**(마법사, 아래), 엔진 `studio/templates/` 목록(색 견본·설명·디자인 기준), 작업 공간 서버면 그 작업 공간의 회사 템플릿(`작업 공간` 배지), 시작용 내용(`starters/`, 있을 때). 카드마다 **미리 보기** |
| 샘플 둘러보기 | 참고할 사이트를 등록·삭제하고 새 탭으로 연다(사용자 설정 `samples`) |
| 템플릿 검토 | `/review` — 템플릿·레이아웃 후보와 참고 자료를 미리 보고 검토·승인(등록일·검토일·승인일·이력). [research/review](research/review/README.md) |

### 서버 작업 — nexa-slide 엔진 개발

작업 공간 세션이 할 수 없는 **엔진 변경**(새 레이아웃·유형·렌더 버그·명령 추가)을 요청으로 모아 **엔진 개발 세션 하나**가 순서대로 처리한다([dev/engine-request-design.md](dev/engine-request-design.md)).

- 카드(최근 작업 항목과 같은 4줄 틀): 1줄 제목 · 2줄 엔진 경로 · 3줄 배지(`main` 해시 · 작업 브랜치 `engine-dev` 해시(+앞선 커밋 수) · 상태별 요청 수, 없으면 "처리할 요청 없음") · 4줄 세션 상태 배지 + 마지막 세션 요약 + 오른쪽 끝 [세션 시작]/[세션 중지](최근 작업과 같은 알약 버튼) · 그 아래 최근 요청 8건(첨부 축소판 포함) · 맨 아래 **[요청 추가]**.
- **새로 고침 없이 갱신**: 시작 페이지는 5초마다(`/api/home/live`) 최근 작업의 서버·세션 상태(웹 세션 처리 중·턴·세션 ID)와 서버 작업 카드를 다시 읽는다 — 창이 열려 있거나 입력 중·탭이 숨겨져 있으면 건너뛰고 탭으로 돌아오면 바로.
- **승인 대기 알림**(관리자): 작업 공간 세션이 넘긴 엔진 요청(승인 대기)이 있으면 모든 페이지(시작 페이지·Studio·계정)의 메뉴 단추(☰)에 빨간 숫자 배지, 탭 제목 앞 `(n)`, 새로 생기면 토스트("서버 작업 보기" 링크, 처음 한 번 "데스크톱 알림 켜기" — 켜면 브라우저 알림도). 10초마다 `GET /api/engine/notice`(허브, 큐 파일만 읽음). 메뉴의 "서버 작업" 항목에도 승인 대기 수.
- **세션 꺼짐 배너**: 처리·승인 대기가 있는데 엔진 세션이 꺼져 있으면 카드 위에 "처리 대기 n건 · 세션 꺼짐" 경고 — 관리자에게는 [세션 시작], 일반 사용자에게는 **[관리자에게 시작 요청]**(누르면 `hub/engine/start-request.json` 에 사용자·시각이 묶여 기록되고 접근 로그 `event=engine.start_requested`, 관리자 화면 배너에 "kiros33 님이 10/14 14:10 에 시작을 요청"). 기본 메뉴(☰)의 "서버 작업" 항목에도 대기 건수 배지. 세션을 시작하면 시작 요청은 지워진다. 자동 시작은 두지 않는다(결정 유지).
- 요청을 넣을 때 세션이 꺼져 있으면 응답(`note`)·토스트·CLI 출력(`안내: …`)에 "엔진 개발 세션이 꺼져 있어 관리자가 시작해야 처리됩니다" — 작업 공간 세션은 그 문장을 원 요청 `reply` 에 그대로 옮겨 적는다(`turn_prompt.md`).
- 카드 목록은 **최근 5건**. **[더 보기 (전체 n건)]** → `/engine` 전체 목록 페이지(`studio/engine.html`): 검색(제목·내용·답·요청자·커밋, `#9`·`#1,5,8-9` 는 요청 번호 지정(나머지 낱말은 그 안에서 찾기), 일치 부분 강조 — 기본은 **퍼지**(띄어쓰기·한두 글자 차이 허용), 입력칸 옆 토글 **Aa 대소문자 · ab 단어 단위 · .\* 정규식**은 일반 편집기의 찾기와 같고 브라우저에 기억된다. 공용 모듈 `studio/search.js`, 편집기의 요청 기록 창도 같은 것을 쓴다)·상태별 칩·30건씩 더 보기·제목을 눌러 내용·답·첨부(라이트박스) 펼치기·관리자 조작(승인·거절·적용됨·삭제). API `GET /api/engine/requests?status=&q=` 는 부분 일치 검색(CLI 용), 응답에 `total`.
- **[요청 추가]**: 로그인 사용자 누구나(제목·내용). 내용 칸은 Enter = 큐에 넣기, Shift+Enter = 줄바꿈. 내용 칸에 클립보드 그림 Ctrl+V·끌어다 놓기·[＋ 첨부]로 파일을 붙일 수 있다 — `POST /api/engine/attach` 로 `hub/engine/attach/_new/` 에 올라가고 큐에 넣을 때 `attach/<요청 id>/` 로 옮겨져 `evidence` 에 경로가 붙는다(`GET /api/engine/attach/<id>/<파일>` 로 본다). 엔진 개발 세션은 `--restricted` 라 cwd 밖을 읽지 못하므로 턴마다 worktree 의 `.nexa/attach/<id>/` 로 복사해 `attachments` 로 보여 준다. 작업 공간 세션이 넘긴 요청(`python3 nexa.py engine_request add …`)은 **승인 대기(triage)** 로 들어와 관리자가 승인해야 처리된다(프롬프트 인젝션 연쇄 차단).
- **수동 엔진 세션**: 이미 열려 있는 Claude Code 세션(터미널·VS Code, 엔진 저장소나 작업 공간에서 연 것)에 **`/nexa-slide-server`** 를 입력하면 그 세션이 큐를 맡는다(서버 작업 세션은 하나 — 웹 엔진 세션이 켜져 있으면 `refused`, 먼저 [세션 중지]; 다른 터미널 세션이면 물은 뒤 `--takeover`). 작업 공간 폴더 또는 그 저장소 루트에서 연 세션은 **`/nexa-slide-session`** 으로 그 작업 공간의 슬라이드 세션(편집기 요청 처리)이 된다 — 웹 세션이 맡고 있으면 `refused`(web-session), 서버가 꺼져 있으면 먼저 `nexa.py start`. **표시**: 감시 명령의 `--agent`·`--model`(슬래시 명령이 자기 모델 ID 를 넣는다)과 Claude Code 환경변수(`CLAUDE_CODE_SESSION_ID`·`CLAUDE_CODE_ENTRYPOINT`)로 카드가 "수동 세션 · 이름 · claude claude-fable-5-1 · vscode · #세션ID" 를 보인다(`procutil.session_meta`). **수명**: Monitor 를 건 세션(터미널·VS Code)이 닫히면 감시는 표준 출력이 닫힌 것을 보고 몇 초 안에 스스로 끝난다(`procutil.StdoutWatch` — 0바이트 쓰기 판정이 3초 이상 '닫힘'이고 실제 한 줄 `{"event":"ping"}` 쓰기도 실패할 때만. Node(Monitor) 파이프에서 0바이트 판정이 간혹 오판하므로). 관리자는 서버 작업 카드의 **[끊기]**(최근 작업 카드는 [끊기]/[세션 중지])로 밖에서 끝낼 수 있다 — `POST /api/engine/session {action: stop}`·`/api/project session stop` 이 웹 세션이 없으면 하트비트의 수동 감시 프로세스를 자식까지 끝내고 `stopped` 로 표시한다(`procutil.stop_manual`). 그 뒤 [세션 시작]으로 웹 세션을 띄운다(엔진 `.claude/commands/nexa-slide-server.md` · 작업 공간은 `init_workspace`/`update_launcher` 가 같은 명령 파일을 둔다). 명령은 큐 감시 `watch_engine_requests.py --stream` 을 Monitor 로 띄우고, 요청이 오면 엔진 worktree 에서 처리하는 절차를 세션에 알려 준다. 세션 ID 만으로 밖에서 연결하는 방식은 Claude Code 가 외부 입력 주입 API 를 제공하지 않아 불가능하다(문서 확인). 카드에 "수동 세션 · <이름>" 과 폴더가 보이고 [세션 시작]은 "터미널이 맡음"으로 바뀐다. 명령은 카드 세션 줄의 **⋯**(관리자)에서 복사한다 — 웹 엔진 세션이 켜져 있으면 "먼저 [세션 중지]" 안내가 함께 보인다(둘은 동시에 못 맡는다). 처리할 요청(open)이 생기면 Monitor 알림 `{"event":"request","item":{…}}` 이 오고, 세션은 worktree 에서 구현 → 검증 → 커밋 → `python3 studio/engine_request.py status <id> done --commit … --reply …` 로 끝낸다. 웹 엔진 세션이 살아 있으면 거절(`refused`), 거꾸로 수동 감시가 살아 있으면 [세션 시작]이 거절된다.
- **[세션 시작]**(관리자): 에이전트·모델을 고르면 허브가 `<엔진>/.claude/worktrees/engine-dev`(브랜치 `engine-dev`)를 만들고 큐의 요청을 하나씩 턴으로 처리 — 구현 → 검증 → 커밋(`engine-request #N`) → `done` + reply(커밋·검증). 운영 트리(main)는 건드리지 않는다. [진행]은 SSE 모달, [세션 중지]는 실행 중 턴까지 끝낸다.
- 관리자 조작: 승인(`triage`→`open`) · 거절 · **적용됨**(`engine-dev` 를 main 에 병합하고 허브·작업 공간 서버를 재시작한 **뒤**에 표시 — 병합과 재시작은 사람이, [server-admin.md](server-admin.md)) · 삭제.
- 큐·세션 상태·로그는 사용자 설정 폴더 `hub/engine/`(저장소 밖). API: `GET /api/engine`(+`startRequest`·`sessionOff`·첨부), `GET/POST /api/engine/requests`(`add`·`status`·`priority`·`remove`·`startRequest`), `GET/POST /api/engine/session`(+`/events`·`/log`), `POST /api/engine/attach` · `GET /api/engine/attach/<id>/<파일>`.

### 미리 보기

템플릿 카드·시작용 내용 카드·새로 만들기 양식의 **미리 보기**는 고른 템플릿 × 내용으로 만든 슬라이드를 창에 보여 준다.
창 안에서 템플릿과 내용을 바꿔 가며 비교하고, "이 조합으로 만들기"로 새로 만들기 양식에 그대로 옮긴다.

- 내용을 고르지 않으면 **레이아웃 견본**(레이아웃마다 필드 예시로 한 장 - `layout_samples.py`)을 그 템플릿으로 보여 준다.
- 서버(`GET /api/preview?template=&starter=`)가 사용자 설정 폴더의 `hub/preview/<템플릿>--<내용>/` 에 임시 작업 공간을
  `init_workspace.py` 로 만들고 빌드한다. 엔진·작업 공간에는 아무것도 쓰지 않는다.
- 조합마다 처음 한 번만 빌드하고, 엔진 코드·템플릿·시작용 내용이 바뀌면 다시 만든다. 지워도 다음 미리 보기 때 다시 생긴다.
- 그리기는 편집기와 같은 `render.js` 다(PowerPoint 결과와의 차이는 `compare.py` 기준과 같다).
- 작업 공간 서버의 시작 페이지에서는 그 작업 공간의 회사 템플릿도 미리 볼 수 있다 — `template.json` 과 `assets/brand/*.png` 를 임시 작업 공간에 복사해 빌드한다(`hub/preview/ws-<이름>--<템플릿>--…/`).

### 회사 템플릿 만들기(마법사)

색 5개·로고·글꼴로 **작업 공간 템플릿**(`templates/<이름>/template.json` — 엔진 템플릿을 `extends` 하고 `tokenOverrides` 만, [templates.md](templates.md#작업-공간-템플릿회사-템플릿--extends--tokenoverrides-만))을 만든다. 엔진 저장소에는 아무것도 쓰지 않는다.

- 여는 곳: 템플릿 탭 맨 앞 카드, 새로 만들기 ①의 템플릿 격자 끝 카드. 새로 만들기에서 열면 "만들기"가 양식에 그 템플릿을 **골라 두고**(격자에 ✎ 카드) 작업 공간을 만들 때 함께 만든다(`POST /api/project create` 의 `wizard`) — 서버가 뜨기 전에 두므로 재시작이 없다. 템플릿 탭에서 열면 **적용할 작업 공간**(이 서버의 작업 공간 · 최근 작업)을 고른다.
- 입력: 기반 템플릿(엔진 템플릿, 기본 `lecture`) → 색 5개(주색 · 바탕 · 본문 글자 · 보조색 1 · 보조색 2, 시작값은 기반 템플릿의 색) → 로고 PNG(`assets/brand/logo.png` 로 저장, 비율은 PNG 머리) · 회사 이름(alt) → 글꼴(기반 템플릿 세트 중 하나 또는 **전용 글꼴 파일 올리기** — `fonts/` + `nexa-slide.json` `fontPresets`) → 이름(영문·숫자·`-`·`_`, 엔진 템플릿 이름 불가) · 표시 이름.
- 미리 보기: 서버 왕복 없이 브라우저에서 — 기반 템플릿의 `/api/preview` 결과(빌드된 레이아웃 견본)에 파생 토큰을 `Render.setTokens` 로 덮어 그린다. 파생(`*-container` · `on-*` · 바탕 단계 · `panel` · `day3`)은 `POST /api/project {action: "palette", colors}` → `studio/palette.py`(순수 함수, 한 곳) 가 계산하고 대비 4.5:1 미만인 짝은 **대비 경고**로 보인다. "고급" 펼침에서 파생값을 하나씩 고친다. 올린 로고는 미리 보기 슬라이드의 로고 자리에 object URL 로 바꿔 보인다.
- 만들기: `POST /api/project {action: "template", ws, name, base, colors, label?, brand?, font?, overwrite?}`(관리자, 또는 이 허브에서 연 작업 공간(최근 작업)에 한해 로그인 사용자 · 작업 공간 서버는 자기 작업 공간만) → `templates/<이름>/template.json` · `assets/brand/logo.png` · `fonts/<파일>` 을 쓰고 `nexa-slide.json` 의 `template`(·`brand`·`fontPresets`·`fontPreset`)을 바꾼다(`set_template` 과 같은 처리 — 공유 파일에만). 접근 로그 `event=template.create:<작업 공간>:<이름>`.
- 만든 뒤: 그 작업 공간 서버가 떠 있으면 **[지금 다시 시작]**(허브에서 `stop` → `start`; 작업 공간 서버 자신의 페이지면 터미널 `nexa.py restart` 안내). 기존 덱의 글자 크기 하한은 `build_deck --force` 때 적용되고 PPTX 는 다시 내보낸다.

### 새로 만들 때 하는 일

버튼과 명령이 같은 일을 한다. 서버의 `plan`(`POST /api/project {"action": "plan", …}`)이 양식 값으로 만들 폴더·포트와
`init_workspace.py` 명령을 정하고, 양식 아래 **"또는 명령으로 만들기"** 에 그 명령을 그대로 보여 준다(PowerShell · bash 고르기, 복사 버튼).
"만들고 Studio 열기"는 같은 명령을 실행한 뒤 서버를 띄운다.

```powershell
# ① 작업 공간 만들기 + 덱 빌드 (양식 값이 채워진 예)
python3 'D:\Projects\nexa-slide\studio\init_workspace.py' 'C:\Users\me\Documents\NexaSlide\신제품-소개' --title '신제품 소개' --template report --port 5611 --build --purpose '영업팀 신제품 교육' --direction '20분 발표' --direction '결론 먼저' --ask-draft
# ② 서버 시작 → http://127.0.0.1:5611/
python3 'C:\Users\me\Documents\NexaSlide\신제품-소개\nexa.py' start
```

1. `init_workspace.py <폴더> --title … --template … [--starter …] --port N --build` 로 작업 공간을 만들고 `content/*.json`(밑줄로 시작하는 공통 파일 제외)을 빌드한다.
2. 목적·대상·작성 방향·참고 자료(`--purpose` `--audience` `--direction`… `--material`…)가 있으면 `BRIEF.md` 에 쓰고, 작업 공간 `CLAUDE.md` 에 "초안 전에 BRIEF.md 를 읽는다"를 덧붙인다.
3. "Claude 세션에 초안 작성 요청 남기기"(`--ask-draft`)를 켰으면 첫 덱 첫 슬라이드에 대기(`open`) 요청을 하나 남긴다. 세션이 연결되면 전달된다.
4. 최근 작업에 올린다(명령으로 만들어도 시작 페이지 "최근 작업"에 보인다).

**최근 작업의 실행 상태**: 항목마다 그 작업 공간 서버가 지금 떠 있는지 확인해(`server.json` 의 주소가 실제로 그 작업 공간을 내주는지) 보여 준다.

| 상태 | 표시 | 버튼 |
|---|---|---|
| 실행 중 | `포트 5603`(초록 — 실제로 쓰는 포트, 중계가 켜져 있으면 그 서버로 바로 가는 링크) | **서버 중지** — 그 작업 공간 서버만 끈다(`service.py stop`). 지금 이 페이지를 내주는 작업 공간 서버는 끄지 않는다 |
| 꺼짐 | `포트 5603`(회색 — 설정 포트 — `nexa-slide.json`·`nexa-slide.local.json`) | **서버 시작** — 서버만 띄우고 페이지는 그대로 |

항목은 네 줄 — 1줄 제목(오른쪽 끝에 ✕ 목록에서 빼기), 2줄 경로, 3줄(오른쪽 정렬) git · 덱 개수 · 포트 · 서버 시작/중지, 4줄 AI 세션.
**AI 세션 줄(4줄)** — `웹 세션 · claude · opus · <시작 사용자> · 대기 n/처리 중 n` / `수동 세션 · <label>` / `세션 없음 (· 마지막 …)`.
**[세션 시작]** 은 창에서 에이전트·모델(설치·로그인 상태, 작업 공간 기본값 미리 선택, 직접 입력, "이 작업 공간 기본으로 저장")을 고르고, **서버가 꺼져 있으면 먼저 띄운 뒤** 그 서버의 세션을 시작한다(`POST /api/project {"action": "session", "op": "start"|"stop"|"status", path, agent?, model?, saveAs?}` → `hub.session_ws`). 실패하면 창 안에 사유가 남는다(허브가 옛 판이면 재시작 안내).
**[세션 중지]** 는 실행 중 턴의 프로세스까지 끝낸다. 수동 세션이 맡고 있으면 단추가 없다. 로그인 사용자 누구나 쓸 수 있다 — [dev/web-session-design.md](dev/web-session-design.md).

항목의 줄 구성은 위 표 아래 설명과 같다(제목 줄 끝 ✕ · 경로 · 서버 · 세션).
항목(제목)을 누르면 예전처럼 연다 — 꺼져 있으면 띄운 뒤 이동, 이미 떠 있으면 다시 띄우지 않고 바로 그 주소로 이동.
5. 버튼이면 그 작업 공간 서버를 띄워 Studio 로 이동한다. 명령이면 ② 를 실행하고 주소를 연다.

**포트**: 양식의 포트 칸을 비우면 5600 부터 비어 있고 최근 작업 공간 설정이 쓰지 않는 포트를 고른다(허브 포트 제외 - 칸에 제안값이 보인다).
적으면 그 포트로 만든다. 지금 다른 프로그램이 쓰는 포트·허브 포트는 거절하고, 다른 작업 공간 설정과 같으면 알린다.

**경로에 `&`**(예: `S&OP`): Windows 의 pyenv-win `python3` 은 배치(.bat) 대리 실행기라 인자의 `&` 에서 명령이 잘린다. 이때 명령 안내는 실제 파이썬 실행 파일 경로로 바뀌고 경고가 보인다 — 가능하면 폴더 이름에서 `&` 를 뺀다.

이미 작업 공간이 있는 폴더면 만들지 않고 "열기"를 권한다. 작업 공간이 없는 폴더를 열면 그 폴더를 루트로 새로 만들기를 권한다.
저장소 루트를 열면 루트 표식 `.nexa-slide.json` 의 `workspace`(없으면 `slides/`, 그것도 없으면 바로 아래 작업 공간 폴더)를 연다
(폴더 고르기 창도 저장소 루트에 "작업 공간" 표시).

### 작업 공간 관리 — 정리·보관

작업 공간 카드의 **🧹**(허브 관리자, 또는 작업 공간 서버에 직접 접속한 운영자)를 누르면 **정리·보관 창**이 뜬다(`studio/tidy.py`, 작업 공간 서버 `GET/POST /api/tidy` - 허브에서는 중계 `/w/<id>/api/tidy`, 서버가 꺼져 있으면 카드의 [시작]으로 먼저).

- **정리 대상**(범주마다 체크, 기본은 산출물·고아 첨부·세션 로그): **산출물** = `out/*.pptx·*.pdf·*.fonts.json`, `out/<덱>/slide-NN.png`(렌더), `out/import/`, Chrome 프로필 - 다시 만들 수 있다. **고아 첨부** = `out/attach/<덱>/` 중 그 덱의 요청이 참조하지 않는 파일, 없는 덱의 첨부 폴더. **세션 로그** = `out/.studio/sessions/`, 1MB 넘는 `server.log`(비움). **참조 없는 그림** = `assets/images`·`assets/import` 중 어느 덱(`decks/*.json`)·내용(`content/*.json`)·브랜드 설정도 쓰지 않는 그림(mermaid `.mmd` 는 `.png` 의 짝으로 같이) - 백업·휴지통의 덱이 참조하는 그림은 "백업 참조"로 표시하고 기본으로 남긴다. **백업·휴지통** = `decks/.history/`·`decks/.trash/` - 되돌리기·되살리기에 쓰이므로 기본은 두고, 지우려면 확인을 받는다. 실행 중 상태 파일(`out/.studio/server.json`·`session.json` 등)·`nexa-slide.json`·`.env`·`.git` 은 건드리지 않는다.
- **정리**는 지우지 않고 `out/.tidy/<시각>/` 에 같은 경로로 **옮겨 둔다**(되돌리기: `nexa.py tidy restore --stamp <시각>`). **[비우기]** 가 완전히 지운다.
- **압축 보관**: 작업 공간(저장소 루트 표식 `.nexa-slide.json` 이 있으면 루트째)을 `<기준 폴더>/_archive/<제목>-<시각>.zip` 으로. 기본은 `out/`(요청 첨부 `out/attach` 는 포함)·`decks/.history`·`decks/.trash`·`.env`·`nexa-slide.local.json`·`.git` 제외(`.gitignore` 와 같은 기준), "전부 넣기"는 `.git` 과 실행 상태 파일만 뺀다. 보관 뒤 카드의 ✕ 로 목록에서 빼고 폴더를 지우면 된다(폴더 삭제는 사용자가 - 서버는 작업 공간 폴더 자체를 지우지 않는다).
- CLI: `python3 nexa.py tidy`(보고) · `tidy --apply [--only output,attach,log,image,backup] [--include-kept]` · `tidy --purge` · `tidy restore --stamp …` · `nexa.py archive [--all] [--out <zip>]`.
- **원인 쪽 수정**: 요청 초안 지우기(`discard`)·첨부 바꾸기(`update`)가 이제 파일도 지우고, 엔진 요청 삭제(`engine_requests.remove`)가 `attach/<id>/` 를 지운다. 허브의 엔진 요청 첨부는 `GET/POST /api/engine/tidy`(관리자) - 큐에 없는 요청의 첨부 폴더와 하루 넘게 요청에 붙지 않은 `attach/_new/` 파일.

## 기본 메뉴

Studio 와 시작 페이지 머리줄 **왼쪽 위 메뉴 단추(☰)** 로 왼쪽 서랍을 연다(GitHub 방식, `studio/menu.js`).

- 홈 · 새 슬라이드 만들기 · 폴더·저장소 열기 · Studio(현재 작업 공간)
- 튜토리얼 · 데모 · 템플릿 · 샘플 둘러보기
- 최근 작업(🔍 로 이름·경로 찾기, 누르면 그 작업 공간 서버를 띄워 이동)
- 기준 폴더 설정
- **표시 언어** — 누르면 목록(`System (한국어)` · `English` · `한국어`)이 펼쳐지고 ✓ 가 지금 값. 고르면 **새로 고침 없이 즉시** 바뀐다
- 계정 · 로그아웃(허브 로그인 사용자)

Esc·바깥·닫기 단추로 닫는다. 주소에 `?menu=open` 을 붙이면 메뉴를 연 채로 연다.

### 표시 언어(i18n)

한국어가 원문이고 영어는 `studio/i18n.js` 의 **사전**으로 바꾼다 — 화면 파일(HTML·JS)의 글은 그대로 두고, 페이지가 뜬 뒤 DOM 의 글(텍스트·`placeholder`·`title`·`aria-label`·`<title>`)을 사전으로 바꾸며, `MutationObserver` 가 뒤에 생기는 글(동적 화면·토스트)도 바꾼다. `confirm`·`prompt`·`alert` 의 글도 거친다.

- **시스템 기본**(`system`, 기본값): 브라우저 언어(`navigator.language`)가 한국어면 한국어, 아니면 영어. 메뉴에는 `System (한국어)` 처럼 지금 결정된 언어가 같이 보인다.
- 저장: 브라우저 `localStorage` `nexa-lang`(이 PC·이 브라우저). 주소에 `?lang=en|ko|system` 을 붙이면 그 값으로 바꿔 저장한다.
- `<html lang>` 이 실제 언어로 바뀐다(글꼴·맞춤법 검사 기준).
- 변수가 든 문구(`슬라이드 3`, `요청 2개 보내기`, `10/14 16:39 · 사용자 중지`)는 정규식 패턴과 ` · ` 조각 단위 번역으로 처리한다. 사전에 없는 글은 한국어 그대로 남는다 — **템플릿·시작 내용·글꼴 목록의 설명문과 슬라이드 내용(데이터)은 번역하지 않는다**.
- 새 UI 글을 넣을 때: 화면 코드는 한국어로 쓰고, `i18n.js` 의 `EN` 사전에 같은 글을 키로 영어를 더한다(` · ` 로 이어진 글은 조각마다). 코드에서 직접 번역한 글이 필요하면 `I18N.t("…")`.
- 로그인 페이지(`/login`)도 `/studio/i18n.js` 를 로그인 없이 읽는다(`AUTH_FREE`).

## API

| 메서드 · 경로 | 설명 |
|---|---|
| `GET /api/home` | `{mode, documents, projectsRoot, projectsRootDefault, current, refused, recent, templates, starters, samples, demo, user, proxy, sessionGlobal}`. `recent[].session` = `{kind: web\|manual\|none, connected, label, agent, model, user, started, lastSeen, open, working, last, defaults}`(파일만 읽음) |
| `POST /api/project` | `{"action": "create", title, template, starter?, folder?, sub?, port?, purpose, audience, direction, materials, askDraft}` · `{"action": "plan", …create 와 같음}` → `{path, port, url, args, commands: {powershell, bash: {init, start}}, warnings}` · `{"action": "open", path}` · `{"action": "demo"}` · `{"action": "forget", path}` → `{ok, path, url, direct, id, hubUrl}` (`url` = `hubProxy` 가 켜져 있으면 `/w/<이름>/`, 아니면 `direct`). 실패하면 400 `{error, needInit?, existing?, log?}` |
| `/w/<이름>/…` | 중계 — 그 작업 공간 서버의 `/…` 로 넘긴다(위 "한 주소로 중계"). 모르는 이름은 404, 서버를 띄우지 못하면 502 |
| `/api/auth/…` · `/login` · `/setup` · `/account` | 로그인·계정 — [auth.md](auth.md). 위의 모든 API 는 로그인 뒤에 있다(미인증 401) |
| `GET /api/preview?template=&starter=` | 미리 보기 - 템플릿 × 시작용 내용(없으면 레이아웃 견본)을 사용자 설정 폴더의 임시 작업 공간에 빌드 → `{template, starter, tokens, base, decks}`. 작업 공간 서버에서는 그 작업 공간의 회사 템플릿도 |
| `POST /api/project` `{"action": "palette", colors}` | 회사 템플릿 마법사의 색 파생(쓰기 없음) → `{colors(역할 색 전부), warnings[{fg, bg, ratio}]}` |
| `POST /api/project` `{"action": "template", ws, name, base, colors, label?, description?, brand?: {name, logo: {name, data(base64 PNG)}, wordmark?}, font?: {preset} \| {name, family, files: {regular, bold?}}, overwrite?}` | 회사 템플릿 만들기 → 작업 공간 `templates/<이름>/template.json`·로고·글꼴 파일을 쓰고 `nexa-slide.json` 의 `template` 을 바꾼다 → `{name, base, label, dir, files, colors, warnings, config, restart: {needed, running, url, id, hubUrl}, template(카드), note}`. 관리자 또는 최근 작업의 작업 공간(403) · 엔진 이름·금지 입력은 400 · 이미 있으면 400 `{exists: true}` |
| `POST /api/settings` | `{projectsRoot?, samples?, hubProxy?, sessionAgent?, sessionModel?, sessionModels?, sessionIdleMinutes?, sessionTurnMinutes?, sessionMax?, sessionMaxTurns?, sessionBudgetUsd?, engineMaxTurns?, engineTurnMinutes?, engineContinue?, agentPaths?}` - 빈 값은 기본으로. `session*`·`agentPaths` 는 관리자만(403) |
| `POST /api/project` `{"action": "session", op, path, agent?, model?, saveAs?}` | 작업 공간 웹 세션 `start`·`stop`·`status`·`model` — 서버가 꺼져 있으면 먼저 띄운다. 응답은 그 서버의 `/api/wsession` 과 같고 `url`(서버 주소)이 붙는다 |
| `GET /api/fs?path=<폴더>` | 폴더 고르기 - 하위 폴더 `[{name, path, git, workspace}]`, 드라이브 목록, 바로 가기(문서·기준·홈) |

`/api/fs` 는 이 PC 의 폴더 이름을 보여 준다. 서버는 `127.0.0.1` 에만 열린다([server.md](server.md)).
