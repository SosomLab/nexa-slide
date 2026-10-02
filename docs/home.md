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

## 기준 폴더

특별히 정하지 않으면 **운영체제의 기본 문서 폴더** 아래 `NexaSlide/` 가 기준 폴더이고, 제작마다 그 아래에 폴더를 하나씩 만든다.

| 운영체제 | 문서 폴더 |
|---|---|
| Windows | 알려진 폴더 Documents(`SHGetKnownFolderPath`). OneDrive·다른 드라이브로 옮겼으면 그 위치 |
| macOS | `~/Documents` |
| Linux | `xdg-user-dir DOCUMENTS`(한국어 환경이면 `~/문서`일 수 있다). 없으면 `~/Documents` |

우선순위: 환경변수 `NEXA_SLIDE_PROJECTS` > 사용자 설정 `projectsRoot`(시작 페이지 메뉴 "기준 폴더 설정") > 문서 폴더/`NexaSlide`.
현재 값 확인: `python3 studio/paths.py`

**폴더·저장소를 지정하면** 기준 폴더 대신 그 폴더 아래에 만든다. 하위 폴더는 제목(폴더 이름으로 바꾼 것)으로 자동으로 채우고, git 저장소를 고르면 `slides` 로 채운다.
제목을 바꾸면 따라 바뀌지만, 사용자가 하위 폴더를 직접 고치면 그 뒤로는 건드리지 않는다(비우면 그 폴더에 바로 만든다).
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
| `recent` | 최근 작업 `[{path, title, opened}]` - 최대 30개 |
| `samples` | 등록한 샘플 사이트 `[{name, url, note}]` |

## 시작 페이지 구성

| 탭 | 내용 |
|---|---|
| 시작 | **새 슬라이드 만들기**(① 제목·템플릿·시작용 내용 ② 목적·대상·작성 방향·참고 자료 ③ 저장 위치), **폴더·저장소 열기**, **최근 작업** |
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
5. 버튼이면 그 작업 공간 서버를 띄워 Studio 로 이동한다. 명령이면 ② 를 실행하고 주소를 연다.

**포트**: 양식의 포트 칸을 비우면 5600 부터 비어 있고 최근 작업 공간 설정이 쓰지 않는 포트를 고른다(허브 포트 제외 - 칸에 제안값이 보인다).
적으면 그 포트로 만든다. 지금 다른 프로그램이 쓰는 포트·허브 포트는 거절하고, 다른 작업 공간 설정과 같으면 알린다.

이미 작업 공간이 있는 폴더면 만들지 않고 "열기"를 권한다. 작업 공간이 없는 폴더를 열면 그 자리에 새로 만들기를 권한다.

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
| `POST /api/project` | `{"action": "create", title, template, starter?, folder?, sub?, port?, purpose, audience, direction, materials, askDraft}` · `{"action": "plan", …create 와 같음}` → `{path, port, url, args, commands: {powershell, bash: {init, start}}, warnings}` · `{"action": "open", path}` · `{"action": "demo"}` · `{"action": "forget", path}` → `{ok, path, url}`. 실패하면 400 `{error, needInit?, existing?, log?}` |
| `GET /api/preview?template=&starter=` | 미리 보기 - 템플릿 × 시작용 내용(없으면 레이아웃 견본)을 사용자 설정 폴더의 임시 작업 공간에 빌드 → `{template, starter, tokens, base, decks}` |
| `POST /api/settings` | `{projectsRoot?, samples?}` - `projectsRoot` 를 빈 값으로 주면 기본으로 |
| `GET /api/fs?path=<폴더>` | 폴더 고르기 - 하위 폴더 `[{name, path, git, workspace}]`, 드라이브 목록, 바로 가기(문서·기준·홈) |

`/api/fs` 는 이 PC 의 폴더 이름을 보여 준다. 서버는 `127.0.0.1` 에만 열린다([server.md](server.md)).
