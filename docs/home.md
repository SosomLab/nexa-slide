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

계정(`users.json`)·세션·접근 로그도 이 폴더에 있다. 허브는 로컬이어도 로그인이 필요하다 — [auth.md](auth.md).
| `recent` | 최근 작업 `[{path, title, opened}]` - 최대 30개 |
| `samples` | 등록한 샘플 사이트 `[{name, url, note}]` |

## 시작 페이지 구성

| 탭 | 내용 |
|---|---|
| 시작 | **새 슬라이드 만들기**(① 제목·템플릿·시작용 내용 ② 목적·대상·작성 방향·참고 자료 ③ 저장 위치), **폴더·저장소 열기**, **최근 작업**(실행 상태·포트 · 시작/중지) |
| 튜토리얼 | 작업 공간 정하기 → 템플릿·방향 → Studio 편집 → Claude 세션 요청 → 발표·내보내기 |
| 데모 | 엔진 예제(`example/`)를 기준 폴더의 `nexa-slide-demo/` 로 처음 한 번 복사해 연다 |
| 템플릿 | 엔진 `studio/templates/` 목록(색 견본·설명·디자인 기준), 시작용 내용(`starters/`, 있을 때). 카드마다 **미리 보기** |
| 샘플 둘러보기 | 참고할 사이트를 등록·삭제하고 새 탭으로 연다(사용자 설정 `samples`) |
| 템플릿 검토 | `/review` — 템플릿·레이아웃 후보와 참고 자료를 미리 보고 검토·승인(등록일·검토일·승인일·이력). [research/review](research/review/README.md) |

### 미리 보기

템플릿 카드·시작용 내용 카드·새로 만들기 양식의 **미리 보기**는 고른 템플릿 × 내용으로 만든 슬라이드를 창에 보여 준다.
창 안에서 템플릿과 내용을 바꿔 가며 비교하고, "이 조합으로 만들기"로 새로 만들기 양식에 그대로 옮긴다.

- 내용을 고르지 않으면 **레이아웃 견본**(레이아웃마다 필드 예시로 한 장 - `layout_samples.py`)을 그 템플릿으로 보여 준다.
- 서버(`GET /api/preview?template=&starter=`)가 사용자 설정 폴더의 `hub/preview/<템플릿>--<내용>/` 에 임시 작업 공간을
  `init_workspace.py` 로 만들고 빌드한다. 엔진·작업 공간에는 아무것도 쓰지 않는다.
- 조합마다 처음 한 번만 빌드하고, 엔진 코드·템플릿·시작용 내용이 바뀌면 다시 만든다. 지워도 다음 미리 보기 때 다시 생긴다.
- 그리기는 편집기와 같은 `render.js` 다(PowerPoint 결과와의 차이는 `compare.py` 기준과 같다).

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
| 실행 중 | `포트 5603`(초록 — 실제로 쓰는 포트) | **중지** — 그 작업 공간 서버만 끈다(`service.py stop`). 지금 이 페이지를 내주는 작업 공간 서버는 끄지 않는다 |
| 꺼짐 | `포트 5603`(회색 — 설정 포트 — `nexa-slide.json`·`nexa-slide.local.json`) | **시작** — 서버만 띄우고 페이지는 그대로 |

항목은 세 줄 — 1줄 제목, 2줄 경로, 3줄(오른쪽 정렬) 덱 개수 · 포트 · 시작/중지 · ✕(목록에서 빼기).
항목(제목)을 누르면 예전처럼 연다 — 꺼져 있으면 띄운 뒤 이동, 이미 떠 있으면 다시 띄우지 않고 바로 그 주소로 이동.
5. 버튼이면 그 작업 공간 서버를 띄워 Studio 로 이동한다. 명령이면 ② 를 실행하고 주소를 연다.

**포트**: 양식의 포트 칸을 비우면 5600 부터 비어 있고 최근 작업 공간 설정이 쓰지 않는 포트를 고른다(허브 포트 제외 - 칸에 제안값이 보인다).
적으면 그 포트로 만든다. 지금 다른 프로그램이 쓰는 포트·허브 포트는 거절하고, 다른 작업 공간 설정과 같으면 알린다.

**경로에 `&`**(예: `S&OP`): Windows 의 pyenv-win `python3` 은 배치(.bat) 대리 실행기라 인자의 `&` 에서 명령이 잘린다. 이때 명령 안내는 실제 파이썬 실행 파일 경로로 바뀌고 경고가 보인다 — 가능하면 폴더 이름에서 `&` 를 뺀다.

이미 작업 공간이 있는 폴더면 만들지 않고 "열기"를 권한다. 작업 공간이 없는 폴더를 열면 그 폴더를 루트로 새로 만들기를 권한다.
저장소 루트를 열면 루트 표식 `.nexa-slide.json` 의 `workspace`(없으면 `slides/`, 그것도 없으면 바로 아래 작업 공간 폴더)를 연다
(폴더 고르기 창도 저장소 루트에 "작업 공간" 표시).

## 기본 메뉴

Studio 와 시작 페이지 머리줄 **왼쪽 위 메뉴 단추(☰)** 로 왼쪽 서랍을 연다(GitHub 방식, `studio/menu.js`).

- 홈 · 새 슬라이드 만들기 · 폴더·저장소 열기 · Studio(현재 작업 공간)
- 튜토리얼 · 데모 · 템플릿 · 샘플 둘러보기
- 최근 작업(🔍 로 이름·경로 찾기, 누르면 그 작업 공간 서버를 띄워 이동)
- 기준 폴더 설정

Esc·바깥·닫기 단추로 닫는다. 주소에 `?menu=open` 을 붙이면 메뉴를 연 채로 연다.

## API

| 메서드 · 경로 | 설명 |
|---|---|
| `GET /api/home` | `{mode, documents, projectsRoot, projectsRootDefault, current, refused, recent, templates, starters, samples, demo}` |
| `POST /api/project` | `{"action": "create", title, template, starter?, folder?, sub?, port?, purpose, audience, direction, materials, askDraft}` · `{"action": "plan", …create 와 같음}` → `{path, port, url, args, commands: {powershell, bash: {init, start}}, warnings}` · `{"action": "open", path}` · `{"action": "demo"}` · `{"action": "forget", path}` → `{ok, path, url, direct, id, hubUrl}` (`url` = `hubProxy` 가 켜져 있으면 `/w/<이름>/`, 아니면 `direct`). 실패하면 400 `{error, needInit?, existing?, log?}` |
| `/w/<이름>/…` | 중계 — 그 작업 공간 서버의 `/…` 로 넘긴다(위 "한 주소로 중계"). 모르는 이름은 404, 서버를 띄우지 못하면 502 |
| `/api/auth/…` · `/login` · `/setup` · `/account` | 로그인·계정 — [auth.md](auth.md). 위의 모든 API 는 로그인 뒤에 있다(미인증 401) |
| `GET /api/preview?template=&starter=` | 미리 보기 - 템플릿 × 시작용 내용(없으면 레이아웃 견본)을 사용자 설정 폴더의 임시 작업 공간에 빌드 → `{template, starter, tokens, base, decks}` |
| `POST /api/settings` | `{projectsRoot?, samples?, hubProxy?}` - `projectsRoot` 를 빈 값으로 주면 기본으로 |
| `GET /api/fs?path=<폴더>` | 폴더 고르기 - 하위 폴더 `[{name, path, git, workspace}]`, 드라이브 목록, 바로 가기(문서·기준·홈) |

`/api/fs` 는 이 PC 의 폴더 이름을 보여 준다. 서버는 `127.0.0.1` 에만 열린다([server.md](server.md)).
