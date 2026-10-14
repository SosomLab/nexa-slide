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
- **작업 공간당 서버 하나**: 이 작업 공간 서버가 이미 살아 있으면(`out/.studio/server.json` 의 포트·설정 포트에 실제로 물어 확인) 시작을 거부하고 주소를 알려 준다(`--force` 로 무시).
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
| `/login` · `/setup` · `/account` | 허브의 로그인 · 최초 관리자 설정 · 계정(비밀번호, 관리자면 사용자 관리) — [auth.md](auth.md) |

허브의 모든 경로는 `/login`·`/setup`·`/api/auth/state`·`/api/auth/login`·`/api/auth/setup` 을 빼고 로그인 뒤에 있다. 미인증 요청은 401(API·정적·산출물) 또는 302 `/login`(페이지)이고 본문에 내용이 없다.

보안 범위:
- 점(`.`)으로 시작하는 경로 조각은 모두 403 — `out/.studio`(세션 상태)·`decks/.history`·`.env` 등.
- 각 경로는 그 기준 폴더 밖으로 나갈 수 없다(`..` 정규화 후 검사, 403).
- `assetRoot` 아래 파일은 읽기 가능하다. 저장소 전체를 `assetRoot` 로 잡았다면 그 저장소 파일이 로컬에서 보인다는 뜻이다(127.0.0.1 전용).

## API

| 메서드 · 경로 | 설명 |
|---|---|
| `GET /api/decks` | 덱 목록 `[{id, title, slides, updated, version}]` |
| `GET /api/deck/<id>` | 덱 JSON. 헤더 `X-Deck-Version` = 파일 mtime_ns |
| `PUT /api/deck/<id>?base=<ver>&origin=editor\|claude&action=save\|restore&request=&note=&label=` + 헤더 `X-Nexa-Tab` | 덱 저장 — 원자적 쓰기, 저장 전 `.history` 백업(50개 유지), **변경 원장에 한 줄**(응답 `seq`). `base` 가 현재 버전과 다르면 **409**(`force=1` 이면 무시) - [change-ledger.md](change-ledger.md) |
| `GET /api/version/<id>` | `{deck, requests, changes, session, deckIds, decksVer, config, engine}` — 편집기가 2초마다 확인(외부 변경 감지·원장 기록·세션 상태·덱 목록·설정·엔진 변경 → 탭 갱신·새로 고침 안내) |
| `GET /api/changes/<id>` | 변경 원장 - `?limit=&before=&since=&origin=&slide=&group=1&recent=1&seq=N` ([change-ledger.md](change-ledger.md#api)) |
| `GET /api/requests/<id>` | 요청 메모 목록 |
| `POST /api/requests/<id>` | `{"action": "add"\|"update"\|"delete"\|"send"\|"discard", …}` — add 는 `status`(draft/open)·`region`·`attachments`(아래 attach 로 올린 것만, 최대 10), send = 초안→대기(slide 생략 시 전체), discard = 초안 지우기, update 는 `status`·`reply`·`text`·`attachments`, delete 는 첨부 파일도 지운다 |
| `POST /api/attach/<id>` | 요청 첨부 올리기 `{name, type, data(base64)}` → `{path, name, type, size, url}`. 그림(png/jpg/gif/webp/svg)·PDF·글(txt/md/csv/json)·pptx/docx/xlsx, 12MB 까지. 파일은 `out/attach/<덱>/<시각>.<확장자>`(작업 공간 안, git 제외), 편집기는 `url`(`/out/attach/…`)로 본다 |
| `POST /api/export/<id>` | PPTX 생성 → `{url: "/out/<id>.pptx?v=…"}` |
| `GET /api/render/<id>` | 마지막 PowerPoint 렌더 PNG 목록 |
| `POST /api/render/<id>` | PPTX 생성 + PowerPoint COM 렌더(Windows, 한 번에 하나 — 겹치면 429) |
| `GET /api/layouts` | 레이아웃 목록 |
| `POST /api/newslide` | `{layout, part}` → 자리 표시 내용으로 만든 슬라이드 |
| `GET /api/fonts` · `POST /api/fonts` | 글꼴 프리셋 목록·현재 값 / `{preset}` 으로 전환 |
| `GET /api/fontfile/<이름>` | 설치된 OFL 글꼴 파일(편집기 `fonts.css` 용) |
| `GET /api/config` | 작업 공간 이름·경로(`path`)·포트·제목·브랜드(로고·워드마크·파비콘·로고 비율) |
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
| `GET /api/home` · `POST /api/project` · `POST /api/settings` · `GET /api/fs` · `GET /api/preview` | 시작 페이지 - [home.md](home.md#api) |
| `GET /api/check/<id>` | 레이아웃 검사 결과 `{issues[{rule, severity, slide, n, elements, box, message, detail}], errors, warnings, minFontPt}` |

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
- 자동 병합은 없다. 한 덱을 두 브라우저에서 열면 늦게 저장한 쪽이 충돌 알림을 받는다.
