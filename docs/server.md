# 서버

## 실행

```bash
python3 studio/service.py --workspace <작업 공간> start|stop|restart|status|url   # 백그라운드 서비스(권장)
python3 studio/server.py  --workspace <작업 공간> [--port N | --port auto] [--force] # 앞에서 실행
python3 studio/service.py start                                                    # 작업 공간 밖에서 → 시작 페이지(허브, 5599)
```

- 작업 공간 없이 띄우면 **허브**(시작 페이지)로 뜬다. 실행 정보·로그는 사용자 설정 폴더 `hub/.studio/` - [home.md](home.md).

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

보안 범위:
- 점(`.`)으로 시작하는 경로 조각은 모두 403 — `out/.studio`(세션 상태)·`decks/.history`·`.env` 등.
- 각 경로는 그 기준 폴더 밖으로 나갈 수 없다(`..` 정규화 후 검사, 403).
- `assetRoot` 아래 파일은 읽기 가능하다. 저장소 전체를 `assetRoot` 로 잡았다면 그 저장소 파일이 로컬에서 보인다는 뜻이다(127.0.0.1 전용).

## API

| 메서드 · 경로 | 설명 |
|---|---|
| `GET /api/decks` | 덱 목록 `[{id, title, slides, updated, version}]` |
| `GET /api/deck/<id>` | 덱 JSON. 헤더 `X-Deck-Version` = 파일 mtime_ns |
| `PUT /api/deck/<id>?base=<ver>` | 덱 저장 — 원자적 쓰기, 저장 전 `.history` 백업(50개 유지). `base` 가 현재 버전과 다르면 **409**(`force=1` 이면 무시) |
| `GET /api/version/<id>` | `{deck, requests, session, deckIds, decksVer, config, engine}` — 편집기가 2초마다 확인(외부 변경 감지·세션 상태·덱 목록·설정·엔진 변경 → 탭 갱신·새로 고침 안내) |
| `GET /api/requests/<id>` | 요청 메모 목록 |
| `POST /api/requests/<id>` | `{"action": "add"\|"update"\|"delete"\|"send"\|"discard", …}` — add 는 `status`(draft/open)·`region`, send = 초안→대기(slide 생략 시 전체), discard = 초안 지우기, update 는 `status`·`reply`·`text` |
| `POST /api/export/<id>` | PPTX 생성 → `{url: "/out/<id>.pptx?v=…"}` |
| `GET /api/render/<id>` | 마지막 PowerPoint 렌더 PNG 목록 |
| `POST /api/render/<id>` | PPTX 생성 + PowerPoint COM 렌더(Windows, 한 번에 하나 — 겹치면 429) |
| `GET /api/layouts` | 레이아웃 목록 |
| `POST /api/newslide` | `{layout, part}` → 자리 표시 내용으로 만든 슬라이드 |
| `GET /api/fonts` · `POST /api/fonts` | 글꼴 프리셋 목록·현재 값 / `{preset}` 으로 전환 |
| `GET /api/fontfile/<이름>` | 설치된 OFL 글꼴 파일(편집기 `fonts.css` 용) |
| `GET /api/config` | 작업 공간 이름·경로(`path`)·포트·제목·브랜드(로고·워드마크·파비콘·로고 비율) |
| `GET /api/session` | Claude 세션 연결 상태 `{connected, label, mode, last_seen, age, open, working}` |
| `POST /api/flush/<id>` | "지금 보내기" — 감시 스크립트가 대기 없이 열린 요청을 바로 전달 |
| `GET /api/history/<id>` | 자동 백업 목록 `[{file, kind(save/build), at, size}]` · `?f=<파일>` 이면 그 시점 덱 JSON |
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
