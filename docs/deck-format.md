# 덱 형식

원본은 두 가지다 — **내용 원본** `content/<id>.json`(레이아웃 이름 + 필드)과 그것을 빌드한 **덱** `decks/<id>.json`(요소 좌표까지 풀린 것, 편집기가 고치는 대상).

## 덱 JSON · 요소 모델

```json
{ "id": "ch00", "title": "…", "part": "day1", "version": "0.1", "updated": "…",
  "slides": [ { "id": "s01", "layout": "cover", "notes": "발표자 노트", "bg": "surface", "elements": [ … ] } ] }
```

**단위**: 좌표·크기·글자 크기 모두 **px (슬라이드 1280×720 기준)**. PPT 변환 시 EMU = px × 9525, pt = px × 0.75.
색은 토큰 이름(`primary`, `day1-container`, `s3` …) 또는 `#RRGGBB`. 반경은 px 또는 `r-s`/`r-m`/`r-l`/`r-full`.
공통 필드: `id`, `type`, `x`, `y`, `w`, `h`, `z`(선택, 없으면 배열 순서), `locked`(선택 — 편집기에서 이동·삭제 막음).

| type | 필드 | PPT 변환 |
|---|---|---|
| `rect` | `fill`, `radius`, `stroke`, `strokeWidth`, (선택) `text`·글자 필드 | 사각형/둥근 사각형(반경 = adjustments) |
| `ellipse` | `fill`, `stroke`, (선택) `text`·글자 필드 | 타원 |
| `pill` | `fill`, `color`, `text`, `size`, `bold`(기본 굵게) | 둥근 사각형(반경 = 높이/2) + 가운데 글자 |
| `text` | `text`, `size`, `bold`, `color`, `align`(left/center/right), `valign`(top/middle/bottom), `font`(body/mono), `lineHeight`, `wrap`, (선택) `fill`·`radius`·`pad`[위,오,아,왼] | 글상자(자동 맞춤 끔, 여백 0) / fill 이 있으면 글자 있는 도형 |
| `image` | `src`(`assetRoot` 기준 경로) | 그림 |
| `line`·`arrow` | `x1`,`y1`,`x2`,`y2`, `color`, `width`, `head`(none/end/start/both), `dash`(solid/dash/dot) | 연결선 + 화살 머리(XML tailEnd/headEnd, lg) |
| `curve` | `points`(요소 상자 기준 [[x,y],…]), `color`, `width`, `head`(end/none) | 자유형 꺾은선(채우기 없음) + 끝 화살 머리 — 반원 되돌이 화살표 등 |
| `table` | `rows`(2차원, 첫 행 머리), `colW`(비율), `header`, `headFill`, `headColor`, `size`, `colFont`, `align`, `rule` | 표(스타일 없음, 머리 행 채우기, 본문 행 아래 선) |
| `plan` | `text`(DBMS_XPLAN 원문), `size`, `lineHeight`, `fill`, `pad` — `[[값]]` = 경고 강조, `[[ok:값]]` = 개선 강조 | 고정폭 글자, 강조 run = 굵게 + 글자색 + **run 강조색(a:highlight)** |
| `plan-table` | `columns`, `colW`, `opCol`(들여쓰기 열), `rows[{cells, depth, hl:{열번호: warn/ok}, note}]`, `calloutW` | 표 + 오른쪽 설명 콜아웃(연결선 + 둥근 상자) |
| `code` | `text`, `lang`(sql/python), `size`, `lineHeight`, `start`, `focus`[줄], `show`[[from,to],…] | 그룹 도형: 줄 번호 여백·코드 면·강조 줄 면·테두리·줄 번호 글상자·코드 글상자(run 단위 색·굵게·기울임) |
| `bullets` | `items`(문자열 또는 `{text, sub:[…]}`), `size`, `subSize`, `lineHeight`, `gap`, `subGap`, `dot`, `color`, `subColor` | 단락 글머리(●/–, 글머리 색) |

**인라인 강조**(text·pill·rect·ellipse·table 셀·bullets): `**굵게**`, `==강조==`(CI 적색 굵게), `[[토큰|색 글자]]`, `{page}`(쪽 번호).

**코드**: DBeaver 라이트 테마 색(예약어·함수 굵은 남색, 테이블·CTE 보라, 테이블 별칭 보라 기울임, AS 뒤 결과 별칭 청록 기울임, 문자열 녹색, 숫자 파랑, 주석 회색, 바인드 갈색).
줄 번호는 항상 표시. 한 슬라이드 15~18줄 이내 — 긴 코드는 `show` 로 발췌(사이는 `⋮` 한 줄, 원본 줄 번호 유지)하고 전체 파일 칩을 옆에 둔다(`code_excerpt` 레이아웃, 18줄 넘으면 build 경고).

## 레이아웃 (`layouts.py`, `content/<id>.json` 의 `layout`)

`cover` 표지 · `toc` 목차 · `revisions` 개정 내역 · `chapter` 장 표지 · `section` 절 구분 · `bullets` 본문 글머리 · `sequence` 본문+시퀀스 다이어그램(`groups` 프로세스 경계 · `frames` UML 결합 프래그먼트 `["loop"|"opt"|"alt", 조건, y1, y2, 참여자0, 참여자1]` · 숫자 원 · `returns` 반원 되돌이 화살표(비표준, 필요 시)) ·
`table` 표 · `code_plan` 코드+실행계획(plan) · `plan_table` 실행계획 해설 표 · `compare` 전후 비교 · `files` 예제 파일 · `code_excerpt` 긴 코드 발췌 · `lab` 실습 · `summary` 장 정리.
추가: `chapter_toc` 장 목차(중분류 지도) · `subsection` 소분류(상위 절 칩 + 같은 절 소분류 흐름) · `flow` 순서 흐름(단계 카드 + 규칙 카드) · `cards` 카드 대비 2~3장 · `end` 문서 끝(EoD).
슬라이드마다 `"level": "req"|"adv"` 를 주면 머리의 부 칩 옆에 필수/심화 칩이 붙는다.
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
