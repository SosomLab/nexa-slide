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
5. **kind 는 등록부로** - `== "sheet"` 2분기(19개 파일 약 57곳)를 종류 등록부 조회로 바꾼다. 모르는 kind 가 슬라이드로 떨어지지 않게 한다.

## 3. 문서 형식 (`decks/<id>.json`, kind = "page")

```json
{"id": "report1", "title": "…", "kind": "page", "version": 1, "updated": "…", "slides": [],
 "page": {"size": "A4", "orient": "portrait", "margin": {"t": 25, "r": 20, "b": 25, "l": 20},
          "header": {"blocks": []}, "footer": {"blocks": []}, "first": null, "number": {"show": true, "pos": "footer-center"}},
 "styles": {"body": {"font": "body", "size": 10.5, "line": 1.6}, "h1": {"based": "body", "size": 20, "bold": true}},
 "blocks": [
   {"id": "b01", "type": "p", "style": "h1", "runs": [{"t": "제목"}]},
   {"id": "b02", "type": "p", "align": "justify", "runs": [{"t": "본문 "}, {"t": "굵게", "b": 1}, {"t": " 색", "c": "accent"}]},
   {"id": "b03", "type": "p", "list": {"kind": "bullet", "level": 0}, "runs": [{"t": "항목"}]},
   {"id": "b04", "type": "table", "cols": [40, 60], "rows": [{"id": "r1", "head": true, "cells": [{"id": "c1", "blocks": []}]}]},
   {"id": "b05", "type": "image", "src": "assets/…", "w": 80, "align": "center"},
   {"id": "b06", "type": "break", "kind": "page"}
 ],
 "objects": []}
```

- `slides: []` 는 서버 검증 호환용으로 둔다(시트와 같은 이유) - 종류 등록부가 자리 잡으면 뺀다.
- 길이 단위 = mm, 글자 크기 = pt. 색·글꼴은 토큰 이름(`accent`, `body`) 또는 값 - 슬라이드와 같은 `tokens.json`·`fontPresets` 를 쓴다.
- **블록마다 id** - 병합·diff·작업(op)·AI 제안의 단위. 표는 행·셀 id.
- **목록은 문단의 속성**(`list: {kind: bullet|number|check, level, restart?, done?}`) - Word 의 번호 매기기와 같다. 이어진 목록 문단이 한 목록이고 번호는 그릴 때 센다(DP-P06).
- `runs` = [{t, b, i, u, s, c, hl, sup, sub, font, size, link, ruby}] - 인접한 같은 서식은 합쳐 저장한다(정규화).
- `objects`(2단계) = 글 상자·도형·그림: `{id, anchor: "block:<id>" | "page:<n>", x, y, w, h, wrap, …}`. 모양·선·채움은 슬라이드 요소와 같은 표현을 쓴다(공용 렌더).

## 4. 구성

### 4-1. 화면(공용)

| 모듈 | 내용 | 뽑는 곳 |
|---|---|---|
| `nexa-shell.js` · `nexa-shell.css` | api · toast · 상태 칩 · 배너 · 메뉴(openMenu) · 실행 취소 뼈대 · save/scheduleSave · loadDeck/poll/applyVersion · 확대 · 머리 막대·옆 패널 뼈대 | studio.js · sheet.js 의 중복 약 250줄, 인라인 스타일 약 880줄 |
| `nexa-newdoc.js` | "새 문서" 대화 상자 - 슬라이드/시트/페이지 선택 + 종류별 템플릿(추천 순). 홈·세 편집기가 같이 쓴다 | home.html setKind · studio deckCreate · sheetnew.js |
| `nexa-text.js` | **글 편집 엔진**(§5) | 새로 |
| `nexa-format.js` | 글자·문단 서식 막대, 글꼴·색 고르기 | studio.js palette·colorOptions·글꼴 세트, sheet.js 글꼴 |
| `nexa-export.js` | 내보내기 메뉴·진행·내려받기 | studio doExport · sheet exportXlsx |
| 기존 공용 | nexa-merge · nexa-live · nexa-requests · wsession · menu · search · lightbox | 그대로(kind 분기만 등록부로) |

### 4-2. 화면(페이지 고유)

`page.html` · `page.js`(편집기) · `page-render.js`(블록 → DOM, 인쇄·미리 보기와 같이 씀) · `page-print.html`(Chrome 인쇄용).

### 4-3. 서버

| 모듈 | 내용 |
|---|---|
| `kinds.py` | 종류 등록부: 이름 · 편집기 html · 새 문서 만들기 · 형식 검증 · 병합 단위 · 내보내기 · 확장자 · 템플릿 폴더 |
| `page_doc.py` | 새 문서 · 검증 · 정규화 · 스타일 풀기 |
| `export_docx.py` | 표준 라이브러리 zip + XML 직접 작성(document · styles · numbering · header/footer · media) |
| PDF | Word 가 있으면 DOCX → Word COM(`render_docx.ps1`, 매크로·이벤트 끔), 없으면 Chrome `--print-to-pdf` 로 `page-print.html`(DR-P06) |
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

- 1단계: 편집 화면은 이어진 본문에 **쪽 경계선**(블록 높이를 재서 표시, 정확도는 근사)과 수동 쪽 나누기. 정확한 쪽 모양은 **인쇄 미리 보기**(page-print.html 이 블록을 쪽 상자에 흘림)와 PDF.
- 2단계: 편집 화면도 쪽 상자에 흘린다(줄 단위 분할, 표 행 분할·머리글 행 반복, 외톨이 줄 제어, 각주).

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

## 10. 2단계 설계 메모 (2026-11-26, 다음 세션이 이어서)

지금까지: 본문은 **한 호스트의 평평한 블록 목록**(nexa-text 가 `#ed` 의 자식으로 블록을 그린다). 표 칸은 칸마다 따로 붙인 편집기(편집기 안의 편집기 - `mine()` 이 가린다).
2단계의 세 가지(실시간 쪽 나눔 · 다단 · 쪽 고정 개체)는 모두 "블록을 어디에 놓는가"를 바꾸는 일이라 **한 번에 설계한다**.

### 10-1. 실시간 쪽 나눔 (PG-102)
- 모델은 그대로(평평한 blocks). **배치만** 쪽 상자로: `#ed` 안에 쪽 요소(`.pg-sheet` - 용지 크기, 머리말·본문·꼬리말 자리)를 만들고 블록 요소를 그 본문 자리에 넣는다.
- nexa-text 에 `opts.place(el, block, index)`(블록 요소를 넣을 부모를 돌려준다)와 "호스트의 직계 자식"이라는 가정 풀기가 필요하다: `pointFrom` 은 `[data-id]` 를 가진 가장 가까운 블록 요소까지 올라가고(지금은 host 의 자식까지), `render` 는 부모가 다른 요소도 순서대로 옮긴다.
- 넘침 계산: 그린 뒤 블록 높이를 재서(`offsetHeight`) 쪽 본문 높이(`pageBox.ch` mm → px)에 쌓는다. 넘치는 블록은 다음 쪽으로. **문단 중간 분할**은 줄 단위로: 문단 요소의 `Range.getClientRects()` 로 줄 경계를 얻어 앞쪽 줄 수를 정하고, 한 문단을 두 요소(같은 data-id, `data-part`)로 그린다 - 위치 변환은 part 를 이어 붙여 센다.
- 표: 행 단위로 나누고 머리글 행을 다음 쪽 머리에 되풀이(그린 것일 뿐 모델은 그대로). 외톨이 줄(문단의 첫 줄·끝 줄만 남는 것)은 2줄 규칙.
- 입력마다 전체를 다시 흘리지 않는다: 바뀐 블록이 있는 쪽부터 뒤로만. 긴 문서(200쪽)는 보이는 쪽 근처만 정확히, 나머지는 높이 추정(가상 스크롤) - 1차 구현은 전체 흘리기 + 디바운스로 시작한다.
- 머리말·꼬리말·쪽 번호는 쪽 요소마다 그린다(지금의 `#pgHeader`·`#pgFooter` 를 대체). 인쇄는 쪽 요소마다 `break-after: page` - 화면과 인쇄가 같아진다(PG-054 완성).

### 10-2. 구역·다단 (PG-101)
- 지금은 배치용 표(DP-P07). 진짜 다단: `break` 블록의 `kind: "section"` 이 그 뒤 구역의 쪽 설정·단(`cols: [{w}], gap, sep`)을 갖는다(없으면 문서의 `page`). 쪽 상자 안에 단 상자를 만들고 블록을 단 → 쪽 순서로 흘린다(10-1 의 배치 함수가 "쪽·단" 두 단계가 된다). 단 나누기 = `break kind column`.
- DOCX: 구역마다 `w:sectPr`(구역의 마지막 문단 pPr 안) + `w:cols`(equalWidth 0, `w:col w:w`).

### 10-3. 쪽 고정 개체 (PG-103)
- `objects: [{id, type: "box"|"shape"|"line"|"image", anchor: "page:<n>"|"block:<id>", x, y, w, h(mm), wrap: "none"|"square"|"top-bottom", z: "front"|"behind", …모양}]`. 모양·선·채움·글은 슬라이드 요소의 표현(render.js)을 같이 쓴다 - 타원·괄호·화살표·말풍선이 이미 있다.
- 화면: 쪽 요소 위의 절대 위치 층(쪽 고정) 또는 그 블록 요소 기준(문단 고정). 끌어 옮기기·크기 조절은 슬라이드 편집기의 것을 공용으로(PG-109 와 함께). 둘러싸기는 1차로 none(겹침)과 top-bottom(블록 사이에 자리 비우기)만.
- DOCX: `wp:anchor`(positionH/V relativeFrom page|paragraph, EMU) + `wps:wsp`(도형·글 상자) / `pic:pic`. 가져오기는 지금 글만 꺼낸다(DP-P14).
- 예시 해설지의 타원·괄호·끊어 읽기 사선·단어를 잇는 화살표는 **글 범위에 붙어야** 줄이 바뀌어도 따라간다. Word 에는 그런 기능이 없다(도형은 문단에 고정될 뿐). 1차: 쪽 고정 도형으로 손으로 놓기(한글에서 하던 방식). 2차(Word 호환을 벗어나므로 사용자 결정 필요 - D-P04): 글 범위 표시(`mark`)로 그리고 DOCX 로는 그 순간의 위치에 도형으로 굳혀 내보내기.

### 10-4. 단어 아래 주석 (D-P01)
- 후보: ① 윗주를 "아래"에도(run 의 `gloss`) - 화면은 `::after`, DOCX 는 대응 기능이 없어 **조합 문자 배치(EQ 필드 `\\o`/`\\s`)나 표(단어마다 칸 2줄)**로 근사 ② 줄 사이에 주석 줄을 따로 두고 탭으로 맞춤(글이 바뀌면 어긋난다) ③ 낱말 표(배치용 표 한 행에 단어 칸, 아래 행에 뜻). Word 에서 정확히 나가는 것은 ③뿐이다. 사용자 결정이 필요하다.

### 10-5. 공용화 나머지 (PG-109 · PG-108)
- 저장·실행 취소·밖의 변경 따라가기(page.js 의 save · sealUndo · poll)는 studio.js·sheet.js 와 뼈대가 같다 → `nexa-shell.js` 에 `createDoc({load, dump, merge, onExternal})` 로 올리고 세 화면이 쓴다. 실시간 연결(nexa-live)·함께 보는 사람도 그때 페이지에 붙는다.
- 서식 막대(page.html `#tools` + page.js bindTools)는 `nexa-format.js` 로 뽑아 슬라이드 글 상자·시트 셀이 nexa-text 를 쓸 때(PG-108) 같이 쓴다. 기존 `**굵게**` 표기 ↔ runs 변환기가 먼저다.
