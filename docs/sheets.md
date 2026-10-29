# 시트(엑셀) — AI 와 함께 쓰는 표 문서

> engine-request #12 · 검토와 1단계 구현. 슬라이드 덱과 같은 방식(편집기에서 보고 고치고, 요청 → 세션이 파일을 고침 → done + reply)으로
> 엑셀 시트를 함께 만든다. 파일을 주고받지 않고, 마지막에 `.xlsx` 로 내보낸다.

## 1. 구현 가능성 — 가능하다(기존 구조를 거의 그대로 쓴다)

| 덱에 있는 것 | 시트에서 | 비고 |
|---|---|---|
| `decks/<id>.json` 저장 · 버전 · `PUT ?base=` 409 충돌 | **그대로** | 시트 문서도 `decks/<id>.json` 에 `"kind":"sheet"` 로 둔다 |
| 백업·변경 원장(`.history/<id>/`) | 그대로(1단계는 덱 수준 변경 한 줄) | 셀 단위 diff 는 2단계 |
| 요청 파일 `decks/<id>.requests.json`·상태 기계·감시·하트비트 | **그대로** | 대상: `slide`=시트 탭 id, 새 필드 `range`(예 `B2:D5`) |
| 세션 저장 `draft_deck` → `save_deck --request` | 그대로 | 세션은 JSON 의 `sheets[].cells` 를 고친다 |
| 2초 폴링(`/api/version/<id>`) 다시 읽기·충돌 배너 | 같은 방식 | 시트 화면(`sheet.js`)이 따로 구현 |
| 렌더(`render.js`)·PPTX(`export_pptx.py`) | **쓰지 않는다** | 시트 화면은 격자, 내보내기는 `export_xlsx.py`(XlsxWriter) |

XlsxWriter 는 python-pptx 의 의존성이라 이미 설치돼 있고, xlsx 읽기(첨부)는 `import_doc.read_xlsx` 가 표준 라이브러리로 한다.
M365(OneDrive·Graph API) 직접 연동은 하지 않는다 — 원래 불편(파일을 열어 고치고 다시 보내기)을 없애는 것이 목적이라
**편집 원본은 nexa-slide 안의 JSON**, 엑셀은 산출물(내보내기)이다. 엑셀에서 고친 파일을 다시 들여오는 것은 2단계(가져오기).

## 2. 문서 형식

```jsonc
{
  "id": "d1a2b3c4", "title": "분기 매출", "kind": "sheet", "version": "0.1", "updated": "…",
  "slides": [],                      // 덱 도구와 호환(항상 빈 목록)
  "sheets": [{
    "id": "t01", "name": "Sheet1",
    "size": {"rows": 50, "cols": 12},  // 화면에 보이는 격자 크기(선택, 데이터보다 작으면 데이터에 맞춘다)
    "cols": {"A": 140, "C": 90},       // 열 너비 px(없으면 96)
    "rows": {"1": 30},                 // 행 높이 px(없으면 24)
    "freeze": "A2",                    // 틀 고정 - 이 셀의 위·왼쪽이 고정(선택)
    "merges": ["A1:D1"],
    "cells": {
      "A1": {"v": "분기 매출", "b": true, "size": 14, "fill": "#1F4E79", "color": "#FFFFFF", "align": "center"},
      "A2": "지역", "B2": "1분기",       // 값만 있으면 문자열·숫자·불 그대로
      "B3": 1200,
      "C3": {"v": 0.15, "fmt": "0.0%"},
      "D3": {"f": "=B3*(1+C3)", "v": 1380, "fmt": "#,##0"}
    }
  }]
}
```

셀 키 — `v` 값(문자열·숫자·불), `f` 수식(`=` 로 시작, `v` 는 마지막 계산값 캐시), `fmt` 엑셀 표시 형식, `b`·`i`·`u` 굵게·기울임·밑줄,
`color` 글자색, `fill` 배경, `align` `left|center|right`, `valign` `top|middle|bottom`, `size` 글자 크기(pt), `wrap` 줄바꿈, `note` 메모.
값이 문자열이어도 `=` 로 시작하면 수식이 아니다 — 수식은 `f` 에만 둔다.

**동적 배열(넘침)** — `FILTER`·`SORT`·`SORTBY`·`UNIQUE`·`SEQUENCE`·`TRANSPOSE` 를 쓴 수식(또는 엑셀에서 가져온 동적 배열 `"da": true`)은 결과가 여러 칸이면
오른쪽·아래 칸으로 넘친다. 넘친 칸은 계산기가 `{"v": 값, "sp": "기준 칸"}` 으로 채우고(사람·AI 는 쓰지 않는다), 자리에 값이 있으면 기준 칸이 `#SPILL!`,
결과가 없으면 `#CALC!` 이다. 결과가 줄면 남은 넘친 칸은 비운다. 다른 곳에 복사된 `sp` 칸은 값만 남는다.
내보낼 때 기준 칸은 엑셀 동적 배열 수식(`write_dynamic_array_formula`)으로 쓰고, 가져올 때 `cm`·여러 칸 배열 수식을 `da` 와 `sp` 로 되살린다.
넘친 범위 전체는 `H2#` 로 참조한다(`=SUM(H2#)` · `=H2#*10` 도 넘친다 · 넘치지 않는 칸이면 `#REF!`). 엑셀 파일에는 `ANCHORARRAY(H2)` 로 저장된다.
새 함수(LET·XMATCH·TEXTJOIN·FILTER …)는 내보낼 때 `_xlfn.`·LET 이름은 `_xlpm.` 을 붙이고(엑셀이 `#NAME?` 없이 연다 - Excel 로 확인), 가져올 때 뗀다.

**표(엑셀 표)** — 탭 `tables: [{"name": "매출표", "ref": "A1:D5", "cols": ["지역", "1분기", …], "header": true, "totals": false, "style": "TableStyleMedium2"}]`.
수식에서 구조적 참조로 쓴다 - `매출표[1분기]`(데이터 행) · `매출표[[#Headers],[2분기]]` · `매출표[#All]` · `매출표[[1분기]:[2분기]]` · 표 안에서 `[@1분기]`(이 행).
가져올 때 `xl/tables` 를 읽고(파일 형식 `[#This Row],` → `@`), 내보낼 때 `add_table` 과 파일 형식으로 되돌린다(Excel 로 확인).
표 정의 없이 가져온 옛 문서의 구조적 참조·외부 통합 문서 참조처럼 계산기가 읽지 못하는 수식은 엑셀이 마지막에 계산한 값을 그대로 둔다.

**이름 정의(엑셀 이름 관리자)** — 문서 `names`(통합 문서 범위)와 탭 `names`(그 시트 범위) = `{"이름": "값"}`.
값은 범위(`"데이터!$B$2:$B$5"` - 문서 이름은 탭 이름을 붙인다, 탭 이름은 붙이지 않으면 그 탭) · 상수(`"0.1"`) · 수식(`"=…"`).
수식에서 이름 그대로 쓴다 - `=SUM(매출)*세율`. 같은 이름이면 탭 이름이 문서 이름보다 먼저다. 정의가 없는 이름을 쓴 셀은 엑셀이 마지막에 계산한 값을 그대로 둔다(가져온 문서가 `#NAME?` 로 덮이지 않게).
행·열을 넣거나 지우면 이름 정의도 옮긴다 - 범위 안에 넣으면 범위가 늘고, 지운 칸만 가리키던 이름은 `#REF!`(`sheet_struct.py`·화면 `shiftAxis`, 동시 편집 병합도 같다 - [collab.md](collab.md) 3-2).
가져오기·내보내기는 엑셀 `definedNames` 와 주고받는다.

**수식형 요약 `GROUPBY`·`PIVOTBY`**(엑셀 365, 넘친다) — 피벗 표 대신 수식 한 칸으로 요약한다.
`=GROUPBY(행 필드, 값, 집계)` 은 행 필드별 집계 + 맨 아래 `Total`, `=PIVOTBY(행 필드, 열 필드, 값, 집계)` 은 행×열 표 + 행·열 합계.
집계는 함수 이름(`SUM`·`AVERAGE`·`COUNT`·`COUNTA`·`MAX`·`MIN`·`MEDIAN`·`PRODUCT`)이나 LAMBDA(`LAMBDA(v,SUM(v)/2)`)·이름 정의 함수.
GROUPBY 는 행 필드·값 여러 열, 머리글(0·1·3 - 생략하면 자동), 합계(1 아래·-1 위·0 없음), 정렬(열 ±n), 거르기 배열을 받는다.
아직 안 되는 것: 소계(합계 깊이 2)·머리글 만들기(2)·PIVOTBY 여러 열 필드·값 열로 정렬. 엑셀 파일에는 `_xlfn.GROUPBY(…,_xleta.SUM)` 으로 쓰고 가져올 때 뗀다.

**LAMBDA 계열**(엑셀 365) — `LAMBDA(매개변수…, 식)` 와 그것을 받는 `MAP`·`BYROW`·`BYCOL`·`REDUCE`·`SCAN`·`MAKEARRAY`.
`=SUM(MAP(B2:B5,LAMBDA(x,x*2)))` · `=BYROW(B2:C5,LAMBDA(r,SUM(r)))`(행마다 하나 - 넘친다) · `=REDUCE(0,B2:B5,LAMBDA(a,v,a+v))` · `=SCAN(0,B2:B5,LAMBDA(a,v,a+v))`(누계) · `=MAKEARRAY(3,2,LAMBDA(r,c,r*c))`.
LET 이름에 담아 `=LET(f,LAMBDA(a,b,a+b),f(2,3))` 으로 부르고, **이름 정의에 담으면 사용자 함수**다 - 이름 관리자 `세후 = LAMBDA(x,x*0.9)` → 셀에서 `=세후(1000)`
(자기를 부르는 재귀는 깊이 200까지). 칸 값이 함수로 남으면 `#CALC!`, 인수 개수가 틀리면 `#VALUE!`. 엑셀 파일은 매개변수에 `_xlpm.`, 이름 정의 안의 LAMBDA·새 함수에 `_xlfn.` 을 붙인다(가져올 때 뗀다).

## 3. 요청(세션 규약)

편집기 요청 항목 `{deck, id, slide, range, text, …}` — `slide` 는 시트 탭 id, `range` 는 고른 셀 범위(`A1`, `B2:D5`).
세션은 `kind:"sheet"` 문서면 `sheets[]` 의 `cells` 를 고친다(수식은 `f`, 값은 `v`, 계산값 `v` 는 비워 두면 화면이 다시 계산).
나머지 순서(`working` → `draft_deck` 사본 → Edit → `save_deck --request` → `done` + `reply`)는 슬라이드와 같다.

## 4. API

| | |
|---|---|
| `POST /api/decks {action:"create", kind:"sheet", title}` | 새 시트 문서(탭 1개). `GET /api/decks` 항목에 `kind` |
| `GET/PUT /api/deck/<id>` | 슬라이드 덱과 같다. `kind:"sheet"` 면 `sheets` 목록을 검사 |
| `POST /api/requests/<id> {action:"add", slide, range, text}` | `range` 를 받는다 |
| `POST /api/export/<id>` | `kind:"sheet"` 면 `out/<id>.xlsx` (`export_xlsx.py`) |
| `/studio/sheet.html?deck=<id>` | 시트 편집 화면. 편집기(`index.html`)가 시트 문서를 열면 여기로 보낸다 |

## 5. 시트 테마 — 슬라이드 템플릿처럼

회사 산출물 엑셀은 모양이 정해져 있다. 표지(로고·과제명·문서명·날짜), 개정 이력, 개요(문서 정보·범례), 요약, 상세 목록이 들어가고, 머리 색·테두리·글꼴·바닥 로고가 같다.
테마는 이것을 **색·글꼴(palette) + 이름 있는 셀 스타일(styles) + 페이지 틀(pages) + 로고(그림)** 로 묶는다. 슬라이드 템플릿이 장 레이아웃과 색을 묶는 것과 같은 방식이다.

| 위치 | 내용 |
|---|---|
| 엔진 `studio/sheet_themes/<이름>/theme.json` | 공개 테마만 둔다(로고 없음, 작업 공간 brand 로고 `@brand/logo` 를 쓴다) |
| 작업 공간 `assets/sheet-themes/<이름>/theme.json` + 그림 | 회사 테마. 로고 같은 상표 파일은 엔진 저장소에 넣지 않는다 |

```jsonc
{
  "name": "corp", "label": "회사 산출물", "font": "맑은 고딕", "size": 10, "grid": false,
  "palette": {"primary": "#2C3E50", "secondary": "#44607A", "line": "#BFC9D4", "band": "#EDF1F5", "input": "#FFF2CC", "warn": "#C0392B", "muted": "#7F8C8D"},
  "styles": {                                  // 셀 키(b·color·fill·align·valign·size·wrap·fmt·bd)의 묶음. 색은 팔레트 이름이나 #RRGGBB
    "title":   {"size": 16, "b": true, "color": "primary"},
    "section": {"size": 12, "b": true, "color": "primary"},
    "header":  {"b": true, "color": "#FFFFFF", "fill": "primary", "align": "center", "valign": "middle", "wrap": true, "bd": "line"},
    "label":   {"b": true, "color": "#FFFFFF", "fill": "secondary", "align": "center", "bd": "line"},
    "cell":    {"bd": "line", "valign": "middle"},
    "key":     {"b": true, "color": "primary", "align": "center", "bd": "line"},
    "input":   {"fill": "input", "align": "center", "bd": "line"},
    "warn":    {"b": true, "color": "warn"}
  },
  "vars": {"client": "", "project": "", "author": "", "version": "1.0"},   // 페이지 글의 {{이름}} 자리(새 시트를 만들 때 채운다, 그 밖에 {{title}}·{{date}})
  "pages": [                                   // 시트 탭 틀 - 형식은 2절 탭과 같고 셀에 "s": "<스타일>" 과 {{자리}} 를 쓴다
    {"kind": "cover",    "name": "표지", ...}, {"kind": "history", "name": "이력", ...},
    {"kind": "overview", "name": "개요", ...}, {"kind": "summary", "name": "요약", ...}, {"kind": "list", "name": "상세목록", ...}
  ]
}
```

문서와 셀에 새로 생기는 키
- 문서 `theme: "<이름>"` — 테마가 있으면 셀의 `s`(스타일 이름)를 그 테마에서 찾아 셀 키 아래에 깐다(셀 키가 이긴다). 테마를 바꾸면 모든 셀이 새 스타일로 바뀐다.
- 셀 `bd` 테두리 — `"line"`(팔레트 이름)·`"#BFC9D4"` 이면 네 변 가는 선, `{"t": 색, "r": 색, "b": 색, "l": 색}` 이면 변마다(없는 변은 선 없음).
- 탭 `grid: false` — 눈금선 숨김(표지·개요). 탭 `print: {"landscape": true, "fitWidth": 1}` — 인쇄 설정.
- 탭 `drawings: [{"type": "image", "src": "logo.png", "at": "B2", "dx": 0, "dy": 0, "w": 330, "h": 72}]` — 셀에 고정한 그림(px).
  `src` 는 테마 폴더 기준이거나 작업 공간 기준(`assets/...`)이고, `@brand/logo` 는 작업 공간 brand 로고다.

계산 규칙(스타일 풀기·팔레트 이름 → 색)은 화면(`sheet.js`)과 내보내기(`export_xlsx.py`) 두 곳에 있다. 테마 파일은 `sheet_theme.py` 가 읽는다.

**테마 만들기(샘플링)** — `python3 nexa.py sheet_theme import <샘플.xlsx> --name <이름>`
- 샘플 엑셀의 글꼴·주요 색(머리·라벨·테두리·입력칸·강조), 열 너비, 표지의 그림(로고)과 글 상자(과제명·문서명·날짜 자리)를 읽는다.
- 결과는 `assets/sheet-themes/<이름>/` 에 테마와 그림으로 만든다. Excel 이 있으면(Windows) 도형 묶음 로고도 그림으로 떠낸다. 만든 뒤 `theme.json` 을 사람이나 AI 가 다듬는다.

**엑셀 파일로 시작** — 시작 페이지 ＋ 새 시트 → "또는 엑셀 파일로 시작" 에서 .xlsx·.xlsm 을 고르면 테마 대신 그 파일이 첫 시트가 된다
(`init_workspace.py --kind sheet --sheet-import <파일>` → `sheet_import.py`). 값·수식·서식·병합·그림·매크로까지 옮기고 원본은 `materials/` 에 남는다.

## 6. 시트 → 슬라이드 연결

시트 범위를 슬라이드의 **표·차트**로 넣는다(편집기 ＋ 추가 → 데이터 → "시트에서 표·차트"). 요소에는 연결 정보와 지금 값이 함께 들어간다 - 렌더·PPTX 규칙은 그대로.

```jsonc
{"type": "table", "rows": [["지역", "매출"], ["서울", "1,200"]], "link": {"deck": "<시트 문서 id>", "tab": "t01", "range": "A1:B5", "as": "table", "header": true}}
{"type": "chart", "chart": "column", "categories": ["서울", …], "series": [{"name": "매출", "values": [1200, …]}], "link": {…, "as": "chart"}}
```

- 표는 **보이는 글**(표시 형식 반영 - `1,200`·`15.0%`·날짜), 차트는 첫 열 = 범주, 첫 줄 = 계열 이름, 나머지 = 계산값(수식은 계산해서).
- 편집기가 덱을 열 때 연결된 요소의 원본을 다시 읽어 바뀌었으면 맞춘다(실행 취소 한 번). 오른쪽 클릭 → 시트에서 새로 고침 · 원본 시트 열기 · 시트 연결 끊기(값은 남김).
- API `GET /api/sheet-range?deck=&tab=&range=&as=table|chart&header=1`, CLI `nexa.py sheet_link <시트> <탭> <범위> [--as chart]`(세션이 요소를 만들 때 - 결과 JSON 의 데이터와 link 를 그대로 요소에).

## 7. 개발 방향 (조사: [research/sheet-survey.md](research/sheet-survey.md) — M365 Excel · Google Sheets 기준)

기준 제품의 흐름도 우리와 같다. Excel 은 `=COPILOT()` 셀 함수를 2026-09 에 폐지하고 **사이드 패널 + 계획/적용**으로 옮겼다.
Gemini in Sheets 도 **미리보기 카드 → 적용 → 실행 취소** 로 움직인다. "범위를 고르고 → 요청 → AI 가 고치고 → 답(reply)" 은 지금 구조 그대로 그 방향이다.

원칙
- **두 곳 동일성**: 수식 계산과 표시 형식은 화면(JS)과 내보내기(Python) 두 곳에 생긴다. 함수는 천천히 늘리고, 같은 JSON 이면 같은 값·같은 표시 문자열인지 확인하는 `check_parity` 식 시트 시험을 둔다.
- **AI 가 쓴 수식도 계산된다**: 세션은 `f` 만 쓰고 `v` 는 비워도 된다. 내보낼 때 Python 평가기가 캐시 값을 채운다. XlsxWriter 는 캐시 값을 0 으로 쓰기 때문에, 뷰어·미리보기에서는 0 으로 보인다.
- **라이선스(MIT)**: 쓰지 않는다 — HyperFormula(GPL)·Handsontable 7+(상용)·Luckysheet(보관)·Univer Pro. 조건부로 쓴다 — Apache-2.0(Univer OSS·SheetJS CE)은 NOTICE 를 지키면 쓸 수 있다.
- **필터·정렬 보기는 사용자별 상태**(Sheets 필터 보기와 같다): 사람과 AI 가 같은 문서를 보므로 공유 JSON 을 바꾸지 않는다.

진행(2026-10-29 · 0.24.0): **1 완료**, **2 대부분 완료**(아래 ✅), **3 일부**(동적 배열·`H2#`·LET/XMATCH·엑셀 표·시트 → 슬라이드 연결 ✅), **4 일부**(xlsx 왕복 시험 ✅). 동시 편집은 [collab.md](collab.md) 2단계(SSE·presence)와 3단계 첫 조각(AI 제안 골라 받기)까지.

| 단계 | 내용 |
|---|---|
| **1** ✅ | 문서 형식·만들기(편집기 덱 메뉴, 시작 페이지 ＋ 새 시트)·저장·요청 `range`·시트 화면(격자, 기본 서식, 수식 7개, 요청 패널)·xlsx 내보내기·세션 안내 |
| **2 쓸 만한 시트** (직접 구현) — ✅ 채우기 핸들 · Ctrl+D/R/Enter · TSV·값만 붙여넣기 · 행·열 삽입/삭제 · 찾기·바꾸기 · 상태 표시줄 · 테두리 · 형식 코드 · 순환 감지 · 함수 약 70개(목표 30 넘음) · 시트 간 참조 · Python 계산기 · 드롭다운 · 조건부 서식 11종 · xlsx·xlsm 가져오기(openpyxl 대신 표준 라이브러리) · 정렬·필터·숨기기 · 함수 자동 완성 / 남음: 가상 스크롤, 그림·도형 가져오기 | 가상 스크롤 · 채우기 핸들(복사·등차·날짜·"텍스트+숫자", 상대 참조 이동) · Ctrl+D/R/Enter · TSV·값만 붙여넣기 · 행·열 삽입/삭제(참조 재작성, `#REF!`) · 찾기·바꾸기 · 상태 표시줄 합계/평균/개수 · 테두리(`border`) · 형식 코드 하위 집합 · 의존성 그래프·순환 감지 · 함수 약 30개(COUNTA·SUMIF·COUNTIF·IFERROR·AND/OR·&·LEFT/RIGHT/LEN·TEXT·TODAY·VLOOKUP/XLOOKUP …) · 시트 간 참조 · **Python 평가기(내보낼 때 캐시 값)** · 드롭다운 유효성·단순 조건부 서식(→ xlsx) · **xlsx 가져오기(openpyxl)** |
| 2 AI 요청 UX — ✅ 범위 요청·첨부·Enter 전송·처리 중 표시(공용 요청 패널) / 남음: 바뀐 셀 강조·"바뀐 셀 n개"·[되돌리기]·예시 칩 | 요청에 범위 값·수식 스냅숏과 머리글 행을 함께 보낸다 · `working` 동안 대상 범위에 AI 색 테두리("작업 중") · `done` 이면 **바뀐 셀을 잠깐 강조**하고 reply 에 "바뀐 셀 n개" · reply 의 **[되돌리기]**(백업 버전으로) · 예시 칩("합계 행 추가", "이 열 % 형식", "빈칸 0") · 오류 셀에 "원인 설명" 칩 |
| **3 분석 가능한 시트** | XLOOKUP·SUMIFS·날짜 함수·동적 배열(spill, `#SPILL!`). 함수가 60개를 넘으면 Univer `engine-formula`(Apache-2.0)를 서버(Node)·브라우저 공용 엔진으로 검토한다(시험 필요) · 표(머리글·줄무늬·요약 행·구조적 참조) + **열 유형**(AI 가 지키기 쉬운 스키마) · 사용자별 필터 보기 · 차트(시트 범위 → **슬라이드 덱에 삽입**, 기존 차트 경로 재사용) · 요청 `mode: plan`(계획만 쓰고 [진행]에 실행) · 제안 초안(미리보기 → 적용/취소) |
| **4 AI 협업 시트** | AI 셀(수식이 아니라 셀 속성 `{ai, src}` — 결과는 값으로 저장, 다시 생성은 요청으로만) · ✅ GROUPBY/PIVOTBY 식 수식형 요약(0.24.2)·LAMBDA 계열(0.24.3) · 셀 수정 기록(요청 id·사람/AI·이전 값) · xlsx 왕복 회귀 시험 · AI 세션이 로컬 pandas 로 분석해 시트·차트로 써 넣기 |

동시 편집(여러 사람이 같은 시트를 함께 고치는 것)의 방향은 [research/realtime-collab.md](research/realtime-collab.md) 를 따른다. 시트의 병합 단위는 **셀**이다.
