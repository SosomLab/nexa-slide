# 덱 형식

원본은 두 가지다 — **내용 원본** `content/<id>.json`(레이아웃 이름 + 필드)과 그것을 빌드한 **덱** `decks/<id>.json`(요소 좌표까지 풀린 것, 편집기가 고치는 대상).

## 덱 JSON · 요소 모델

```json
{ "id": "ch00", "title": "…", "part": "day1", "version": "0.1", "updated": "…",
  "slides": [ { "id": "s01", "layout": "cover", "notes": "발표자 노트", "bg": "surface", "elements": [ … ] } ] }
```

**단위**: 좌표·크기·글자 크기 모두 **px (슬라이드 1280×720 기준)**. PPT 변환 시 EMU = px × 9525, pt = px × 0.75.
색은 토큰 이름(`primary`, `day1-container`, `s3` …) 또는 `#RRGGBB`. 반경은 px 또는 `r-s`/`r-m`/`r-l`/`r-full`.

**채우기 `fill`**(rect·ellipse·pill·text·plan)은 색 외에 투명도·선형 그라데이션도 받는다 — 편집기(CSS)와 PPTX(`a:alpha`·`a:gradFill`) 같은 규칙(`common.fill_spec` ↔ `render.fillSpec`, `check_parity` 가 비교):
- `"#RRGGBBAA"` — 끝 두 자리 = 불투명도(`00` 투명 ~ `FF` 불투명). `{"color": "primary", "alpha": 0.5}` 도 같다(토큰에 투명도).
- `{"gradient": {"angle": 0, "stops": [[0, "#002F7B00"], [1, "#002F7B"]]}}` — 선형 그라데이션. `angle` 은 도(0 = 왼→오, 90 = 위→아래, 시계 방향 — PPT `a:lin` 과 같음, 기본 0). 정지점 = `[위치 0~1, 색, (불투명도 0~1)]`, 색만 나열하면(`"stops": ["#DCE3F0", "#3F62A2"]`) 고른 간격. 바깥 `alpha` 는 전체에 곱한다.
- 편집기 서식 줄·속성 탭의 채우기는 단색 토큰만 고르고(고르면 그라데이션이 단색으로 바뀜), 그라데이션·투명도는 "요소 JSON (고급)" 에서 적는다.
공통 필드: `id`, `type`, `x`, `y`, `w`, `h`, `z`(선택, 없으면 배열 순서), `locked`(선택 — 편집기에서 이동·삭제 막음).

| type | 필드 | PPT 변환 |
|---|---|---|
| `rect` | `fill`, `radius`, `stroke`, `strokeWidth`, (선택) `text`·글자 필드 | 사각형/둥근 사각형(반경 = adjustments) |
| `ellipse` | `fill`, `stroke`, (선택) `text`·글자 필드 | 타원 |
| `pill` | `fill`, `color`, `text`, `size`, `bold`(기본 굵게) | 둥근 사각형(반경 = 높이/2) + 가운데 글자 |
| `text` | `text`, `size`, `bold`, `color`, `align`(left/center/right), `valign`(top/middle/bottom), `font`(body/heading/mono — `code` 는 mono 로 받음), `lineHeight`, `wrap`, (선택) `fill`·`radius`·`pad`[위,오,아,왼] | 글상자(자동 맞춤 끔, 여백 0) / fill 이 있으면 글자 있는 도형 |
| `image` | `src`(`assetRoot` 기준 경로) | 그림 |
| `line`·`arrow` | `x1`,`y1`,`x2`,`y2`, `color`, `width`, `head`(none/end/start/both), `dash`(solid/dash/dot) | 연결선 + 화살 머리(XML tailEnd/headEnd, lg) |
| `curve` | `points`(요소 상자 기준 [[x,y],…]), `color`, `width`, `head`(end/none) | 자유형 꺾은선(채우기 없음) + 끝 화살 머리 — 반원 되돌이 화살표 등 |
| `table` | `rows`(2차원, 첫 행 머리), `colW`(비율), (선택) `rowH`(행별 비율 - 머리 행부터, `h` 에 맞춰 나눔. 합을 `h` 와 같게 두면 px 그대로. 없으면 고르게), `header`, `headFill`, `headColor`, `size`, `font`(본문 셀 글꼴 역할 body/heading/mono, 기본 body), `colFont`(열별 역할 배열 `["body", "mono", …]` — 값은 `font` 와 같은 body/heading/mono, `code` 는 mono 로 받음, 빈 문자열·null·모자란 열은 `font`. 머리 행은 항상 본문 글꼴), `align`, `rule` | 표(스타일 없음, 머리 행 채우기, 본문 행 아래 선) · 행 높이 = `rowH` |
| `plan` | `text`(DBMS_XPLAN 원문), `size`, `lineHeight`, `fill`, `pad` — `[[값]]` = 경고 강조, `[[ok:값]]` = 개선 강조 | 고정폭 글자, 강조 run = 굵게 + 글자색 + **run 강조색(a:highlight)** |
| `table` 추가 | `merge`: `[[행, 열, 행수, 열수], …]`(0부터, 머리 행 포함 — 왼쪽 위 셀이 그 영역을 차지하고 덮인 셀은 그리지 않는다, 겹치면 앞 것만, 표 밖은 잘라냄). PPTX 는 셀 병합으로 | 편집기 표 속성 "셀 병합" 칸 |
| `image` 추가 | `mermaid`: 이 그림을 그린 mermaid 코드(편집기 ＋ 추가 → 다이어그램 코드(mermaid)… · 속성 [다이어그램 코드 수정…]). PNG 는 `assets/images/diagram-*.png`, 코드는 옆 `.mmd` | Node(npx) 필요 |
| `chart` | `chart`(`column` `stackedColumn` `bar` `line` `area` `pie` `doughnut`), `categories[]`, `series[{name, values[]}]`(원형은 첫 계열), `title`, `legend`(`none`·`bottom`·`right`, 기본: 계열 2개 이상·원형이면 아래), `labels`(값 표시), `grid`(눈금선, 기본 켬), `axisMax`, `size`(글자 px, 기본 14), `colors[]`(토큰·#hex) | 편집기는 SVG, PPTX 는 **PowerPoint 차트**(편집 가능 — 색·범례·값 표시·눈금 규칙은 같되 그림은 PowerPoint 가 그린다). 편집기 ＋ 추가 → 차트…, 속성 데이터 칸(`범주 \| 계열…`) |
| `icon` | `icon`(내장 아이콘 이름 — check close plus minus arrowRight/Left/Up/Down chevronRight/Left play pause stop info checkCircle xCircle warning question home user users mail doc folder calendar clock pin chat heart bolt search star flag gear), `fill`(아이콘 색, 기본 primary), `color`(대비 색, 기본 white) | 짧은 변 기준 정사각형. 편집기는 SVG, PPTX 는 custGeom 자유형(층마다 도형, 둘 이상이면 묶음) |
| `group` | `children`(요소 배열 — 좌표는 묶음 상자 `x,y` 기준), `x,y,w,h`, `rot`·`flipH`·`flipV`(묶음 전체) | PPTX 묶음 도형(grpSp). 편집기 Ctrl+G 묶기 / Ctrl+Shift+G 풀기(풀면 새 id), 크기 조절은 자식을 비율로. 표·묶음은 묶음 안에 넣지 않는다 |
| `plan-table` | `columns`, `colW`, `opCol`(들여쓰기 열), `rows[{cells, depth, hl:{열번호: warn/ok}, note}]`, `calloutW` | 표 + 오른쪽 설명 콜아웃(연결선 + 둥근 상자) |
| `shape` | `shape`(종류: `triangle` `rtTriangle` `diamond` `parallelogram` `trapezoid` `pentagon` `hexagon` `octagon` `rightArrow` `leftArrow` `upArrow` `downArrow` `leftRightArrow` `chevron` `homePlate` `star5` `plus` `callout` `roundCallout` `can` `cube`), `fill`, `stroke`, `strokeWidth`, `text`, `size`, `color`, `bold`, `align`(기본 가운데), `valign`, `pad` | PowerPoint 기본 도형(prstGeom, 기본 조정값). 편집기는 같은 기하를 SVG 경로로 그리고 글은 프리셋의 글 영역에 둔다. 편집기 ＋ 추가 → 도형… / 다이어그램… |
| `code` | `text`, `lang`(언어 35종 - 아래), `lineNo`(false = 줄 번호 숨김), `size`, `lineHeight`, `start`, `focus`[줄], `show`[[from,to],…] | 그룹 도형: 줄 번호 여백·코드 면·강조 줄 면·테두리·줄 번호 글상자·코드 글상자(run 단위 색·굵게·기울임) |
| `bullets` | `items`(문자열 또는 `{text, sub:[…]}`), `size`, `subSize`, `lineHeight`, `gap`, `subGap`, `dot`, `color`, `subColor`, `spread`(참이면 **균등 간격** — 행 높이(줄바꿈 수 + 1 줄, 자동 줄바꿈은 세지 않음)를 뺀 나머지를 행 사이에 고르게 나눠 상자 `h` 를 채운다. 원본 PPT 의 "세로 고르게" 글상자용), `autoNum`(기본 참 — 항목 글 앞의 **번호를 자동 감지**해 ● 대신 그 번호로 표기: `1. ` `1) ` `(1) ` `a. ` `A) ` `①` `가. `(번호 뒤 공백 필요, 두 자리까지 — `2024. 매출`·`1.5배` 는 번호가 아님). **글머리 기호**도 감지: `* ` `- ` `+ `(공백 필요)와 `· • ● ○ ◦ ■ □ ▪ ◆ ◇ ▲ ▶ ► → ➤ ✓ ✔ ✗ ★ ☆ ※` 등(공백 없어도) — 그 기호를 글머리 색으로 ● 자리에 그린다(● ■ ◆ ▲ ▼ ★ 은 60% 크기). `marker`(항목, 기본 `●`)·`subMarker`(하위, 기본 `–`) = **글머리 종류**: 기호 한 글자, 번호 매기기 `1.` `1)` `(1)` `a.` `a)` `A.` `A)` `①` `가.`(순번 자동 — 하위는 상위 항목마다 1부터, PPTX 자동 번호), `none`(글머리 없음, 내어쓰기도 없음). 글 앞에 적은 번호·기호가 있으면 그것이 우선. 편집기 속성 "글머리 종류"에서 고른다. 글은 그대로 두고 렌더만 바꾸므로 손으로 적은 번호를 지울 필요가 없다. 번호는 글 색·크기, 내어쓰기는 번호 폭만큼 넓어진다. `false` 면 감지하지 않음) | 단락 글머리(●/–, 글머리 색) · 번호 항목은 PPTX 자동 번호(`a:buAutoNum`, 가. 같은 것은 글자 그대로) · 뒤 간격 = 단락 뒤 간격 |

**인라인 강조**(text·pill·rect·ellipse·shape·table 셀·bullets): `**굵게**`, `==강조==`(CI 적색 굵게), `[[토큰|색 글자]]`, `__밑줄__`, `*기울임*`(한 글자 이상, 앞뒤에 글자·공백 없이), `{page}`(쪽 번호).

**링크**(선 제외 모든 요소): `link` — `https://…`(새 탭) · `#3`(3번 슬라이드) · `#<슬라이드 id>`. 발표 화면에서 누르면 이동, PPTX 는 click_action(hlinkClick). **그림자**: `shadow: true` 또는 `{blur, dx, dy, color, alpha}`(기본 6·2·3·검정·0.3 — 편집기 drop-shadow, PPTX outerShdw). **그림 자르기·투명도**(image): `crop: [왼, 위, 오른, 아래]`(0~0.95 비율, PowerPoint crop 과 같은 뜻), `opacity`(0~1).

**회전·뒤집기**(text·pill·rect·ellipse·shape·image): `rot`(도, 시계 방향, 중심 기준 — PPT 의 회전과 같다) · `flipH` · `flipV`(참이면 뒤집기, 뒤집은 뒤 회전). 편집기 속성 "위치·크기" 아래. 선·표·글머리·코드는 회전하지 않는다.

**코드**: DBeaver 라이트 테마 색(예약어·함수 굵은 남색, 테이블·CTE 보라, 테이블 별칭 보라 기울임, AS 뒤 결과 별칭 청록 기울임, 문자열 녹색, 숫자 파랑, 주석 회색, 바인드 갈색).
줄 번호는 항상 표시. 한 슬라이드 15~18줄 이내 — 긴 코드는 `show` 로 발췌(사이는 `⋮` 한 줄, 원본 줄 번호 유지)하고 전체 파일 칩을 옆에 둔다(`code_excerpt` 레이아웃, 18줄 넘으면 build 경고).

## 레이아웃 (`layouts.py`, `content/<id>.json` 의 `layout`)

`cover` 표지 · `toc` 목차 · `revisions` 개정 내역 · `chapter` 장 표지 · `section` 절 구분 · `bullets` 본문 글머리 · `sequence` 본문+시퀀스 다이어그램(`groups` 프로세스 경계 · `frames` UML 결합 프래그먼트 `["loop"|"opt"|"alt", 조건, y1, y2, 참여자0, 참여자1]` · 숫자 원 · `returns` 반원 되돌이 화살표(비표준, 필요 시)) ·
`table` 표 · `code_plan` 코드+실행계획(plan) · `plan_table` 실행계획 해설 표 · `compare` 전후 비교 · `files` 예제 파일 · `code_excerpt` 긴 코드 발췌 · `lab` 실습 · `summary` 장 정리.
추가: `chapter_toc` 장 목차(중분류 지도) · `subsection` 소분류(상위 절 칩 + 같은 절 소분류 흐름) · `flow` 순서 흐름(단계 카드 + 규칙 카드) · `cards` 카드 대비 2~3장 · `end` 문서 끝(EoD).
슬라이드마다 `"level": "req"|"adv"` 를 주면 머리의 부 칩 옆에 필수/심화 칩이 붙는다.
행을 쌓는 레이아웃(`summary`·`lab`·`agenda`·`numbered_rows`)은 `"rowH": <px>`(행 간격 고정) 또는 `"rowSpread": true`(본문 영역을 행 수로 고르게 나눔)로 행 간격을 바꾼다.

### 요소 자리·앞뒤 순서·추가 요소 — `place` · `extra` (모든 레이아웃)

원본 PPT 를 옮기는 덱처럼 레이아웃이 놓은 요소를 **원본 좌표·앞뒤 순서(z)·색**으로 바꾸거나, 레이아웃에 없는 글상자(출처·질문 문구)를 더해야 할 때 — 덱에 덧입히지 말고(다음 build 가 "편집기 수정"으로 보고 멈춘다) content 의 슬라이드에 적는다. build 가 레이아웃을 그린 뒤 적용하므로 다시 build 해도 같은 결과다.

```json
{"layout": "bullets", "title": "…", "items": ["…"],
 "place": {"image#1": {"x": 820, "y": 200, "w": 380, "h": 300, "z": -1},
           "pill#1":  {"fill": "#C00000", "color": "white"},
           "title":   {"x": 100},
           "e07":     null},
 "extra": [{"type": "text", "x": 64, "y": 640, "w": 700, "h": 20, "text": "출처: …", "size": 12, "color": "on-surface-variant", "role": "footnotes"},
           {"id": "q1", "type": "text", "x": 900, "y": 300, "w": 300, "h": 80, "text": "질문: …", "size": 16, "z": 2}]}
```

- `place`: `{키: {덮어쓸 필드…}}` — 요소 모델의 어떤 필드든(`x`·`y`·`w`·`h`·`z`·`fill`·`color`·`text`·`size`·`spread`…) 덮어쓴다. 값이 `null` 이면 그 요소를 뺀다. 없는 키는 build 가 경고만 하고 지나간다.
  키는 **요소 id**(`e05` — build 결과 덱에서 확인) · **역할**(`title`·`subtitle`·`crumb`·`page`·`footnotes`·`label`) · **유형#순번**(`image#1`·`pill#2`·`ellipse#1`·`bullets#1` — 그 유형의 n번째, 1부터). 내용이 바뀌어 id 가 밀릴 수 있는 곳은 역할·유형#순번이 안전하다.
- `extra`: 덱 요소를 그대로 적는다(위 표의 type·필드). id 는 레이아웃 요소의 뒤 번호를 잇고(`e09`…), 직접 주면 그 id. `z` 로 앞뒤 순서(음수 = 뒤, 없으면 배열 순서 = 레이아웃 요소 뒤).
- 적용 순서: 레이아웃 → `place` → `extra`. 글자 최소 크기(템플릿 `sizes.minPx`)는 `extra` 에도 적용된다(`role` 로 역할별 기준).

### 글자 크기 배율 — `fontScale` (내용 파일 전체 또는 슬라이드마다)

내용 파일 맨 위 `"fontScale": 1.2` 는 그 장의 모든 슬라이드 글자를 1.2배로 하고(레이아웃 → `place` → `extra` 뒤에), 커진 글에 맞춰 상자 높이·세로 배치를 다시 잡는다 — `studio/scale_fonts.py` 와 같은 규칙([operation.md](operation.md) "글자 크기 일괄 확대"). 슬라이드에 `"fontScale": 1.1` 을 주면 그 장은 그 값, `0` 이면 뺀다.
`{"ratio": 1.2, "roles": ["body", "title"], "keep": true}` 형태면 역할을 고르고(`body` = `role` 없는 요소), `keep` 은 바닥을 넘쳐도 비율을 낮추지 않는다. 바닥을 넘쳐 비율을 낮추거나 그대로 둔 슬라이드는 build 가 알린다.
슬라이드마다 `"source": ["자료 1 절", "자료 2 절"]` 은 **각주 번호의 기준 목록**이다(첫째가 ¹, 둘째가 ²). 슬라이드에는 **그리지 않는다** — 근거 줄·근거 상자 없음.
본문에는 그 근거를 쓴 곳에 **각주 표식** `[[theory|¹]]` 만 단다(이론 색 위첨자).
자료명·절·쪽과 원문은 발표자 노트의 `── 원문 (각주 순서, 원어 그대로) ──` 아래에 같은 번호로 적는다. 노트에 "근거: …"로 시작하는 줄은 쓰지 않는다.
근거 표기(노트): `자료명 버전 §절 p.쪽` — 예 `Oracle Performance Tuning Guide 19c §3.1.1 p.3-3`(쪽은 원본 PDF의 인쇄 쪽 번호). 쪽이 없는 웹 자료는 절 제목, 영상은 `(영상)`.

### 장 덱의 기본 구성

메인 표지(공통) → 전체 목차(공통, 현재 장 강조) → 개정 이력 → 장 표지(대분류) → 장 목차 → 절 구분(중분류) → 소분류 → 본문 → 예제·실습 → 장 정리 → EoD(공통, 다음 장 자동).
공통 슬라이드는 `content/_common.json` 한 곳에서 고치고, 장 내용 파일에 `"common": true`·`"chapterLabel"` 을 주면 build 가 앞뒤에 붙인다.
공통을 바꾼 뒤에는 각 장을 `build_deck.py <id> --force` 로 다시 만든다(편집기에서 고친 내용은 `.history` 에 백업된다).
장 파일 구조: `revisions`(그 장의 개정 이력 — 앞부분에 놓인다) + `slides`(장 블록: 장 표지 ~ 장 정리). 표지에는 장 정보를 넣지 않는다.
**통합본**: `python3 studio/build_deck.py book [--chapters ch00 ch18 …]` → `decks/book.json`.
앞부분 공통(표지·전체 목차·통합 개정 이력 — 장 열 추가) + 장 블록들(목차 순서, 장마다 자기 부 색) + EoD 하나.
`--chapters` 를 생략하면 목차 순서에서 내용 파일이 있는 장을 모두 넣는다.
공통 머리(부 칩·제목·부제·로고)와 바닥(경로·워드마크·쪽 번호 `{page}`)은 `B.head()`·`B.foot()`.

### 코드 언어 (`lang`)

`studio/code_langs.json` 에 정의(화면 `render.js` 와 PPTX `common.py` 가 같은 파일·같은 알고리즘 - `check_parity` 가 언어별 예제로 동일성 검사). 없으면(편집기에서 언어 칸을 비움) 색은 `sql` 규칙(예전 기본)이고 언어 이름표는 없다, 모르는 이름은 `plain`(색 없음). 이름·별칭은 대소문자 무시(예: `sh`·`shell` → `bash`, `cs`·`c#` → `csharp`, `js` → `javascript`, `py` → `python`, `rs` → `rust`, `html` → `xml`, `ini` → `toml`, `mssql`·`oracle` → `sql`).

`plain` · `sql` · `bash` · `powershell` · `c` · `cpp` · `csharp` · `java` · `kotlin` · `scala` · `javascript` · `typescript` · `json` · `yaml` · `toml` · `xml` · `css` · `scss` · `markdown` · `diff` · `python` · `ruby` · `perl` · `php` · `go` · `rust` · `swift` · `dart` · `objectivec` · `vbnet` · `lua` · `r` · `graphql` · `makefile` · `dockerfile`

역할(색은 템플릿 `codeStyle`): 예약어 `k` · 타입·키·태그 `tb` · 함수·속성 `ca` · 문자열 `st` · 숫자·리터럴 `nu` · 주석 `co` · 변수·전처리·장식자 `bi`. SQL 은 전용 규칙(테이블·별칭 `tb`/`al`, 결과 컬럼 별칭 `ca`, 바인드 `bi`).
