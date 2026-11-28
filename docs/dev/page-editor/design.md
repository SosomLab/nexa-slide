# 페이지(Page) 편집기 - 설계

> 세 번째 문서 종류. 슬라이드(PowerPoint) · 시트(Excel)에 이어 **페이지(Word · Pages)**.
> 결정 = [decisions.md](decisions.md) · 할 일 = [TODO.md](TODO.md) · 지금 상태 = [STATUS.md](STATUS.md) · 무인 진행 규칙 = [../autodev.md](../autodev.md)

## 1. 목표와 범위

- **1단계(범용 워드)**: 문단·글자 서식, 스타일, 목록, 표, 그림, 머리말·꼬리말·쪽 번호, 용지·여백, 쪽 경계 표시, DOCX·PDF 내보내기, 템플릿, AI 요청·변경 이력·병합 저장.
- **2단계**: 편집 중 실시간 쪽 나눔, 구역·다단(너비가 다른 2단 포함), 글 상자·도형(문단/쪽 고정), 윗주(루비), 각주, DOCX 가져오기, 해설지 템플릿 완성(예시 PDF 재현).
- **3단계**: 변경 내용 추적·메모, 목차·상호 참조, 표 스타일, 개요 보기.
- 예시 문서(수능특강 해설지, 한글에서 만든 12쪽 A4, 너비가 다른 2단 + 단어 주석 + 도형 + 떠 있는 상자)는 **2단계의 수락 기준**이다. 단어 주석·도형은 Word·Pages 에 대응 기능이 있는 것(윗주 · 글자 테두리/음영/형광펜 · 고정 도형 · 글 상자)으로만 만든다(DR-P03). 단어 **아래** 주석처럼 Word 에 대응 기능이 없는 것은 D-P01(미정).

## 2. 원칙

1. **문서 모델은 하나** - 흐르는 본문 + 쪽 고정 개체(DR-P02). Pages 식 2모드는 두지 않는다.
2. **JSON 이 진실의 원본** - DOCX·PDF 는 내보내기 산출물. 렌더 규칙은 화면(JS)과 내보내기(Python) 두 곳에 있고 동일성 시험으로 묶는다(슬라이드의 `check_parity` 와 같은 방식).
3. **외부 편집 라이브러리 없음** - 글 편집 엔진을 자체 구현하고 세 종류가 같이 쓴다(DR-P04). 빌드 단계 없는 순수 JS 를 유지한다.
4. **공용 뼈대 먼저** - 슬라이드·시트의 중복을 공용 모듈로 뽑고 그 위에 페이지를 만든다(DR-P09). 공용화는 동작을 바꾸지 않는다(회귀: run_all · PPTX XML 동일).
5. **kind 는 등록부로** - `== "sheet"` 2분기(19개 파일 약 57곳)를 종류 등록부 조회로 바꾼다. 모르는 kind 가 슬라이드로 떨어지지 않게 한다. (2026-11-27: 서버 쪽 `kinds.py` 는 미룸 - PG-020, 지금은 `page` 갈래 분기 추가. 화면 쪽은 `nexa-kinds.js`)
6. **같은 기준 하나**(DR-P14) - 개체 선택·이동·크기·편집·지우기와 문서 저장·불러오기·밖의 변경 따라가기·실행 취소는 세 종류가 공용 모듈 하나의 기준을 따른다(저장 `nexa-doc.js` · 개체 조작 `nexa-objects.js`). 화면은 어댑터(문서 읽기·쓰기·그리기 훅)만 갖고, 새 기능을 한 화면에만 따로 만들지 않는다.

## 3. 문서 형식 (`decks/<id>.json`, kind = "page")

```json
{"id": "report1", "title": "…", "kind": "page", "version": 1, "updated": "…", "slides": [],
 "page": {"size": "A4", "orient": "portrait", "margin": {"t": 25, "r": 20, "b": 25, "l": 20},
          "header": {"blocks": []}, "footer": {"blocks": []}, "first": null, "number": {"show": true, "pos": "footer-center"},
          "columns": {"count": 2, "gap": 8}},
 "styles": {"body": {"font": "body", "size": 10.5, "line": 1.6}, "h1": {"based": "body", "size": 20, "bold": true}},
 "blocks": [
   {"id": "b01", "type": "p", "style": "h1", "runs": [{"t": "제목"}]},
   {"id": "b02", "type": "p", "align": "justify", "runs": [{"t": "본문 "}, {"t": "굵게", "b": 1}, {"t": " 색", "c": "accent"}, {"t": "뜻", "fn": "각주 글"}]},
   {"id": "b03", "type": "p", "list": {"kind": "bullet", "level": 0}, "runs": [{"t": "항목"}]},
   {"id": "b04", "type": "table", "cols": [40, 60], "rows": [{"id": "r1", "head": true, "cells": [{"id": "c1", "blocks": []}]}]},
   {"id": "b05", "type": "image", "src": "assets/…", "w": 80, "align": "center"},
   {"id": "b06", "type": "break", "kind": "page"},
   {"id": "b07", "type": "break", "kind": "section", "columns": {"count": 1}},
   {"id": "b08", "type": "break", "kind": "column"}
 ],
 "objects": [{"id": "o1", "type": "shape", "shape": "ellipse", "anchor": "b02", "rel": "para", "x": 10, "y": 2, "w": 30, "h": 12,
              "fill": null, "line": {"c": "accent", "w": 1, "dash": "solid"}, "z": "front"}]}
```

- `slides: []` 는 서버 검증 호환용으로 둔다(시트와 같은 이유) - 종류 등록부가 자리 잡으면 뺀다.
- 길이 단위 = mm, 글자 크기 = pt. 색·글꼴은 토큰 이름(`accent`, `body`) 또는 값 - 슬라이드와 같은 `tokens.json`·`fontPresets` 를 쓴다.
- **블록마다 id** - 병합·diff·작업(op)·AI 제안의 단위. 표는 행·셀 id.
- **목록은 문단의 속성**(`list: {kind: bullet|number|check, level, restart?, done?}`) - Word 의 번호 매기기와 같다. 이어진 목록 문단이 한 목록이고 번호는 그릴 때 센다(DP-P06).
- `runs` = [{t, b, i, u, s, c, hl, sup, sub, font, size, link, ruby, fn}] - 인접한 같은 서식은 합쳐 저장한다(정규화). `fn` = 그 글 조각 뒤에 다는 **각주 글**(화면은 조각 뒤에 위 첨자 번호 `[data-fn]::after`)(1~2000자, 번호는 문서 순서로 센다 - `page_doc.footnotes`). 본문·표 칸의 fn 만 각주가 된다(머리말·꼬리말·개체 안은 Word 가 받지 않는다).
- **나누기** `{type: "break", kind}` - `kind` = `page`(기본, 쪽 나누기) · `column`(다음 단으로) · `section`(구역 나누기 - 그 뒤부터 `columns` 의 단 수). `columns` 는 `kind: "section"` 에만 둔다.
- **단** `columns` = `{count: 1~4, gap?: mm 0~50(기본 8)}` - 문서 전체는 `page.columns`, 구역 나누기 뒤는 그 블록의 `columns`(`page_doc.columns_of`). 단은 같은 너비만(너비가 다른 2단은 배치용 표 - DP-P07). 화면의 단 고르기는 1~3단.
- `objects`(2단계, PG-103) = 떠 있는 도형·글 상자: `{id, type: "shape", shape, anchor, rel, x, y, w, h, fill?, line?: {c, w(pt 0~20), dash: solid|dash|dot} | null, flip?, z?: "front"|"behind", blocks?(안의 글 - 선에는 없음), valign?: top|middle|bottom, pad?(mm)}`.
  `shape` = rect · round · ellipse · line · arrow · bracket-l · bracket-r · brace-l · brace-r. `anchor` = 본문 맨 위 단계 **문단의 id**(Word 처럼 문단에 매인다 - DP-P15), `rel` = `page`(그 문단이 놓인 쪽의 왼쪽 위 기준) | `para`(그 문단의 왼쪽 위 기준), x·y·w·h 는 mm. 매인 문단이 없어지면 정규화가 첫 문단에 다시 맨다. 둘러싸기(`wrap`)·그림 개체는 아직 없다.

## 4. 구성

### 4-1. 화면(공용)

| 모듈 | 내용 | 뽑는 곳 |
|---|---|---|
| `nexa-shell.js` · `nexa-shell.css`(js 는 api·toast·상태·배너·메뉴까지 - PG-010, 나머지·css 는 PG-011·PG-012) | api · toast · 상태 칩 · 배너 · 메뉴(openMenu) · 실행 취소 뼈대 · save/scheduleSave · loadDeck/poll/applyVersion · 확대 · 머리 막대·옆 패널 뼈대 | studio.js · sheet.js 의 중복 약 250줄, 인라인 스타일 약 880줄 |
| `nexa-newdoc.js` | "새 문서" 대화 상자 - 슬라이드/시트/페이지 선택 + 종류별 템플릿(추천 순). 홈·세 편집기가 같이 쓴다 | home.html setKind · studio deckCreate · sheetnew.js |
| `nexa-text.js` | **글 편집 엔진**(§5) | 새로 |
| `nexa-format.js`(아직 없음 - PG-043·PG-108) | 글자·문단 서식 막대, 글꼴·색 고르기 | studio.js palette·colorOptions·글꼴 세트, sheet.js 글꼴 |
| `nexa-export.js`(아직 없음 - PG-013) | 내보내기 메뉴·진행·내려받기 | studio doExport · sheet exportXlsx |
| 기존 공용 | nexa-merge · nexa-live · nexa-requests · wsession · menu · search · lightbox | 그대로(kind 분기만 등록부로) |

### 4-2. 화면(페이지 고유)

`page.html` · `page.js`(편집기) · `page-render.js`(블록 → DOM) · `page-flow.js`(실시간 쪽 나눔 - 10-1). 인쇄용 페이지를 따로 두지 않는다 - 인쇄·서버 Chrome PDF 모두 `page.html`(`?print=1`)이 화면 쪽 나눔 그대로 찍는다(처음 계획한 `page-print.html` 은 만들지 않았다).

### 4-3. 서버

| 모듈 | 내용 |
|---|---|
| `kinds.py`(미룸 - PG-020) | 종류 등록부: 이름 · 편집기 html · 새 문서 만들기 · 형식 검증 · 병합 단위 · 내보내기 · 확장자 · 템플릿 폴더 |
| `page_doc.py` | 새 문서 · 검증 · 정규화 · 스타일 풀기 |
| `export_docx.py` | 표준 라이브러리 zip + XML 직접 작성(document · styles · numbering · header/footer · media) |
| PDF | Word 가 있으면 DOCX → Word COM(`render_docx.ps1`, 매크로·이벤트 끔), 없으면(또는 `?via=chrome`) 서버 Chrome 인쇄로 `page.html?deck=<id>&print=1`(DR-P06) |
| `import_docx.py` | Word 문서 가져오기(DP-P14) - 문단·서식·목록·표·그림·머리말 · 각주 → 앞 글자의 `fn` · 떠 있는 기본 도형·글 상자 → 개체 · 구역 `w:cols` → 단. `--blocks` = 문서를 만들지 않고 블록만 꺼냄(요청 첨부) |
| `deckmerge` · `deckops` · `deckdiff` · `proposals` · `ledger` | `blocks`(id 목록) 병합기·작업·diff 추가 - JS 쪽 nexa-merge 와 같은 사례 파일로 맞춘다 |
| `page_templates/` | 페이지 템플릿(§7) |

## 5. 글 편집 엔진 `nexa-text.js`

- **모델**: 문단 = `runs[]`. 엔진은 DOM 을 진실로 삼지 않는다 - 입력을 가로채 모델을 고치고 DOM 을 다시 그린다.
- **입력**: `contenteditable` 호스트 + `beforeinput` 가로채기(insertText · deleteContent* · insertParagraph · insertFromPaste · formatBold 등). **한글 조합(IME)** 중에는 브라우저가 DOM 을 고치게 두고 `compositionend` 에서 그 문단만 모델로 읽어 들인다.
- **선택**: 모델 좌표 `{block, offset}` ↔ DOM Range 변환. 서식 명령은 선택 범위의 runs 를 쪼개고 합친다.
- **붙여넣기**: HTML → runs 정규화(허용 서식만), 일반 글, 다른 문서의 블록.
- **실행 취소**: 공용 뼈대(문서 스냅숏 + NexaMerge.seal)를 쓰되 입력은 묶는다(단어·시간 단위).
- **쓰임**: 페이지 본문·표 셀·머리말 → 1단계. 슬라이드 글 상자·시트 셀 편집에 넣는 것은 페이지에서 안정된 뒤(2단계, 기존 `**굵게**` 표기와 runs 의 변환기를 둔다).
- **시험**: 모델 연산은 node 단위 시험(사례 파일), 입력·조합은 헤드리스 시나리오(CDP `Input.insertText` · `Input.imeSetComposition`).

## 6. 쪽 나눔

- 1단계(끝): 편집 화면은 이어진 본문에 **쪽 경계선**(근사)과 수동 쪽 나누기.
- 2단계(1차 끝 - PG-102 · 10-1): 편집 화면에서 실시간으로 쪽을 나눈다(줄 단위 분할 · 표 행 분할·머리글 행 반복 · 외톨이 줄 · 각주 자리). 인쇄는 그 결과를 그대로 쓴다(PG-054).

## 7. 템플릿

- `studio/page_templates/<이름>/template.json`(page · styles · 예시 blocks · 미리 보기 정보). 로고·전용 글꼴은 넣지 않는다.
- 기본 세트(DR-P07): 빈 문서 · 보고서 · 기획서/제안서 · 회의록 · 공문/레터 · 매뉴얼 · 이력서 · 논문/리포트 + 학습 자료 3종(2단 해설지 틀 · 문제지 · 어휘 정리).
- 추천 순서: 슬라이드와 같은 점수(만든 작업 공간·미리 보기·비슷함) - `hub.template_rec` 를 종류별로 쓰게 넓힌다.

## 8. 작업 공간·덱

- 작업 공간을 만들 때 첫 문서 종류를 셋 중에서 고른다. 그 뒤 덱 추가는 어느 화면에서든 셋 중 아무 종류(공용 "새 문서" 대화 상자).
- 내보내기는 덱 단위: 슬라이드 → PPTX/PDF · 시트 → XLSX · 페이지 → DOCX/PDF.
- 완성 전에는 **숨김**(DR-P11)이었고 2026-11-26 **기본 켬**으로 풀었다(DR-P13 · `RELEASED`). 끄기 = 작업 공간 `nexa-slide.json` 의 `"experimental": {"page": false}` 또는 환경 변수 `NEXA_SLIDE_EXPERIMENTAL=-page`.

## 9. 단계(백로그의 묶음)

| 묶음 | 내용 | 끝났다는 기준 |
|---|---|---|
| A0 | 무인 진행 체계(규칙 · 백로그 · 작업판 · 검증 진입점 · 권한) | `verify.py --level quick` 요약 한 화면, 작업판 갱신 |
| A1 | 공용 뼈대 - nexa-shell(js·css) 뽑기 | run_all 통과 · 슬라이드·시트 동작 같음 · PPTX XML 같음 |
| A2 | 종류 등록부 + 새 문서 대화 상자(세 화면·홈) | 어느 화면에서든 슬라이드·시트 추가, 페이지는 숨김 |
| B1 | nexa-text 엔진(모델 연산 → 입력 → 조합 → 붙여넣기) | 단위 시험 + 한글 조합 시나리오 |
| B2 | 페이지 편집기 뼈대(page.html·js·render, 문단·글자 서식, 스타일) | 만들기 → 편집 → 저장 → 다시 열기 |
| B3 | 목록 · 표 · 그림 · 쪽 설정 · 머리말/꼬리말/쪽 번호 · 쪽 경계 | 시나리오 |
| C1 | DOCX 내보내기 + PDF(Word/Chrome) + 동일성 시험 | Word 에서 열림(COM 검증) · 구조 비교 |
| C2 | 템플릿 11종 + 추천 | 홈·새 문서에서 고르기 |
| C3 | 병합·작업·diff·원장·제안·AI 요청(세션 규약) | 두 창 시나리오 · collab_sim 페이지 덱 |
| D | 1단계 마감 - 숨김 해제 판단(사용자) · 문서 | 보고 |
| E… | 2단계(실시간 쪽 나눔 · 구역/다단 · 개체 · 윗주 · 각주 · 가져오기 · 해설지 재현) | 예시 PDF 와 나란히 비교 |

## 10. 2단계 - 구현된 방식 (2026-11-26 메모를 2026-11-27 코드대로 고침)

공통 전제: 본문은 **한 호스트의 평평한 블록 목록**(nexa-text 가 `#ed` 의 자식으로 블록을 그린다)이고, 2단계의 쪽 나눔 · 다단 · 개체 · 각주 · 인쇄는 **이 구조를 바꾸지 않는다**. 처음 메모(쪽 요소 `.pg-sheet` 안에 블록을 옮겨 넣고 한 문단을 `data-part` 두 요소로 쪼개기)는 쓰지 않았다 - 글 편집 엔진(위치 계산·한글 조합·선택)과 병합·변경 기록이 "블록 하나 = DOM 하나"를 전제로 하기 때문이다. 표 칸은 칸마다 따로 붙인 편집기(편집기 안의 편집기 - `mine()` 이 가린다).

### 10-1. 실시간 쪽 나눔 = 빈 자리 끼우기 (PG-102 · `page-flow.js`)
- 모델·DOM 은 그대로 두고 쪽 경계에 **글이 없는 빈 자리**만 끼운다. 빈 자리에는 글자가 없어 nexa-text 의 글자 수 위치·조합·선택이 그대로 돈다.
  - 블록째 다음 쪽으로(`push`) = 그 블록의 위 여백(`margin-top`)을 늘린다. 쪽 머리로 민 블록에는 `.pg-pushed`.
  - 문단 가운데 줄 사이(`split`) = 그 줄 앞에 `span.pg-gap`(글 없는 너비 100% inline-block)을 끼운다. 줄 경계는 `Range.getClientRects()`.
  - 표의 행 사이(`row`) = 빈 행 `tr.pg-gaprow` 를 끼우고, 머리글 행이 있으면 그 사본 `tr.pg-headrep` 를 다음 쪽 머리에 되풀이(사본은 `data-id` 없음 · 편집 불가). 합친 칸이 걸친 행·머리글 바로 아래는 나누지 않는다.
- 계산은 순수 함수 `NexaPageFlow.plan(items, H, G, linesOf, opt)` → `{breaks, notes}`(시험 `page_flow_check.js`), 화면 붙이기는 `NexaPageFlow.create(opts)` → `{schedule, run, clear, pages}`. 좌표는 빈 자리를 뺀 자연 위치, 외톨이 줄 규칙 포함.
- 종이는 `#paper` 뒤에 쪽 수만큼 `.pg-sheet` 를 그리고(덮개 = 여백 가림 · 쪽 틈 · 쪽마다 머리말·꼬리말·쪽 번호 `.pg-hf`), 본문은 그 위의 `#ed` 하나다.
- 다시 재기: 바뀔 때 `schedule()` 이 16ms 뒤 **전체**를 다시 잰다(바뀐 쪽부터만 · 가상 스크롤은 아직 - 긴 문서 성능은 PG-102 남은 일). 본문 너비가 바뀌면(쪽 설정·글꼴) 빈 자리를 걷고 다시 잰다.

### 10-2. 구역·다단 = 단 너비로 좁힌 한 줄기 + 음수 밀기 (PG-101 1차 · DP-P16)
- 형식: 문서 `page.columns {count, gap}`, 구역 나누기 `{type: "break", kind: "section", columns}` 뒤부터 그 단 수, 단 나누기 `{type: "break", kind: "column"}`(3절). 같은 너비 단만 - 너비가 다른 2단은 배치용 표(DP-P07). 단 구분선(`sep`)·구역마다 다른 쪽 설정은 없다.
- 화면: 다단 구역의 블록마다 너비를 단 너비 `(본문 너비 - (n-1)·gap) / n` 로 좁혀 **한 줄기로** 쌓고, 다음 단에 놓일 블록은 위 여백을 음수로 줘서(앞 블록의 아래 여백만큼 빼서) 그 단의 위로 끌어올린 뒤 `position: relative; left = 단 번호 × (단 너비 + gap)` 로 옆으로 옮긴다(`plan` 의 `type: "col"`). 블록이 단을 넘치면 통째로 다음 단(마지막 단이면 다음 쪽 첫 단)으로 - **1차는 다단 구역에서 문단·표를 나누지 않는다**.
- DOCX: 구역마다 `w:sectPr` + `w:cols w:num w:space`(둘째 구역부터 `w:type continuous`, 머리말·꼬리말 참조는 첫 구역에만). 가져오기는 `w:cols` → `page.columns` / 구역 나누기 블록.
- 브라우저 인쇄·"PDF(화면 그대로)" 에서는 음수 밀기가 인쇄의 쪽 나눔과 맞지 않아 쪽 수가 화면과 다르다 - 알려진 한계(DP-P17 · PG-110). Word 로 내보낸 문서·Word 변환 PDF 는 맞다.

- **문단 나눔(PG-101 2차 · DP-P22 - 방식 D "꼬리를 보이는 곳만 옮긴다")**: 단에 다 안 들어가는 글 문단은 넘치는 줄부터 다음 단(마지막 단이면 다음 쪽 첫 단)으로 잇는다. 문단 요소는 하나 그대로 두고, 꼬리 줄을 `span.pg-colpart`(`position: relative` · `left` = 단 차 × 단 걸음 · `top` = 세로 이동)로 감싸 **보이는 곳만** 옮긴다(`plan` 의 `type: "colsplit"` · `at` = 꼬리가 시작하는 글자 위치) - 글자 수·위치 계산·한글 조합·선택은 그대로이고, 뒤 블록이 그 이동을 위 여백으로 받는다. 꼬리 자리는 1단의 줄 나눔과 같은 기준(앞 줄 아래 끝과 이 줄 위 끝의 가운데를 단 머리에 - 글자 상자의 위 끝을 맞추면 줄 간격의 반만큼 본문 밖으로 나가 150% 에서 걸친다). 외톨이 줄 규칙은 1단과 같다. 조합 중에는 다시 나누지 않고 끝난 뒤 나눈다. 글이 줄거나 단을 끄면 조각을 걷는다. 저장 문서·DOCX 에는 흔적이 없다.
  - 나누지 않는 것(통째로 다음 단): 바탕색/테두리 · 윗주 · 그림/개체가 든 문단 · 표.
  - 각주가 달린 문단도 나눈다(1974d97): 줄마다 그 줄의 각주 높이를 그 쪽의 각주 자리로 잡는다(1단의 줄 나눔과 같은 규칙) · 꼬리가 다음 쪽으로 가면 꼬리 줄의 각주도 다음 쪽 아래 · 나뉜 글 조각의 각주 번호는 뒤 조각에만(`data-fn` 을 `data-fn-hold` 로 잠시 옮김 - 걷으면 되돌림).
  - 시험의 겹침 판정은 "보이는 자리"로: 나뉜 문단의 실제 상자는 한 단에 길게 남으므로 `.pg-colpart` 가 든 문단은 글 줄 사각형으로 본다(나뉘지 않은 문단은 상자 그대로).

### 10-3. 개체 = 본문 문단에 매기 (PG-103 1차 · DP-P15)
- 형식은 3절 `objects`(`type: "shape"` · 9모양 · `anchor` = 본문 문단 id · `rel: "page" | "para"` · x·y·w·h mm · `z: "front" | "behind"` · 안의 글 `blocks`). 처음 메모의 `anchor: "page:<n>"`(쪽 번호 고정)은 쓰지 않는다 - 내보낸 DOCX 에서 줄 나눔이 달라져도 개체가 그 문단을 따라가게.
- 화면: 쪽 위의 층(`#objs`, 글 뒤는 `#objsBack`)에 절대 위치로 그린다. 자리 = 매인 문단이 놓인 쪽의 왼쪽 위(`rel page`) 또는 그 문단의 왼쪽 위(`rel para`)에서 잰 mm. 끌기·크기·메뉴(채움·선·글 뒤로·다른 문단에 다시 매기)는 page.js 안에 있다(슬라이드 편집기와 공용화는 PG-109). 매인 문단이 지워지면 남은 문단에 다시 맨다.
- 둘러싸기(`wrap`)는 아직 없다 - 개체는 글 위에 겹친다. 그림 개체도 아직 없다(그림은 본문 블록 `type: "image"`).
- DOCX: `wp:anchor`(positionH/V relativeFrom page|paragraph, EMU · `behindDoc` = z behind) + `wps:wsp`(도형·글 상자). 가져오기(`import_docx.py`)는 떠 있는 기본 도형·글 상자를 개체로(자리·크기·모양·선·채움·안의 글·글 뒤 - 모르는 모양·묶음·그림은 개체로 만들지 않고, 글 상자의 글은 문단으로 남긴다 - DP-P14).
- 예시 해설지의 타원·괄호·끊어 읽기 사선·단어를 잇는 화살표는 **글 범위에 붙어야** 줄이 바뀌어도 따라간다. Word 에는 그런 기능이 없다(도형은 문단에 매일 뿐). 지금: 문단에 맨 도형을 손으로 놓기. 글 범위 표시(`mark`)로 그리고 DOCX 로는 그 순간의 위치에 도형으로 굳혀 내보내기는 Word 호환을 벗어나므로 사용자 결정(D-P04).

### 10-3a. 각주 = 글 조각의 `fn` (PG-105 1차)
- 형식: run 의 `fn`(각주 글). 번호는 문서 순서(머리글 사본 행 안의 것은 세지 않음), 화면은 조각 뒤 위 첨자 번호(`[data-fn]::after`).
- 쪽 나눔: 블록·줄·행마다 달린 각주 높이 합(`fn`)을 재서(`noteH` - 본문 너비로 그려 잼, 글·자릿수로 기억) 그 참조가 놓인 쪽의 아래에 자리를 내주고 본문은 그만큼 덜 들어간다(구분선 높이 `noteSep` 포함). 한 줄도 안 들어가면 한 줄은 둔다.
- DOCX: `w:footnoteReference` + `word/footnotes.xml`. 가져오기는 각주를 그 앞 글자의 `fn` 으로. 미주는 없다.

### 10-3b. 인쇄 = 화면 쪽 나눔 그대로 (PG-054)
- `beforeprint`(또는 `?print=1`)에 인쇄 상태로 들어간다: 쪽 나눔을 한 번 더 재고(이미 인쇄 매체면 다시 재지 않음 - 4075c35), 개체를 매인 문단 안으로 옮겨 붙이고, 각주는 문서 끝 목록(`.pg-endnotes`)으로 모은다. `afterprint` 에 원래대로.
- 인쇄 매체(`page.html` 의 `@media print`): 빈 자리는 **높이 0 + `break-before: page`**(`.pg-gap` · `tr.pg-gaprow` · `#ed > .pg-pushed` 의 위 여백 0) - 화면에서 끼운 자리가 그대로 강제 쪽 나눔이 된다. 쪽 나누기 블록 `.pg-break` 는 `break-after: page`. 머리말·꼬리말·쪽 번호는 `@page` 여백 상자(`#pg-print` 스타일), 확대는 1.
- 서버 Chrome PDF 는 `page.html?deck=<id>&print=1`(글꼴이 뜬 뒤, 최대 3초 기다림). 한계: 다단 구역(10-2) · 쪽 아래 각주(브라우저 인쇄에서는 문서 끝) - PG-110.

### 10-4. 단어 아래 주석 (D-P01)
- 후보: ① 윗주를 "아래"에도(run 의 `gloss`) - 화면은 `::after`, DOCX 는 대응 기능이 없어 **조합 문자 배치(EQ 필드 `\\o`/`\\s`)나 표(단어마다 칸 2줄)**로 근사 ② 줄 사이에 주석 줄을 따로 두고 탭으로 맞춤(글이 바뀌면 어긋난다) ③ 낱말 표(배치용 표 한 행에 단어 칸, 아래 행에 뜻). Word 에서 정확히 나가는 것은 ③뿐이다. 사용자 결정이 필요하다.

### 10-5. 공용화 나머지 (PG-109 · PG-108)

**공용 컴포넌트 - 누가 쓰는지**(2026-11-27, 각 화면 html 의 `<script>` 기준 · ● = 쓴다):

| 파일 | 하는 일 | 슬라이드(index.html) | 시트(sheet.html) | 페이지(page.html) |
|---|---|---|---|---|
| `nexa-shell.js` | 화면 도우미 - api · 토스트 · 상태 · 배너 · 메뉴(PG-010) | ● | ● | ● |
| `nexa-kinds.js` | 문서 종류 등록부(슬라이드·시트·페이지 - 서버 kinds 와 같은 이름) | ● | ● | ● |
| `nexa-newdoc.js` | 새 문서 창(세 종류 템플릿 + 파일 가져오기 · 가져오기 경고 → [열기]) | ● | ● | ● |
| `nexa-text.js` | 글 편집 엔진(runs 모델·입력·한글 조합·선택) - 페이지 본문·표 칸·머리말, 슬라이드 글·도형 글·표 칸(PG-108) | ● | - | ● |
| `nexa-format.js` | 글자 서식 단추 `[data-mark]`(NexaFormat.html/bind/sync) - 페이지 서식 막대 `#fmtMarks` · 슬라이드 편집 중 서식 줄 `#ftb`(PG-043) | ● | - | ● |
| `nexa-requests.js` | 요청 관리(요청 만들기·목록·상태) | ● | ● | ● |
| `nexa-reqpanel.js` | AI 요청 패널 배선(NexaReqPanel.mount - 세션 표시·요청 모듈·보내기·목록·이벤트·판 따라가기, 화면별 차이는 어댑터) - 98c19d1 페이지 · 9251708 시트. 슬라이드는 초안·메모 흐름이 달라 묶지 않음 | - | ● | ● |
| `wsession.js` | 세션 칩·웹 AI 세션 | ● | ● | ● |
| `nexa-merge.js` | 3-way 병합(서버 deckmerge.py 와 같은 규칙) | ● | ● | ● |
| `nexa-live.js` | 실시간 동시 편집 2단계 - 페이지는 ae76948(밖의 저장 즉시 반영 · "함께 N" 칩 · 문단 왼쪽 색 띠 · 지워진 문서는 `NexaLive.stop()`) | ● | ● | ● |
| `nexa-doc.js` | 문서 저장 상태기계(저장·예약 저장·병합 저장·409 · 다시 읽기 직전 판 확인 `stillChanged` - DR-P14 · PG-109) - f21af7c 페이지 · c7ff9fb 시트 · 06e2da5 슬라이드 | ● | ● | ● |
| `nexa-doc.js` 의 `follower` | 밖의 변경 따라가기(판 폴링 · 실시간 연결 겸용 · 처리 중 온 판은 마지막 하나 · 지워진 문서 = 판 없음/"0"/목록에 없음 · 고치는 중이면 저장, 아니면 `stillChanged` 뒤 다시 읽기 - DR-P14 · PG-109) - 8e2fd68 슬라이드·시트 · 5eb8732 페이지(고유 = 3초 폴링 · 충돌 배너/가려진 창에서 쉼 · 선택·표 칸 초점 지키기) · 세 화면 모두 실시간 연결(SSE)이 살아 있으면 폴링은 15초 안전망(페이지 ae76948) | ● | ● | ● |
| `nexa-doc.js` 의 `history` | 실행 취소·다시 실행(snapshot · undo · redo · 밖의 변경을 받을 때 봉인 - 기록 항목 = 문자열 또는 `{b, sel?, a?}` - DR-P14 · PG-109) - ae20ef2 세 편집기(페이지 고유 = 선택 기억 · 슬라이드의 끌기·글 편집 기록 자리는 그대로) | ● | ● | ● |
| `nexa-objects.js` | 개체 조작(고르기·이동·크기·복제·지우기 계산 + attach - DR-P14 · PG-112) - a522140 페이지 개체 · a838578 시트 그림. 슬라이드 요소는 다음(끌기 수식키부터) | (예정) | ● | ● |

**동작 기준표 - 개체 조작·다시 읽기**(DR-P14 · 2026-11-27 · 시험 = page_ui_test 개체 조작 · sheetx_test 그림 단계):

| 동작 | 기준(공용) | 페이지 개체 | 시트 그림 | 슬라이드 요소 |
|---|---|---|---|---|
| 손잡이 | 8방향(`.nx-h[data-nxh=nw…w]`) - 맞은편이 고정 · 변 손잡이는 한쪽 길이만 | ● (선 도형은 se 하나) | ● (se = `#drawHandle`, 상자 `#drawHandles`) · **모서리는 늘 비율 유지, Shift 로 풀기** | 8방향(`#ov .hd[data-h]`) - 그림·아이콘 모서리는 늘 비율 유지 · Shift 로 풀기 / 도형·글 상자는 Shift = 비율 유지(DP-P21 · 자체 구현, 모듈 연결은 예정) |
| 여럿 고르기 | Shift/Ctrl+누르기로 더하기 · 같이 끌기 | ● | ● | ● (자체 배선 · 시험 slidedrag_test) |
| 여럿 고른 것 중 하나를 누르기만 | 그것만 남는다(DP-P20 - PowerPoint 와 같음), 끌면 모두 같이 | ● | 공용 기준(시험 없음) | ● (f4fa1c6 - 공용 기준 함수 · 오른쪽 클릭은 여럿 유지 · 시험 slidedrag_test) |
| 화살표 | 한 걸음 / Shift 큰 걸음 | 0.5mm / 5mm | 1px / 8px(셀 커서는 그대로) | 1px / 8px(`NexaObjects.nudge` · 시험 slidedrag_test) |
| Ctrl+D | 복제하고 새 것을 고른다 | +5mm | +12px(그림을 골랐을 때만 - 아니면 아래로 채우기) | 예정 |
| Shift 끌기 | 한 축으로만 | ● | 공용 기준(같은 코드, 시험 없음) | ● (DP-P21 - 예전 Shift = 격자 끄기는 Ctrl 로 · 시험 slidedrag_test) |
| Ctrl 끌기 | (슬라이드) 격자 8px·스마트 가이드 끄기 = 자유 이동 | - | - | ● |
| Esc · Delete | 고르기 풀기 · 고른 것 지우기(실행 취소 한 번 = 조작 한 번) | ● | ● | 예정 |
| 끌기 시작 | 화면 3px 넘게 움직여야 끌기 | 공용 기준(시험 없음) | ● | 예정 |
| 밖의 변경 다시 읽기 직전 확인 | `NexaDoc.stillChanged` - 서버에 더 묻지 않는다. 방금 끝난 내 저장(1.5초 안, `S.savedAt`)이면 다시 읽지 않고 잠시 뒤 한 번 다시 확인 · 판 "0"·없음(지워진 문서)은 읽지 않음 | (페이지는 자체 저장 흐름) | ● | ● |

- 저장·실행 취소·밖의 변경 따라가기(page.js 의 save · sealUndo · poll)는 studio.js·sheet.js 와 뼈대가 같다 → `nexa-shell.js` 에 `createDoc({load, dump, merge, onExternal})` 로 올리고 세 화면이 쓴다. 실시간 연결(nexa-live)·함께 보는 사람도 그때 페이지에 붙는다.
  지금(2026-11-27): 아직 page.js 안에 있다(`save` · `sealUndo` · 밖의 변경 따라가기) - `nexa-shell.js` 는 api·toast·상태·배너·메뉴까지(PG-010).
- 서식 막대 중 글자 서식 단추는 `nexa-format.js` 로 뽑았다(b01a5cb - 페이지 `#fmtMarks` · 슬라이드 `#ftb`). 문단·스타일·글꼴/색 단추는 아직 page.js bindTools 안에 있고, 시트 셀은 nexa-text 를 쓰지 않는다.
- PG-108 1차(끝): 슬라이드 글·도형 글·표 칸 편집이 nexa-text(studio.js `richEdit` - `Render.runs` 표기 → runs, 저장은 전과 같은 표기 글 · 손대지 않은 줄은 원문 그대로)이고, 편집 중 서식 줄이 있다(eae1b41). 글머리·코드 요소는 원문 편집, 시트 셀은 nexa-text 를 쓰지 않는다.
