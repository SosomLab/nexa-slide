# 설계 메모 — 작은 것 셋: 선·테두리 투명도 · 순서도 도형 4종 · mechanism.md 그림

> 협업 세션 정리, 2026-10-17. 엔진 요청 큐 항목의 근거. "결정" 표시가 없는 것은 **제안**이다.

## A. 선·테두리 투명도 (`stroke`·선 `color` 에 `#RRGGBBAA`)

출처: `docs/dev/pptx-feature-gap.md:15`("선·테두리 투명도 | 채우기만 alpha | 양쪽 | S | 후보").

**지금**
- 채우기는 이미 된다: `common.color_alpha`(`common.py:365`, `len==9`) ↔ `render.js colorAlpha`(`:24`), `fill_spec`/`fillSpec`, PPTX `alpha_el`(`export_pptx.py:189`, alpha<1 일 때만 `a:alpha val=alpha*100000`)을 `shape_fill_line` 채우기에 붙임(`:200-202`).
- 선 쪽은 `color()`(`common.py:349`, `render.js:14`)를 써서 길이 7 이 아니면 **기본값 `#000000`** — 지금 `stroke:"#RRGGBBAA"` 는 편집기·PPTX 모두 **검정 테두리**(버그에 가깝다).
- 선을 내는 곳:
  - render.js: `boxStyle`(`:599`, inset box-shadow), `strokeDashSvg`(`:610-616`), `elShape`(`:683-685`), 선·화살표 `lineSvg`(`:888`), 곡선 `elCurve`(`:910`), 표 테두리(`:954`), 그림 액자 `frameColor`(`:867`).
  - export_pptx.py: `shape_fill_line`(`:217-225`, `shape.line.color.rgb` → python-pptx 가 `a:ln/a:solidFill/a:srgbClr`), `style_line`(`:508`, `:513-514`), `_cell_border`(`:526`, `:531-532`), 액자(`:360`).

**결정(제안)**
- 범위 1차: 도형·상자 `stroke` + 선·화살표·곡선 `color`(둘 다 "선"). 표 셀 테두리·그림 액자는 같은 헬퍼로 바꾸기 쉬우면 같이, 아니면 후속.
- 규칙: `color_alpha`/`colorAlpha` 재사용. HTML 은 `rgba()`, PPTX 는 `a:ln > a:solidFill > a:srgbClr > a:alpha val="…"`(alpha<1 일 때만 — **불투명 선의 XML 은 지금과 바이트 동일**해야 회귀 0).
- 편집기: 채우기 쪽에 투명도 조절 UI 가 있으면 테두리 색 줄(`studio.js:1287` colorRow "테두리")에 같은 방식, 없으면 덱 JSON 으로만(문서에 명시).
- 문서: `docs/deck-format.md:16-20,25,43` 에 stroke/color 도 `#RRGGBBAA` 허용, `pptx-feature-gap.md:15` 상태 갱신.

**완료 기준·시험**
- `check_parity.py` 에 `STROKE_SAMPLES`(`"#002F7B80"`, 토큰 이름, `"#12345"` 잘못된 값, 알파 `FF`·`00`) — JS/Python 결과 동일.
- `export_pptx.py --selftest`(`:1243`, checks `:1266-1277`)에 `a:ln` 안 `a:alpha` 검사 추가. example 덱에는 넣지 않거나, 넣으면 기능 추가로 예제 XML 변경을 명시.
- 회귀: 불투명 선만 있는 덱의 슬라이드 XML 전후 동일(검증 ④).
- PowerPoint 가 있으면 `compare.py` 로 반투명 테두리 픽셀 확인.

## B. 순서도 프리셋 도형 4종 (프로세스·판단·문서·데이터)

**지금**: 21종(triangle … cube), `flowChart*` 0건. 도형 하나 추가에 손댈 곳(조사):
1. `render.js:649-673` `SHAPES` — `{ko, path(w,h,ss), rect(w,h,ss)}`. `shapeNames()`(`:675`)로 메뉴·속성·**삽입 패널 타일(`studio.js:2629`)이 자동 반영**.
2. `export_pptx.py:278-284` `SHAPE_PRESETS`(이름 → `MSO_SHAPE`, 없으면 DIAMOND 로 대체 `:289`).
3. `common.py:1027-1043` `shape_text_rect` — render.js `rect` 와 같은 식(`check_layout.py:92-93` 사용).
4. `import_pptx.py:75-80` `PRST_TO_SHAPE`.
5. `studio.js:2488` `SHAPE_SIZE`(선택, 기본 160×120).
6. i18n `studio/i18n/en.js:181`(한국어 이름 → 영어).
7. 시험 `tests/editor_ui_test.py:24` `SHAPES`, `tests/scenarios/shape_menu.json` 개수 21 하드코딩(`:9,:13`, 마지막 단계), `tests/i18n_scan.py:82`.
8. 문서 `docs/deck-format.md:43`, `docs/dev/web-session-design.md:251`("21종"), CHANGELOG.

**결정(제안)**

| 덱 이름 | ko / en | prstGeom | python-pptx(확인 필요) | 기하(OOXML presetShapeDefinitions 기준, 확인 필요) | 글 영역 |
|---|---|---|---|---|---|
| `flowChartProcess` | 프로세스 / Process | `flowChartProcess` | `MSO_SHAPE.FLOWCHART_PROCESS` | 사각형 | 전체 |
| `flowChartDecision` | 판단 / Decision | `flowChartDecision` | `FLOWCHART_DECISION` | 마름모(꼭짓점 변 중점) | w/4..3w/4, h/4..3h/4 |
| `flowChartDocument` | 문서 / Document | `flowChartDocument` | `FLOWCHART_DOCUMENT` | 21600 격자: (0,0)→(21600,0)→(21600,17322) cubic (10800,17322)(10800,23922)(0,20172) 닫기 | 0,0..w, h·17322/21600 |
| `flowChartInputOutput` | 데이터 / Data | `flowChartInputOutput` | `FLOWCHART_DATA` | 5×5 격자 평행사변형: (0,5)→(1,0)→(5,0)→(4,5) | 정의 파일의 textRect 값 |

- 이름은 기존 관례(prst 와 같은 camelCase — `rtTriangle`, `homePlate`)를 따라 prst 그대로.
- 판단·데이터는 기존 diamond·parallelogram 과 모양이 비슷하지만 **prstGeom 이 달라야** PowerPoint 에서 순서도 도형으로 인식된다 — 별도 항목.
- 기하·글 영역·enum 이름은 반드시 `presetShapeDefinitions.xml`(ECMA-376 Part 1 부록) 원본과 python-pptx 로 확인(조사 환경에 pptx 모듈이 없어 미확인).
- 삽입 패널: 끝에 4개 추가(6열 격자 → 25개 5줄). 구분 머리글은 이번 범위 밖.

**완료 기준·시험**: 4종이 편집기 메뉴·삽입 패널에 보이고, PPTX 에서 `a:prstGeom prst="flowChart…"` 로 나가며, PowerPoint 에서 열어 같은 모양(`compare.py` 가능하면). import_pptx 왕복 시 이름 유지. `check_parity`(shape_text_rect ↔ rect)·`editor_ui_test`·`shape_menu.json`(21→25)·`i18n_scan` 통과.

## C. `docs/mechanism.md` 그림 (엔진 요청 흐름)

**지금**: mechanism.md 는 **mermaid 8개**(`:6-7` 규칙: 구성=flowchart, 시간 순서=sequenceDiagram, 수명=stateDiagram, 그림마다 "단계 | 소스·함수" 표). 엔진 요청 흐름은 8절(`:310-371` — 큐 sequence `:315`, 상태 `:349`)에 **이미 있다**. 빠진 것(grep 0건): `link_origin`·`resume_origin`·`engineNote`(E-5 원 요청 연결·자동 재개), `watch_engine_requests`·`/nexa-slide-server`·하트비트 kind=manual·`--takeover`/`kill_tree`·[끊기]→`stop_manual`(수동 세션 12.2). `engine-request-design.md` 자체의 ASCII 그림(`:17-26`, `:39-43`)은 설계 초안이라 그대로 둔다.

**결정(제안)**: 새 형식 없이 **mechanism.md 의 mermaid 관례**를 따른다.
- 8절에 sequenceDiagram 하나: 작업 공간 세션 → `engine_request add --request` → `link_origin`(원 요청 `engineRequest:N`) → 개발 세션 done → `resume_origin`(engineNote) → 관리자 병합·재시작 → applied → 원 요청 `status: open` → 작업 공간 세션 재개. 뒤에 "단계 | 소스·함수" 표.
- 수동 세션: sequence(또는 state) 하나 — `/nexa-slide-server` → `watch_engine_requests --stream` 하트비트 → 요청 이벤트 → `stdout_closed` 종료 / `--takeover` `kill_tree` / 허브 [끊기] `stop_manual`.
- 1절 구성도(`:24`)에 수동 세션 노드가 없으면 추가.
- 이것은 문서 작업이라 **협업 세션이 맡아도 된다** — 개발 세션이 원하면 넘겨받는다.

**완료 기준**: mermaid 가 GitHub 미리 보기에서 그려지고, 표의 함수 이름이 코드에 실제로 있다(grep).
