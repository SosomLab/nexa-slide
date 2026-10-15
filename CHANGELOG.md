# 변경 이력

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
