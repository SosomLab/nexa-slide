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

**폴더·저장소를 지정하면** 기준 폴더 대신 그 폴더 아래에 만든다. 하위 폴더를 비우면 그 폴더에 바로 만들고, git 저장소를 고르면 하위 폴더 `slides` 를 권한다.
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
| 템플릿 | 엔진 `studio/templates/` 목록(색 견본·설명·디자인 기준), 시작용 내용(`starters/`, 있을 때) |
| 샘플 둘러보기 | 참고할 사이트를 등록·삭제하고 새 탭으로 연다(사용자 설정 `samples`) |

### 새로 만들 때 하는 일

1. `init_workspace.py <폴더> --title … --template … --deck intro [--starter …]` 로 작업 공간 뼈대를 만든다(빈 포트 자동).
2. 받은 목적·대상·작성 방향·참고 자료를 `BRIEF.md` 에 쓰고, 작업 공간 `CLAUDE.md` 에 "초안 전에 BRIEF.md 를 읽는다"를 덧붙인다.
3. `content/*.json`(밑줄로 시작하는 공통 파일 제외)을 빌드한다.
4. "Claude 세션에 초안 작성 요청 남기기"를 켰으면 첫 덱 첫 슬라이드에 대기(`open`) 요청을 하나 남긴다. 세션이 연결되면 전달된다.
5. 최근 작업에 올리고, 그 작업 공간 서버를 띄워 Studio 로 이동한다.

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
| `POST /api/project` | `{"action": "create", title, template, starter?, folder?, sub?, purpose, audience, direction, materials, askDraft}` · `{"action": "open", path}` · `{"action": "demo"}` · `{"action": "forget", path}` → `{ok, path, url}`. 실패하면 400 `{error, needInit?, existing?, log?}` |
| `POST /api/settings` | `{projectsRoot?, samples?}` - `projectsRoot` 를 빈 값으로 주면 기본으로 |
| `GET /api/fs?path=<폴더>` | 폴더 고르기 - 하위 폴더 `[{name, path, git, workspace}]`, 드라이브 목록, 바로 가기(문서·기준·홈) |

`/api/fs` 는 이 PC 의 폴더 이름을 보여 준다. 서버는 `127.0.0.1` 에만 열린다([server.md](server.md)).
