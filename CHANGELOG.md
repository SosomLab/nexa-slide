# 변경 이력

## 0.22.33 - 2026-10-27 · 엔진 배포 진행을 단계·시험 묶음별로 · 배포 시간 단축 · 요청 전 main 따라잡기

- **진행 표시**: 펼친 배포 판에 큰 단계 표시줄(확인→병합→시험→턴 대기→main 반영→재시작→push→적용됨, 끝난 것 ✓·지금 것 돌아감), 끝난 단계마다 한 줄과 걸린 시간, 지금 단계의 경과 시간, **시험 묶음별 진행 막대·칩**(26개 묶음이 끝날 때마다 ✓/✕·초), 경과·예상 시간. 계획 판에도 예상 시간.
  `run_all` 이 묶음마다 `-- 통과|실패 <이름> <초>s` 를 바로 찍고(`--exact` 이름 그대로 고르기 추가), `engine_deploy` 가 출력을 줄 단위로 따라가 `deploy.json` 의 `tests` 에 남긴다.
- **시간 단축**(지난 배포 13분 39초):
  - 비교 시험 재실행 생략 - 병합 전 main 의 시험 기록(`test-baseline.json`)이 있으면 그것과 비교한다. 배포한 병합본의 결과가 다음 배포의 기준이 되므로 연속 배포에서는 시험을 한 번만 돈다(지난번 비교 재실행 약 5분).
  - `race` 시험 2분 15초 → 몇 초: 포트 50개를 하나씩 0.4초 기다리며 두드리던 것을 한꺼번에(Windows 는 닫힌 localhost 포트도 시간 초과까지 기다린다).
  - 문서(`docs/`·`*.md`)만 바뀐 배포는 시험을 건너뛴다.
- **엔진 세션이 요청을 처리하기 전에 `engine-dev` 를 main 으로 따라잡는다**(`wsession.EngineProfile.sync_main`, 턴마다) - 전에는 배포 끝에만 맞춰서, 터미널에서 main 에 직접 병합한 뒤 온 요청은 옛 코드 위에서 고쳐졌다. 배포 안 한 커밋이 없으면 ff, 있으면 main 병합, 충돌·커밋 안 한 변경이면 그대로 두고 세션 로그에 경고.
- README "AI 세션 준비": [세션 시작] 은 서버가 `claude`·`codex` CLI 를 직접 실행하므로 서버 PC·같은 사용자에 설치·로그인이 필요하다는 안내와 AI 별(Claude Code·Codex CLI) 펼침 단락으로 설치·로그인·확인 명령.
- `englist` 시험: 이 PC 에 없는 글꼴(Pretendard)의 `/api/fontfile` 404 를 콘솔 오류로 치지 않는다(`share` 와 같음).
- 참고(엔진 밖 환경): 운영 PC 의 Python 에 `python-pptx`·`Pillow` 가 없어 PPTX 시험 9개(deck·effect·tableobj·uxpack·chart·docstruct 등)가 0초에 실패하고 있었다 - `pip install -r requirements.txt` 로 설치했다. 운영 허브의 PPTX 내보내기도 같은 까닭으로 안 되던 상태였다. 설치 뒤 전체 시험 실패는 12개 → 4개(smoke·englist 는 Pretendard 글꼴 미설치 404, thread 는 smoke 에 딸림, editor 는 fx_test 시나리오 하나 - 모두 병합 전에도 같음).

## 0.22.32 - 2026-10-27 · 카드 배포 단추를 펼침 단추로 · 진행 중 단계 표시

- 시작 페이지 "서버 요청" 카드의 `[배포…]`(회색 기본 단추)를 주 색 **[🚀 배포 준비 ▾]** 로. 누르면 커밋·요청·[배포 시작] 판이 아래로 펼쳐지고 단추는 판과 이어진 **[▴ 접기]** 탭이 된다(`닫기` 글자 단추 대신). 진행 중이면 접힌 단추는 `배포 진행 보기`.
- 배포가 오래 걸리는 단계(병합본 시험, 병합 전 비교 시험, 렌더 동일성, 턴 대기, 허브 재시작, push)를 시작할 때 `deploy.json` 에 `cur` 를 남겨, 카드 배지 옆과 펼친 판에 "지금 하는 단계 · 시작 시각"이 보인다 - 전에는 시험 몇 분 동안 `배포 중` 만 보였다.

## 0.22.31 - 2026-10-27 · 시각 템플릿 casebook·electric(승인 참고 덱 024·025)

엔진 요청 #5(사용자: "24, 25 번 템플릿을 추가 승인했어. 선택할 수 있도록 반영해줘"). 템플릿 검토에서 승인한 참고 덱 둘을 `graphite`(참고 덱 101) 선례대로 `lecture` 바탕 시각 템플릿으로 — 색·모서리·부품만 바꾸고 레이아웃 코드는 그대로.

- **`casebook`**(024 campaign-case-study-deck — 캠페인 사례집): 따뜻한 크림 바탕, 갈색 먹 글자, 테라코타 강조 하나, 굵은 고딕 제목(명조인 `archive` 와 다름), 고정폭 키커(`labels: mono`), 어두운 사진 표지·마감 패널(`panel`), 거대 흐린 쪽번호(`pageGhost`), 작은 모서리 2·4·6.
- **`electric`**(025 campaign-strategy-deck — 캠페인 전략 기획안): 흰 바탕, 먹색 글자, 전기 파랑 강조 하나(`swiss` 의 빨강 자리), 고정폭 키커, 어두운 표지·결정 요청 패널, 모서리 없음, 바닥글은 기본 가는 줄.
- 시작 페이지·`set_template` 목록에 바로 보인다(폴더가 목록). 문서 `templates.md`·`starters.md`·README, 영어 라벨·설명 `en.js`. 검토 등록부의 "구현" 기록은 승인 상태가 운영 트리 등록부에만 있어 이 가지에서는 손대지 않았다(`/review` 메모로 남길 것).

## 0.22.30 - 2026-10-27 · 허브 페이지 새 판 안내 · 모델 목록 고성능 순(fable 별칭)

- **허브 페이지 [새로 고침] 안내**(사용자 지적: 작업 공간 편집기는 서버가 바뀌면 갱신 단추가 뜨는데 5599 시작 페이지는 반응이 없다): 편집기만 `/api/version` 의 `engine` 값으로 새 판을 알았고 허브 페이지에는 그 감지가 없었다. `/api/engine/notice`(공통 메뉴가 10초마다 부름)에 허브 화면 판 `ui`(studio/*.html·*.js·i18n/*.js 최신 수정 시각)를 싣고, `menu.js` 가 처음 본 값과 달라지면 하단에 "화면이 새 판으로 바뀌었습니다 [새로 고침] ✕" 를 띄운다(시작 페이지·/engine·글꼴·계정 등 메뉴가 있는 허브 페이지 모두, 중계 편집기 /w/… 는 제외 - 자기 안내가 있다). 배포·병합으로 화면 파일이 바뀌면 열린 창이 옛 스크립트로 남던 것(입력란 수정이 안 보이던 원인)을 알 수 있다. 시험 `englist_test` 에 notice.ui 변화.
- **Claude 모델 목록**: `["fable", "opus", "sonnet", "haiku"]` - 고성능 순, Fable 은 전체 ID 대신 별칭 `fable`(CLI 2.1.308 에서 `--model fable` → claude-fable-5-1 실측). 판을 고정하려면 세션 시작 창의 직접 입력. 기본 선택은 그대로 opus.

## 0.22.29 - 2026-10-27 · 엔진 배포 - 카드 [배포] 로 병합·시험·재시작·push·적용됨

사용자 지적(2026-10-27): 관리자로 로그인했는데도 승인한 엔진 요청이 main·운영에 반영되지 않는다 - 엔진 세션은 규약상 merge·push·재시작이 막혀 있고(요청 #4 거절), 허브에는 그 단계를 실행할 기능이 없었다. 사람 승인은 두고 실행만 자동으로 바꿨다. 설계 `docs/dev/engine-deploy-design.md`.

- **`studio/engine_deploy.py`**: `plan`(들어갈 커밋·요청·파일·막는 이유) · `run`(시험용 worktree 에서 `--no-ff` 병합 → `run_all` 후 실패 묶음만 병합 전 main 에서 다시 돌려 새 실패만 막음 · 렌더 파일이면 `check_parity` → 처리 중 턴 대기 → 운영 트리 ff → 허브 재시작·생존 확인(실패하면 `reset --keep` 후 재시작 = rolledback) → 떠 있던 작업 공간 서버 재시작 → push → done 요청 applied(병합 커밋·판) → engine-dev ff) · `status`. 허브가 떼어 낸 프로세스로 실행해 허브 재시작에도 끊기지 않는다. 기록 `hub/engine/deploy.json`·`deploy-logs/`.
- **API**: `GET /api/engine/deploy`(계획+기록, `?fetch=0` 기록만) · `POST /api/engine/deploy {action: run}` - 관리자만, 엔진 세션 턴 처리 중이면 409, 시작 전에 웹 엔진 세션을 끈다. `GET /api/engine` 에 `deploy`(관리자).
- **카드**: 완료 요청·앞선 커밋이 있으면 `[배포…]` - 요청·커밋·파일·막는 이유·순서, [배포 시작], 단계별 진행(✓/✕)·마지막 배포 배지. 손으로 하는 [적용됨]은 그대로 남김.
- 시험 `engine_deploy_test`(임시 저장소 + bare origin: 계획·병합 커밋·push·applied·engine-dev 맞춤·충돌 시 main 불변·겹치는 미커밋 변경 막음·새 실패만 막는 비교) · `englist_test` 에 배포 API 조회.
- 문서: `engine-request-design.md` 10절 결정 3 변경, `server-admin.md` 9절 카드 [배포].

## 0.22.28 - 2026-10-18 · 엔진 세션 상태 갱신을 outbox 로 · 고아 working 되돌리기 · 카드 제목 '서버 요청'

Codex 엔진 세션 둘째 운영 시험(2026-10-17 21시, 사용자 요청 #13 "카드 제목 '서버 작업' → '서버 요청'")에서: 세션이 `.nexa/engine_request.py status …` 로 큐 파일(사용자 설정 폴더)을 쓰는 것도 샌드박스 안에서 30초 넘게 멈췄고(작업 공간 세션의 `add` 와 같은 현상), 허브 재시작으로 세션이 끊기자 #13 이 `working` 으로 고아가 됐다. 0.22.27 의 반복 방지·허브 커밋은 재시작 전 세션이라 아직 적용 전이었다.

- **outbox**: worktree 의 `.nexa/engine_request.py`(세션용 실행 파일)가 `status` 를 큐에 직접 쓰지 않고 `.nexa/outbox/<id>-<ms>.json` 에 적는다(즉시 "턴 끝에 반영" 안내). 턴이 끝나면 `EngineProfile.apply_outbox` 가 시각 순으로 `engine_requests.update` 에 반영(applied 면 appliedCommit) → 이어서 허브 대신 커밋·반복 방지. `list`·`show`·`add` 는 그대로 CLI. 턴 프롬프트에 "같은 턴에서 show 로 확인해도 안 바뀐 것이 정상".
- **고아 working 되돌리기**: 새 엔진 세션 시작(`check_start`) 때 `engine_requests.reclaim_stale()` 이 남은 `working` 을 `open`(+"[세션이 끊겨 되돌림]")으로 - `awaiting` 아님이라 새 세션이 바로 받는다.
- **#13**: 시작 페이지 엔진 세션 카드 제목 `서버 작업` → **`서버 요청`**(Codex 엔진 세션이 `home.html` 수정, 커밋은 개발 세션 대행 1e83e70) + `en.js` "Server requests". 메뉴 배지·`/engine` 목록 제목·안내 문구의 "서버 작업" 은 그대로(요청 범위 = 카드 제목).
- 시험 `engine_commit_test` 에 (d) 고아 되돌리기 (e) shim → outbox → reconcile 반영·커밋 추가.

## 0.22.27 - 2026-10-17 · Codex 샌드박스에서 엔진 요청 등록 - 작업 공간 서버 경유

사용자 지적(편집기: Codex 가 "엔진 요청 등록 명령이 50초 넘게 응답 없음"). 현상: 작업 공간 Codex 세션 안에서만 `engine_request add --request … --deck …` 가 첫 시도는 멈추고 둘째는 빈 출력으로 실패했다(샌드박스 밖에서는 1초; 엔진 세션의 `status` 쓰기는 같은 큐 파일인데 된다 — 큐 파일 쓰기 자체보다 CLI 가 작업 공간 서버로 되돌아가는 `link_origin` POST 경로가 의심되나 확정하지 못함). 턴은 실패하지 않아 편집기에는 "대기 + 사유" 로만 보였다. 서버 경유로 바꾸자 같은 요청이 바로 등록됐다.

- 작업 공간 서버에 **`POST /api/engine_request`**(로컬 직접 접속만, 허브 중계 403, 허브 서버 404): `{title, body, request?, deck?, slide?, evidence?}` → `engine_requests.add(kind=session)` + `link_origin`(원 요청 배지) → `{ok, item, note}`. 접근 로그 `engine.request:<id>`. 사용자는 `X-Nexa-Session-User`(세션 CLI 가 `NEXA_SLIDE_USER` 로 보냄).
- `engine_request.py add`: 작업 공간 안(`NEXA_SLIDE_WORKSPACE`)이고 서버가 떠 있으면 그 API 로(`via_server`), 서버가 없거나 실패하면 전처럼 파일에 직접(안내 한 줄). 출력은 같다 - 턴 프롬프트·명령 파일 변경 없음.
- 시험 `engine_link_test` 에 API·CLI 경유 등록 검사. 문서 `openai-codex.md`·`server.md`.
- **Codex 엔진 세션(서버 작업)**: 샌드박스가 `.git` 쓰기를 막아 worktree 에서 `git commit` 이 'index.lock: Permission denied' 로 실패한다(`--add-dir`·`writable_roots` 로도 안 풀림, 실측). → 엔진 턴 프롬프트 `{commit}` 자리에 Codex 용 안내(커밋하지 말고 `--commit auto`), 턴이 끝나면 **허브가 worktree 변경을 대신 커밋**(`EngineProfile.commit_for`: `engine-request #<n>` 메시지, 해시를 큐에 적음). 또 세션이 스스로 `open` 으로 되돌린 항목(질문·실패)을 큐가 턴마다 다시 보내 **같은 요청을 무한 반복**(#11 에서 턴 3~5, 토큰 280만)하던 것 — 마지막 이력이 engine-session 의 open 이면 사람이 손대기 전까지 다시 보내지 않는다(`EngineQueueSource.returned_by_session`). 시험 `engine_commit_test`.

## 0.22.26 - 2026-10-17 · 회사 템플릿 만들기 마법사 · 작업 공간 템플릿(extends+tokenOverrides)

엔진 요청 #3(협업 세션 설계 메모 `docs/dev/template-wizard-design.md`, 0절 원칙 충돌은 **안 A** 로 확정). 회사 색·로고·서체를 공개 엔진 저장소에 넣지 않고도 "회사 템플릿"을 쓸 수 있다.

- **작업 공간 템플릿**: `<작업 공간>/templates/<이름>/template.json` 하나 — 반드시 엔진 템플릿을 `extends` 하고 `tokenOverrides`(색)·`label`·`description`·`parts`(·`i18n`)만 바꾼다. `tokens`·`design`·`sizes`·`check` 는 금지(로더가 무시하고 `알림:` 경고), `extends` 가 엔진 템플릿이 아니면 `lecture` 바탕+경고, 엔진과 같은 이름은 엔진 것이 쓰인다(마법사는 생성 거부). 찾는 순서 엔진 `studio/templates/` → 작업 공간 `templates/` — `common.template_dir/template_dirs/load_template/list_templates`, `set_template`(목록에 `[작업 공간]`), `hub.templates(ws)`(그 작업 공간 서버의 시작 페이지에만 `작업 공간` 배지로), `hub.preview`(작업 공간 템플릿은 `template.json`·`assets/brand/*.png` 를 임시 작업 공간에 복사해 빌드), `init_workspace --template`, `workspace_stamp` 가 작업 공간 `templates/**.json` 도 감시. render.js 는 토큰으로 받으므로 변경 없음. **작업 공간 템플릿이 없으면 출력은 그대로**(`engine_regress` 차이 0).
- **`studio/palette.py`**(새, 순수 함수·CLI): 색 5개(주색 `primary` · 바탕 `surface` · 본문 `on-surface` · 보조 `accent1`→`day1` · `accent2`→`day2`) → `lecture/tokens.json` 의 역할 색 23개 파생 — container = 그 색을 surface 쪽으로 85%(어두운 바탕 75%), on-색 = 대비가 큰 흑/백, `on-*-container` = on-surface 쪽 60%(대비 4.5 보장 순서로 대체), `surface-dim/container/-high` 4·6·10%, `on-surface-variant` 는 대비 4.5 가 되는 데까지만 옅게, `outline-variant` 78%, `panel/on-panel`, `day3` = primary·accent2 중간. WCAG 대비 4.5:1 미만인 짝은 `warnings`. `check_layout` 의 `_lum`·`contrast` 가 여기 것을 쓴다(공식 한 곳).
- **허브 API**: `POST /api/project {action: "palette", colors}`(파생 미리 보기, 쓰기 없음) · `{action: "template", ws, name, base, colors, label?, description?, brand?{name, logo PNG(base64), wordmark?}, font?{preset} | {name, family, files{regular, bold?}}, overwrite?}` → `templates/<이름>/template.json` · `assets/brand/logo.png`(PNG 만) · `fonts/<파일>` + `nexa-slide.json` 의 `template`(·`brand`·`fontPresets`·`fontPreset`, 공유 파일에만 — `set_template` 과 같은 처리) → 응답에 만든 파일·파생 색·경고·`restart{needed, running, url, id, hubUrl}`·안내. 관리자, 또는 이 허브에서 연 작업 공간(최근 작업)에 한해 로그인 사용자(아니면 403) · 작업 공간 서버는 자기 작업 공간만. 접근 로그 `event=template.create:<작업 공간>:<이름>`. `create` 에 `wizard` 를 주면 새 작업 공간을 만든 뒤 서버를 띄우기 전에 함께 만든다(재시작 불필요).
- **시작 페이지**(`home.html`): 템플릿 탭 맨 앞 **"＋ 회사 템플릿 만들기"** 카드와 새로 만들기 ① 템플릿 격자 끝의 같은 카드 → 마법사(기반 템플릿 · 색 5개(시작값 = 기반 템플릿 색) · 로고 PNG · 회사 이름 · 글꼴(기반 세트 또는 전용 글꼴 파일 올리기) · 이름·표시 이름 · 적용할 작업 공간 · "고급" 파생값 하나씩 고치기). **브라우저 미리 보기**: 기반 템플릿의 `/api/preview` 결과에 파생 토큰을 `Render.setTokens` 로 덮어 레이아웃 견본을 그리고(색을 바꾸면 즉시), 올린 로고는 object URL 로 바꿔 보이며, 대비 경고를 띄운다. 만들면 **[지금 다시 시작]**(허브에서 `stop`→`start`; 작업 공간 서버 자신이면 `nexa.py restart` 안내) + "기존 덱의 글자 크기 하한은 `build_deck --force` 때" 안내. 새로 만들기에서는 ✎ 카드로 골라 두고 작업 공간과 함께 만든다. i18n ko/en.
- 고침: `hub.preview` 의 stamp 계산이 `int + str` 로 `TypeError` 를 내던 것(0.22.9 부터 `/api/preview` 가 500) → `str()`.
- **엔진 요청 #7(협업 세션 검토)**: 템플릿 이름이 Windows 예약 이름(`con`·`aux`·`com1`…)이면 로고를 먼저 덮어쓴 뒤 폴더 만들기에서 `NotADirectoryError` 로 끝나 반쪽 상태가 남던 것 — 예약 이름을 먼저 거부하고(엔진 이름 검사보다 앞, `con` 은 "엔진 템플릿과 같은 이름" 으로 잘못 안내되던 것도 고침), 템플릿 폴더를 **먼저** 만든 뒤 파일을 쓴다. 기존 로고·글꼴 파일과 바이트가 다르면 `out/.history/wizard/<시각>/` 에 백업하고 덮어쓴다(응답 `backups`·안내). `assetRoot` 가 작업 공간 밖이면 로고는 설정대로 그 폴더에 쓰인다(응답 `files` 에 절대 경로). **#8**: 백업 폴더가 초 단위라 같은 초에 두 번 만들면 앞 백업이 덮이던 것 — 밀리초 + 겹치면 `_2`, `_3` 순번.
- `studio/tests/smoke.js` 단계에 `shot: "<파일>"` — 그 단계 뒤 화면을 PNG 로 남긴다(사람이 보는 점검용). 임시 관리자로 마법사·공유 링크 대화상자·계정 공유 카드·보기 페이지를 헤드리스 Chrome 으로 점검해 이상 없음(계정·링크는 점검 뒤 삭제·회수).
- 시험 `template_wizard_test`(`palette` 단위 · API 로 생성 → 파일 3종 · `resolve_tokens` 색 일치 · `export_pptx --out` 의 `srgbClr` 에 primary · 엔진 이름·PNG 아님·없는 세트·이상한 이름 거부 · 금지 키 무시·경고 · 같은 이름 폴더 무시 · 전용 글꼴 → `fonts/`+`fontPresets` · 비관리자 권한 · 작업 공간 서버의 `/api/templates`·`/api/home`·`/api/preview` · 엔진 저장소 `git status` 불변), `run_all wizard`. 문서 `templates.md`(원칙 문구 — 작업 공간 템플릿은 extends+tokenOverrides 만)·`home.md`·`configuration.md`·`tests.md`.

## 0.22.25 - 2026-10-17 · 보기 전용 공유 링크

엔진 요청 #2(협업 세션 설계 메모 `docs/dev/share-link-design.md`). 로그인 없이 토큰 URL 하나로 **덱 1개를 보기만** 한다(외부 검토자·청중).

- **허브 주소 `/s/<토큰>/`**(`studio/share.py`·`server.py share_route`): `AUTH_FREE` 와 별도로 `authenticate` 전에 접두 분기. 토큰(`token_urlsafe(32)`, 파일에는 sha256 만) → 만료·회수 확인 → (비밀번호 링크면) 쿠키 `nexa_share`(무상태 HMAC, `Path=/s/<토큰>/`, 링크 만료와 세션 7일 중 짧은 쪽) → **허용 목록만** 그 작업 공간 서버로 중계(`proxy()` 재사용, `X-Nexa-User: share:<id>`·`X-Nexa-Role: viewer`): `view.html`·`render.js`·`i18n*`·`tokens.json`·`code_langs.json`·`fonts.css`·`/api/fontcss`·`/api/fontfile/*`·`/wsfonts/*`·그 덱의 `/api/deck/<덱>`(허브가 **`notes` 와 `hidden` 슬라이드를 걸러 낸다**, 보이는 장의 원래 번호는 `page`)·덱이 참조하는 그림(`src`)만. 그 밖 경로·모든 POST/PUT 은 403. 잘못된 토큰·만료·회수는 **같은 안내 페이지**(404/410 으로만 구분, 본문 같음). 로그·경로에는 토큰 대신 `/s/<id>`.
- **보기 페이지 `studio/view.html`**(새): 전체 화면 슬라이드 넘기기(← → · Home/End · 터치 밀기 · 왼쪽/오른쪽 클릭 · `#n`), 쪽 번호·전체 화면 단추, 노트·편집 UI 없음, `render.js` 재사용. 비밀번호 링크는 먼저 입력 화면. `fonts.css` 의 절대 경로(`/api/fontfile/`)를 링크 접두 아래로 바꿔 넣는다.
- **저장 `hub/share.json`**(사용자 설정 폴더, `filelock`): `{links: {<id>: {tokenHash, ws, wsId, deck, by, created, expires, pw: {hash, salt}|null, revoked, views, lastView}}}`. 비밀번호는 `auth.py` scrypt. 실패 잠금은 `auth._FAILS` 에 링크 id 키로 5회/15분(429). CLI `python3 studio/share.py list|revoke <id>`.
- **정책(전역 설정)**: 만들기는 로그인 사용자 누구나(`shareCreate: "any"`, `"admin"` 이면 관리자만), 회수는 만든 사람 또는 관리자, 관리자는 전체 목록. 만료 기본 7일·최대 `shareMaxDays`(기본 90), 영구 링크 없음.
- **UI**: Studio 내보내기 ▾ **공유 링크… (보기 전용)**(허브 경유로 열었을 때만, 명령 팔레트에도) - 만료 1/7/30일·직접, 비밀번호(선택), 만들기 → 주소 한 번만 표시·복사·열어 보기, 이 덱의 링크 목록·[회수]. `/account` 에 **공유 링크** 카드(내 것, 관리자는 전체·회수). 허브 API `GET /api/share?ws=&deck=` · `POST /api/share {action: "create", ws, deck, days?, password?}` · `POST /api/share/<id> {action: "revoke"}`. i18n ko/en.
- **접근 로그 이벤트** `share.create:<id>` `share.revoke:<id>` `share.view:<id>`(조회 수 +1) `share.auth:<id>` `share.auth.fail:<id>` `share.auth.locked:<id>` `share.denied:<id>:<expired|revoked|path|method|owner>` `share.denied:-:unknown|policy`. 토큰 원문은 어디에도 남지 않는다.
- `api_get_fontcss` 가 `X-Forwarded-Prefix` 를 읽어 `/wsfonts/` 앞에 접두를 붙인다 - `/w/<이름>/` 중계에서도 작업 공간 글꼴이 허브로 새지 않는다.
- **엔진 요청 #6(협업 세션 검토)**: 공유 토큰 원문이 허브 `server.log`(`log_message` → stderr, 정상 요청 줄 전부)와 접근 로그의 **이른 거부**(share_route 가 경로를 `/s/<id>` 로 바꾸기 전에 거절되는 잘못된 Host 400·hub-key 위조 403)에 남던 것 — `share.mask_path()` 로 두 곳 모두 `/s/-` 로 가린다. `share_test` 가 이른 거부 두 경우와 `server.log` 까지 grep 하고, 정리 단계에서 허브가 띄운 작업 공간 서버도 끝낸다.
- 문서 `auth.md`(공유 링크 절·설정·API·로그 이벤트) · `editor.md` · `server.md` · `server-admin.md` · `home.md`/`configuration.md`(설정 키) · `tests.md`. 시험 `share_test`.

## 0.22.24 - 2026-10-17 · 엔진 요청 검증 ④ - 전체 작업 공간 PPTX XML 회귀(`engine_regress.py`)

엔진 요청 #1(협업 세션 설계 메모 `docs/dev/engine-regress-design.md`). 엔진 변경이 **다른 작업 공간**을 깨는지 한 명령으로 본다.

- `studio/engine_regress.py [--base main] [--ws …] [--no-example] [--allow <덱>[:<장>]…] [--max-seconds 600] [--deck-seconds 120] [--json] [--keep]`: 사용자 설정 `settings.json` `recent` 의 작업 공간(+ 엔진 `example`)을 사용자 설정 폴더 `hub/engine/scratch/regress-<시각>/` 에 복사하고(out·.history·.studio·fonts·.git 제외, 밖을 가리키는 assetRoot·content·decks 는 사본 local 설정에 절대 경로), 기준 엔진(`git archive <base> studio` → `scratch/engine-<해시>/`, 재사용)과 지금 트리 엔진으로 덱마다 `export_pptx --out` 해 PPTX zip 의 모든 항목을 비교한다 — `docProps/core.xml`(시각) 제외, XML·rels 는 canonicalize, `presentation.xml` 구역 id 는 순번 치환, 미디어는 바이트. 차이는 **장별**(slideN·rels·notesSlideN)과 기타 부품으로 보고하고 첫 차이 줄을 보여 준다. 원본에는 쓰지 않고 사본은 끝나면 지운다.
- 판정: `--allow` 로 표시한 차이는 의도한 변경(expected). 종료 코드 0 동일/전부 의도 · 1 예상 밖 · 2 실패·시간 초과(조용히 통과하지 않는다). 이 PC(작업 공간 2 · 덱 2 · 12장) 6초.
- 규약: `engine_turn_prompt.md` 검증 단계 ④, `/nexa-slide-server`·`$nexa-slide-server`(엔진·작업 공간 명령 파일) 검증 목록에 추가 — 렌더·내보내기·레이아웃·템플릿을 건드렸으면 돌리고 결과 요약을 reply 에.
- 시험 `engine_regress_test`(엔진 복제본에서 변경 없음 0 · `lecture` 토큰 변경 → demo 7장 unexpected 1 · `--allow` · 깨진 덱 2 · 원본 mtime 불변 · 사본 정리). 문서 `tests.md`·`engine-request-design.md`.
- **최근 작업 오염 가드**(협업 세션 발견 - 시험 작업 공간 `Temp/nexa-slide-tests/…/docstruct…` 가 실제 `settings.json` recent 에 들어감): `paths.remember` 가 OS 임시 폴더 안의 작업 공간은 `NEXA_SLIDE_USER_DIR` 격리가 없으면 기록하지 않는다(격리된 시험은 그대로 기록). 원인은 시험 스크립트가 아니라 임시 작업 공간에서 격리 없이 띄운 서버·`init_workspace` 였다. 시험 `settings_guard_test`.
- **Codex 두 번째 턴 실패 고침**(사용자 지적 - 편집기에 "턴이 비정상 종료(코드 2)"): `codex exec resume` 뒤에 `--sandbox`·`-m`·`--json` 을 두면 "Usage: codex exec resume --json [SESSION_ID]" 로 거절된다 — exec 옵션을 **`resume` 앞에** 둔다(`codex exec [옵션] resume <thread_id> -`, 실측). 고친 뒤 "버전 0.5·작성자" 요청을 Codex 가 draft_deck → apply_patch → save_deck → content 반영 → done 으로 끝까지 처리함.
- **엔진 요청 #5(협업 세션 검토)**: ① Windows pyenv-win 의 `python` 래퍼(.bat)가 인자를 cmd 로 다시 해석해 여러 줄 `--body` 가 첫 줄에서 잘리고(`|| goto :error` 가 붙음) `< > | &` 가 리다이렉트가 되던 것 — `engine_request.py add --body-file <파일>|-`·`status --reply-file`, 잘린 값은 **거부**(안내), 턴 프롬프트·`CLAUDE.md` 에 주의. 그 리다이렉트로 저장소 루트에 생겨 791b652 에 섞여 들어간 빈 파일 `10.0` 삭제. ② `status <n> applied --applied-commit <해시>`(문서대로; 옛 `--commit` 도 같은 뜻), `server-admin.md` 9절. ③ `engine_regress.py` 의 기준 엔진 사본은 최근 3개만 남긴다. 시험 `engine_request_cli_test`.
## 0.22.23 - 2026-10-17 · 선·테두리 투명도 · 순서도 도형 4종

엔진 요청 #4 의 A·B(설계 메모 `docs/dev/small-items-2026-10-17.md`).

- **선·테두리 투명도**: 도형·상자·글 상자의 `stroke`, 선·화살표·곡선의 `color`, 표 셀 테두리(`borders`·셀 `bd`), 그림 액자 `frameColor` 에 `#RRGGBBAA`(끝 두 자리 = 불투명도) - 전에는 길이 7 이 아니면 **검정**이 됐다. 편집기는 `rgba()`(`render.strokeCss`), PPTX 는 `a:ln > a:solidFill > a:srgbClr > a:alpha`(`export_pptx.stroke_rgb`·`set_line_color`, 1 미만일 때만 - **불투명한 선의 XML 은 전과 바이트 동일**, example 덱 회귀 0). 채우기와 같은 규칙(`common.color_alpha` ↔ `render.colorAlpha`). 편집기 색 선택 상자는 단색 토큰만 - 투명도는 요소 JSON 으로("(직접)" 으로 보임).
- **순서도 도형 4종** `flowChartProcess`(프로세스) · `flowChartDecision`(판단) · `flowChartDocument`(문서) · `flowChartInputOutput`(데이터) - 도형 21 → 25종. 모양은 사각형·마름모·평행사변형과 비슷하지만 prstGeom 이 달라 PowerPoint 가 순서도 기호로 인식한다. 기하·글 영역은 ECMA-376 presetShapeDefinitions(문서 = 21600 격자, 밑변 (21600,17322)→(0,20172) 3차 곡선, 글 영역 높이 17322/21600 · 데이터 = 5×5 격자 평행사변형, 글 영역 w/5~4w/5). `render.js SHAPES`·`export_pptx.SHAPE_PRESETS`(`MSO_SHAPE.FLOWCHART_*`)·`common.shape_text_rect`·`import_pptx.PRST_TO_SHAPE`(왕복 이름 유지)·`studio.js SHAPE_SIZE`. 삽입 패널·속성 "도형 종류" 는 `shapeNames()` 로 자동. 편집기 이름은 "순서도: 프로세스" 식(다이어그램 "프로세스 (갈매기)"·메뉴 "문서" 와 구별, en "Flowchart: Process").
- 시험: `check_parity` 에 선 색 표본(알파 80 · 토큰 · 잘못된 값 · FF · 00 · 모르는 토큰)과 **모든 도형의 글 영역**(`render.shapeRect` ↔ `common.shape_text_rect`, 25종 × 4 크기) · `export_pptx --selftest` 에 테두리·선의 `a:ln` 안 `a:alpha`, 순서도 prst, 불투명 테두리에 alpha 없음 · `shape_menu.json` 21→25 · `editor_ui_test` 도형 목록. 문서 `deck-format.md`·`editor.md`·`pptx-feature-gap.md`(두 항목 완료)·`web-session-design.md`.

## 0.22.22 - 2026-10-17 · Codex 웹 세션 실동작 · Codex 스킬 $nexa-slide-session / $nexa-slide-server

사용자 요청("Codex 로 작업 폴더 세션·서버 작업 세션을 만들어 동작", "VS Code 의 `/nexa-slide-server`·`/nexa-slide-session` 처럼 Codex 에서도"). 작업 공간 `테스트1` 에서 Codex 웹 세션 턴을 끝까지 확인(Windows · codex-cli 0.163 · gpt-6-luna).

- **Codex 어댑터 결함 셋 고침**(`studio/agents/codex.py`): ① `turn_cmd()` 가 wsession 이 넘기는 `allow_web`·`add_dirs`·`new_session_id`·`name` 을 받지 않아 첫 턴이 `TypeError` 로 끝나던 것(`base.py` 서명도 맞춤) ② Windows 에서 chocolatey·npm 판 `codex.exe` 옆에 `codex-code-mode-host.exe` 가 없어 명령 실행이 전부 "fail closed" 되던 것 — `executable()` 이 host 가 있는 **데스크톱 앱 동봉 CLI**(`%LOCALAPPDATA%/OpenAI/Codex/bin/<해시>/codex.exe`)를 우선하고 probe 가 `codeModeHost`·안내를 준다 ③ `--ignore-user-config` 가 `[windows] sandbox = "elevated"` 까지 버려 기본 샌드박스가 `CreateProcess` 실패하던 것 — 사용자 `config.toml` 의 값을 읽어 `-c windows.sandbox=…` 로 넘긴다(없으면 elevated). `verified = True`, 기본 모델 목록 `gpt-6-luna`.
- **턴 프롬프트 `{shell}` 자리**(`turn_prompt.md`·`engine_turn_prompt.md` + `Agent.shell_note`): Claude 용 "다른 Bash 는 거절 · Edit 로 고친다" 문구를 Codex 가 그대로 믿고 "파일 도구가 없다"며 멈추던 것 — Codex 에는 "Read 는 셸 읽기, Edit 는 `apply_patch`, 작업 공간 안은 셸로 읽고 고쳐도 된다" 를 넣는다.
- **Codex 스킬**: 엔진 저장소 `.codex/skills/nexa-slide-server/SKILL.md`, 작업 공간에는 `init_workspace.ensure_codex_skills`(새 작업 공간·`update_launcher`, 저장소형이면 루트에도)가 `.codex/skills/nexa-slide-session/`·`nexa-slide-server/` 를 둔다 — Codex 대화창에 `$nexa-slide-session`/`$nexa-slide-server` 한 줄로 Claude 의 슬래시 명령과 같은 연결. Monitor 가 없으므로 **1회 대기 명령 반복**: `watch_requests --ttl 600`(요청 묶음을 내고 끝남 / `ttl`) · `watch_engine_requests --wait --ttl 600`(**새 `--wait`** — 요청이 생길 때까지 기다렸다가 한 건 내고 끝남 / `expired`). `.gitignore` 에 `.codex/*` + `!.codex/skills/`.
- 문서 `openai-codex.md`(Windows 주의·스킬·확인됨 표), `claude-session.md`. 시험 `codex_adapter_test`(설치 없이: 인자·실행 파일 고르기·windows.sandbox·`{shell}`) · `e3` 재확인. VS Code 작업 공간 설정 `.vscode/settings.json`(git 제외)에 pyenv 인터프리터 경로.

## 0.22.21 - 2026-10-16 · 노트 패널 재배치

- **노트 패널**(사용자 지적 - ✨ 칩과 입력 칸이 너무 붙어 있음): 위 줄은 **발표자 노트 · 글자 수**(왼쪽)와 **✨ 이 장 노트 쓰기 · ✨ 빈 노트 모두 쓰기 · 지우기**(오른쪽, 지우기는 노트가 있을 때만), 아래 입력 칸은 남은 높이를 다 쓰는 세로 배치. 아래 패널 기본 높이 98 → 132(최소 72, `LAYOUT_VER` 3 으로 저장된 높이 초기화). 입력 중 제목 옆 글자 수·탭 배지·지우기 표시를 같이 갱신. 안내 문구를 "이 슬라이드에서 말할 내용 - PPTX 노트·발표자 보기에 들어간다"로.
- 점검: 입력 → 저장 대기·PPTX 노트·발표자 보기·노트 페이지 PDF 경로, ✨ 칩 → 세션 요청(`quickRequest`) 확인. `ux7_test` 에 노트 단계.

## 0.22.20 - 2026-10-16 · 셀 편집 캐럿 위치 고침

- **셀 더블클릭 직후 캐럿이 여백 밖(셀 왼쪽 끝)에 붙던 문제**(사용자 지적 - 글을 치기 시작해야 제자리로 옴): 편집 상자를 flex 로 세로 가운데 맞추던 것을 블록으로 바꾸고 위 여백을 `(행 높이 − 줄 높이)/2`(셀 `valign` 위/아래면 그에 맞게)로 계산 - 빈 상자에서 Chrome 이 flex 컨테이너의 캐럿을 여백을 무시하고 그리는 동작을 피한다. 셀 `pad`·`align` 도 편집 상자에 반영. `ux7_test` 에 빈 셀 편집 단계.

## 0.22.19 - 2026-10-16 · 표 오른쪽 클릭 메뉴 · 띠 끌어 행/열 옮기기 · 덱 탭 메뉴 정리

- **표 오른쪽 클릭 메뉴**(사용자 요청): 표 안을 오른쪽 클릭하면 그 셀을 고르고(이미 고른 범위 안이면 범위 유지) 메뉴 앞에 셀 기준 항목 - **행 위/아래에 삽입 · 열 왼쪽/오른쪽에 삽입 · 행/열 삭제**(여러 줄이면 "행 n개 삭제") · **셀 병합/병합 풀기 · 셀 비우기 · 셀 서식 지우기**(덧씌우기·셀 객체 서식만 지우고 글은 유지) · **셀 글 편집 · 행/열/표 전체 선택 · ↕ 행 높이를 글에 맞춤**. 렌더 표·표 객체 모두.
- **띠 끌어 행/열 옮기기**: 이미 고른 열(행)의 띠(파란 표시, `grab` 커서)를 끌면 놓을 자리에 파란 선이 뜨고 놓으면 그 자리로 **순서가 바뀐다** - 렌더 표는 `rows`·`colW`/`rowH`·`colFont`·`align` 과 `cellFill`·`borders`·`merge` 좌표를 같이 옮기고, 표 객체는 `rows`/`cols`/`cells`. 되돌리기 가능(토스트에 안내). 고르지 않은 띠를 끌면 전과 같이 범위 선택.
- **덱 탭 오른쪽 클릭 메뉴**: "새 덱"을 맨 끝(구분자 뒤)으로.
- 시험: `ux7_test`(메뉴 항목·삽입 → 행/열 +1·띠 끌어 첫 열을 끝으로·Ctrl+Z).

## 0.22.18 - 2026-10-16 · 표 이동 손잡이·행/열 띠·경계 끌기·행 높이 맞춤·줄무늬 · 그림 톤 · 도형 광선/부드러운 가장자리

- **표 이동**(사용자 지적 - 표 안이 셀 선택이 되자 옮기기 어려움): PowerPoint 처럼 **바깥 점선 띠(10px)와 왼쪽 위 ✥ 손잡이**를 끌면 표가 움직이고, **Alt+끌기**도 이동. 표 안은 셀 선택(가장자리 여유 2px).
- **행/열 띠**: 표 위·왼쪽의 얇은 띠를 누르면 열·행 전체 선택(끌면 여러 줄, Shift 범위, Ctrl 더하기). **경계 끌기**: 안쪽 열·행 경계를 끌어 이웃 열 폭·행 높이를 바꾼다(표 크기는 그대로, `colW`·`rowH`/`cols[].w`·`rows[].h`). **↕ 글에 맞춤**(서식 줄·속성): 셀 글 양을 재서 행 높이를 다시 나누고 표 높이를 맞춘다.
- **줄무늬** `banding`(렌더 표)·`style.banding`(표 객체): 본문 둘째 행부터 한 줄 걸러 `bandFill`(기본 `surface-container`) - 두 렌더러·PPTX 같은 규칙.
- **그림 톤** `tone`: 흑백(`a:grayscl`)·흐리게(`a:blur`)·어둡게(`a:lum`)·세피아(`a:duotone`) - 편집기 CSS filter, 속성 "톤".
- **도형 광선·부드러운 가장자리**: rect·ellipse·pill·text·shape 에 `effect: glow|softEdge`(+`effectLevel`·`effectColor`) - 속성 "효과", PPTX `a:effectLst`.
- 시나리오 `ux6_test`.

## 0.22.17 - 2026-10-16 · 표 객체(table-obj) · 캔버스 셀 선택·셀 편집·셀 서식 · 렌더 표 ↔ 표 객체 상호 변환

`docs/dev/table-model-design.md` 를 사용자 방향(렌더 표는 유지하고 표 객체를 따로 두되 서로 변환)으로 구현. 편집기 시나리오 `ux5_test`, 시험 `tableobj_test`, `check_parity` 에 표 객체·변환 왕복 예제.

- **표 객체** 요소 `table-obj`: 표 → 행(`h`·`header`·행 기본 서식) → 셀(`{v, fill, color, bold, italic, align, valign, font, size, pad, bd, span}` 또는 문자열)의 중첩 구조, 열 `cols[{w, font, align}]`, 표 기본 `style{headFill, headColor, rule, gridLines, size, font, color, header}`. 우선순위 셀 > 행 > 열 > style. 두 렌더러(`common.table_obj_grid` ↔ `render.tableObjGrid`)가 같은 격자로 풀고, PPTX 는 셀마다 크기·세로 정렬·여백·기울임·채움·테두리·병합(`gridSpan`)을 쓴다. ＋ 추가 "표 객체" 타일.
- **상호 변환**: 렌더 표 → 표 객체(`table_to_obj`/`tableToObj` - 글·열 폭·열 글꼴·정렬·행 높이·머리·셀 채움·테두리·병합 그대로), 표 객체 → 렌더 표(`obj_to_table`/`objToTable` - 셀·행 단위 글자 서식은 버리고 버린 목록을 안내). 서식 줄 "⇄ 객체/렌더", 속성 탭 단추, 오른쪽 클릭 메뉴. 렌더 표에서 셀 글자 서식(색·굵게·크기·세로·기울임)을 넣으면 **자동으로 표 객체로 바뀐다**(채움·테두리·병합은 렌더 표의 덧씌우기로 그대로).
- **캔버스 셀 선택**(렌더 표·표 객체 공통): 고른 표 안을 누르면 셀, 끌면 범위, Shift+클릭 범위, Ctrl+클릭 더하기/빼기(가장자리 6px 는 표 이동). 방향키로 셀 커서(Shift = 범위), Tab/Shift+Tab 옆 셀(마지막이면 행 추가), Delete 비우기, Enter/F2·두 번 클릭 = **그 셀만 편집**(Tab 으로 다음 셀 계속), Esc 셀 선택 해제. 셀 서식 줄: 채우기·글자색·굵게·기울임·가로 3·세로·크기·테두리(변 고르기·굵은 위 선·지우기)·병합/풀기·고른 셀 기준 행/열 삽입·삭제. 속성 탭에 고른 셀 안내.
- 표 속성 공통: 행·열 삽입·삭제가 렌더 표의 덧씌우기(cellFill·borders·merge) 좌표를 같이 옮긴다. 찾기/바꾸기·유형 바꾸기(내용 옮김)·서식 복사가 표 객체도 다룬다. `check_layout` 는 표 객체의 가장 작은 셀 크기로 최소 글자 검사.

## 문서 - 2026-10-16 · 표 셀 선택·중첩 모델 검토

- `docs/dev/table-model-design.md`: 캔버스 셀 선택(클릭·끌기·Shift/Ctrl·행/열 띠·셀 단위 편집·탭 복사/붙여넣기)과 PowerPoint 식 표 → 행 → 셀 중첩 모델(간결형 `string[][]` 과 상호 변환, 우선순위 셀 > 행 > 열 > 표) 설계·단계·비용(P1 M~L · P2 L · P3 M, 합계 4~6일)·위험 - 사용자 결정 대기.

## 0.22.16 - 2026-10-16 · 덱 탭(긴 제목 말줄임·끌어서 이동·☰ 덱 목록·새 덱 메뉴) · 메뉴 줄임표 제거

- **덱 탭**: 긴 제목은 앞에서부터 20em(한글 약 20자·영문 약 40자)까지 보이고 끝은 …(제목 전체는 툴팁). 탭 줄은 스크롤바 없이 **끌어서**·휠·‹ › 화살표(넘칠 때만 보임)로 좌우 이동하고, 덱을 바꾸면 그 탭이 보이게 맞춘다. 맨 앞 **☰ 덱 목록** 단추 - 드롭다운(★ 시작 덱·✓ 지금 덱·장 수)에서 골라 이동, 맨 아래 "새 덱". 덱 탭 오른쪽 클릭 메뉴에 **새 덱** 복원.
- **메뉴 줄임표 제거**(사용자 지시): 제목 바꾸기·복제·덱 삭제(휴지통)·유형 바꾸기·아래에 새 슬라이드·다른 덱에서 장 가져오기·차트 데이터 표로 편집·턴 로그·웹 세션 시작·모델 바꾸기·글꼴 설정 보기·수정·그림 파일·다이어그램 코드·▦ 표로 편집·그림 바꾸기·다이어그램 코드 수정·직접 입력(시작 페이지 포함). 관례상 "…"은 "눌러도 바로 실행되지 않고 창·입력이 더 열린다"는 표시였는데, 이 편집기는 모든 창이 Esc 로 닫히고 되돌릴 수 있어 표시를 뺐다. 영어 사전 키도 같이 갱신. 시나리오 `ux4_test`.

## 0.22.15 - 2026-10-16 · 내용 유지 유형 전환 · 입력 중 넘침 경고 · 섹션 접기 · 차트 데이터 표 · 자동 정리 · UI 다듬기

`docs/dev/feature-comparison.md` 의 M 묶음. 편집기 시나리오 `ux3_test`.

- **유형 바꾸기**가 내용을 옮긴다(`carryContent`): 같은 역할의 글(제목·부제·라벨·각주), 첫 글머리·표·차트·코드·그림(로고 제외), 글머리가 없는 유형이면 본문 글자 상자로, 표만 있던 장을 글머리 유형으로 바꾸면 행을 항목으로. 섹션·숨김도 유지. 안내 토스트에 옮긴 것을 적는다.
- **입력 중 넘침 경고**: 글자 편집 중 상자 높이보다 글이 길어지면 상자 아래에 "넘침 예상 +Npx"(차단하지 않음).
- **섹션 접기**: 왼쪽 레일에 구분 머리(슬라이드 `section` 또는 장 표지 레이아웃) - 누르면 그 구분의 장을 접고(장 수 표시) 다시 누르면 펼침(브라우저 기억, 덱별).
- **차트 데이터 표**: 차트 속성 "▦ 표로 편집…" - 범주 × 계열 격자에서 셀 편집, 행·열 추가/삭제, 적용(데이터 모델은 그대로). 팔레트 "차트 데이터 표로 편집…".
- **⚒ 자동 정리**(검사 탭·팔레트): AI 없이 - 슬라이드 밖 요소를 안으로, 글자 높이·폭이 넘치는 상자를 자리가 있는 만큼 늘린다. 저장·재검사 뒤 적용, Ctrl+Z 되돌림.
- UI 다듬기(캡처 점검): 속성 라벨 줄바꿈 없이(이 장 글꼴·덱 글꼴·섹션·대체 글), 글자 절의 긴 표기 안내는 ⓘ 툴팁으로, 삽입 타일 라벨 두 줄, 차트 이름 짧게(세로 100%·누적 가로·콤보 막대+선), 내보내기 메뉴 구분선, 오른쪽 클릭 "서식 적용"은 복사한 서식이 있을 때만, Ctrl+H 는 입력 칸에서도.

## 0.22.14 - 2026-10-16 · 편집 편의 묶음 - 찾기/바꾸기 · 서식 복사 · 다른 덱에서 장 가져오기 · 유인물·노트 PDF · 대체 텍스트·대비 검사 · 발표 펜·레이저 · 노트 칩

`docs/dev/feature-comparison.md` 의 S 묶음(사용자 "구현 가능한 기능은 바로 진행" 지시). 편집기 시나리오 `ux2_test`, 시험 `uxpack_test`.

- **찾기/바꾸기** `Ctrl+H`(팔레트 "찾기/바꾸기"): 덱 전체의 글·글머리(하위 포함)·표 셀·실행계획 표·차트 제목/범주/계열·묶음 안 요소·노트. 찾기는 공용 NexaSearch(퍼지, Aa/ab/.* 토글), 바꾸기는 글자 그대로(또는 정규식). 결과를 누르면 그 장·요소로, "이것만"/"모두 바꾸기"(Ctrl+Z 되돌림).
- **서식 복사** 🖌(서식 줄·오른쪽 클릭·`Ctrl+Shift+C`/`V`): 요소 종류별 서식 키(글자류 크기·굵게·색·글꼴·정렬·채우기·테두리·모서리·그림자…, 선 색·두께·점선·화살, 표 머리·격자, 그림 효과…)를 복사해 누른 요소에 적용, 🖌 두 번 클릭 = 여러 요소에 계속. **기본 서식**: 오른쪽 클릭 "이 서식을 새 ○○ 요소의 기본으로" → 이후 ＋ 추가 때 적용(브라우저 기억).
- **다른 덱에서 장 가져오기…**(썸네일 메뉴·팔레트): 덱 고르기 → 장 체크 → 지금 장 다음에(슬라이드 id 새로, 숨김 해제).
- **표·차트 데이터 칸**: Excel 에서 붙여 넣은 탭 구분 줄도 칸으로 읽는다.
- **그림 대체 텍스트** `alt`(속성) → 편집기 `<img alt>`·PPTX `descr`(없으면 빈 값). **검사 규칙** `t6.contrast.low`(글자색 ↔ 채우기/슬라이드 배경 대비 < 3:1, WARNING)·`t7.alt.missing`(INFO - 목록에만, 건수·고치기 요청에서 제외).
- **유인물·노트 PDF**: 내보내기 ▾ "유인물 PDF - 쪽당 3장 + 메모 줄 / 6장", "노트 페이지 PDF"(`print.html?layout=h3|h6|notes`, A4 세로, Chrome 으로만, 파일 꼬리 `-handout3`·`-handout6`·`-notes`).
- **발표 중** `Ctrl+P` 펜(장 넘기면 지움) · `Ctrl+L` 레이저 · `E` 지우기. 글 편집·노트·메모에 브라우저 맞춤법 검사 켬.
- **AI 세션 칩**: 글자 빠른 칩에 "비즈니스 어투로·영어로 번역·다른 표현 2안", 글머리에 "더 짧게·비즈니스 어투로"; 노트 탭에 "✨ 이 장 노트 쓰기 / 빈 노트 모두 쓰기"(본문 불변). 레이아웃 고치기 요청은 보낼 때 검사 건수를 적고 완료 뒤 "검사 n → m건" 배지.

## 문서 - 2026-10-16 · 다른 PPT 제작 도구·MS Office 대비 추가 구현 후보

- `docs/dev/feature-comparison.md`: Gamma·Canva·Beautiful.ai·Pitch·Genspark·Manus·Google/Figma Slides 와 PowerPoint 저작 기능 기준으로 nexa-slide 에 없는 기능을 범주별 표(현재·추가 구현·크기·권장)로 정리 - 적용 대상 판단용. 기존 조사(`docs/research/diagram-table-editing-survey.md`)의 15개 후보와 `pptx-feature-gap.md` 를 잇는다.

## 0.22.13 - 2026-10-16 · 차트 - 누적 가로·100% 누적·콤보(보조 축)·축 제목·숫자 형식

PowerPoint 차트와 호환되는 수준으로(모두 네이티브 `c:chart`, PowerPoint 에서 편집 가능), 데이터 입력은 기존 `범주 | 계열…` 표 그대로(사용자 지시).

- 종류 추가: `stackedBar`(누적 가로) · `stackedColumn100`·`stackedBar100`(100% 누적 — 축 0~100%, 값 표시는 원래 값) · `combo`(막대 + 선: `lineSeries` 로 선 계열 지정(이름·번호, 기본 마지막), `secondaryAxis` 면 선은 오른쪽 보조 축 — PPTX 는 `c:barChart` + `c:lineChart`, 보조 축은 둘째 `c:valAx`(crosses max), 데이터는 같은 내장 워크북). 편집기 ＋ 추가 → 차트… 11종, 서식 줄 종류 상자, 속성 "선 계열"·"보조 축".
- 축 제목 `axisTitle`(값)·`catTitle`(범주)·`axisTitle2`(보조) · 숫자 형식 `numFmt`·`numFmt2`(Excel 식 `#,##0` `0.0` `0%` `#,##0"억"` — 편집기 `chartFmt`, PPTX `formatCode`, 눈금과 값 표시 모두) · `axisMax2`.
- 주 값 축 선택 수정: python-pptx `value_axis` 는 값 축이 둘이면 둘째를 고르므로 첫 `c:valAx` 를 직접 쓴다. 시험 `chart_test`(PPTX XML: barDir·grouping·lineChart·둘째 valAx·축 제목·formatCode, render.js: 가로 누적·100%·콤보 선·보조 축 눈금·축 제목 회전).

## 0.22.12 - 2026-10-16 · 표 셀별 채움·테두리·격자

- 표 `cellFill`(셀·행·열 바탕색) · `borders`(셀·행·열의 변별 선 - 색·두께) · `gridLines`(모든 칸 격자) - `common.table_cell_styles` ↔ `render.tableCellStyles`(`check_parity` 표 예제 2개 추가), PPTX 셀 채움·`a:lnT/B/L/R`. 편집기 표 속성에 "셀 채움"·"셀 테두리"(`행,열,…; …`, `*` = 줄 전체)·"격자" 칸. 상태 표·합계 행(위 굵은 선)·열 구분선용. `docstruct_test` 에 표 확인 추가.
- 정리: `common.table_merges`·`render.tableMerges` 가 세 번 정의돼 있던 것을 하나로.

## 0.22.11 - 2026-10-16 · 글 표기 4종 · 숨김 슬라이드·구분(섹션)·문서 속성 · 테두리 점선·액자 색 · SVG 그림 PPTX

PowerPoint 미구현 기능 목록(`docs/dev/pptx-feature-gap.md`)의 "후보" 중 글 표기·문서 구조·도형·그림 묶음(사용자 "진행" 지시). 편집기(`render.js`)·PPTX(`common.py`·`export_pptx.py`) 같은 규칙, `runs_test`·`check_parity`·새 시험 `docstruct_test`.

- **인라인 표기**(text·pill·rect·ellipse·shape·표 셀·글머리): `~~취소선~~`(PPTX `strike`), `^{위첨자}`·`_{아래첨자}`(글자 65%, `baseline` ±), `[[bg:토큰|형광펜]]`(글자 배경 = run 강조색 `a:highlight`), `[[link:https://…|글]]`·`[[link:#3|글]]`·`[[link:#s07|글]]`(글자 단위 링크 - 밑줄, 글자색 유지 `hlinkClr`(Office 2019+), 발표 화면에서 누르면 이동). 겹쳐 쓸 수 있다. 속성 탭 힌트·사전 갱신.
- **숨김 슬라이드** `hidden`: 속성 탭(슬라이드) 스위치, 썸네일 배지, 발표·인쇄·PDF 건너뜀(`pStep`), PPTX `show="0"`. **구분(섹션)** `section`: 속성 탭 입력, 장 표지(`chapter`) 레이아웃은 제목으로 자동 → PPTX `p14:sectionLst`. **문서 속성**: 제목 = 덱 제목, 작성자 = 작업 공간 `author`(없으면 `brand.name`).
- **도형 테두리 점선·파선** `strokeDash`(rect·ellipse·pill·text·shape; 속성 "테두리 선" 두께·실선/파선/점선) - 편집기는 SVG 점선, PPTX `prstDash`. **액자 색·두께** `frameColor`·`frameWidth`(그림 `frame` 효과, 속성에 테두리 색·px).
- **SVG 그림 내보내기**: 지금까지 `add_picture` 가 SVG 를 읽지 못해 실패했다(결함) → PowerPoint 2016+ `asvg:svgBlip` 으로 넣고 대체 PNG(옆 같은 이름 `.png`, 없으면 1×1 투명).
- 표·차트는 묶기(Ctrl+G) 대상에서 막고 안내한다(PPTX 묶음에 넣지 못해 조용히 빠지던 것).

## 0.22.10 - 2026-10-16 · 시작용 내용 24종 영어 번역 · 슬라이드 유형 `when` 영어 · PPTX 미구현 기능 목록

- **시작용 내용 번역본**: `studio/i18n/content.en.starters1~3.json`(시작용 내용 24종의 글 1,251개 - 보고·제안·RFP·회고·온보딩·강의 교안 등). `content_i18n.load_map` 이 `content.<lang>.json` 과 `content.<lang>.*.json` 을 합쳐 쓰므로 `init_workspace --starter … --lang en` 과 시작 페이지 미리 보기·**새로 만들기**(영어 표시일 때 `lang` → `--lang en`)가 번역본 폴더(`content.en/`) 없이도 사전으로 번역해 복사한다(번역본 폴더가 있으면 그것이 우선). 시험 `content_i18n_test` 에 "26개 파일 한글 없음"·`init_workspace --lang en` 확인 추가.
- 슬라이드 유형 43개에 `i18n.en.when`(언제 쓰는지) 추가 - 검토 페이지·`I18N.pick(type, "when")`.
- `docs/dev/pptx-feature-gap.md`: PowerPoint 에서 동작하지만 엔진(편집기·PPTX 내보내기)에 아직 없는 기능 목록 - 적용 대상 판단용(2026-10-16 코드 조사).
- 진행 현황: 정리·보관 창(🧹) 운영 작업 공간 확인, 그림 프레임 효과(#11) 사용자 PowerPoint 확인.

## 0.22.9 - 2026-10-16 · 견본 내용 영어화(빌드 단계) · 튜토리얼 새 기능 안내

- **견본 내용 언어**: `studio/i18n/content.en.json`(레이아웃 견본·슬라이드 유형 예시·레이아웃이 넣는 자리 글 약 330개) + `content_i18n.tr`. 편집기 슬라이드 추가 창(`/api/slidetypes?lang=`)·시작 페이지 미리 보기(`/api/preview?lang=`, 레이아웃 견본)·`nexa.py layout_samples --lang en` 이 영어 견본을 보인다. 시작용 내용은 `starters/<이름>/content.<lang>/` 가 있을 때만(`init_workspace --lang`) - 번역본은 아직 없어 한국어 그대로(알려진 한계).
- 튜토리얼에 "최근 추가된 기능" 카드(요청 기록 창·엔진 요청 배지·덱 복제·시작 덱·그림 효과·정리·보관·표시 언어)와 서식 줄·내보내기 설명 갱신.
- 시험 `content_i18n_test.py`(run_all `content_i18n`). 설계 `docs/dev/i18n.md` 3절.

## 0.22.8 - 2026-10-16 · 데이터 라벨 i18n 필드(`I18N.pick`) · 시험 실행기 Chrome 포트·종료 보강

- 템플릿(`templates/*/template.json`)·시작용 내용(`starters/*/starter.json`)·슬라이드 유형(`studio/slide_types.json` 묶음·유형)에 **`i18n: {en: {label, description|desc|purpose}}`** 를 넣었다(영어 사전에서 옮김). 서버 목록(`list_templates`·`hub.templates/starters`·`/api/slidetypes`)이 `i18n` 을 그대로 주고, 화면은 **`I18N.pick(obj, "label")`**(언어 파일의 값 → 없으면 원문을 사전으로)로 고른다 - 시작 페이지 템플릿·시작용 내용 카드·선택 상자·미리 보기, 편집기 슬라이드 추가 창·⋯ 메뉴. 데이터를 고칠 때 그 파일의 `i18n` 만 같이 고치면 된다(`docs/dev/i18n.md` 2절). 유형의 `when` 은 화면에 쓰지 않아 비워 둠.
- `smoke.js`: 실행마다 다른 Chrome 디버그 포트(앞선 실행의 창에 붙던 것), Windows 에서 Chrome 프로세스 트리 종료.

## 0.22.7 - 2026-10-16 · 엔진 요청 ↔ 원 요청 연결 · 적용 뒤 자동 재개

- 세션이 엔진 요청으로 넘긴 원 요청(작업 공간 requests.json)에 `engineRequest: N` 이 기록되고 편집기 카드에 **엔진 요청 #N** 배지(중계면 `/engine?q=#N` 링크)가 보인다(`engine_request add --request --deck` → `engine_requests.link_origin`).
- 큐 상태가 바뀌면 원 요청에 `engineNote` 로 알린다 - done(처리됨, 적용되면 다시 처리) · rejected(거절). **applied(적용됨)** 가 되면 원 요청 `status` 를 `open` 으로 되돌려 작업 공간 세션이 이어서 처리한다(`engine_requests.resume_origin`, CLI·허브 API 공통). 작업 공간 서버 `update` 에 `engineRequest`·`engineNote` 허용.
- 시험 `engine_link_test.py`(run_all `englink`). 설계 `docs/dev/engine-request-design.md` 12.2.

## 0.22.6 - 2026-10-16 · 그림 많은 덱 - lazy 로딩·실패 재시도·재검증 캐시

- **문제**: 그림이 많은 덱에서 썸네일(모든 장)과 캔버스가 바뀔 때마다 그림 수십 장을 한꺼번에 다시 내려받아(서버가 모든 파일을 `no-store` 로 주고, 다시 그릴 때 요청이 끊김 `ERR_ABORTED`) 일부가 깨진 그림으로 남았다.
- **수정** ① 그림은 보일 때 읽는다(`<img loading="lazy" decoding="async">`, `render.js` - 인쇄·캡처·발표자 보기는 `Render.setLazy(false)` 로 바로 다 읽음). ② 읽기 실패는 0.5·1.5·4초 뒤 캐시를 우회해 3번까지 다시 시도(`studio.js` 그림 error 위임 처리). ③ 서버가 그림·글꼴·산출물에 `ETag`·`Last-Modified`·`Cache-Control: private, max-age=0, must-revalidate` 를 주고 `If-None-Match` 면 304 - 엔진 화면 파일(HTML·JS·토큰)은 전처럼 `no-store`.
- 시험: 편집기 시나리오 `imgload_test.json`(12장×6 그림 덱 - 캔버스·썸네일 72장 깨짐 0, 틀린 src 재시도 복구), `deck_test` 에 304 재검증.
- `smoke.js`: 시나리오의 `ignoreErrors`(정규식)로 일부러 내는 콘솔 오류를 뺄 수 있다.

## 0.22.5 - 2026-10-16 · 내보내기 파일 이름 = 덱 제목

- PPTX·글꼴 포함 PPTX·PDF 를 **덱 제목** 이름으로 받는다(예: `가정형호스피스 사례관리.pptx`, 글꼴 포함은 `… - 글꼴 포함.pptx`). 파일 이름에 못 쓰는 글자(`\ / : * ? " < > |`)는 공백으로. 저장 자체는 전처럼 `out/<id>.pptx` 라 렌더·비교·글꼴 도구는 그대로 - `/api/export` 응답의 `name`, 편집기 ⬇ 링크의 `download`, 그리고 `/out/<id>.pptx|.pdf` 를 직접 열 때도 `Content-Disposition` 으로 같은 이름(`server.export_name`·`studio.js exportName`).
- 시험 `deck_test` 에 export 이름·헤더 확인.

## 0.22.4 - 2026-10-16 · 인라인 강조 겹치기(엔진 요청 #12)

- `**굵게**`·`==강조==`·`[[토큰|색]]`·`__밑줄__`·`*기울임*` 을 **겹쳐** 쓸 수 있다 — `[[s1|**굵은 색 글자**]]`, `**[[s1|색]]**` 처럼 안쪽 표기를 다시 풀어 바깥 스타일과 합친다(`render.js runs`·`common.runs` 재귀, 같은 규칙). 전에는 안쪽 기호가 글자로 남았다.
- 시험 `runs_test.py`(run_all `runs`): 겹친 표기 8가지를 Python·render.js 양쪽에서 같은 결과로. 문서 `deck-format.md`.

## 0.22.3 - 2026-10-16 · 그림 프레임 효과(엔진 요청 #11)

- 그림(`image`) 요소에 **프레임 효과** `effect`(`softEdge` 부드러운 가장자리 · `round` 둥근 모서리 · `circle` 원형 · `frame` 흰 테두리+그림자 · `glow` 빛) 와 `effectLevel`(1~3, 기본 2), `effectColor`(glow 색, 기본 primary). 원본 파일은 바꾸지 않고 속성으로만 적용된다. 편집기(`render.js effectCss`: mask·border-radius·border·box-shadow)와 PPTX(`export_pptx.apply_effect`: `a:softEdge`·`a:glow`·`prstGeom roundRect/ellipse`·`a:ln`+그림자)가 같은 수치(`EFFECT_PX`).
- 속성 탭 "효과" 선택 상자 + 수준 세그, 서식 줄의 그림 효과 선택 상자. 시험 `effect_test.py`(run_all `effect`)·`ftb_test` 단계. 문서 `deck-format.md`·`editor.md`(오래된 "회전·그림자·투명도 미지원" 한계 문구도 고침).

## 0.22.2 - 2026-10-16 · PPT 줄 배치 보정을 글꼴 메트릭으로 자동 계산(엔진 요청 #10)

- **문제**: 편집기의 세로 보정 `pptTextShift` 가 맑은 고딕·Consolas 에서 잰 상수였고 `measuredFor` 가 맞을 때만 적용돼, 기본 세트(Pretendard)·KoPub 등 다른 글꼴에서는 보정이 전혀 없었다 — 타원·상자의 글이 PowerPoint 보다 줄 높이 1.0 에서 2~4px 위, 1.6 에서 4~8px 아래로 어긋남(가정형호스피스 로마자 원, KoPub Bold 28px lineHeight 1).
- **수정**: `common.ppt_text_shift` 가 역할별 글꼴 파일(`measure.regular`, 작업 공간 `fonts/`·설치 폴더)의 세로 메트릭 C = (winAscent+winDescent)/unitsPerEm 을 읽어 `[0.355, −0.362×C]` 를 `fonts.pptTextShift` 와 각 `fontPresets[*].pptTextShift` 에 넣고, `render.js shift()` 가 역할(body·heading·mono)별로 쓴다. 상수는 Pretendard·KoPub돋움체 Medium/Bold·JetBrains Mono 를 PowerPoint 렌더와 대조해 맞춤(잔차 ±1px, 크기 16~44·줄 높이 1.0~1.6·pad 유무·타원/상자). 글꼴 파일이 없으면 C=1.2 로 계산. 옛 측정 상수(`tokens.json pptTextShift`)는 뺐다.
- 벤치 `studio/tests/shift_bench.py`(PowerPoint 필요, 수동). 문서 `editor.md`·`configuration.md`·`operation.md`·`templates.md`·`dev/tests.md`.

## 0.22.1 - 2026-10-15 · 덱 탭 제목 표시 · 덱 복제 · 짧은 해시 id · 시작 덱

- 덱 탭이 **제목**으로 보인다(시작 덱은 ★). 덱 id 는 엔진이 만드는 **짧은 해시 8자**(`deck_admin.new_id`) - 툴팁·메뉴 머리에 표시만. ＋ 는 제목만 묻는다. 오른쪽 클릭 메뉴는 제목 바꾸기 · **복제…**(`deck_admin.copy` - 새 id, content 도 복사) · **시작 덱으로/해제**(`nexa-slide.json` `startDeck`, 편집기가 주소에 덱이 없을 때 처음 여는 덱) · 삭제. "덱 이름(id) 바꾸기"·"새 덱…" 항목은 뺐다(rename 은 CLI 에만).
- API `POST /api/decks` 에 `copy`·`start`, `create` 는 id 생략 가능, `GET /api/decks` 에 `start`. CLI `nexa.py deck create [<id>] | copy <id> | start [<id>]`, `list` 에 ★.
- 시험 `deck_test.py`(run_all `deck`) · 편집기 시나리오 `deck_test.json`. 문서 `docs/editor.md` 덱 관리.
- 시험 실행기 `smoke.js`: 단계가 **글(문자열)을 돌려주면 실패**로 친다(`dump` 단계만 결과 글). 그동안 글을 돌려주고도 통과로 찍히던 숨은 실패 3건을 고침 - `shape_menu` 실행 취소 6번, `group_test` 배지 높이(단추는 숨겨져 0), `ux_test` 삽입 패널 6묶음(아이콘 묶음 추가 이후).
- `smoke_run.py` 의 덱 단계를 새 방식(제목만 묻기·해시 id·복제)으로 고치고, 결과 글을 보여 주는 두 단계는 `dump` 로 표시.

## 0.22.0 - 2026-10-15 · 작업 공간 관리 - 정리(임시·산출물·끊어진 그림·고아 첨부·세션 로그)·압축 보관

- **`studio/tidy.py`**: `scan`(범주별 보고 - output 산출물·attach 고아 첨부·log 세션 로그·image 참조 없는 그림(백업·휴지통 참조는 `kept` 표시)·backup 백업·휴지통), `clean`(지우지 않고 `out/.tidy/<시각>/` 로 옮김, mermaid `.mmd` 는 `.png` 와 짝), `restore`, `purge`, `archive`(zip - 기본 제외 `out/`(첨부 제외)·`.history`·`.trash`·`.env`·`nexa-slide.local.json`·`.git`, `--all`). CLI `nexa.py tidy|archive`(실행기 안내에 추가).
- 작업 공간 서버 **`GET/POST /api/tidy`**(허브 관리자 중계 또는 로컬 직접 접속) · 시작 페이지 카드 **🧹 정리·보관 창**(범주 체크·목록·[고른 범주 정리]·[비우기]·[zip 으로 보관]).
- 원인 쪽: 요청 `discard`·`update` 가 첨부 파일을 지우고, 엔진 요청 `remove` 가 `attach/<id>/` 를 지운다. 허브 `GET/POST /api/engine/tidy`(관리자) - 큐에 없는 요청의 첨부·하루 넘은 `_new/` 파일.
- 시험 `studio/tests/tidy_test.py`(run_all `tidy`). 문서 `docs/home.md` "작업 공간 관리", `docs/dev/tests.md`.
- 시험 기반: `smoke.js` 가 페이지 이동 뒤 문서·편집기 슬라이드가 그려질 때까지 기다린다(묶음 실행에서 `tbl_test` 가 가끔 너무 일찍 돌던 것) · `smoke_run.py` 단독 실행 시 `tempfile` 누락 수정 · 엔진 갱신 표식(`ENGINE_UI`)에 언어 파일(`en.js`·`en.pages.js`·`en.review.js`) 포함.

## 0.21.42 - 2026-10-15 · 다국어 체계 - 언어 파일 분리(`studio/i18n/en.js`) · 검사·스캔 도구 · 설계 문서

- **사전·패턴을 `studio/i18n/en.js` 로 분리** — 글만 있는 언어 파일(`window.NEXA_LOCALES.en = { name, dict, patterns }`). 엔진 `i18n.js` 는 어느 언어든 `NEXA_LOCALES` 에서 읽고(`langs()`·`options()` 가 파일에서 자동), 새 언어 = 파일 하나. 같은 언어를 영역별 여러 파일로 나눌 수 있다(예: `en.review.js` - 협업 세션 영역). 모든 페이지(편집기·시작·서버 작업·계정·로그인·글꼴·발표자·인쇄·슬라이드·**템플릿/슬라이드 유형 검토**)에 언어 파일 → 엔진 순서로 태그.
- 검사 `studio/tests/i18n_check.js`(언어 파일 문법·중복 키·대표 문구 번역, 실패 시 종료 코드 1) · 런타임 스캔 `studio/tests/i18n_scan.py [editor|home]`(편집기 5667·격리 허브 5798 을 영어로 띄워 탭·메뉴·창 상태마다 남은 한글을 모음, 검토 페이지 포함).
- 설계 `docs/dev/i18n.md`: 층 구조(엔진·언어 파일·페이지·검사), 키 규칙, 데이터 라벨(`i18n` 필드 + `I18N.pick`) 다음 단계, 슬라이드 안 글(견본 내용) 현지화는 빌드 단계 `--lang`(언어별 내용 파일) 설계, 협업 세션과의 영역 분담.
- 시험 `tbl_test` 첫 단계가 속성 탭·요소 목록이 뜰 때까지 기다린다(다른 시나리오 뒤에 돌 때 가끔 실패하던 것).

## 0.21.41 - 2026-10-15 · 다국어 보강(런타임 스캔) · 설정·새로 만들기·미리보기 UI 손질

- **영어 표시 보강 332개 키 + 패턴 40여 개** — 편집기(서식 줄 종류별 툴팁·속성·메뉴·삽입 패널 아이콘 이름·단축키 도움말 조각·슬라이드 추가 창의 유형 묶음·이름·설명·글꼴 페이지)와 시작 페이지(설정 창 문서 폴더·기본·환경변수·git 경고·에이전트 상태, 설치 안내 창, 세션 시작 창 한도·기본 모델, 서버 작업 카드 ⋯ 메뉴, 계정, 서버 작업 목록). 검사 방법: 편집기·허브를 영어(`?lang=en`)로 띄워 여러 화면 상태에서 한글이 남은 텍스트 노드·title·placeholder 를 모으는 런타임 스캔(개발 메모 `docs/dev/i18n.md`).
- 새로 만들기: 제목이 비었을 때 명령·경로의 자리 글이 표시 언어를 따른다(`plan` 의 `defaultTitle`, 영어 = Title). 작업 공간 폴더 입력칸 폭 고정(영어에서 글이 길어져 칸이 사라지던 것) · 예시 문구의 "면" 이 "Face" 로 번역되던 것(`ppt → <폴더>/ppt`) · 쉘 토글 이름 "Bash".
- 설정 창: 숫자 칸 라벨 한 줄(Concurrent sessions 줄바꿈으로 깨지던 것)·칸 사이 세로 간격.
- 미리 보기 창: **내용 → 템플릿 순서**로 바꾸고 "내용을 바꾸면 어울리는 템플릿으로 자동으로 바뀐다(템플릿을 바꿔도 내용은 그대로)" 안내 - 새로 만들기 폼의 내용 선택에도 같은 안내. 바닥줄(n장 · 안내) 번역.
- 서식 줄: 그림 투명도 칸 폭(100 이 잘리던 것). 썸네일 배지 높이 고정(변경 배지가 두껍게 보이던 것)·"변경1" 로 숫자 붙여 쓰기·영어 "Changes 1".
- 알려진 한계: 미리 보기·레이아웃 견본·시작용 내용의 **슬라이드 안 글(견본 내용)** 은 한국어 데이터라 영어로 바뀌지 않는다 - 내용 현지화 설계는 `docs/dev/i18n.md`.

## 0.21.40 - 2026-10-15 · 서식 줄 종류별 설정 · 긴 값 표시 규칙(선택 상자 말줄임+보조 글줄 · 목록 가로 스크롤)

- **서식 줄이 요소 종류마다 자주 쓰는 설정을 바로 보인다**(속성 탭과 같은 값, `renderFtb`/`onFtb`): 글머리 = 글꼴·글머리 종류 ▾(항목·하위·번호 감지)·● 점 색·↕ 줄 높이·항목 간격·하위 크기·T 글자 상자로; 표 = ＋행 －행 ＋열 －열(행×열)·머리 면·머리 글자; 도형/차트/아이콘 = 맨 앞 종류 선택 상자, 차트 범례(순환)·값·눈금선, 아이콘 색·대비 색; 그림 = 투명도 %·✂ 자르기 ▾·🖼 바꾸기·mermaid 코드; 묶음 = 풀기; 코드 = # 줄 번호; 글자 = ≡ 글머리로. 공통 = 🔗 링크 ▾(입력·지우기)·◱ 그림자·↻ 회전(0/90/180/270·±15°)·뒤집기. 켜진 상태는 단추가 진하게. 표 행·열 조작은 `tableOp` 로 모아 속성 탭과 공유.
- **긴 값 표시 규칙**(일관성): 값 하나를 고르는 **선택 상자**는 칸 안에서 말줄임(`select.ell`) + 아래 **보조 글줄**(`.sub`)에 고른 값의 전체 설명(글꼴 세트 = 세트 이름 · 글꼴 구성, 기본이면 실제 쓰이는 세트) + 툴팁; 펼친 목록은 브라우저가 내용 폭대로 그린다. 여러 줄 **목록**(요소 목록 `.ellist`, 변경 탭 최근 수정 대상 `.hscroll`)은 줄을 자르지 않고 목록 전체를 가로로 넘긴다. 전에 글꼴 세트 선택 상자를 감싸던 가로 스크롤 칸(`.scrollx`)은 없앴다.
- 시험 `scenarios/ftb_test.json`(표·글머리·그림·상자·도형의 서식 줄 단추와 메뉴 동작) · `fontsel_test.json` 을 새 규칙으로.

## 0.21.39 - 2026-10-15 · 요청 탭 최근 보기 + 요청 기록 창 · 공용 찾기(퍼지 · Aa/ab/.* 토글)

- 0.21.39.2: 번호 지정 `NexaSearch.split` — 요청 기록 창의 **`#4`** 는 슬라이드 4 의 요청(`#4,5,7-10` 처럼 여러 장·범위), 서버 작업 목록의 `#9`·`#1,5,8-9` 는 요청 번호 — 나머지 낱말만 글 찾기에 쓴다(`#4 세로` = 슬라이드 4 안에서 '세로'). 필터 줄에 "범위" 라벨(상태와 같은 꼴).
- 0.21.39.1: 요청 기록 창의 머리줄 클래스가 편집기의 크기 조절 손잡이 `.hd`(절대 위치·빨간 원)와 겹쳐 제목이 입력칸 위에 떠 있던 것 — 창 안 클래스를 `rh-` 접두로 바꾸고 입력칸 위·옆 여백을 늘렸다.
- **요청 탭 기본 보기 = 최근**: 최근 24시간에 진행(만듦·보냄·상태 변경·답)된 요청과 아직 끝나지 않은 요청만("이 슬라이드"/"최근 (n)"). 서버가 요청 갱신 때 `updated` 를 적는다(`api_post_requests` update·send - **재시작 필요**). 카드에 마지막 진행 시각(↻).
- **[더보기 · 이전 n]** → **요청 기록 창**(`#reqHist`): 서버 작업 목록처럼 페이지를 옮기지 않고 편집 화면 위에 겹쳐 뜨는 창 - 편집 중인 덱·선택·저장 상태를 벗어나지 않는다(Esc·바깥·✕ 닫기). 찾기(내용·답·요소·첨부 이름, 강조, 대화 묶음 단위)·범위(전체/이 슬라이드)·상태 필터, "슬라이드 n" 링크는 창을 닫고 이동, 완료/다시 열기/삭제 가능. 요청 카드 그리기를 `reqCardHtml` 로 모아 탭과 창이 같이 쓴다.
- **공용 찾기 `studio/search.js`(NexaSearch)**: 기본 **퍼지**(낱말마다 부분 일치 → 없으면 글자 순서대로 틈 2자까지 - 띄어쓰기·한두 글자 차이 허용), 토글 **Aa 대소문자 · ab 단어 단위 · .\* 정규식**(일반 편집기의 찾기와 같음, localStorage `nexa-search-<key>`), 정규식 오류 표시. 서버 작업 목록(`/engine`)도 같은 모듈로 바꿈(입력칸 옆 토글). API `?q=` 는 부분 일치 그대로(CLI 용).
- 시험 `scenarios/reqhist_test.json`(메모 → 더보기 창 → 퍼지 '글머리기호' → 단어 단위 → 정규식·오류 → Esc). 영어 사전에 새 문구. 문서 `editor.md`·`home.md`·`dev/tests.md`.

## 0.21.38 - 2026-10-15 · 줄바꿈 일치 - 도형 글 영역 들여넣기

- 편집기(`render.js elBox`)와 배치 검사(`check_layout`, `common.text_pad_effective`)의 글 영역 여백을 PowerPoint 의 도형 글 영역 들여넣기와 같게 — 타원은 폭·높이 × 0.14645, 둥근 사각형·칩은 반경 × 0.29289(`export_pptx.text_pad` 와 같은 규칙). 전에는 편집기가 도형 폭 전체에 글을 놓아 PowerPoint 보다 한 줄 적게 접혔다.
- 검증 도구 `studio/lines_pptx.ps1`(PowerPoint COM 줄 수 JSON). 글 상자 60개 60/60, 기호·굵게·숫자+단위·괄호를 섞은 120개 116~117/120 — 남은 차이(숫자+단위·괄호·가운뎃점·굵은 낱말이 줄 끝에 올 때)는 글꼴 폭 계산의 미세한 차이로 알려진 한계(`docs/editor.md`).

## 0.21.37 - 2026-10-15 · 알려진 한계 확정

- 편집기 기능의 세부 한계 11항목(회전 손잡이·크기 조절 가이드·변환 색·차트 세부·묶음·그림자 옵션·mermaid·PDF·발표자 보기·아이콘·글머리 위치)을 사용자 결정으로 **알려진 한계**로 두고 완료 처리 — `docs/editor.md` "알려진 한계" 절.

## 0.21.36 - 2026-10-15 · 발표 단추 툴팁

- ▶ 발표 단추 툴팁에 발표 중 키(N 노트·시간, **P 발표자 보기** - 새 창, 두 창 동기화, Esc 끝)를 적었다(영어 사전 포함).

## 0.21.35 - 2026-10-15 · 마무리 - 편집기 UI 시험 저장소 반영 · 옛 메뉴 제거 · 영어 사전 보강 · 링크 표시

- `studio/tests/editor_ui_test.py` + `scenarios/*.json`(7개): 그림·도형/차트/아이콘/다이어그램 타일·표 단추·묶음·링크/그림자/자르기·발표자 보기·명령 팔레트·스마트 가이드·선택 상자 넘침 — 시험용 작업 공간을 스스로 만들고 `run_all.py` 기본 묶음에 포함. 실행기 `smoke.js` 는 작업 공간 서버의 엔진 알림 404 와 시험이 일부러 보낸 `/api/image` 400 을 오류로 치지 않는다.
- 삽입 패널로 바뀐 뒤 남아 있던 옛 메뉴 함수 제거. 영어 표시 사전에 새 안내문(차트·아이콘·묶음·mermaid·삽입 패널·발표자 보기)과 패턴(덱 목록 `(n장)`, `자동 (포트)`, `세트 …`, 마지막 세션, 세션 연결 없음) 추가.
- 편집 화면에서 링크가 걸린 요소 오른쪽 위에 🔗 표시(발표 화면·내보내기에는 없음).

## 0.21.34 - 2026-10-15 · 글머리 기호 세로 가운데

- 편집기 글머리(●·–·기호·번호)가 글자 기준선에 붙어 작은 ● 가 아래로 처지던 것 — 첫 줄 상자의 세로 가운데에 절대 배치(`.rs-bu`), 글자 크기와 무관하게 글줄 가운데. 글 들여쓰기는 내어쓰기 대신 왼쪽 여백으로(줄바꿈 정렬 같음). PPTX 는 PowerPoint 가 기준선에 두는 그대로.

## 0.21.33 - 2026-10-15 · PPTX → 덱 자동 변환

- `import_pptx <파일> --deck <id> [--title …] [--force]`: 분석 결과를 바로 `decks/<id>.json` 으로 — 글 상자(글머리·수준이 있으면 `bullets`, 번호·기호는 글 앞에 적어 자동 감지), 표, 그림(`assets/import/<id>/` 로 복사), 차트(종류 매핑), 프리셋 도형(`shape`), SmartArt 글. 위치·크기는 원본(1280×720 환산), 글자 크기는 pt×4/3, 색·글꼴은 템플릿 기본. 노트·숨김 유지. `docs/claude-session.md`·`editor.md`.

## 0.21.32 - 2026-10-15 · 아이콘 요소

- 새 요소 `icon`(내장 33종: 확인·닫기·더하기·화살표·꺾쇠·재생·정보·경고·물음·집·사람·메일·문서·폴더·달력·시계·위치·말풍선·하트·번개·찾기·별·깃발·톱니 …): 삽입 패널 "아이콘" 타일, 속성 종류·아이콘 색·대비 색. 편집기는 24×24 채움꼴 경로를 SVG 로, PPTX 는 같은 경로를 `custGeom` 자유형 도형으로(층마다 도형, 둘 이상이면 묶음) — PowerPoint 에서 색·크기를 고칠 수 있는 벡터. 상표·외부 아이콘 세트는 쓰지 않는다(MIT).

## 0.21.31 - 2026-10-15 · UX - 삽입 패널 · 명령 팔레트 · 스마트 가이드 · 접는 절

- ＋ 추가가 긴 메뉴·하위 메뉴 대신 **검색 가능한 삽입 패널**(기본·데이터·미디어·도형·다이어그램 타일, 글자를 치면 걸러짐, Enter = 첫 항목)로. **명령 팔레트** `Ctrl+K`·`/`: 넣기와 동작(발표·내보내기·검사·고치기·슬라이드/요소 복제·삭제·묶기·배치·확대·도움말)을 한 곳에서, 최근 쓴 것이 위. **스마트 가이드**: 끌 때 다른 요소의 가장자리·가운데와 슬라이드 가운데에 붙고 빨간 점선(Shift = 자유). 속성의 드문 절(글머리 종류)은 접힘(상태 기억). `?` 도움말 보강. 지침 `docs/dev/ux-guidelines.md`.

## 0.21.30 - 2026-10-15 · 차트 요소

- 새 요소 `chart`(세로·누적 세로·가로 막대, 꺾은선, 영역, 원형, 도넛): 편집기는 데이터에서 SVG 로(축 눈금 1·2·5 단위, 범례 아래/오른쪽, 값 표시, 눈금선, 색 팔레트), PPTX 는 PowerPoint 원래 차트(python-pptx `add_chart` — 같은 색·범례·값 표시·눈금·gapWidth 80, 편집 가능). ＋ 추가 → 차트…, 속성 "차트" 절(종류·제목·데이터 표·범례·값 표시·눈금선·글자 크기·축 최댓값). `docs/deck-format.md`.

## 0.21.29 - 2026-10-15 · 하이퍼링크 · 그림자 · 그림 자르기·투명도 · 발표자 보기 · PDF 내보내기

- 요소 `link`(주소·`#번호`·`#슬라이드 id`): 속성 "링크" 칸, 발표 화면에서 눌러 이동, PPTX click_action. `shadow`(기본 또는 {blur,dx,dy,color,alpha}): 속성 "그림자" 스위치, 편집기 drop-shadow ↔ PPTX outerShdw. 그림 `crop`(왼·위·오른·아래 %)·`opacity`: 속성 칸, PPTX crop·alphaModFix.
- **발표자 보기** `studio/presenter.html`(발표 모드에서 **P**): 지금·다음 슬라이드·노트·경과 시간, BroadcastChannel 로 발표 화면과 쪽을 맞춤.
- **PDF 내보내기**(내보내기 ▾): PowerPoint(pwsh, `render_pptx.ps1 -Pdf`)가 있으면 PPTX → PDF, 없으면 Chrome/Edge 헤드리스가 `studio/print.html`(슬라이드마다 한 쪽 1280×720)을 인쇄. `POST /api/export/<id>?pdf=1` → `/out/<id>.pdf`.

## 0.21.28 - 2026-10-15 · 편집기 패널 넘침 방지

- 속성·요청·기록·변경 패널에서 자식이 부모(절·행·패널)를 벗어나지 않게 — 긴 선택지(글꼴 세트·덱 글꼴 세트·색)는 칸 안에서 가로 스크롤, 그 밖의 긴 글·코드·표는 절 안에서 스크롤 또는 줄바꿈(`.sec`·`.row`·`.panel` 공통 규칙).

## 0.21.27 - 2026-10-15 · 요소 묶음 · 도형 글 영역 검사

- 새 요소 `group`(`children`, 묶음 상자 기준 좌표): 편집기 **Ctrl+G** 묶기 / **Ctrl+Shift+G**·[묶음 풀기] 풀기(오른쪽 클릭 메뉴에도), 묶음 안 자식을 눌러도 묶음이 잡힘, 크기 조절은 자식 비율, 묶음의 회전·뒤집기는 전체에. PPTX 는 묶음 도형(`grpSp`, 표는 못 넣음). `docs/deck-format.md`·`editor.md`.
- `check_layout`·`scale_fonts` 가 `shape` 요소의 글 영역(프리셋 글 상자, `common.shape_text_rect`)으로 넘침을 본다.
- 슬라이드 축소판의 요청·처리 배지를 복제·삭제 단추와 같은 크기(11px, 2px 8px)로 맞추고(처리 배지가 더 크게 보이던 것), 칸이 좁아 숫자를 붙여 쓴다(`요청1`·`처리1`).

## 0.21.26 - 2026-10-15 · 표 셀 병합 · mermaid 다이어그램 요소

- 표 `merge: [[행, 열, 행수, 열수], …]`(편집기 표 속성 "셀 병합" 칸) — 편집기는 왼쪽 위 셀을 넓혀 그리고 덮인 셀은 비우며(`tableMerges`/`common.table_merges` 같은 규칙), PPTX 는 셀 병합.
- ＋ 추가 → **다이어그램 코드(mermaid)…**: 코드 창(Ctrl+Enter) → `POST /api/mermaid`(작업 공간 서버, mermaid-cli·npx, 처음엔 내려받기) → `assets/images/diagram-<날짜-시각>.png`(+`.mmd`) → 그림 요소(`mermaid` 코드 보관, 속성 [다이어그램 코드 수정…]로 다시 그림). Node 가 없으면 안내.

## 0.21.25 - 2026-10-15 · 밑줄·기울임 · 회전·뒤집기 · 감시 하트비트 쓰기 재시도

- 인라인 강조에 **`__밑줄__`**·**`*기울임*`** 추가(편집기·PPTX 동일, `runs()` 양쪽 — 표 셀·글머리·도형 글 포함). `docs/deck-format.md`.
- 요소 **회전·뒤집기**: `rot`(도, 시계 방향, 중심 기준)·`flipH`·`flipV` — 편집기는 CSS transform(뒤집은 뒤 회전), PPTX 는 `a:xfrm` rot·flipH·flipV(PowerPoint 와 같은 뜻). 속성 "위치·크기" 아래 회전 칸과 ⇋ 좌우·⇅ 상하 단추(text·pill·rect·ellipse·shape·image).
- 수동 감시(`watch_engine_requests`·`watch_requests`)의 하트비트 쓰기가 Windows 파일 공유 충돌(허브가 읽는 순간 `PermissionError`)로 조용히 끝나던 것 — 바꿔치기를 잠깐 뒤 다시(최대 10회), 한 번 실패해도 감시는 계속, 출력 오류로 끝날 때는 stderr 에 이유를 남긴다.

## 0.21.24 - 2026-10-15 · 표 행·열 단추 · 글머리 감지 스위치 · import_pptx 도형·글머리 · 적용 커밋 필드

- 편집기 표 속성 **＋행 −행 ＋열 −열**(머리 행·첫 열은 남김, `colW`·`colFont` 같이 맞춤). 글머리 속성 **글 앞 번호·기호 감지 켬/끔**(`autoNum`).
- `import_pptx`: 프리셋 도형의 `prst` 와 덱 `shape` 종류(`PRST_TO_SHAPE`, 글 없는 화살표·별 같은 도형도 남김), 단락 글머리(자동 번호 → `marker` 종류·`start`, 글자 글머리 `bullet`, 없음) — slides.md 에 `[1.]`·`[•]` 로. `docs/claude-session.md`.
- `engine_request.py status <id> applied --commit` 이 처리 커밋(`commit`)을 덮어쓰던 것 → `appliedCommit` 에 기록.

## 0.21.23 - 2026-10-15 · 시험 모음을 저장소에 (`studio/tests/`)

- 그동안 개발 세션의 임시 폴더에만 있던 자동 시험을 `studio/tests/` 로 옮겼다 — `run_all.py`(기본 묶음: i18n·smoke(헤드리스 클릭 50여 단계)·e3·e4(수동 세션 수명)·englist·race·thread, 약 5분 · `--sessions` 로 실제 claude 턴 시험 c2·c3·c3b·c4), 헤드리스 실행기 `smoke.js`. 격리된 허브(5799)·작업 공간(`<임시 폴더>/nexa-slide-tests/`, 저장소 밖)을 쓰고 운영 서버를 건드리지 않는다. 작업 공간형 시험은 `init_workspace`+`build_deck` 으로 픽스처를 스스로 만든다. `docs/dev/tests.md`.

## 0.21.22 - 2026-10-15 · 서버 작업 목록 - 카드는 최근 5건, 전체 목록·검색 페이지

- 시작 페이지 서버 작업 카드의 요청 목록을 **최근 5건**으로 줄이고 **[더 보기 (전체 n건)]** 를 둔다 → 새 페이지 **`/engine`**(`studio/engine.html`, 허브 전용): 검색(제목·내용·답·요청자·커밋·`#번호`, 일치 강조)·상태별 칩(건수)·30건씩 더 보기·제목 클릭으로 내용·답·검증·첨부(라이트박스) 펼치기·관리자 승인·거절·적용됨·삭제. `GET /api/engine/requests?q=` 검색과 `total` 추가. `docs/home.md`.

## 0.21.21 - 2026-10-15 · 그림 삽입

- 편집기 ＋ 추가 → **그림 파일…**, 캔버스에 **끌어다 놓기**(놓은 자리), 글 입력 중이 아닐 때 **Ctrl+V**(클립보드 그림) → `POST /api/image`(작업 공간 서버, png·jpg·gif·webp·svg, 12MB)가 `assetRoot/assets/images/<날짜-시각>-<이름>` 에 저장하고 `image` 요소로 넣는다(640×400 안에 비율 유지, 여러 장은 겹쳐 넣고 모두 선택). 그림 속성 **[그림 바꾸기…]**(폭 유지, 높이는 비율). `docs/editor.md`.

## 0.21.20 - 2026-10-15 · 도형 삽입 · 다이어그램 삽입

- 새 요소 `shape`(PowerPoint 기본 도형 21종: 삼각형·직각 삼각형·마름모·평행사변형·사다리꼴·오각형·육각형·팔각형·오른쪽/왼쪽/위/아래/좌우 화살표·갈매기·오각 화살표·별·십자·사각형/둥근 설명선·원기둥·정육면체). 편집기는 PowerPoint 프리셋의 기본 조정값 기하를 SVG 경로(clip-path)로 그리고 글은 프리셋의 글 영역에 가운데(`render.js SHAPES`), PPTX 는 `prstGeom`(python-pptx `MSO_SHAPE`)으로 내보내 PowerPoint 에서 그대로 편집된다. 채우기(단색·투명도·그라데이션)·테두리·글 속성은 상자와 같다.
- 편집기 ＋ 추가 → **도형…**(아이콘 격자) · **다이어그램…**(프로세스(갈매기)·흐름(상자·화살표)·순환·계층(조직도)·열 목록·벤·타임라인·매트릭스 2×2·피라미드 — SmartArt 대신 요소 묶음을 넣고 요소마다 고친다). 속성 "도형 > 종류"로 바꾸기. `docs/deck-format.md`·`docs/editor.md`.

## 0.21.19 - 2026-10-15 · 글머리 종류 고르기 · 글머리 목록 요소 추가 · 글자 상자 ↔ 글머리 변환

- 편집기 ＋ 추가 메뉴에 **글머리 목록**(항목·하위 항목이 든 `bullets` 요소). 글자 상자 속성의 **[≡ 글머리 목록으로 바꾸기]**(줄 = 항목, 앞 공백 두 칸 = 하위)와 글머리 요소의 **[글자 상자로 바꾸기]**(위치·크기·글자색 유지).
- 글머리 요소 속성 **글머리 종류**(`marker`·`subMarker`): 기호(● ○ ■ □ ◆ ▪ ▸ – ✓ · ◦)·번호 매기기(`1.` `1)` `(1)` `a.` `a)` `A.` `A)` `①` `가.` — 순번 자동, 하위는 상위 항목마다 1부터, PPTX `a:buAutoNum`)·없음(`none`, PPTX `a:buNone`, 내어쓰기 없음). 글 앞에 직접 적은 번호·기호(0.21.17·18 감지)가 우선. 편집기·PPTX 동일 규칙(`common.marker_num`/`render.js markerNum`), 동일성 검사 예제 4개 추가. `docs/deck-format.md`·`docs/editor.md`.

## 0.21.18 - 2026-10-15 · 글머리 기호 자동 감지

- 0.21.17 의 번호 감지에 더해 항목 글 앞의 **글머리 기호**(`* ` `- ` `+ ` 는 공백 필요 · `· ‧ ∙ ㆍ • ● ○ ◦ ◎ ■ □ ▪ ▫ ◆ ◇ ◈ ▲ △ ▼ ▽ ▶ ► ▸ ▹ ▷ → ➜ ➤ ➢ ✓ ✔ ✗ ✘ ✦ ✧ ★ ☆ ※ ◉ ⦁` 는 공백 없어도)를 감지해 ● 대신 그 기호를 글머리 색으로 그린다(편집기·PPTX `buChar` 동일, ● ■ ◆ ▲ ▼ ★ 은 60% 크기). `a-b`·`**굵게**` 는 아님. `autoNum: false` 로 함께 끔. 동일성 검사 예제 추가.

## 0.21.17 - 2026-10-15 · 글머리 번호 자동 감지 (엔진 요청 #9)

- `bullets` 항목 글 앞의 번호(`1. ` `1) ` `(1) ` `a. ` `A) ` `①` `가. ` + 공백)를 자동 감지해 ● 대신 그 번호로 표기 — 편집기(render.js `bulletNum`)와 PPTX(`a:buAutoNum` type·startAt, 가. 같은 것은 `buChar` 글자 그대로) 동일 규칙(`common.bullet_num`, 동일성 검사 예제 추가). 글(덱·content)은 그대로라 손으로 적은 번호를 지울 필요가 없다. 번호는 글 색·크기, 내어쓰기는 번호 폭만큼(`num_hang`). 두 자리까지만(`2024. 매출` 제외), 공백 없는 `1.5배` 제외. 요소 `autoNum: false` 로 끔. `scale_fonts` 높이 계산도 반영.

## 0.21.16 - 2026-10-15 · 수동 감시의 stdout 닫힘 오판 방지

- 운영에서 Monitor(Node 파이프)에 한 줄 쓴 뒤 0바이트 WriteFile 판정이 '닫힘'으로 오판해 감시가 45초 만에 스스로 끝난 것(협업 세션 재현) — `procutil.StdoutWatch`: 판정이 3초 이상 이어지고 실제 한 줄 `{"event":"ping"}` 쓰기도 실패할 때만 끝낸다(쓰기가 되면 오판으로 보고 계속). 두 감시 스크립트가 이것을 쓴다. 서버 변경 없음(감시를 다시 걸면 적용).

## 0.21.15 - 2026-10-15 · 수동 세션에 모델·세션 ID 표시

- `watch_engine_requests`·`watch_requests` 에 `--agent`·`--model`(기본: Claude Code 안이면 claude, `NEXA_SLIDE_MODEL`/`ANTHROPIC_MODEL`), Claude Code 환경변수에서 세션 ID(`CLAUDE_CODE_SESSION_ID`)·연 곳(`CLAUDE_CODE_ENTRYPOINT` → vscode/cli)을 자동으로 하트비트에 담는다(`procutil.session_meta`). 서버 작업 카드·최근 작업 카드의 수동 세션 줄에 "이름 · claude <모델> · vscode · #세션ID(복사)" 표시. 슬래시 명령 `/nexa-slide-server`·`/nexa-slide-session` 과 작업 공간 `CLAUDE.md` 가 자기 모델 ID 를 `--model` 로 넘기도록 안내. `watch_engine_requests --stream` 은 연결 직후 `{"event":"idle","connected":true,"open":n,"triage":n}` 한 줄을 내 세션이 바로 "연결됨" 을 알린다(협업 세션 제안).

## 0.21.14 - 2026-10-15 · 수동 세션 수명 - 세션이 닫히면 감시 종료 · 웹 [끊기] · takeover 수정

- `studio/procutil.py`(새): `pid_alive`·`kill_tree`·`stdout_closed`·`stop_manual`. `watch_engine_requests`·`watch_requests --stream` 은 Monitor 를 건 세션(터미널·VS Code)이 닫혀 표준 출력의 읽는 쪽이 사라지면 1초 안에 스스로 끝난다(전에는 Windows pyenv 래퍼 아래에서 고아로 남아 카드가 계속 "수동 세션"). `--takeover` 가 이전 감시를 실제로 끝낸다(전에는 둘이 같이 돌았다).
- 웹에서 끊기: 서버 작업 카드의 **[끊기]**(관리자) · 최근 작업 카드의 수동 세션 [끊기] — 세션 stop API(`/api/engine/session`·`/api/wsession`·허브 `/api/project session stop`)가 웹 세션이 없으면 하트비트의 수동 감시 프로세스를 자식까지 끝내고 `stopped` 로 표시한다. 작업 공간 서버가 꺼져 있어도 허브가 하트비트 파일로 끝낸다. 응답 `manual {stopped, pid, label}`.
- 슬래시 명령 안내에 수명·[끊기] 뒤 동작(다시 띄우지 않음) 추가.

## 0.21.13 - 2026-10-15 · ⓘ 설정 안내 - clone 이후 할 일 · 슬래시 명령 /nexa-slide-server · /nexa-slide-session

- 슬래시 명령 개명·분리(0.21.12 의 `/nexa-engine` →): **`/nexa-slide-server`** = 서버 작업(엔진 요청 큐) 세션 하나(엔진 저장소·작업 공간 어디서 연 세션이든), **`/nexa-slide-session`** = 그 작업 폴더의 슬라이드 세션(편집기 요청 처리, `watch_requests --stream`). 작업 공간은 `init_workspace`·`update_launcher` 가 두 파일을 작업 공간과 **저장소 루트**(VS Code 를 보통 루트에서 열고 Claude Code 는 cwd 의 명령만 읽으므로, 루트 판은 `python3 slides/nexa.py`) 양쪽에 두고 엔진이 만든 옛 `nexa-engine.md` 는 지운다. 명령 안에 예외 처리: 이미 이 세션이 연결돼 있으면 다시 띄우지 않음, 웹(엔진) 세션이 맡고 있으면 `refused` → [세션 중지] 안내, 다른 터미널 세션이면 물은 뒤 `--takeover`, 서버 꺼짐 → `nexa.py start`, 엔진 못 찾음 → `nexa.py engine <폴더>`, Monitor 만료(`ttl`) → 다시.
- 시작 페이지 머리 **ⓘ 설정 안내**(최근 작업 카드 ⓘ 도 같음): 엔진·작업 공간 저장소를 받은 뒤 이 PC 에서 할 일을 실제 경로가 채워진 명령(엔진 clone·pip·server.py·git pull·`/nexa-slide-server`, 작업 공간 `nexa.py engine`·`update_launcher`·`start`·`/nexa-slide-session`)과 복사 단추로. 작업 공간 선택 가능.
- 문서: `install.md` "저장소를 받은 뒤 할 일(clone 이후)" 절(`update_launcher` 가 `.claude/commands/nexa-slide-server.md`·`.claude/settings.json`·`.env.example` 을 자동 생성, 커밋해 둘 파일과 PC 별 파일), `new-project.md` 2.2·명령 요약, `configuration.md`, `home.md`.

## 0.21.12 - 2026-10-15 · /nexa-slide-server - 열린 세션에서 한 줄로 서버 작업 맡기

- 슬래시 명령 `/nexa-slide-server`(엔진 `.claude/commands/nexa-slide-server.md`, 작업 공간은 `init_workspace`·`update_launcher` 가 `.claude/commands/nexa-slide-server.md` 를 둠): 이미 열려 있는 Claude Code 세션(터미널·VS Code)에서 입력하면 큐 감시를 Monitor 로 띄우고 요청 처리 절차(엔진 worktree·engine_request 상태)를 따른다. 카드 ⋯ 상자에 안내. 세션 ID 로 밖에서 연결하는 방식은 Claude Code 에 외부 입력 주입 API 가 없어 불가(문서·실험 확인).

## 0.21.11 - 2026-10-15 · 서버 작업 ⋯ 메뉴는 항상

- 서버 작업 카드의 ⋯(터미널 세션으로 맡기기)가 웹 엔진 세션이 켜져 있으면 숨겨져 연결 방법을 찾을 수 없던 것 — 관리자에게 항상 보이고, 웹 세션이 켜져 있으면 "먼저 [세션 중지]"를, 수동 세션이면 누가 맡고 있는지를 상자 위에 알린다.

## 0.21.10 - 2026-10-15 · 표 글꼴 역할 적용 · 표 유형 선택 (engine-request #7·#8)

- 표(table) 요소의 `font`·`colFont`(열별) 글꼴 역할이 렌더·PPTX·편집기에 적용되지 않던 것 — 글꼴 역할 정규화(`fontRole`/`font_role`: body·heading·mono, "code" 는 mono)를 두고 표 본문 셀 = `colFont[열]` > `el.font` > 본문(머리 행은 본문)으로 통일. `check_layout` 글자 폭 측정·`layouts` table 레이아웃(content 의 font 전달)도 같은 규칙. 속성 패널 "적용 글꼴"이 표를 무조건 코드로 보이던 것 수정, 열별 역할 표시, 서식 줄 글꼴 선택을 표에도.
- 표 속성에 **유형** 선택(일반 = 본문 글꼴 · 코드 = 고정폭 · 제목 글꼴)과 열별 글꼴 입력. `docs/deck-format.md`(font·colFont 값 형식)·`editor.md`·`fonts.md`.
- 엔진 개발 세션(engine-request #7·#8)이 만들어 main 에 병합·적용. 검증: `check_parity`(표 글꼴 역할 예제 3개 포함) 모두 같음 · `export_pptx --selftest` · 스모크.

## 0.21.9 - 2026-10-15 · 요소 목록 클릭 때 목록이 움직이지 않게 · 토스트 위치

- 서버 작업 요청 양식의 내용 칸: Enter = 큐에 넣기, Shift+Enter = 줄바꿈(편집기 요청 칸과 같게).
- 메모를 남길 때 뜨는 토스트가 아래의 "보낼 요청" 바와 겹치던 것 — 바가 떠 있으면 토스트를 그 위로 올린다.
- 속성 탭 요소 목록에서 요소를 고르면 위쪽 절(글자·면 등)이 바뀌어 목록이 위아래로 움직이던 것 — 다시 그린 뒤 목록이 화면의 같은 자리에 있도록 패널 스크롤을 맞춘다(연속 클릭·Ctrl/Shift 선택이 편하게).

## 0.21.8 - 2026-10-15 · 요소 목록 선택

- 속성 탭 요소 목록: 클릭 = 선택, Ctrl+클릭 = 더하거나 빼기, Shift+클릭 = 기준점(마지막 클릭)부터 범위 선택. 고른 행이 보이도록 스크롤.
- **회귀 수정**: 속성 패널의 클릭 처리기 등록이 코드 주석 뒤에 묻혀(0.18.x 코드 언어 기능 때) 패널 안 단추(맨 앞·맨 뒤·복제·삭제·JSON 적용·요소 목록 선택·정렬 세그먼트)가 눌러도 동작하지 않던 것.

## 0.21.7 - 2026-10-15 · 수동 엔진 세션(터미널이 서버 작업 큐를 맡기)

- `python3 studio/watch_engine_requests.py --stream`(Monitor) — 터미널의 Claude Code 세션이 엔진 요청 큐를 맡는다. 하트비트(kind=manual)로 시작 페이지 서버 작업 카드에 "수동 세션 · <이름> · <폴더>" 가 보이고 [세션 시작]은 "터미널이 맡음"으로. 처리할 요청(open)이 생기면 Monitor 알림, 상태 변경은 `engine_request.py status …`. 웹 엔진 세션과 서로 배타(둘 다 거절). 승인 대기 알림의 "세션 꺼짐" 판정에도 반영.

## 0.21.6 - 2026-10-15 · 도형 안 글자 세로 중심 보정(글꼴 세트별)

- 원·칩 등 도형 안의 글자가 브라우저에서 PowerPoint 보다 2.5px 위에 보이던 것: 맑은 고딕·Consolas 로 잰 PPT 줄 배치 보정(`pptTextShift`)이 다른 글꼴 세트(KoPub돋움체 등)에도 그대로 적용돼서. 보정은 **측정한 글꼴(`measuredFor`)을 쓸 때만** 적용하고, 다른 세트는 세트 자체의 `pptTextShift` 가 있으면 그것, 없으면 0. 측정: 원(56px) 안 I·II·III — PowerPoint dy −1.0px, 브라우저 −3.5px → 보정 뒤 −1.0px.
- ▶ 발표 단추를 **Shift+클릭**하면 현재 슬라이드부터 발표(Shift+F5 와 같다).
- 작업 공간 서버로 직접 연 페이지에서 승인 대기 알림 폴링이 404 를 반복 기록하던 것 - 한 번 보고 그만.

## 0.21.5 - 2026-10-15 · 속성 패널 재설계 · 적용 글꼴 · 세션 ID 배지(턴 전)

- **속성 패널**: 그룹 카드(위치·크기 / 순서 / 글자 / 면·테두리 / 선 / 코드 … / 동작 / JSON(접힘))로 다시 배치. 누를 수 있는 것은 모두 테두리 있는 단추(맨 뒤·뒤로·앞으로·맨 앞 네 단추, 복제·요청·삭제), x·y·w·h 는 2×2 격자, 잠금은 머리의 스위치, 정렬·세로는 아이콘 세그먼트, 입력칸에 테두리·포커스 표시.
- **적용 글꼴**(글자가 있는 요소): 역할(본문/코드) · 라틴 + 한글 글꼴 · px = pt · 굵게 · 어느 세트(덱/작업 공간/템플릿)에서 왔는지 · CSS 이름 · 이 브라우저에 없으면 경고.
- 글꼴 역할에 **제목(heading)** 선택지(서식 줄·속성) — 세트의 제목 글꼴을 쓰는 요소가 "본문 글꼴"로 보이던 것. 글머리·실행계획에도 적용 글꼴 카드. 세트의 역할 글꼴 자체가 굵은 서체(KoPub돋움체 Bold 등)면 "굵게 토글과 별개"로 알린다.
- 세션 ID 배지: 첫 턴 전(대화 파일 없음)이면 점선 "ID … · 턴 전" 으로 보이고 복사 때 `claude --resume` 로는 아직 열리지 않는다고 안내한다(재시작 직후 세션에서 "No conversation found" 가 난 사례).
- 엔진 요청 #6(채우기 투명도·선형 그라데이션, 아래 0.21.4)을 main 에 병합·적용.

## 0.21.4 - 2026-10-15 · 도형 채우기 투명도·선형 그라데이션 (engine-request #6)

- rect·ellipse·pill·text·plan 의 `fill` 에 **투명도·선형 그라데이션**: `"#RRGGBBAA"`(끝 두 자리 = 불투명도) · `{"color": "primary", "alpha": 0.5}` · `{"gradient": {"angle": 0, "stops": [[0, "#002F7B00"], [1, "#002F7B"]]}}`(angle 0 = 왼→오, 90 = 위→아래, 시계 방향 = PPT `a:lin`; 정지점 `[위치, 색, (불투명도)]` 또는 색 나열 = 고른 간격). 편집기는 CSS `rgba`·`linear-gradient`, PPTX 는 `a:alpha`·`a:gradFill`(gsLst + lin, scaled=0) — `common.fill_spec` ↔ `render.fillSpec` 같은 규칙, `check_parity` 가 예제 20개 + 덱의 모든 fill 을 비교. `docs/deck-format.md`.
- 편집기 서식 줄·속성 탭: 그라데이션 채우기는 견본에 그대로 보이고 이름은 "그라데이션·투명도 (요소 JSON 에서 고침)" — 토큰을 고르면 단색으로 바뀐다. 입력은 "요소 JSON (고급)" 에서.
- `export_pptx --selftest [--out x.pptx]`: 채우기 견본 6개를 내보내 슬라이드 XML(gradFill 위치·정지점·각도·alpha·단색 불변) 8항목 점검. 단색 채우기의 XML 은 전과 같다(solidFill 경로 불변).

## 0.21.3 - 2026-10-15 · 여러 요소에 한 요청 메모

- 서버 작업 카드 [적용됨]이 병합 커밋 해시(기본값 = 지금 main HEAD)를 물어 `appliedCommit` 으로 기록한다. 협업 세션: `docs/server-admin.md` 9절 "엔진 요청 적용 절차", `docs/mechanism.md` 엔진 요청 큐·개발 세션 흐름과 0.19~0.21 API, i18n 사전에 템플릿·시작 내용 설명문 46개.
- 요소를 여러 개 고른 채(Shift/Ctrl+클릭·범위 선택) 오른쪽 클릭 "이 요소 n개에 요청 메모" 또는 서식 줄 💬 — 팝오버에 "요소 n개 (글자 e03, 원 e05 …)", 요청에 `elements` 목록(`element` 는 첫 요소), 캔버스에 요소마다 테두리, 요청 카드에 "e03 외 2". 세션에는 `elements` 가 전달되고 `draft_deck --element e03,e05`(쉼표)로 줄 번호를 본다. 전에는 여러 개를 골라도 첫 요소 하나만 담겼다.

## 0.21.2 - 2026-10-15 · 글자 크기 일괄 확대 scale_fonts · content fontScale (engine-request #5)

- **`scale_fonts <덱> --ratio 1.2 [--role body,title] [--slides …] [--dry-run] [--keep-ratio] [--no-fit]`**(`studio/scale_fonts.py`): 덱 전체 글자 크기를 비율로 키우고(바닥 부품·잠긴 요소는 `--role` 로 고르지 않으면 그대로) 글이 상자보다 커지면 상자 높이(칩은 폭, 표는 `rowH`)를 늘려 아래 요소를 내린다. 바닥을 넘치면 그 장만 비율을 0.02 씩 낮춘다. 저장은 `save_deck` 과 같은 경로(변경 원장·백업·충돌 검사).
- content `"fontScale": 1.2 | {ratio, roles, keep}`(장 전체·슬라이드별, 0 = 뺌)을 `build_deck` 이 같은 규칙으로 적용 — 다시 빌드해도 유지. `docs/operation.md` "글자 크기 일괄 확대" · `deck-format.md` · `templates.md`(lecture-large 와의 차이).
- 엔진 개발 세션(engine-request #5)이 만들어 main 에 병합·적용. 검증: `check_parity` 모두 같음 · 시험 덱 ×1.2 저장 뒤 `check_layout` ERROR 0.

## 0.21.1 - 2026-10-15 · 덱 관리 · 세션 ID 복사·검색 · 엔진 요청 #4 적용

- **덱 관리**(`studio/deck_admin.py`, `POST /api/decks`, `nexa.py deck …`): 편집기 덱 탭 끝 **＋** = 새 덱(이름·제목 → 표지 1장), 탭 **오른쪽 클릭** = 제목 바꾸기(덱 + `content/<id>.json`) · 덱 이름(id) 바꾸기(요청·기록 `.history`·첨부 `out/attach`·content 를 함께 옮기고 안의 id·첨부 경로도) · 새 덱 · 삭제(`decks/.trash/<id>-<시각>/` 로 이동). 웹 세션 턴이 도는 중에는 이름 바꾸기·삭제 거절. `docs/editor.md` 덱 관리 절.
- 세션 ID 배지: 누르면 **ID 복사**, Shift+누르면 확인 명령(`cd "<폴더>"; claude --resume <ID>`) 복사. 클립보드 API 가 막힌 환경은 숨은 입력칸으로. Studio 칩 메뉴도 두 항목. claude 세션 표시 이름을 `nexa-slide web: <폴더> #<ID 앞 8자리>` 로 — `claude --resume` 목록에서 `#56e85d12` 로 검색해 고를 수 있다.
- 서버 작업 카드: 세션이 꺼진 채 할 일이 있어 배너가 보일 때 세션 줄의 [세션 시작]을 감춰 버튼이 둘 되지 않게. 배너 문구는 승인 대기/처리 대기 수.
- 엔진 요청 #4(`place`·`extra`·`spread`·`rowH`·`rowSpread`, 아래 0.20.3) 를 main 에 병합·적용.
- 검증: 덱 관리 CLI 전 과정(만들기·중복/잘못된 이름 거절·이름 바꾸기와 딸린 것 이동·제목·휴지통) · 헤드리스 스모크 44단계(＋·제목·이름·삭제 포함) · `check_parity` · 회귀(웹 검색·후속·서버 작업·B-5·동시 기동).

## 0.21.0 - 2026-10-15 · 세션 식별자 · 상태 자동 갱신 · 승인 대기 알림 · Word·Excel·PDF 내용 추출

- **세션 식별자**: 웹 세션·엔진 개발 세션이 시작할 때 claude 세션 ID 를 정해(`--session-id`, 이후 `--resume`) 턴 0 부터 시작 페이지 세션 줄·서버 작업 카드·Studio 세션 칩 메뉴에 `ID 1a2b3c4d` 표시 — 누르면 `cd "<폴더>"; claude --resume <ID>` 복사.
- **새로 고침 없이 갱신**: 시작 페이지가 5초마다 최근 작업의 서버·세션 상태와 서버 작업 카드를 다시 읽는다(`/api/home/live`, 창이 열려 있거나 입력 중이면 건너뜀).
- **승인 대기 알림**(관리자): 메뉴 단추 숫자 배지·탭 제목 `(n)`·새 요청 토스트(+선택: 데스크톱 알림), 모든 페이지에서 10초마다(`/api/engine/notice`). 폴링 줄은 접근 로그에서 뺀다.
- **`import_doc <파일>`**(`studio/import_doc.py`): Word(.docx — 제목 수준·문단(굵게)·목록 수준·표·각주·그림) · Excel(.xlsx/.xlsm — 시트별 표·날짜 변환·수식(계산값이 없으면 수식 그대로)·병합·숨긴 시트·차트 계열 값(캐시가 없으면 참조를 셀에서 찾음)) · PDF(책갈피·쪽별 글·표·그림, PyMuPDF — 없으면 pypdf 로 글만) → `out/import/<이름>/content.md`·`content.json`·`images/`. Word·Excel 은 추가 설치 없음, PyMuPDF 는 선택(`requirements.txt`). 입력·출력은 작업 공간 안만. `--selftest`. 웹 세션 턴 프롬프트·help·실행기·문서.
- 검증: import_doc selftest 10항목 · 실제 엑셀(차트·병합·날짜)·PDF(표·그림·책갈피) 추출 · 밖 파일 거절, 실제 sonnet 턴이 엑셀·PDF 첨부를 import_doc 로 읽어 값을 답함 + 세션 ID 가 턴 전후 같고 claude 세션 파일 생성, 헤드리스 스모크 40단계(승인 대기 배지·탭 제목·토스트·주기 갱신·표시 언어와 제목 접두), 회귀(웹 검색·후속·서버 작업·B-5·git 실제 턴).
## 0.20.3 - 2026-10-15 · content 에서 요소 자리·앞뒤 순서·추가 요소 · 글머리/행 균등 간격 (engine-request #4)

- **`place`·`extra`**(모든 레이아웃, `layouts.apply_place`): content 의 슬라이드에 `"place": {키: {x, y, w, h, z, fill, color, text, …} | null}` 로 레이아웃이 놓은 요소를 덮어쓰거나 빼고, `"extra": [덱 요소…]` 로 레이아웃에 없는 요소(출처·질문 글상자 등)를 더한다. 키 = 요소 id(`e05`) · 역할(`title`·`crumb`…) · 유형#순번(`image#1`·`pill#2`). 원본 PPT 를 옮기는 덱이 덱에 덧입히던 것(다음 build 가 편집기 수정으로 보고 멈춰 매번 `--discard-edits`)을 content 로 옮긴다 — 다시 build 해도 같은 결과. 없는 키는 경고만. `docs/deck-format.md`.
- **글머리 균등 간격** `bullets.spread`(render.js `bulletRows` ↔ common.py `bullet_rows` — export_pptx 에서 옮김): 행 높이(줄바꿈 수 + 1 줄)를 뺀 나머지를 행 사이에 고르게 나눠 상자 높이를 채운다(마지막 행 뒤 0). `check_parity` 가 글머리 행(기본·spread·행 하나)도 비교한다.
- **행 간격** `rowH`(px)·`rowSpread`(본문 영역을 행 수로 고르게) — `summary`·`lab`·`agenda`·`numbered_rows`(`layouts.row_pitch`). 주지 않으면 전과 같다.
- 검증: `check_parity -W example`(글머리 4개 포함 모두 같음) · 임시 작업 공간에서 place(id·역할·유형#순번·null 삭제·없는 키)·extra(z·직접 id)·spread·rowSpread·rowH 빌드 → `--force` 재빌드가 편집 감지 없이 통과 · `export_pptx` · `check_layout` ERROR 0 · 예제 덱(`demo`) 재빌드 결과의 행 좌표·필드 수가 저장소 덱과 같음(place·extra 가 없으면 전과 같은 코드 경로).

## 0.20.2 - 2026-10-14 · 서버 시작 출력의 pid

- `nexa.py start`·`restart`(`service.py start`)가 "시작: … (pid ?)" 로 찍히던 것 - 포트는 답하는데 `server.json` 이 아직 안 쓰인 순간(설정 포트로 찾음)을 잡았기 때문. 실제 pid 가 보일 때까지 잠깐(최대 3초) 더 기다린다. 동시 기동 시험 통과.

## 0.20.1 - 2026-10-14 · PPTX 내용 추출 · 템플릿 고르기 명령 (engine-request #3)

- **`import_pptx <파일.pptx> [--out <폴더>]`**(`studio/import_pptx.py`): AI 세션이 Read 로 열 수 없는 PPTX 첨부에서 슬라이드별 제목·본문(수준·굵게 `**…**`·가장 큰 글자 pt)·표(행×열)·차트(종류·제목·범주·계열 값)·SmartArt 글·발표자 노트·숨긴 슬라이드를 `out/import/<이름>/slides.md`·`slides.json`(도형마다 kind·role·box 1280×720 기준) 으로, 그림을 `images/`(같은 그림은 한 번, emf·wmf·bmp 는 Pillow 로 PNG) 로 꺼낸다. 그룹 안 도형 좌표는 슬라이드 기준으로 환산, 제목 자리가 없는 덱은 위쪽 1/3 의 가장 큰 글을 제목으로 추정(`title?`). 입력 파일과 `--out` 은 작업 공간 안만(웹 세션이 저장소 루트 접근을 받았으면 그 루트 안까지) - 이 명령으로 작업 공간 밖 파일을 읽지 못하게. `--selftest` 로 견본 PPTX(제목·노트·굵게·수준·표·차트·그림·그룹) 추출 점검.
- **`set_template [<이름>] [--json]`**(`studio/set_template.py`): 고를 수 있는 템플릿 목록(이름·라벨·설명, 숨긴 것 제외)과 현재 선택을 보이고, 이름을 주면 `nexa-slide.json` 의 `template` 을 바꾼다(`set_fonts` 와 같은 방식 - 공유 파일에만, PC 별 덮어쓰기 알림). 숨긴 템플릿은 `replacedBy` 를 안내. 반영에는 서버 재시작·`build_deck --force` 가 필요하다고 출력.
- `help`·실행기 설명·웹 세션 턴 프롬프트(PPTX 첨부는 `import_pptx` 로, 테마 변경은 `set_template` 로 하되 웹 세션 안에서는 재시작하지 않고 안내)·`docs/claude-session.md`·`docs/templates.md`·`docs/editor.md`.

## 0.20.0 - 2026-10-14 · 웹 세션 git·push·저장소 루트 권한

- 관리자 "AI 세션 전역 기본"에 **git 기록 허용 · push 허용 · 저장소 루트 접근**(사용자 설정 `sessionAllowGit`·`sessionAllowPush`·`sessionRepoRoot`, 기본 끔, 경고문). 세션 시작 창(허브·Studio)에 전역이 켜진 항목만 "이 세션에 … 허용" 체크(관리자만, 기본 해제, push 를 고르면 git 기록도). 작업 공간 설정에 `false` 로 끌 수 있다.
- 권한: git 기록 = `add`·`commit`·`switch`/`checkout`·`merge`·`branch`·`stash`·`tag`(+조회), push = `push`·`pull`·`fetch`, 저장소 루트 = `--add-dir <루트>` + 루트 아래 Read/Edit/Write(`.git/` 직접 수정 금지). 강제 push·`reset --hard`·`clean`·`rebase`·`config`·`remote`·`git -C`·`restore` 등은 켜도 거절. git 이 대화형으로 묻지 않게(`GIT_TERMINAL_PROMPT=0`·`GCM_INTERACTIVE=never`·`GIT_MERGE_AUTOEDIT=no`).
- 턴 프롬프트(허용 세션만): 저장소 규칙을 따른 커밋 메시지 + `Requested-by: <사용자>` 트레일러, 요청대로 브랜치→병합, push 전 확인·실패는 reply 에.
- 칩·세션 줄·시작 토스트에 `git`·`push`·`root` 배지, 접근 로그 `settings.sessionAllow…:on|off`·`session.start:…:git:push:root`.
- 검증: 임시 저장소(루트 작업일지 + `slides/` 작업 공간 + bare 원격)에서 **실제 sonnet 턴**으로 루트 문서 수정 → commit(트레일러) → push 확인, 거절 경로(전역 꺼짐·codex·권한 JSON) · 권한 강제 확인(`claude -p` 로 강제 push·reset --hard·config·`git -C` 가 DENIED, `git status` 는 ALLOWED, 저장소 변화 없음).

## 0.19.1 - 2026-10-14 · 후속 요청(대화)

- 요청 탭 카드의 **[후속 요청]** — 앞선 요청에 이어 묻거나 답한다(인라인 입력칸, 앞선 답 접어서 인용, ＋ 첨부·Ctrl+V, Enter 보내기). 새 요청에 `parent`·`thread` 가 붙고 대상(슬라이드·요소·영역)은 물려받으며, 원 요청은 그대로 둔다. 세션에는 같은 대화의 앞선 요청·답이 `context`(최근 6개)로 함께 간다.
- 요청 탭은 같은 대화를 한 묶음(연결선·들여쓰기·"후속" 표시)으로, 썸네일 배지는 대화 단위로 하나. 열린 요청의 답(질문)은 노란 줄. "다시 열기" 툴팁에 "답을 달려면 후속 요청".
- 처리 규약: 사용자에게 묻는 reply 면 `done` 으로 하지 않는다(`turn_prompt.md`·`claude-session.md`), 웹 세션은 질문으로 끝나는 reply 인데 `done` 이면 경고 이벤트.
- 검증: 후속 요청 서버 시험 9건(물려받기·후속의 후속·없는 parent 400·brief context·질문 판정) · 헤드리스 스모크(후속 요청 입력·Enter·묶음 표시) · 회귀(c1 실제 턴·c2·e2·b5) 통과.

## 0.19.0 - 2026-10-14 · 표시 언어(영어) · 웹 세션 웹 검색 허용 · 첨부 미리보기 · 서버 작업 카드 개편 · 기동 잠금

- **표시 언어**: 기본 메뉴(☰) "표시 언어" — `System (한국어)` · `English` · `한국어`(✓ 표시). 고르면 새로 고침 없이 즉시 바뀐다. `studio/i18n.js` 사전(약 920개 + 변수 문구 패턴)으로 DOM 글·placeholder·title·`<title>`·confirm/prompt 를 바꾸며, 동적 화면도 `MutationObserver` 로 반영. 시스템 기본 = 브라우저 언어. 저장 `localStorage nexa-lang`, 주소 `?lang=en|ko|system`. 템플릿·시작 내용·글꼴 목록 설명과 슬라이드 내용(데이터)은 번역하지 않는다. `docs/home.md` 표시 언어 절.
- **웹 세션 웹 검색 허용**(관리자): 설정 모달 "AI 세션 전역 기본 → 웹 검색 허용" 을 켜면 세션 시작 창에 "이 세션에 웹 검색 허용"(관리자만, claude 만)이 생기고 그 세션에서만 `WebSearch`·`WebFetch` 가 열린다(curl·wget·powershell·mcp 는 계속 거절). 칩·세션 줄에 "웹 허용", 접근 로그 `settings.sessionAllowWeb:on|off` · `session.start:…:web`, 턴 프롬프트에 출처 URL·`research/<주제>.md`·검색어에 내부 정보 금지 규칙. `docs/server-admin.md` 보안 주의.
- **요청 첨부**: 작은 📎 → 테두리 있는 **＋ 첨부** 버튼(요청 탭·메모 팝오버·서버 작업 요청 양식). 축소판을 누르면 새 창 대신 **화면 위 미리보기(라이트박스+캐러셀, `studio/lightbox.js`)** — ◀ ▶·← →·스와이프·축소판 줄·"n / m", 휠 확대·끌어 이동·두 번 누르기, Esc·바깥·✕, [원본 열기]·[내려받기], PDF iframe, "이 슬라이드의 모든 요청 첨부" 토글. 붙여넣기·끌어다 놓기가 두 번 올라가던 것 수정.
- **요청 탭**: 제목이 연결된 세션의 에이전트에 따라 "Claude/Codex 에게 요청", 세션이 없으면 "AI 에게 요청". 세션이 없는데 대기 요청이 있으면 "세션이 꺼져 있어 처리되지 않습니다 — 웹 세션 시작…", 마지막 웹 세션이 서버 재시작·유휴로 끝났으면 그 사유·시각을 안내 줄·칩 툴팁·칩 메뉴에.
- **서버 작업 카드**(시작 페이지): 최근 작업 항목과 같은 4줄 틀(제목 · 엔진 경로 · 배지 main/작업 브랜치/상태별 요청 수 · 세션 줄 + 오른쪽 끝 알약 버튼), 요청 목록(첨부 축소판), 맨 아래 [요청 추가]. 요청 양식에 첨부(Ctrl+V·끌어다 놓기·＋ 첨부 → `hub/engine/attach/<요청 id>/`, 엔진 세션은 worktree `.nexa/attach/` 사본으로 Read). 처리·승인 대기가 있는데 엔진 세션이 꺼져 있으면 배너 — 관리자 [세션 시작] / 일반 사용자 [관리자에게 시작 요청](묶음 기록, 접근 로그 `engine.start_requested`), 메뉴 "서버 작업" 배지. 요청을 넣을 때·CLI 출력에 "엔진 개발 세션이 꺼져 있어 관리자가 시작해야 처리됩니다" 안내(작업 공간 세션은 원 요청 reply 에 옮겨 적음).
- **서버 2중 기동 경합 수정**: `service.py start` 가 작업 공간 잠금 `out/.studio/start.lock` 으로 줄을 세우고, 서버는 포트를 연 뒤 다른 서버가 먼저 떴으면 물러난다(허브 중계 자동 기동 + `nexa.py restart` 가 같은 초에 들어온 사례).
- 시작 페이지 [세션 시작] 창이 열리지 않던 결함(04f26a4 회귀, `#sessSaveRow` 를 그리기 전에 접근) 핫픽스. `engine_request.py` 는 작업 공간·세션 환경에서 `--kind/--user` 를 무시하고 `session`(승인 대기)으로 강제.
- 검증(격리 환경, worktree 엔진): 웹 검색 허용 25건 · 서버 작업 16건 · 동시 기동 ×4 ×3회 · 첨부 실제 턴(ZEBRA) · B-4/B-5/중계 회귀 · **헤드리스 클릭 스모크**(관리자·일반 사용자, 시작 페이지·Studio 주요 버튼, 콘솔 오류 0 — `scratchpad/smoke.js`).

## 0.18.4 - 2026-10-14 · 언어 이름표 표시 스위치

- 속성 탭 코드 언어 칸 옆에 **표시** 스위치(켜짐 초록) - 캔버스 언어 이름표 표시 여부, ⋯ 더보기 설정과 같은 값(기본 켜짐).
- 이름표의 "· 번호 없음" 표시 제거.
- 줄 번호 보기/숨김 단추도 같은 스위치로.

## 0.18.3 - 2026-10-14 · 코드 언어 이름표 설정

- ⋯ 더보기 → **코드 언어 이름표 표시**(기본 켜짐, 브라우저 기억). 화면 배치 초기화 때 함께 되돌린다.

## 0.18.2 - 2026-10-14 · 언어 이름 Bash

- 코드 언어 이름 "Bash · Shell" → **Bash**(별칭 sh·shell·zsh 는 그대로).

## 0.18.1 - 2026-10-14 · 코드 언어 이름표

- 편집 캔버스의 코드 블록 오른쪽 위에 설정된 언어 이름표(SQL · Rust …, 줄 번호를 숨겼으면 "· 번호 없음"). 편집 화면에만 - 슬라이드·발표·PPTX 에는 없음, 확대와 무관하게 같은 크기.

## 0.18.0 - 2026-10-14 · 코드 언어 35종 하이라이트 · 줄 번호 보기 · 복사

- 코드 요소 `lang` 에 언어 35종: Bash · PowerShell · C · C++ · C# · Java · Kotlin · Scala · JavaScript · TypeScript · JSON · YAML · INI/TOML · HTML/XML · CSS · SCSS/Less · Markdown · Diff · Python · Ruby · Perl · PHP · Go · Rust · Swift · Dart · Objective-C · VB.NET · Lua · R · GraphQL · Makefile · Dockerfile · SQL(기존 전용 규칙) · 일반 글자. 별칭(sh·cs·js·py·rs·html·ini·mssql …) 대소문자 무시. 정의는 `studio/code_langs.json` 한 파일, 화면(`render.js`)과 PPTX(`common.py`)가 같은 알고리즘(주석·문자열·변수·전처리·장식자·숫자·예약어·타입·함수 호출·키·태그·속성).
- `lineNo: false` = 줄 번호 숨김(화면·PPTX).
- 편집기: 속성 탭 언어 = 찾기 목록(입력하면 좁혀짐), 줄 번호 보기/숨김, 📋 복사. 서식 줄에 언어 단추(찾기 메뉴)와 📋. 여러 코드 요소에 함께 적용.
- 편집기 화면 글의 "—" 를 "-" 로, 코드 속성 제목의 설명 제거.
- 검증: `check_parity` 코드 43개(언어 35종 · 별칭 · 모르는 이름 · 대문자 · 이모지 · 줄 번호 숨김) 화면·PPTX 모두 같음(`tests/fixtures/code_samples.json`), 교재 ch00 PPTX 슬라이드 XML 53장 전후 동일(SQL 회귀 없음), PPTX 줄 번호 숨김 확인, headless 편집기에서 언어 찾기(rs → Rust, json)·줄 번호 숨김 확인.

## 0.17.2 - 2026-10-14 · 기본 화면 배치

- 기본 폭: 왼쪽 썸네일 레일 210 → 226px, 오른쪽 패널 330 → 392px. 노트·개요·검사는 아래(최대화 아님)가 기본.
- 이 배치로 처음 열 때 한 번, 브라우저에 저장된 패널 크기·최대화 상태를 비워 새 기본값으로 시작한다(`layoutVer`). 이후 조절한 크기는 다시 기억한다.

## 0.17.1 - 2026-10-14 · 최대화 배치

- 아래 줄 "⤢ 맞춤" 옆 **⛶ 최대화**: 노트·개요·검사 탭과 패널을 오른쪽 패널 아래로 옮겨 가운데를 슬라이드에 쓴다(자동 맞춤). 최대화 중에는 **🗗 복원** 으로 바뀌어 원래 배치로 돌린다. Ctrl+Shift+M, 브라우저 기억, 오른쪽 패널을 숨기면 먼저 복원. 높이는 아래 패널과 같은 스플리터·값을 쓴다.
- 오른쪽 패널에 가로 스크롤바가 생기던 것 정리.
- 최대화 배치에서 높이 스플리터가 노트 탭과 노트 사이에 걸리던 것 - 오른쪽 아래 영역 맨 위(노트 탭 위)로.

## 0.17.0 - 2026-10-14 · 여러 요소 선택·이동·공통 속성 · 패널 크기 조절

- **다중 선택**: Shift/Ctrl+클릭(캔버스·속성 탭 요소 목록), 빈 곳을 끌어 범위 선택, Ctrl+A(이 장 전체). 요소마다 얇은 선택 상자 + 묶음 점선 상자, 서식 줄 맨 앞에 "N개 선택".
- **함께 이동**: 끌기·방향키로 고른 요소 모두(잡은 요소 기준 격자 맞춤, 잠긴 요소 제외). 복제·복사·잘라내기·붙여넣기·삭제·앞뒤 순서도 여러 개(상대 순서 유지).
- **공통 속성**: 서식 줄의 값은 그 속성이 있는 요소 모두에 같은 값으로(글자 크기·글꼴·색·굵게·정렬·줄 간격·채우기·테두리·선·잠금). 속성 탭은 같은 종류 요소 모두에(위치·크기는 선이 아닌 모든 요소, 글자 내용은 주 선택만).
- **✥ 위치 조정(여러 개)**: 선택 묶음 기준 맞춤 6종, 가로·세로 같은 간격 분배, 주 선택과 같은 너비·높이·크기.
- **패널 크기 조절**: 왼쪽 레일에 더해 아래 패널(노트·개요·검사) 높이와 오른쪽 패널 폭도 경계를 끌어 조절, 두 번 클릭 = 처음 크기, 브라우저 기억. 크기가 바뀌면 슬라이드를 새 영역에 맞춰 다시 그린다(확대 "맞춤") - 창 크기·패널 접기도 같은 방식(ResizeObserver). 노트 패널 기본 높이 140 → 98px(70%).
- 검증: headless 브라우저에서 범위 선택 8개 · Shift+클릭 2개 · 함께 이동(둘 다 40px) · 아래 패널 98 → 181px · 오른쪽 330 → 432px 와 그때마다 확대 자동 맞춤 확인.

## 0.16.13 - 2026-10-14 · 내 편집도 "확인함" 전까지 표시

- 현재 편집기에서 수정한 변경(편집)도 다른 변경처럼 썸네일 배지·캔버스 파란 점선으로 표시한다 - 방금 고친 것을 바로 확인하고, "확인함" 으로 숨긴다. (0.16.0~0.16.12 는 내 편집을 기본으로 표시하지 않았다.)

## 0.16.12 - 2026-10-14 · 최근 수정 대상 - 제목 칸 넓힘

- 번호 · 출처 · 시각 칸을 최소 폭으로(시각은 "20분" 처럼 "전" 생략, 툴팁에 절대 시각) - 제목 칸이 남는 폭을 모두 쓴다.

## 0.16.11 - 2026-10-14 · 출처 배지 = 필터 칩 글자 · 단추 묶음 구분선

- 변경 목록·최근 수정 대상의 출처 배지 글자를 필터 칩과 같게: **편집**(현재 편집기, 초록) · **협업**(다른 편집기, 청록) · **AI** · **빌드** · **외부**. "편집기 · 나" 표기는 없앰.
- 필터 칩(무엇을 볼지)과 동작 단추(확인함 · 최근 3개 표시 · 표시 끄기) 사이에 구분선 - 다른 묶음으로 보이게.

## 0.16.10 - 2026-10-14 · 변경 필터·배지 "Claude" → "AI"

- 필터 칩과 출처 배지의 "Claude" 를 **AI** 로(툴팁 "AI에서 수정, 파일 직접 수정은 추정"). 원장 값(`origin: claude`)과 API 는 그대로.

## 0.16.9 - 2026-10-14 · 변경 필터 이름

- 필터 "내 편집" → **편집**(현재 편집기에서 수정), "다른 창" → **협업**(다른 편집기에서 수정). 편집기 배지 툴팁도 같은 말로.

## 0.16.8 - 2026-10-14 · 변경 탭 칩·단추·최근 수정 대상 표 다듬기

- 필터 칩: 높이 고정(개수 숫자 유무와 상관없이 같음), 미선택은 회색 · 선택만 검정 바탕 흰 글자, 마우스를 올리면 글자색 강조.
- 확인함 · 최근 3개 표시 · 표시 끄기: 진한 회색 바탕 기본, 마우스를 올리면 글자색 강조, 칩과의 간격을 조금 넓힘.
- 최근 수정 대상 표가 패널 밖으로 넘치던 문제 - 칸 폭 고정(번호 · 제목 · 출처 · 시각), 긴 제목은 말줄임, 바뀐 종류는 제목 툴팁으로.

## 0.16.7 - 2026-10-14 · 변경 탭 머리 정리

- 제목 오른쪽 **ⓘ** 단추로 설명 보기/숨기기(토글). 다른 단추·객체를 누르면 자동으로 숨긴다.
- 출처 필터를 색 칩으로(전체 · 내 편집 · 다른 창 · Claude · 빌드 · 외부 - 고른 칩은 진한 색), 칩마다 대상 설명 툴팁.
- 확인함 · 최근 3개 표시 · 표시 끄기 를 같은 폭으로 나눈 단추로.

## 0.16.6 - 2026-10-14 · 변경 표시 단추 정리 · 복제한 요소가 표시에서 빠지던 문제

- 변경 탭 단추를 목적별로: **확인함**(최근 변경까지 확인 - 모든 묶음을 미표시로, 이후 묶음마다 "표시"로 다시 확인) · **최근 3개 표시**(최근 묶음 3개의 "표시"를 대신 누름) · **표시 끄기/켜기**(변경 기록을 보지 않고 작업 - 묶음별 상태는 두고 화면 표시만 감춤, 브라우저 기억). 0.16.5 의 "표시 지우기"·"모두 다시 표시"를 대신한다.
- 수정: 묶음 안에서 같은 요소가 추가 → 삭제 → 다시 추가되면(복제 후 지웠다 다시 복제) 중간 삭제의 "사라짐" 이 남아 그 요소가 표시·점선에서 빠지던 문제 - 마지막 상태를 따른다(`ledger._merge_item`). 묶음 응답에 내부 키 `_els` 가 새던 것도 정리.

## 0.16.5 - 2026-10-14 · 변경 표시 - 내 편집도 켜기 · 모두 다시 표시

- 변경 탭 묶음마다 **표시/숨기기** 를 내 편집 묶음에도 - 기본은 표시하지 않지만 "표시" 를 누르면 썸네일 배지·캔버스 파란 점선으로 보인다.
- **모두 다시 표시**: "표시 지우기"(확인한 것으로) 나 숨기기를 되돌려 내 편집이 아닌 변경을 다시 표시한다. 전에는 되돌릴 방법이 없었다.

## 0.16.4 - 2026-10-14 · 변경 탭 "편집기" 배지가 스크롤되지 않던 문제

- 변경 탭 출처 배지 "편집기 · 나" 가 패널을 스크롤해도 제자리에 떠 있고 빨간 테두리가 붙던 문제: 배지 클래스 `editor` 가 글자 편집 상자 규칙 `.editor`(position:absolute · outline)와 이름이 겹쳤다. 배지 클래스를 `o-editor` · `o-claude` · `o-build` · `o-external` 로.

## 0.16.3 - 2026-10-14 · 기록 탭에 last-build.json 이 끼던 문제

- 기록 탭 맨 위에 "빌드 전 · 마지막 빌드 시각" 항목이 보이던 문제: `last-build.json`(백업이 아니라 마지막 빌드 결과 - build 의 편집 보호용)의 이름 `last-build` 도 "-build" 로 끝나 빌드 백업으로 분류됐다. 먼저 걸러 목록에서 뺀다(0.15.x 부터 있던 버그). 이름 정렬상 늘 맨 위에 와서, 되돌리면 "빌드 전" 이 아니라 마지막 빌드 결과로 돌아갔다.

## 0.16.2 - 2026-10-14 · 빈 슬라이드

- 슬라이드 추가 창 맨 위에 **빈 슬라이드** - 템플릿 기본 항목(로고 · 바닥 경로 · 워드마크 · 쪽번호)만 있는 장. 레이아웃 `blank`(레이아웃 탭·content 에서도 쓸 수 있다, 필드 `crumb`). 기본 항목은 템플릿 구조 부품(`foot_parts`)을 따른다.

## 0.16.1 - 2026-10-14 · 레일 "+ 새 슬라이드" = 맨 아래에 추가

- 왼쪽 레일 맨 아래 **＋ 새 슬라이드** 는 지금 슬라이드 다음이 아니라 **맨 마지막**에 넣는다. 특정 슬라이드 다음에 넣을 때는 그 썸네일 오른쪽 클릭 메뉴 "아래에 새 슬라이드…"(기존 동작). 추가 창 안내문도 위치에 맞게.

## 0.16.0 - 2026-10-14 · 변경 원장 - 편집기·Claude·빌드·외부 변경을 덱당 1,000건 보존

- **변경 원장** `decks/.history/<덱>/changes.jsonl`(`studio/ledger.py`): 덱 파일의 모든 쓰기를 한 줄씩 - 출처(editor · claude · build · external)와 확신도(exact · inferred · unknown), 행위(save · restore · build · detect · startup), 주체(세션 라벨 · 편집기 탭 id · 요청 id · 메모), 전후 (버전 · 크기 · sha256 · 직전 백업 파일), 장·요소 단위 diff. 덱당 최근 1,000줄(`nexa-slide.json` `ledger.keep`, `keep+100` 넘으면 압축, `seq` 유지). 교차 프로세스 잠금은 `out/.studio/ledger-<덱>.lock`(msvcrt / fcntl). 찢어진 마지막 줄은 무시. 문서 [docs/change-ledger.md](docs/change-ledger.md).
- 기록 지점 넷: ① `PUT /api/deck`(편집기 저장 · `?origin=claude` 세션 저장 · `?action=restore` 되돌리기, 헤더 `X-Nexa-Tab` 으로 이 창/다른 창 구분, 응답 `seq`) ② `build_deck.py --force`(원자적 쓰기로 바꾸고 build 줄) ③ `GET /api/version` 폴링에서 밖에서 바뀐 덱 발견 - (mtime_ns, size) 서명 → sha256, 1.5초 유예 뒤 원장 꼬리와 대조, 덮이기 직전 상태를 `<시각>-ext.json` 으로 저장(기록 탭 `ext`), 출처는 세션 연결 + `working` 요청 / 감시 세션 작업 중 / 다른 세션 작업 중 → "Claude 추정"(근거를 `evidence` 에), 아니면 "외부" ④ 서버 기동 때 마지막 줄과 파일 해시가 다르면 `startup` 한 줄.
- **`save_deck.py`**: Claude 세션용 저장 CLI - 서버가 있으면 `X-Deck-Version` 을 base 로 PUT(백업·409·원장은 서버가), 없으면 직접 쓰고 원장 줄. `claude-session.md` §3 과 작업 공간 CLAUDE.md 템플릿의 처리 규약을 "파일 직접 쓰기" 에서 "`save_deck` 으로 저장" 으로.
- **비교 규칙을 서버로**(`studio/deckdiff.py`): 0.15.3 편집기 JS `diffDeck` 을 1:1 이식(GEO/TXT 분류 · 60자 전→후 · 엄격 증가 LIS 이동 판정 · 추가/수정/이동/삭제 순서). 동등 비교는 키 정렬 canon + 정수값 float 정규화라 키 순서만 다른 같은 객체는 변경이 아니다(JS 와 다른 점 - 가짜 변경 제거). 요소 200개 상한(`truncated`), 덱 수준 키 변경은 `fields`. 편집기의 JS diff 는 제거(기준 구현은 `tests/deckdiff_ref.js`).
- **변경 탭 재작성**(같은 자리·같은 CSS 축): 출처 필터(전체 · 내 편집 · 다른 창 · Claude · 빌드 · 외부, 브라우저 기억) · **최근 수정 대상** 표(슬라이드별 마지막 변경 - 출처 배지 · 상대 시각 · 종류, 누르면 이동) · 묶음 목록(같은 출처·창에서 `ledger.groupGap` 60초 안의 저장은 한 묶음, 빌드·되돌리기·외부·요청 전환이 경계; 저장 N회(요약)) · 출처 배지(`.org` - 편집기 초록 · Claude 파랑 · 빌드 호박 · 외부 회색 · 추정은 점선 + 툴팁 근거) · **직전으로**(그 변경 직전 백업으로 되돌리기 - 백업이 50개 상한으로 지워졌으면 비활성) · 더 보기. 썸네일 배지·개요 배지·캔버스 점선은 "표시 지우기" 이후의 **내 편집이 아닌** 변경만. 기록 탭 되돌리기도 같은 경로(`restore`).
- API: `GET /api/changes/<id>`(`limit · before · since · origin · slide · group · recent · seq`, 각 줄 `backupExists`), `GET /api/version` 응답 `changes`. `atomic_write` 는 `ledger.py` 로 옮겨 서버·build·save_deck 가 같은 것을 쓴다.
- 검증: `check_changes.py --js` 33건(JS 기준과 동일 - 키 순서·이모지 길이 2건은 의도된 차이) + 속성 검사 3,000회; 임시 작업 공간 서버 시나리오 28건(편집기 저장 · 같은 내용 생략 · 다른 창 · 409 · save_deck 서버/직접 · 직접 쓰기 → Claude 추정 + `-ext` 백업 · 하트비트 없는 외부 쓰기 · 서버 켠 채 build(중복 없음) · touch 무시 · 재시작 startup · group/recent/필터/seq · 복원 · 찢어진 줄 · 압축) 모두 통과; `check_parity -W example` 같음; build 결과 JSON 이 main 과 동일; 교재 ch11 PPTX 슬라이드 XML 전후 동일. 설계 보고서 [docs/research/change-ledger-design.md](docs/research/change-ledger-design.md), 개발 과정 [docs/dev/0.16.0-change-ledger.md](docs/dev/0.16.0-change-ledger.md).

## 0.15.3 - 2026-10-14 · 표 행별 높이 `rowH`

- 표(`table`·`plan-table`)에 **행별 높이 `rowH`**(머리 행부터, `colW` 처럼 비율 - `h` 에 맞춰 나눔, 합을 `h` 와 같게 두면 px 그대로). 없으면 지금처럼 고르게. 모자란 행은 준 값의 평균, 0 이하·숫자 아님이 섞이면 무시. 화면(`render.js rowHeights`)·PPTX(`common.row_heights`) 같은 규칙, 실행계획 해설 표 콜아웃도 행별 위치를 따른다.
- 편집기 표 속성에 "행 비율" 입력. content `table` 레이아웃의 `rowH` 는 숫자(모든 행 같음) 외에 행별 목록(px)도 받는다.
- 검증: `check_parity` 예제·교재 작업 공간(표 30개) 모두 같음, `rowH` 없는 덱의 PPTX 슬라이드 XML 변화 없음.

## 0.15.2 - 2026-10-14 · 최근 작업 상태 표시 간소화 · 세 줄 배치

- 최근 작업 상태 글자("실행 중"·"중지됨")를 빼고 포트만 — 실행 중이면 초록 `포트 N`(실제로 쓰는 포트) + **중지**, 꺼져 있으면 회색 `포트 N`(설정 포트) + **시작**. 버튼으로 상태가 구분된다.
- 최근 작업 항목을 세 줄로: 1줄 제목 · 2줄 경로 · 3줄(오른쪽 정렬) 덱 개수 · 포트 · 시작/중지 · ✕.

## 0.15.1 - 2026-10-14 · 최근 작업 실행 상태 · 시작/중지, 저장소 루트 표식

- 최근 작업 항목마다 **실행 상태와 포트**: 실행 중이면 `실행 중 · 포트 N`(실제로 쓰는 포트) + **중지** 버튼, 꺼져 있으면 `포트 N`(설정 포트) + **시작** 버튼. 상태는 `server.json` 의 주소가 실제로 그 작업 공간을 내주는지 두드려 확인한다(항목들을 동시에).
- 시작은 서버만 띄우고 페이지는 그대로, 중지는 그 작업 공간 서버만 끈다(이 페이지를 내주는 서버 자신은 끄지 않음). `POST /api/project` 의 `start`·`stop`.
- 항목을 누르면 예전처럼 연다 — 이미 떠 있으면 서버를 다시 띄우지 않고 바로 이동(더 빠름).
- **저장소 루트 표식 `.nexa-slide.json`**(커밋): `{"workspace": "ppt"}` — 작업 공간 폴더 이름(slides · ppt · 그 밖의 이름)을 루트에 남긴다. 시작 페이지 열기·엔진 도구(`common.py`)·세션 훅·`init_workspace.py` 가 이것으로 작업 공간을 찾는다 — 이름을 바꾼 작업 공간도 루트에서 `service.py status` 등이 동작하고, 같은 루트에 다시 만들면 기존 작업 공간을 쓴다. 예전 저장소는 `nexa.py update_launcher` 가 더한다.

## 0.15.0 - 2026-10-14 · 여러 PC 에서 같은 저장소 — PC 별 설정 주입

- **PC 별 설정 `nexa-slide.local.json`**(작업 공간, git 제외): 공유 `nexa-slide.json` 위에 덮어써 읽는다(dict 는 안쪽 항목만). 엔진 위치·포트 등 PC 마다 다른 값을 커밋하지 않고 넣는다. 편집기·`set_fonts` 의 설정 저장은 공유 파일에만.
- **`.env` 로 엔진 위치 주입**: 작업 공간 `.env`(git 제외)의 `NEXA_SLIDE_HOME` 이 가장 먼저 쓰인다. 만들 때 샘플 `.env.example`(커밋)과 이 PC 의 `.env`(지금 엔진 위치)를 함께 둔다 — 다른 PC 는 샘플을 복사해 고친다. `.env` 의 다른 값도 엔진 도구에 환경변수로 넘긴다.
- **엔진 위치 순서**: 실행기(`nexa.py`)가 `.env` > `nexa-slide.local.json` > 셸 환경변수 `NEXA_SLIDE_HOME` > 이 PC 의 사용자 설정 > `nexa-slide.json` 순으로 실제로 엔진이 있는 첫 경로를 쓴다. 엔진을 한 번 실행하면(시작 페이지·`service.py start`·`init_workspace.py`) 그 PC 의 엔진 위치가 사용자 설정에 기록된다 — 엔진을 옮기면 새 위치에서 한 번 실행하면 된다.
- 실행기 명령 `engine`(엔진 위치 보기 · `engine <폴더>` 로 이 PC 전용 지정 · `--clear`), 엔진을 못 찾으면 찾아본 곳과 지정 방법을 안내.
- 예전 작업 공간: `python3 <작업 공간>/nexa.py update_launcher`(새 도구 `studio/update_launcher.py`) — 실행기를 바꾸고 `.gitignore` 에 `.env`·`nexa-slide.local.json` 을 더하며, 없으면 `.env.example`·`.env` 를 둔다.
- 시작 페이지 최근 작업·빈 포트 판정이 PC 별 포트까지 본다. `SLIDES.md` 에 "여러 PC 에서 쓰기".

## 0.14.0 - 2026-10-14 · 저장소형 작업 공간 (지정 폴더 = 저장소 루트, 슬라이드 = slides/)

- **지정한 폴더 = 저장소 관리 기준 폴더**: `init_workspace.py <폴더>` 가 폴더 자체가 아니라 `<폴더>/slides/` 에 작업 공간을 만든다 — 실행은 `python3 <폴더>/slides/nexa.py start`. 루트는 사용자가 기초 자료를 모아 정리하고 관련 소스도 개발하는 곳(구조 자유), 슬라이드는 그 자료를 근거로 `slides/` 에서 만든다.
- **루트에는 폴더를 만들지 않는다**: 만드는 폴더는 `slides/` 하나. 루트에는 md 만 — `SLIDES.md`(개념·구조·슬라이드 서버 실행 방법), 없을 때만 `CLAUDE.md`(`@slides/CLAUDE.md` 를 불러옴)·`AGENTS.md`. 이미 있는 파일은 건드리지 않고 넣을 한 줄을 알린다. `slides/CLAUDE.md` 에 "저장소 자료를 근거로" 안내를 덧붙인다.
- `nexa-slide.json` 에 `repo.root`. 폴더 이름이 `slides` 면 그 폴더가 작업 공간(상위 = 루트), 이미 작업 공간이 있는 폴더는 그대로 쓴다. `--flat`(예전 방식) · `--slides-dir`.
- 작업 공간 찾기(`common.py`)·세션 훅이 저장소 루트에서 `slides/` 를 찾는다 — 루트에서 `studio/service.py status` 도 동작.
- 시작 페이지: 만들 위치 = 저장소 루트(작업 공간 `slides/` 표시), git 저장소를 고르면 하위 폴더를 비움, 저장소 루트를 열면 `slides/` 를 연다. 미리보기·데모는 예전처럼 폴더 하나.
- 시작 페이지 **작업 공간 폴더** 칸(저장 위치 아래, 기본 `slides`) — 예: `ppt` 면 `<폴더>/ppt`(`--slides-dir ppt`). 열기는 루트 바로 아래의 작업 공간 폴더도 찾는다.
- 수정: 0.9.0 에서 빠진 시작 페이지 **열기·데모**(`open_ws`·`demo` 없음 → `NameError`, 최근 작업 열기 실패) 되살림.
- 시작 페이지 "명령으로 만들기"의 **bash · zsh** 명령은 경로 구분자를 `/` 로(Windows 도 `D:/…`) — PowerShell 명령은 그대로.
- 수정: 시작 페이지 기준 폴더 설정의 **찾아보기** 창이 설정 창 뒤에 가려지던 문제, **시작용 내용**을 골라도 "빈 시작"으로 돌아가던 문제(템플릿 목록을 다시 그릴 때 선택이 풀림).
- macOS·Linux: 서버 포트 재사용(`SO_REUSEADDR`)을 Windows 에서만 끔 — POSIX 에서 `restart`·다시 열기가 방금 끈 포트를 30~60초 열지 못하던 문제. 빈 포트 판정도 같은 규칙.
  세션 훅의 파이썬 이름을 실행할 때 고름(`python3` 없으면 `python`) — 만든 PC 와 여는 PC 의 OS 가 달라도 동작. 글꼴 포함 저장(`embed_fonts`)은 Windows 가 아니면 글꼴 설치 전에 안내하고 끝냄.
  `service.py stop` 이 이미 끝난 pid 에서 트레이스백 대신 정리. 낡은 `install_fonts.ps1` 안내 → `python3 nexa.py install_fonts`.

## 0.13.4 - 2026-10-13 · Windows venv 서비스 시작 시 콘솔 창 수정

- Windows 에서 venv 의 Python(`.venv\Scripts\python.exe <작업 공간>\nexa.py start`)으로 서비스를 시작하면 빈 콘솔 창이 뜨고, 그 창을 닫으면 서버가 끝나던 문제 수정. venv 의 `python.exe` 는 기본 Python 을 자식으로 띄우는 런처라 `DETACHED_PROCESS`(콘솔 없음)로 띄우면 자식이 새 콘솔을 연다 - `service.py` 가 `DETACHED_PROCESS` 없이 `CREATE_NO_WINDOW` 의 숨은 콘솔을 물려주도록 바꿨다. 시작한 터미널을 닫아도 서버가 유지되는 동작은 그대로(시스템 Python·venv 모두 start·restart·stop 확인).

## 0.13.3 - 2026-10-02 · 시각 템플릿 graphite

- 승인한 참고 덱 101(디자인 시스템 관리자처럼 콘텐츠 덱 정리하기)을 **`graphite`** 템플릿으로: 흰 바탕, 검정 글자, 강조색 없이 회색 단계와 검정 굵기만, 가는 회색 선 구획, 큰 검정 숫자, 모서리 없음, 쪽 번호만(`foot: minimal`). `lecture` 바탕. 등록부에 구현 기록.

## 0.13.2 - 2026-10-02 · 추천 시각 템플릿 4개

- **추천 시각 템플릿 4개** 엔진에 추가(`lecture` 바탕, 색·글꼴·모서리·부품만): `editorial`(미색·명조·진홍, 고정폭 라벨 + 검정 띠) · `ledger`(크림·남색·금색, 명조, 모서리 없음, 남색 띠) · `signal`(노랑·검정·빨강, 굵은 고딕, 검정 띠) · `forest`(숲녹색·크림·테라코타, 명조, 큰 장식 쪽 번호). 레이아웃 견본·시작용 짝 모두 검사 ERROR 0.
- 검토 등록부에는 "추천" 상태 그대로 구현 기록만 남겼다 — `/review` 에서 승인·보류를 계속 정한다.

## 0.13.1 - 2026-10-02 · 템플릿 유형 15개 시작용 기본 구성

- **템플릿 유형 15개 모두 시작용 내용으로**: 목적별로 슬라이드 유형 11~14가지를 섞은 기본 구성(11~17장, 긴 덱은 장 구분 포함). 새로 10개 — `research-report` · `investor-pitch` · `sales-proposal` · `case-story` · `marketing-campaign` · `consulting` · `training-course` · `classroom` · `public-policy` · `talk-story`. 기존 5개(`periodic-report` 등)도 같은 방식으로 늘렸다. 내용은 유형별 예시 — 장을 더하거나 바꾸는 것은 편집기 "유형으로"·"유형 바꾸기".
- 15개 모두 빌드·레이아웃 검사 ERROR 0. 검토 등록부의 템플릿 유형에 구현 기록(승인 상태는 그대로 — 검토는 계속).

## 0.13.0 - 2026-10-02 · 템플릿 부품 · 유형 바꾸기 · 덱·슬라이드 글꼴 · 세션 활동 · 이미지 자리 보완

- **템플릿 부품 `parts`**: 레이아웃 코드는 그대로 두고 공통 부품 모양만 템플릿이 고른다 — `labels: "mono"`, `foot: "band" | "titleblock" | "minimal"`, `pageGhost`. `swiss`(고정폭 라벨 + 아래 띠) · `blueprint`(고정폭 라벨 + 도면 테두리·SHEET) · `archive`(큰 옅은 쪽 번호) · `keynote`(쪽 번호만). 장식은 `role: "decor"` 로 검사에서 뺀다.
- 편집기 **유형 바꾸기**: 썸네일 메뉴 "유형 바꾸기…" — 제목 글자·노트·id 를 남기고 다른 슬라이드 유형으로 바꾼다.
- **덱·슬라이드별 글꼴 세트**(`fontPreset`): 슬라이드 > 덱 > 작업 공간. 슬라이드 속성에서 고르고 편집기·PPTX·검사·쓴 글꼴 기록이 같은 규칙(`preset_fonts` ↔ `presetFonts`).
- **세션 활동 표시**: 새 작업 공간에 Claude Code 훅(`.claude/settings.json` → `nexa.py session_hook`)을 만들어 세션 칩에 "대화 작업 중 N분째 · 요청 n 대기" / "요청 처리 중" / "대기 — 요청 바로 처리" / "다른 세션 N" 을 보인다(`out/.studio/activity.json`).
- 새 작업 공간에 **`AGENTS.md`**(Codex·Gemini CLI·Cursor 용 같은 규칙 — 요청은 1회 대기 반복).
- 시작 페이지: 경로에 `&` 가 있으면 경고하고 명령을 실제 파이썬 실행 파일 경로로 안내(pyenv-win `python3` .bat 대리 실행기 문제).
- `lecture` 알약·태그 글자 15px 로(최소 글자 크기 검사 통과).
- Genspark 이미지 자리: CSS 배경(style 속성·`<style>` 클래스)으로 넣은 사진 11개 보완 — 199개(`04-image-slots.md`).

## 0.12.0 - 2026-10-02 · 승인 템플릿 반영 · 겹치는 기존 것 정리 · 슬라이드 유형 = 장 선별 기준

- **승인한 시각 템플릿 4개** 엔진에 추가: `keynote`(어두운 무대·금색·명조) · `archive`(종이 미색·테라코타·명조) · `blueprint`(도면 청록·주황·각진 모서리) · `swiss`(흰 바탕·빨강 하나·모서리 없음). 레이아웃 56종 견본 검사 ERROR 0.
- **승인한 템플릿 유형 5개 → 시작용 내용**: `periodic-report`(swiss) · `board-decision`(brief) · `ir-finance`(proposal) · `strategy-plan`(proposal) · `lecture-theory`(swiss) — 대표 장 흐름대로, 장마다 노트에 유형·목적(`build_type_starters.py`).
- **겹치는 기존 것은 숨기고 검토 대상으로**: 템플릿 `story`(→ archive)·`report`(→ swiss), 시작용 내용 `weekly-report`·`monthly-report`(→ periodic-report)·`decision-brief`(→ board-decision). `hidden: true` — 목록에서만 빠지고 이미 쓰는 작업 공간·`--starter` 는 그대로. `story-retro` 는 `archive` 로.
- 레이아웃 2종 추가(승인): `donut`(원호를 굵은 곡선으로 — PPTX 편집 가능) · `heatmap`(값 4단 색, 코호트 빈 칸). 결론 패널 색 토큰 `panel`·`on-panel`(어두운 템플릿에서도 읽히게).
- **슬라이드 유형 = 장 선별 기준**: 54개로(도넛·히트맵 추가), 유형마다 고를 신호 `when`. `nexa.py slide_types [낱말] [--json] [--group]`, 작업 공간 `CLAUDE.md` 에 "초안·요청 처리 때 내용 성격에 맞는 유형으로 고른다". 문서 `docs/slide-types.md` 선별 기준.
- 검토 등록부: 승인 안 된 대상 상태 초기화, 승인 대상에 구현 기록("구현됨"), 숨긴 기존 템플릿·시작용 내용을 검토 대상으로(그 템플릿으로 빌드한 미리보기).

## 0.11.0 - 2026-10-02 · 슬라이드 유형 52개 · 새 레이아웃 17종 · 템플릿 유형 15개 · 유형 검토

- **새 레이아웃 17종**(`studio/layouts_more.py`, 기존 요소만 — 렌더러 그대로): 본문 + 결론 패널 · 선 그래프 · 숫자 + 근거 차트 · 범위 막대 · 깔때기 · 선택지 열(추천 강조) · 사분면 · 큰 번호 행 · 트리 · 인물 카드 · 사례 제시 · 사진 도판 · 사진 + 한 문장 · 단계별 풀이 · 확인 문제 · 참고문헌 · 예상 질문. Genspark 전수 조사의 새 유형(03-slide-archetypes) 1·2순위 구현.
- **슬라이드 유형 52개**(`studio/slide_types.json`, 문서 `docs/slide-types.md`): 색·배치가 아닌 목적·구성 기준 8묶음. 유형마다 레이아웃 + 목적에 맞는 예시 내용 + 이미지 자리 안내. `GET /api/slidetypes`(유형별로 빌드한 슬라이드).
- 편집기 **슬라이드 추가 창**: "＋ 새 슬라이드" → 유형으로(목적별 미리보기 카드·찾기) / 레이아웃으로.
- **템플릿 유형 15개**(추천): 156개 덱을 목적·구성·시각 유사성으로 묶음 — 근거 덱·어울리는 시각 템플릿·대표 장 흐름(`docs/research/genspark-skills/05-template-types.md`).
- **검토 등록부**: 추천 상태("추천")와 분석 대상("등록") 구분, **슬라이드 유형 검토**(`/review/slides`, 기본 메뉴) 추가 — 엔진으로 그린 예시 + 근거 장, 템플릿 유형은 대표 장 흐름을 엔진으로 그려 미리보기.

## 0.10.2 - 2026-10-02 · 템플릿 검토를 시작 페이지에

- 검토 등록부를 별도 서버 첫 화면이 아니라 **시작 페이지(허브)에 붙는 페이지** `/review` 로 — 시작 페이지 탭·기본 메뉴 "템플릿 검토", 검토 화면에도 기본 메뉴. API 는 `/api/review/…`, 원본은 `/review/gs/…`(허브 서버가 `review_server` 모듈을 불러 처리, 따로 실행도 같은 경로).

## 0.10.1 - 2026-10-02 · 검토 등록부

- `docs/research/review/` - 템플릿·레이아웃 후보와 참고 자료(덱·사이트·파일)를 등록·미리보기·검토·승인하는 로컬 도구(`review_server.py` → http://127.0.0.1:5590/). 등록일·검토일·승인일·이력·메모를 `registry.json` 에 남기고 최근 등록 순으로 검토한다. 참고 덱은 전체 장 썸네일과 원본 HTML 실제 비율 보기. Genspark 조사 결과(템플릿 후보 8 · 레이아웃 28 · 참고 덱 156)를 `import_genspark.py` 로 등록. 원본은 저장소 밖에서 읽기만 한다.

## 0.10.0 - 2026-10-02 · 변경 기록 · 작업 공간 글꼴 · 글꼴 포함 PPTX · Genspark 전수 조사

- 편집기 **변경** 탭: 밖에서(Claude 등) 바뀐 덱을 다시 불러올 때 전·후를 비교해 장(수정·추가·삭제·이동 - 순서 유지 최장 흐름 밖만 이동)·요소(글자 전 → 후·위치·크기·모양·그림)별로 남긴다. 썸네일·개요 배지, 캔버스 파란 점선, 변경 묶음별 표시·숨기기.
- **작업 공간 글꼴**: 글꼴 파일은 엔진에 두지 않는다(`.gitignore`) — 작업 공간 `fonts/` + `nexa-slide.json` 의 `fontPresets`(전용 세트, 템플릿 세트보다 우선). 서버가 `fonts/` 를 내보내고(`/wsfonts/…`, `GET /api/fontcss` 자동 @font-face), 레이아웃 검사도 `fonts/` 로 잰다. `nexa.py install_fonts`(현재 사용자 설치), 새 작업 공간에 `fonts/README.md`. 추천 글꼴 내려받기 캐시는 엔진 밖으로.
- 편집기 글꼴 표시: 작업 공간 세트를 쓰면 머리줄 칩, ⋯ 메뉴 세트를 템플릿 기본/작업 공간 지정으로 나눔, **글꼴 창**(역할별 글꼴·견본·측정 파일, fonts/ 파일·설치 여부, 세트 JSON 수정·저장 - `POST /api/fonts savePreset`).
- **쓴 글꼴 기록**: 내보낼 때마다 `out/<덱>.fonts.json`(세트·역할별 글꼴·PPTX 에 실제로 들어간 글꼴마다 무료/시스템/전용·원본 파일·설치·포함 허용 fsType) — `font_report.py`.
- **글꼴 포함 PPTX**: 내보내기 메뉴 "PPTX — 글꼴 포함" · `nexa.py embed_fonts <덱>` → `out/<덱>-fonts.pptx`(PowerPoint COM, 쓴 글자만). 작업 공간 글꼴이 설치 안 됐으면 설치할지 묻는다.
- **무료 글꼴 목록·안내 페이지**: `studio/font_catalog.json`(무료 OFL 10종 · 시스템 기본 2종, 이름·라이선스·공식 받는 곳만), `/studio/fonts.html`(규칙, 이 작업 공간 글꼴 상태, 받기 링크, OS별 설치) · `GET /api/fontguide`. 목록 밖 글꼴은 "전용"으로 경고.
- 문서 `docs/fonts.md`, 엔진 `CLAUDE.md` 규칙(글꼴 파일 금지).
- 조사 `docs/research/genspark-skills/` - Genspark 공개 스킬 156개(2,274장) 전수 조사: 01 전수 표 · 02 시각 계열 9묶음과 템플릿 후보 8개 · 03 기존 레이아웃 대응 76% 와 새 유형 28개(우선순위) · 04 이미지 자리 6형태·역할 8가지·어울리는 이미지, `data/`(우리 말 요약만 — 원본은 저장소 밖).

## 0.9.0 - 2026-10-02 · 미리 보기 · 명령으로 만들기 · AI 연결 문서 · 새 덱 안내

- 시작 페이지 **미리 보기**: 템플릿 카드·시작용 내용 카드·새로 만들기 양식에서 템플릿 × 내용으로 실제 빌드한 슬라이드를 창으로 본다(썸네일 → 크게 보기·← →, 덱 탭, "이 조합으로 만들기"). 내용을 고르지 않으면 레이아웃 견본(레이아웃마다 한 장). 사용자 설정 폴더 `hub/preview/<템플릿>--<내용>/` 에 임시 작업 공간을 만들어 빌드하고 엔진·템플릿·내용이 바뀌면 다시 만든다(`GET /api/preview`).
- **명령으로 만들기**: 새로 만들기 양식 아래에 양식 값으로 채운 `init_workspace.py` 명령과 서버 시작 명령을 보여 준다(PowerShell · bash, 복사 버튼, 경고). 서버 `plan`(`POST /api/project action=plan`)이 폴더·포트·명령을 정하고 "만들고 Studio 열기"도 같은 명령을 실행한다.
- 포트 칸: 비우면 비어 있고 최근 작업 공간 설정이 쓰지 않는 포트(허브 포트 제외)를 제안, 적으면 그 포트. 하위 폴더는 폴더·저장소 지정일 때 제목으로 자동 채움(저장소면 `slides`, 직접 고치면 유지, 기본 위치로 돌아가면 비움).
- `init_workspace.py`: `--port N|auto`(쓰는 포트·허브 포트 거절, 다른 작업 공간 설정과 겹치면 알림, 기존 작업 공간은 포트만 변경) · `--build` · `--purpose` `--audience` `--direction`… `--material`…(BRIEF.md) · `--ask-draft` · `--no-remember`. 만든 작업 공간을 최근 작업에 올리고, 끝에 붙여 넣을 수 있는 절대 경로 명령을 안내한다. 브리프·빌드·초안 요청 로직을 허브에서 옮겨 와 버튼과 명령이 같은 결과를 낸다.
- 편집기: 2초 확인에 덱 목록·설정·엔진 버전을 함께 받아(`/api/version` 의 `deckIds`·`decksVer`·`config`·`engine`) 새 덱이 생기면 덱 탭을 바로 갱신하고 "새 덱 — [열기]" 안내, 설정이 바뀌면 자동 다시 적용, 엔진이 바뀌면 [새로 고침] 안내.
- 문서 `docs/ai-editing.md` - 새로 만든 작업 공간에서 AI 로 고치기: Claude Code(터미널·VS Code·Desktop) 상시 감시, 그 밖의 AI(Codex·Gemini CLI·Cursor) 1회 대기 반복·수동 방식, 요청·초안·마무리·문제 해결.
- 수정: `column_chart`·`stack_bars` 필드 예시가 비어 있어 "새 슬라이드"·레이아웃 견본에서 빌드 오류가 나던 문제.
- 조사 `docs/research/genspark-skills/` - Genspark 공개 슬라이드 스킬 156개 전수 조사 계획·원칙·진행 현황(원본은 저장소 밖).

## 0.8.0 - 2026-10-02 · 목적별 시작용 교안 8종 · 목적별 디자인 6종 · 레이아웃 16종

- 시작용 교안(`starters/`): `weekly-report`(8장) · `monthly-report`(11장) · `decision-brief`(2장) · `schedule`(7장) · `story-retro`(12장) · `notice-onboarding`(10장) · `rfp-owner`(12장) · `rfp-response`(14장), `lecture-course` 보강(3일 시간표·한 문장 장). 용도별 인기 템플릿 조사에서 나온 공통 규칙(제목 = 결론, 결론 2장 안, 마지막 장 = 다음 행동, 숫자에 기준·실명·기한, 나쁜 소식 같은 무게)대로 예시를 썼다. `init_workspace.py --starter` 는 시작용 교안이 정한 디자인 템플릿을 기본으로 고른다.
- 디자인 템플릿 6종(`lecture` 바탕, `tokenOverrides` 로 색·글꼴·모서리만): `report`(네이비) · `brief`(차콜·딥 틸) · `story`(미색·테라코타·명조 제목) · `notice`(오렌지·큰 모서리) · `schedule`(블루) · `proposal`(인디고·골드). 칩·글자 최소 15px.
- 토큰: 상태색 `ok`·`caution`·`bad`·`info`·`idle`(+`-container`), 글꼴 키 `heading`(제목용, 기본 = 본문). `template.json` 의 `tokenOverrides` 를 `resolve_tokens` 가 적용(편집기·PPTX·허브 미리보기 공통).
- 레이아웃 16종(`studio/layouts_extra.py`, 기존 요소만 조합): `status_table` · `kpi_tiles` · `issue_cards` · `grid_cards` · `statement` · `quote` · `big_number` · `decision_brief` · `milestones` · `roadmap` · `gantt` · `week_grid` · `photo_text` · `agenda` · `column_chart`(누적·워터폴·합계 막대·여러 판) · `stack_bars`. 공통 필드 `action`(행동 띠)·`footnote`·`kick`.
- `bullets` 에 `aside`(오른쪽 작은 개념 차트 - 세로 막대·가로 누적 막대·범례).
- 문서 `docs/starters.md`(목록·디자인·공통 작성 규칙·레이아웃 필드).

## 0.7.0 - 2026-10-02 · 시작 페이지 · 기본 메뉴 · 제작 도구와 내용 분리

- 엔진에 슬라이드 내용을 두지 않는다: 작업 공간을 못 찾으면 현재 폴더를 쓰지 않고, 서버는 **허브(시작 페이지)** 로 뜬다(포트 5599, 실행 정보는 사용자 설정 폴더). 엔진 폴더 안의 작업 공간(`example/`)은 서버가 열지 않는다. 작업 공간이 필요한 도구는 안내를 내고 끝난다.
- 기준 폴더: 운영체제 기본 문서 폴더(Windows 알려진 폴더 - OneDrive 이동 포함, macOS `~/Documents`, Linux XDG) 아래 `NexaSlide/`, 제작마다 하위 폴더. `NEXA_SLIDE_PROJECTS` · 사용자 설정 `projectsRoot` 로 바꾼다. 사용자가 폴더·저장소를 지정하면 그 아래에 내용과 서버 실행 정보를 넣는다(`studio/paths.py`).
- 시작 페이지 `studio/home.html`(`hub.py`): 새 슬라이드 만들기(템플릿 · 목적·대상·작성 방향·참고 자료 → `BRIEF.md` · 저장 위치 · 첫 초안 요청), 폴더·저장소 열기(폴더 고르기 창, 작업 공간 없으면 그 자리에 만들기), 최근 작업, 튜토리얼, 데모(예제를 기준 폴더로 복사해 열기), 템플릿 목록, 샘플 사이트 등록·둘러보기.
- `/` 이동: 작업할 덱이 있으면 Studio, 없으면 시작 페이지. 만들기·열기는 그 작업 공간 서버를 띄워 Studio 로 넘긴다.
- 기본 메뉴 `studio/menu.js`: Studio·시작 페이지 머리줄 왼쪽 위 메뉴 단추 → 왼쪽 서랍(GitHub 방식) - 홈 · 새로 만들기 · 열기 · Studio · 튜토리얼 · 데모 · 템플릿 · 샘플 · 최근 작업(찾기) · 기준 폴더 설정.
- API: `GET /api/home` · `POST /api/project`(create/open/demo/forget) · `POST /api/settings` · `GET /api/fs`. 문서 `docs/home.md`.
- 0.6.0 시작용 교안(`starters/`)과 함께 병합 - 시작 페이지는 `starters/<이름>/starter.json` 을 인식한다.

## 0.6.0 - 2026-10-02 · 강의 교안 시작용(lecture-course)

- `starters/lecture-course/` - 실제 강의 교재(3일 과정)의 구성을 익명화한 시작용 교안: 공통 표지·전체 목차·EoD(`_common.json`), 과정 안내 장 ch00(본문 24장, 레이아웃 17종 예시)·이론 장 ch01(본문 12장, Mermaid 다이어그램), 일차 이름·표지 배지 선택값. 로고는 자리 표시, 내용은 자리 표시와 일반 예제(주문 관리).
- `init_workspace.py --starter lecture-course` - 시작용 내용·그림 복사, `partLabels`·`coverBadge` 반영, 빌드할 덱 안내.
- `docs/lecture-starter.md` - 구성 순서, 장·절·소분류·실습 번호 체계(장 번호 = 교육 순서), 각주·노트(원문) 규약, 작성 규칙.
- 수정: 작업 공간이 엔진과 다른 드라이브(Windows)에 있으면 실행기 `nexa.py` 안내 문구의 절대 경로 역슬래시가 문법 오류(유니코드 이스케이프)를 내던 문제 - 경로를 `/` 로 쓴다.

## 0.5.3 - 2026-10-02 · 요청 칸 Enter 남기기

- 편집기 요청 탭의 슬라이드 요청 칸: Enter = 메모 남기기(초안), Shift+Enter = 줄바꿈 - 요소 메모 팝오버와 같은 동작. 보내기는 그대로 아래 바 "요청 N개 보내기".

## 0.5.2 - 2026-10-02 · 바닥 각주 가로 배치 · 요청 입력 보관

- 바닥 각주(`role: footnotes`): 위치 표시(crumb)는 각주가 없는 슬라이드와 같은 왼쪽 아래 자리에 고정하고, 각주는 그 바로 위(아래 끝 668, 쪽번호 칩 위)에 9pt(12px)로 1, 2, 3 순서대로 가로로 잇는다. 한 줄 폭을 넘으면 각주 단위로 줄을 바꾼다(`layouts.foot_lines`).
- 바닥 각주 번호는 위첨자 대신 보통 숫자를 굵은 강조색(`==n==`)으로 - 작은 글씨에서도 번호가 잘 보이게. 본문 표식(`[[theory|¹]]`)은 그대로.
- 편집기: 아직 남기지 않은 요청 입력(요청 탭 슬라이드 요청 칸 · 요소 메모)을 덱·슬라이드·요소별로 브라우저에 보관 - 슬라이드를 옮기거나 새로 고쳐도 유지, 메모를 남기면 지움.

## 0.5.1 — 2026-10-01 · 새 프로젝트 시작 도구·설명서

- `studio/init_workspace.py <폴더>` — 작업 공간 뼈대(선택만 담은 nexa-slide.json · 실행기 nexa.py · CLAUDE.md 세션 안내 · 시작용 content · .gitignore · 자리 표시 로고), 빈 포트 자동 선택.
- `studio/layout_samples.py` — 레이아웃 21종과 필드 예시(초안 작성용, 실행기 `nexa.py layout_samples`).
- `docs/new-project.md` — 다른 폴더·저장소에서 VS Code(Claude Code)·Claude Desktop 으로 연결해 초안 작성·검토·내보내기까지, macOS·Windows 명령 병기.

## 0.5.0 — 2026-10-01 · 편집기 UI 개편 (Genspark 작업 화면 방식 차용, 슬라이드 디자인 불변)

- 모드 3분할 **편집(E) · 선택(M) · 그리기(D)** — 선택은 요소를, 그리기는 박스·펜·핀 영역을 눌러 그 자리 **메모 팝오버**(개체 종류별 빠른 칩, Enter = 추가) → 번호 배지·레일 ✎ 배지 → 아래 바 **"요청 N개 보내기"**(초안 → 대기, 즉시 전달). 취소 범위 = 이 슬라이드(없으면 전체).
- 모드 바 아래 **붙박이 서식 줄**: 글꼴 · 크기 px(프리셋)·pt · 글자색 · 굵게 · 정렬 · 줄 간격·세로 정렬 · 채우기 · 테두리 · 선 속성 · 복제 · 삭제 · 잠금 · **위치 조정 ▾**(정렬 6 · 순서 4 · 너비/높이/X/Y). 색은 템플릿 토큰 팔레트.
- 오른쪽 클릭 메뉴, 순서 단축키(Ctrl+] [ · Alt+Ctrl+] [), Ctrl+X/B, 모드 키 E/M/D, 도움말 ?.
- ✨ 레이아웃 고치기(검사 결과를 담아 바로 요청) · ✨ 다듬기.
- 바닥줄: 노트 · 개요 · 검사 탭, ◀ n/N ▶, **확대 10~300%**(Ctrl+휠 포인터 기준 · Ctrl+= - 0 1) · Space+끌기 화면 이동.
- 머리줄: 덱 탭 · ▶ 발표(F5 · Shift+F5 · N 노트·시간) · 기록(자동 백업 되돌리기) · 내보내기 ▾ · 더보기(글꼴 세트·템플릿·단축키).
- **바뀐 것이 없으면 저장하지 않음**. 레일 폭 조절·오른쪽 패널 접기·배치 기억.
- 서버: 요청 `draft`·`region`·`send`·`discard`, `GET /api/history/<id>`. 감시 이벤트에 `region` 포함.

## 0.4.1 — 2026-10-01 · 요청 감시 "가짜 연결" 방지

- Monitor 만료 시 셸만 끝나고 python 감시가 남아 하트비트만 쓰던 문제(편집기는 "연결됨", 요청은 전달 안 됨)를 막음:
  - `--ttl`(`--stream` 기본 1780초) 뒤 `{"event":"ttl"}` 을 내고 스스로 종료
  - `--takeover` 로 남은 이전 감시를 끝내고 넘겨받기

## 0.4.0 — 2026-10-01 · 디자인 템플릿

- `studio/templates/<이름>/`(template.json · tokens.json · design/) — 색·글꼴·글자 크기·검사 기준·디자인 기준 문서를 템플릿으로 묶음.
  - `lecture`(기본): 기존 디자인·크기 그대로(0.3 까지와 결과 동일 확인), 검사 기준 11·8·9pt — 크기 조정은 장 단위 검토에서
  - `lecture-large`: 글자만 일괄 확대(본문 15px · 각주 11px · 경로·쪽번호 12px) — 선택 사항
  - 원칙: 기능(검사·세션 연결·템플릿)은 Genspark 등에서 차용하되 구성·디자인은 기존 형태 유지
- 작업 공간은 선택만: `template`·`fontPreset`. 작업 공간 `tokens.json`·`designCss`·`check.minFontPt` 는 더 쓰지 않는다(`check` 는 ignore·ignoreSlides 만).
  - 글꼴 선택(`set_fonts.py`·편집기)은 `nexa-slide.json` 의 `fontPreset` 을 바꾼다
  - `/studio/tokens.json` 은 템플릿 + 선택을 매번 계산해 준다. `GET /api/templates`
  - `NEXA_SLIDE_TEMPLATE` 로 설정을 바꾸지 않고 미리보기
- 디자인 기준 문서(concept.html·tokens.css)를 템플릿으로 옮기고 회사 로고·문구를 자리 표시로 바꿈.

## 0.3.0 — 2026-10-01 · 레이아웃 검사

- `check_layout.py` + `GET /api/check/<id>` + 편집기 "검사" 탭(저장마다 자동 · 항목 클릭 = 요소로 이동·영역 표시 · 썸네일 ⚠ 배지).
- 규칙: `t1.overlap.text-text` · `t1.overlap.text-crosses-border` · `t2.cutoff.spill` · `t2.cutoff.container` · `t3.offslide` · `t4.font.min`(역할별 최소 pt) · `t5.mono.align`(실행계획 열 정렬).
  Genspark `check_slide_layout` 실측(규칙 id·기하 판정)을 본뜨고, Genspark 에 없는 최소 글자·고정폭 정렬·요소 이동을 더했다.
- 기준 설정 `nexa-slide.json` `check`(minFontPt · ignore · ignoreSlides).
- 검사로 찾은 실제 결함 예(교재 덱): 파일 경로 줄바꿈 겹침, 장 표지 설명 넘침, 8.25pt 글자.

## 0.2.0 — 2026-10-01 · 독립 저장소로 분리

sql-tutorial-with-oracle 저장소의 `ppt/studio`(슬라이드 스튜디오 v0)를 엔진으로 분리했다. 렌더·PPTX 규칙은 그대로다
(분리 전후 ch00·ch18 덱 빌드 JSON 과 PPTX 184·259 파트가 완전히 같음).

- **작업 공간 분리**: `--workspace` / `NEXA_SLIDE_WORKSPACE` / 위로 찾기, 설정 `nexa-slide.json`(경로·`assetRoot`·토큰·브랜드·부 이름·표지 배지·EoD 안내·포트).
  - URL `/studio/`(엔진) · `/out/`(산출물) · 그 밖 `assetRoot`.
- **여러 작업 공간 동시 운영**:
  - 작업 공간별 포트
  - 작업 공간당 서버 하나(중복 시작 거부)
  - 배타적 포트 열기(Windows `SO_EXCLUSIVEADDRUSE`)
  - `service.py start|stop|restart|status|url` 백그라운드 서비스, `status.py`
  - 실행 정보 `out/.studio/server.json`
- **Claude 세션 연결**:
  - `watch_requests.py --stream`(요청 묶음마다 JSON 한 줄 — Monitor 알림), 하트비트 `out/.studio/session.json`
  - 작업 공간당 감시 하나(중복 시 `refused`)
  - 편집기 세션 칩(연결됨/처리 중/연결 없음) · "요청 보내기"/"지금 보내기"(flush) · 요청 상태 `working`
- **배포**: MIT `LICENSE`, `THIRD_PARTY_NOTICES.md`(외부 구성요소 재배포 없음, 회사 CI 미포함), 예제 작업 공간 `example/`(자리 표시 로고), 문서 `docs/` 7편.

## 0.1 — 2026-09 · 슬라이드 스튜디오 v0 (sql-tutorial-with-oracle `ppt/studio`)

덱 JSON 단일 원본, 브라우저 편집기, python-pptx 기본 도형 PPTX, PowerPoint 렌더 미리보기·픽셀 비교, 요청 메모 → 세션 전달(1회 감시).
이력은 원 저장소 git 기록에 있다.
