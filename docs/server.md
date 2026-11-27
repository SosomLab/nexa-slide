# 서버

## 실행

```bash
python3 studio/service.py --workspace <작업 공간> start|stop|restart|status|url   # 백그라운드 서비스(권장)
python3 studio/server.py  --workspace <작업 공간> [--port N | --port auto] [--force] # 앞에서 실행
python3 studio/service.py start                                                    # 작업 공간 밖에서 → 시작 페이지(허브, 5599)
```

- 작업 공간 없이 띄우면 **허브**(시작 페이지)로 뜬다. 실행 정보·로그는 사용자 설정 폴더 `hub/.studio/` - [home.md](home.md).
- **허브는 로컬이어도 로그인이 필요하다.** 처음 접속하면 최초 관리자 설정 페이지가 뜬다. 작업 공간 서버(`nexa.py start`)에는 로그인이 없다 — 그 포트의 직접 노출은 서비스 범위가 아니다. 계정·세션·접근 로그는 사용자 설정 폴더에만(저장소에 들어가지 않음) — [auth.md](auth.md).

### 두 가지 운용 방식

| 방식 | 띄우기 | 브라우저 주소 | 어울리는 때 |
|---|---|---|---|
| **단독** — 작업 공간마다 포트 | `python3 <작업 공간>/nexa.py start` | `http://127.0.0.1:<설정 포트>/` | 작업 공간 하나를 터미널·Claude 세션과 함께 다룰 때 |
| **허브 중계** — 포트 하나로 여러 Studio | `python3 studio/service.py start`(허브) → 로그인 → 시작 페이지에서 열기·만들기, 또는 `/w/<이름>/` 로 바로 | `http://127.0.0.1:5599/w/<이름>/` | 여러 작업 공간을 오가며 쓸 때, 밖(터널)에서 쓸 때. 로그인 사용자가 변경 원장에 남는다 |

두 방식은 **같은 서버 프로세스**를 쓴다 — 허브는 그 작업 공간 서버(별도 프로세스)로 요청을 넘기기만 한다. 따라서
`nexa.py start` 로 띄운 서버가 있으면 허브는 그 서버로 넘기고, 허브가 먼저 띄운 서버는 `nexa.py status`·`url`·`stop` 으로 그대로 다룰 수 있다(작업 공간당 서버 하나).
허브가 띄울 때는 `--port auto` 로 띄우므로, 설정 포트가 다른 작업 공간과 겹쳐도 멈추지 않고 다음 빈 포트를 쓴다(실제 포트는 `out/.studio/server.json`, 시작 페이지의 포트 배지).
중계의 동작·설정(`hubProxy`)은 [home.md](home.md#한-주소로-중계--허브-포트-하나로-여러-studio).

- 포트: `--port` > `nexa-slide.json` 의 `port` > 5600. 쓰는 중인 포트면 알리고 끝낸다(`--port auto` = 그 포트부터 빈 포트 50개 탐색).
- **작업 공간당 서버 하나**: 이 작업 공간 서버가 이미 살아 있으면(`out/.studio/server.json` 의 포트·설정 포트에 실제로 물어 확인) 시작을 거부하고 주소를 알려 준다(`--force` 로 무시). 같은 순간에 `start` 가 둘 들어와도(허브 중계의 자동 기동 + `nexa.py restart`) `service.py` 가 작업 공간 잠금 `out/.studio/start.lock` 으로 줄을 세우고, 서버는 포트를 연 뒤 `server.json` 을 쓰기 직전에 다른 살아 있는 서버가 먼저 떴으면 스스로 물러난다.
- 포트는 배타적으로 연다 — Windows 의 `SO_REUSEADDR` 때문에 두 프로세스가 같은 포트를 여는 문제를 막으려고 `SO_EXCLUSIVEADDRUSE` 를 켠다.
- 실행 정보 `out/.studio/server.json` `{port, url, pid, workspace, title, started}`, 백그라운드 로그 `out/.studio/server.log`.
- `127.0.0.1` 에만 연다(같은 PC 에서만 접속). 다른 PC 에 열지 않는다 — 인증이 없다.
- 표준 라이브러리 `ThreadingHTTPServer` — 요청마다 스레드. 외부 의존 없음.
- 종료: Ctrl+C. 백그라운드로 띄웠다면 포트로 프로세스를 찾아 끝낸다([operation.md](operation.md#포트프로세스-점검)).

## URL 구성

| 경로 | 내주는 곳 |
|---|---|
| `/` | 덱이 있으면 `/studio/`(Studio), 없거나 허브면 `/studio/home.html`(시작 페이지) |
| `/studio/…` | 엔진 `studio/` 폴더(편집기 `index.html`·`render.js`·`studio.js`·`slide.html`) |
| `/studio/tokens.json` | 작업 공간 토큰(없으면 엔진 기본값) |
| `/out/…` | 작업 공간 `out/` — PPTX·렌더 PNG |
| 그 밖 `/…` | `assetRoot` — 덱 그림 경로(`assets/brand/logo.png` 등) |
| `/api/…` | API(아래) |
| `/w/<이름>/…` | 중계 — 그 작업 공간 서버(별도 프로세스·포트)로 그대로 넘기고 응답을 돌려준다. 허브 포트 하나로 여러 Studio 를 쓸 때([home.md](home.md#한-주소로-중계--허브-포트-하나로-여러-studio)). 응답 `Location` 이 `/` 로 시작하면 접두를 다시 붙인다. 자기 작업 공간이면 접두만 떼고 직접 처리. 밖에서 온 `X-Nexa-*` 는 버리고 공유 비밀·사용자 헤더를 붙인다 |
| `/login` · `/setup` · `/account` | 허브의 로그인 · 최초 관리자 설정 · 계정(비밀번호, 관리자면 사용자 관리, 공유 링크) — [auth.md](auth.md) |
| `/s/<토큰>/…` | **보기 전용 공유 링크**(허브, 로그인 없이) — 토큰으로 덱 1개를 `studio/view.html` 로 보여 준다. 허용 목록(보기 페이지·렌더 파일·그 덱의 `/api/deck/<덱>`(노트·숨김 장 제거)·덱이 참조하는 그림)만 그 작업 공간 서버로 중계, 그 밖·모든 쓰기 403. 잘못된 토큰·만료·회수는 같은 안내 페이지(404/410) — [auth.md](auth.md#보기-전용-공유-링크-02225) |

허브의 모든 경로는 `/login`·`/setup`·`/api/auth/state`·`/api/auth/login`·`/api/auth/setup`·`/s/<토큰>/…` 을 빼고 로그인 뒤에 있다. 미인증 요청은 401(API·정적·산출물) 또는 302 `/login`(페이지)이고 본문에 내용이 없다.

보안 범위:
- 점(`.`)으로 시작하는 경로 조각은 모두 403 — `out/.studio`(세션 상태)·`decks/.history`·`.env` 등.
- 각 경로는 그 기준 폴더 밖으로 나갈 수 없다(`..` 정규화 후 검사, 403).
- `assetRoot` 아래 파일은 읽기 가능하다. 저장소 전체를 `assetRoot` 로 잡았다면 그 저장소 파일이 로컬에서 보인다는 뜻이다(127.0.0.1 전용).

## API

| 메서드 · 경로 | 설명 |
|---|---|
| `GET /api/decks` | 문서 목록 `[{id, title, slides, updated, version, start, kind, sheets?}]` — `kind` = `deck`(슬라이드)·`sheet`(시트)·`page`(페이지), `start` = 시작 덱인가, `sheets` = 시트 문서의 탭 수 |
| `POST /api/decks` | 문서 관리(작업 공간 서버만, 허브는 404) — `{action: "create", id?, title?, kind?: deck\|sheet\|page, layout?, part?, theme?, pages?, vars?, starter?}` · `{action: "import", name, data(base64), title?}` · `copy`·`start`·`rename`(`newId`)·`retitle`·`delete` → `{ok, …, decks}`. **create**: `theme` 은 시트면 시트 테마(`pages` = 테마에서 만들 페이지 `kind` 목록 · 없으면 모두, `vars` = `{{자리}}` 값), 페이지면 페이지 템플릿 이름(`/api/page-templates`). 슬라이드에 `starter`(`/api/starters` 의 `name`)를 주면 그 시작용 내용(엔진 `starters/<이름>/content/<덱>.json`)을 새 id 로 복사해 빌드한다(`id`·`layout`·`part` 무시, 디자인 템플릿은 이 작업 공간 것 · 시작용 내용의 그림은 없는 파일만 복사) → `{id, title, kind, slides, starter}`. **import** 는 `name` 의 확장자로 고른다: `.docx` → 페이지([pages.md](pages.md), 30MB · `{…, blocks, warnings}`) · `.pptx` → 슬라이드 덱(`import_pptx.py --deck`, 60MB · zip 이 아니면 400) · 그 밖은 엑셀(`.xlsx`·`.xlsm` 만, 30MB → 시트 [sheets.md](sheets.md) · `{…, sheets, warnings}`). 페이지 문서가 꺼져 있으면(`experimental.page`, [configuration.md](configuration.md#nexa-slidejson)) 페이지 만들기·.docx 가져오기는 400, 웹 세션이 턴을 실행 중이면 `rename`·`delete` 는 409 |
| `GET /api/starters` | 슬라이드 시작용 내용 목록 `[{name, label, description, slides, i18n}]` - 새 문서 창의 슬라이드 템플릿. 덱 내용 원본이 없는 것(설정만 있는 시작용 내용)은 빠진다. 작업 공간 서버만(허브는 404) |
| `GET /api/deck/<id>` | 덱 JSON. 헤더 `X-Deck-Version` = 파일 mtime_ns |
| `PUT /api/deck/<id>?base=<ver>&origin=editor\|claude&action=save\|restore&request=&note=&label=` + 헤더 `X-Nexa-Tab` | 덱 저장 — 원자적 쓰기, 저장 전 `.history` 백업(50개 유지), **변경 원장에 한 줄**(응답 `seq`). `base` 가 현재 버전과 다르면 **409**(`force=1` 이면 무시), `merge=1` 이면 409 대신 3-way 병합 → `{merged, conflicts, deck}`(기준본을 모르면 409 `reason: no-base`) - [collab.md](collab.md) · [change-ledger.md](change-ledger.md). 시트는 `sheets`, 페이지는 `page_doc.validate` 로 형식을 검사한다(틀리면 400) |
| `GET /api/version/<id>` | `{deck, requests, changes, session, deckIds, decksVer, config, engine}` — 편집기가 2초마다 확인(외부 변경 감지·원장 기록·세션 상태·덱 목록·설정·엔진 변경 → 탭 갱신·새로 고침 안내) |
| `GET /api/changes/<id>` | 변경 원장 - `?limit=&before=&since=&origin=&slide=&group=1&recent=1&seq=N` ([change-ledger.md](change-ledger.md#api)) |
| `GET /api/requests/<id>` | 요청 메모 목록 |
| `POST /api/engine_request` | `{title, body?, request?, deck?, slide?, evidence?}` → `{ok, item, note}` — 작업 공간 세션이 엔진 요청을 큐에 넣는 길(**로컬 직접 접속만**, 허브 중계 403). 큐 파일이 작업 공간 밖이라 Codex 샌드박스가 직접 못 쓰므로 `engine_request add` 가 서버가 떠 있으면 이리로 온다(0.22.27). 늘 `session`(triage) |
| `POST /api/requests/<id>` | `{"action": "add"\|"update"\|"delete"\|"send"\|"discard", …}` — add 는 `status`(draft/open)·`region`·`attachments`(아래 attach 로 올린 것만, 최대 10), send = 초안→대기(slide 생략 시 전체), discard = 초안 지우기, update 는 `status`·`reply`·`text`·`attachments`, delete 는 첨부 파일도 지운다 |
| `POST /api/attach/<id>` | 요청 첨부 올리기 `{name, type, data(base64)}` → `{path, name, type, size, url}`. 그림(png/jpg/gif/webp/svg)·PDF·글(txt/md/csv/json)·pptx/docx/xlsx, 12MB 까지. 파일은 `out/attach/<덱>/<시각>.<확장자>`(작업 공간 안, git 제외), 편집기는 `url`(`/out/attach/…`)로 본다 |
| `POST /api/export/<id>` | 문서 종류별 내보내기 → `{ok, path, url, name, …}`. 슬라이드 = PPTX(`?pdf=1` PDF - Windows 에서 PowerPoint(`render_pptx.ps1`), 없거나 실패하면 Chrome/Edge 로 `print.html` 인쇄, 응답 `via: "powerpoint"\|"chrome"`, 둘 다 안 되면 500 · `?layout=notes\|h2\|h3\|h6` 노트·유인물은 Chrome 만 · `?embed=1` 글꼴 포함 PPTX, 작업 공간 글꼴이 설치 안 됐으면 409 `needInstall` - `&install=1` 로 설치). 시트 = `out/<id>.xlsx`(매크로가 있으면 .xlsm, `?macros=0` 이면 빼고 .xlsx - [sheets.md](sheets.md)). 페이지 = `out/<id>.docx`(`export_docx.py`), `?pdf=1` 이면 PDF - Windows 에서 Word(`render_docx.ps1`, 응답 `method: "word"`·`pages` = 쪽 수) 우선, 없거나 실패하면 Chrome/Edge 로 `page.html?print=1` 인쇄(`method: "chrome"`, `pages: null`), `?via=chrome` 이면 Chrome 만(그 밖의 `via` 값은 무시 - Word 우선). 둘 다 안 되면 501 `needPrint`([pages.md](pages.md)). 슬라이드의 `via` 는 요청 인자가 아니라 응답 필드다 |
| `GET /api/render/<id>` | 마지막 PowerPoint 렌더 PNG 목록 |
| `POST /api/render/<id>` | PPTX 생성 + PowerPoint COM 렌더(Windows, 한 번에 하나 — 겹치면 429) |
| `GET /api/layouts` | 레이아웃 목록 |
| `POST /api/newslide` | `{layout, part}` → 자리 표시 내용으로 만든 슬라이드 |
| `GET /api/fonts` · `POST /api/fonts` | 글꼴 프리셋 목록·현재 값 / `{preset}` 으로 전환 |
| `GET /api/fontfile/<이름>` | 설치된 OFL 글꼴 파일(편집기 `fonts.css` 용) |
| `GET /api/config` | `mode`(`workspace`·`hub`) · 작업 공간 이름·경로(`path`)·포트·제목·템플릿(`template`)·로그인 사용자(`user`)·켜진 기능(`experimental`, 예 `["page"]` - 화면이 "페이지" 선택지를 보일지)·브랜드(로고·워드마크·파비콘·로고 비율). 허브면 `brand` 는 비고 `refused`(엔진 안이라 열지 않은 작업 공간) |
| `GET /api/agent` | AI 세션 어댑터 확인 — `{agents: {claude, codex: {installed, loggedIn, version, verified, hint, doc, flags, models}}, agent, model, sources, limits}`(전역 < 작업 공간 우선순위, `?refresh=1` 로 다시 확인). [dev/web-session-design.md](dev/web-session-design.md) |
| `GET /api/wsession` | 웹 AI 세션 상태 — `{state: off\|ready\|running\|error, agent, model, modelActual, sessionId, startedBy, startedAt, turns, lastError, open, working, manual, limits, seq, last}`. 작업 공간 서버에서만(허브는 404 — 중계 `/w/<이름>/api/wsession`) |
| `POST /api/wsession` | `{"action": "start", agent?, model?, saveAs?: "local"\|"shared"}` · `{"action": "stop"}` · `{"action": "model", model, saveAs?}`(실행 중이면 턴이 끝난 뒤 적용) · `{"action": "defaults", sessionAgent?, sessionModel?, saveAs?}`. 로그인 사용자 누구나. 수동 감시가 살아 있거나 PC 동시 세션 한도(`sessionMax`)면 400 |
| `GET /api/wsession/events?since=N` | 진행 이벤트 — `Accept: text/event-stream`(또는 `?sse=1`)이면 **SSE**(`id`=seq, `event`=종류, `data`=JSON, 25초마다 `: keepalive`, `Last-Event-ID` 로 놓친 것부터 재개), 아니면 폴링 JSON. 종류: `state`·`turn.start`·`init`·`text`·`tool`·`tool_result`·`turn.end`·`warn`·`error`·`model`·`idle`. 중계(`/w/<이름>/…`)는 이벤트 스트림을 줄 단위로 바로 흘린다 |
| `GET /api/wsession/log?turn=N` | 그 턴의 어댑터 출력 원문 |
| `GET /api/engine` | (허브) 엔진 개발 — `{session, counts, recent, git: {engine, main, branch, head, ahead, worktreeExists}}` |
| `GET /api/engine/requests?status=` · `POST /api/engine/requests` | 엔진 요청 큐 — `{"action": "add", title, body, …}`(로그인 사용자 누구나) · `{"action": "status", id, status, reply?, commit?, appliedCommit?}`·`priority`·`remove`(관리자). 상태 `triage→open→working→done→applied`·`rejected` |
| `GET /api/engine/session` · `POST /api/engine/session` · `/events` · `/log` | 엔진 개발 세션(허브, `wsession.EngineProfile`) — `/api/wsession` 과 같은 꼴. start/stop/model 은 **관리자만** |
| `GET /api/session` | Claude 세션 연결 상태 `{connected, label, mode, last_seen, age, open, working}` |
| `POST /api/flush/<id>` | "지금 보내기" — 감시 스크립트가 대기 없이 열린 요청을 바로 전달 |
| `GET /api/history/<id>` | 자동 백업 목록 `[{file, kind(save/build/ext), at, size}]` · `?f=<파일>` 이면 그 시점 덱 JSON |
| `GET /api/templates` | 템플릿 목록과 선택된 템플릿 |
| `GET /api/page-templates` · `/api/page-templates/<이름>` | 페이지 템플릿 목록(이 작업 공간에서 자주 쓴 것 넷까지 앞 - `used`·`rec`) · 그 템플릿 문서. 작업 공간 서버만 |
| `GET /api/sheet-themes` · `/api/sheet-themes/<이름>` · `GET /api/sheet-preview?key=` · `GET /api/sheet-range?deck=&tab=&range=` · `GET /api/vba/<id>` | 시트 테마 · 테마 미리 보기(파일 쓰지 않음) · 시트 → 슬라이드 연결 데이터 · VBA 모듈 - [sheets.md](sheets.md) |
| `GET /api/stream/<id>?tab=` · `POST /api/presence/<id>` | 실시간 - 탭당 SSE 하나(`version` · `presence` · `ping`) · 함께 보는 사람 `{tab, where, editing}`(`{leave: true}` 로 뺀다) - [collab.md](collab.md) 2단계 |
| `POST /api/ops/<id>` | 작업(op) 저장 `{base, ops}`(최대 2,000개) - 편집기·시트가 큰 문서를 저장할 때. 페이지 문서는 400(화면이 `PUT ?merge=1` 로 보낸다) - [collab.md](collab.md) 3-4 |
| `GET /api/proposals/<id>[?request=]` · `POST /api/proposals/<id>` | AI 제안 - 목록·하나(기준본·AI 사본) · `{action: create\|accept\|discard, request, …}` - [collab.md](collab.md) 3단계 |
| `GET /api/reqdiff/<id>?request=` | 요청 하나로 AI 가 바꾼 셀 `{found, cells, count, saves?, seq?}`(요청 카드의 "바뀐 셀 n개") |
| `GET /api/home` · `POST /api/project` · `POST /api/settings` · `GET /api/fs` · `GET /api/preview` | 시작 페이지 - [home.md](home.md#api) |
| `GET /api/check/<id>` | 레이아웃 검사 결과 `{issues[{rule, severity, slide, n, elements, box, message, detail}], errors, warnings, minFontPt}` |
| `GET /api/share?ws=&deck=` · `POST /api/share` · `POST /api/share/<id>` | (허브) 보기 전용 공유 링크 목록 · 만들기 `{action: "create", ws, deck, days?, password?}` → `{link, token, url}` · 회수 `{action: "revoke"}` — [auth.md](auth.md#api) |
| `GET /api/fontcss` | 작업 공간 `fonts/` 의 `@font-face` — `X-Forwarded-Prefix`(중계 `/w/<이름>`·공유 `/s/<토큰>`)가 있으면 `/wsfonts/` 앞에 붙인다 |

## 요청 메모 파일

`decks/<id>.requests.json` — 배열.

```json
[{"id": "r20261001172030123", "slide": "s05", "element": "e03", "text": "표를 두 장으로 나눠 줘",
  "status": "open", "reply": "", "created": "2026-10-01T17:20:30"}]
```

`status`: `draft`(초안 — 편집기에서 보내기 전) → `open`(대기) → `working`(세션 처리 중) → `done`(완료). 그리기 모드 요청은 `region`(슬라이드 좌표)을 가진다.

## 동시 편집

- 편집기는 편집 0.7초 뒤 `PUT ?base=<읽은 버전>` 으로 저장한다. 그사이 파일이 바뀌었으면 409 → "외부 버전 불러오기 / 내 편집으로 덮어쓰기" 선택.
- 밖에서(Claude 등) 덱 파일을 고치면 편집 중이 아닐 때 2초 안에 자동으로 다시 불러온다(Ctrl+Z 로 되돌리기 가능).
- 편집기·시트·페이지 화면은 `PUT ?merge=1` 로 저장한다 - 그사이 다른 저장이 있었으면 서버가 기준본 · 보낸 것 · 지금 파일을 3-way 병합한다(서로 다른 장·요소 · 탭·셀 · 블록을 고쳤으면 둘 다 남고, 같은 곳이면 사람끼리는 나중 저장, AI 저장이면 사람이 이긴다). 응답에 `merged`·`conflicts` 가 붙고 진 값은 원장에 남는다. 기준본을 모르면 409 로 위의 선택이 뜬다. 자세히 [collab.md](collab.md).
