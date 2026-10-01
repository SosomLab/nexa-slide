# Genspark AI Slides 실측 보고서 (2026-10-01)

> 목적: 웹 슬라이드 생성·편집 도구의 진행 과정·저장 구조·편집 화면·검사 기능을 관찰해 nexa-slide 설계에 참고한다.
> 방법: Claude 데스크톱 내장 브라우저(무료 플랜 계정)에서 SQL 튜닝 교재 8장 분량 요청문(내용·코드·실행계획·각주·노트·디자인 요구 포함)을 제출하고, 진행 과정·생성 HTML·편집 화면을 DOM/네트워크 수준에서 관찰. 모드 프로페셔널, 모델 Standard, 로고 파일 미첨부.
> 범위: 화면·DOM·네트워크 관찰 결과만 적는다. 생성 HTML 원본과 에이전트가 만든 로고는 교재 저장소 쪽 조사 자료로 따로 두고 이 저장소에는 넣지 않는다(상표·교재 내용).
> 관련: 레이아웃 검사 출력 원문과 판정 기준 역산은 [genspark-check-layout.md](genspark-check-layout.md). 이 실측을 반영한 기능은 CHANGELOG 0.3.0(레이아웃 검사).

## 1. 비용·시간

| 항목 | 값 |
|---|---|
| 걸린 시간 | 제출 약 16:42 → 완료 17:04 KST, **약 22분** (초안 8장 ~11분 + 레이아웃 점검·재작성 ~11분) |
| 크레딧 | 시작 잔액 100(무료 일일 지급) → 0. `spent_since_gift_total` **294**, `tasks_since_gift` 2 (`last_task_cost` 140 → 154). 잔액이 0이어도 작업은 끝까지 진행됨(floor 0) |
| 저장 지점 | 작업 1건이 끝날 때 **덱 전체 1개**(git 커밋, 메시지는 에이전트가 작성: "Add Oracle SQL tuning chapter 0 slide deck (8 slides)") |
| 내보내기 | 무료 플랜 불가 — PDF/PPTX/Google Slides 모두 "Plus, Pro, Team 멤버에게 제공" |

## 2. 진행 과정 (에이전트 작업 흐름)

1. 생각 26초 → `파일 탐색: Checking project state`
2. 생각 46초 → `심층 사고` 할 일 12개: manifest(8장 playlist) · 로고 SVG · 1~8장 각각 · `check_slide_layout` 반복 · 사용자에게 보여 주기
3. `파일 쓰기` 순차: manifest → 로고 → 1장 → (생각 144초) → 2·3·4장 → (생각 138초) → 5·6·7·8장
   - manifest를 먼저 쓰므로 8장 파일명이 처음부터 확정되고 `phase: pending → ready`로 장마다 캔버스에 나타남
4. `슬라이드 레이아웃 확인` 1~4장 / 5~8장 → 3·7장 경고
5. `프레젠테이션: Capturing slide N for visual review`(스크린샷으로 자기 검토) → 3·7장 재작성 → 재검사 → 3장 3회 재작성("그룹 사각형 자체를 떼고") → `일괄 편집`·`파일 편집`(화살표 방향 수정) → 최종 전체 검사·캡처 8장 → 완료 보고
- 사고 과정(영문)이 실시간 노출, 사용자 안내는 한국어. 웹 검색 단계 없음(요청대로).

### 레이아웃 검사 도구 `check_slide_layout` 출력 형식(실물)
```
Layout check — deck <id>, canvas 1920×1080, N slide(s): 0 error(s), 3 warning(s)
ERROR findings are mechanically verified defects (held-out precision >=80%). ...
WARNING findings are likely-but-unconfirmed. Verify with capture_slide_screenshot region capture before acting.
[t2.cutoff.spill] el[10041] (textbox, at 680,548 300×17) "…" — text clipped (rect …, ~114px cut)
[t1.overlap.text-text] el[2] (textbox …) ∩ el[4] (textbox …) → 106×5 at (318,210)
[t1.overlap.text-crosses-border] el[61] (shape …) ∩ el[81] (textbox …) → 101×5 at (339,880)
```
- 규칙 ID 체계 `t1.overlap.*`, `t2.cutoff.*`, 심각도 ERROR(정밀도 ≥80% 검증)/WARNING(캡처로 확인 후 수정), 요소 번호·종류·좌표·교차 영역까지 출력.
- **최소 글자 크기·원문 대조·의미(화살표가 맞는 생명선에 붙었는지)는 검사하지 않음** → 아래 결함이 통과됨.

## 3. 저장 구조 (`GET /api/project/slide_data`)

- `project_type: slides_agent_git`, `editor_version: v1`
- `meta_data.decks[]`: name, folder `<name>.slides`, title, description, slide_count, canvas `{1920,1080}`, cover_url
- `head_sha`(git 커밋), `asset_oids`(파일명→blob SHA), `pilot_mode`, `is_finished`
- `file_contents[]`: index, filename(의미 있는 이름: cover.html, tuning-order.html …), content, cdn_url(`?v=<sha>`), phase
- `multiplayer_info`: version_number, version_etag(낙관적 동시성)
- 버전 기록: `with_version_history=true&history_only=true` → version_number, commit_sha, ctime, version_description

## 4. 슬라이드 HTML 구조 (코드 수준)

- 장당 독립 HTML, `.slide-container` 1920×1080, **모든 최상위 개체 `position:absolute` 픽셀 좌표, 중첩 개체 0**
- 최상위 개체 표시: `data-object="true" data-object-type="shape|textbox|image|table"` — PPTX 기본 개체와 1:1 대응 의도
- 노트: `<template data-slide-notes>` (같은 파일 안)
- 표시: iframe `srcdoc` + `sandbox="allow-scripts allow-same-origin"` + `<base href=…/slides/>`
- CSS 효과(gradient·blur·shadow) 0 — 요청 톤 준수. 글꼴 `'Malgun Gothic','Pretendard','Noto Sans KR'`, 코드 `Consolas,'D2Coding'`
- 코드 블록: 줄마다 flex 행(줄 번호 span + `white-space:pre` 코드 span), 토큰별 인라인 `<span style=color>` 수작업 하이라이트(예약어 #0000A0, 테이블 #0E5C2F, 바인드 #7D5700, 함수 #1170B5, 주석 #7D7D7D 이탤릭, 문자열 #A91F24). **강조 줄 배경은 별도 shape 사각형을 픽셀로 겹침**(코드와 분리 → 줄 높이가 바뀌면 어긋날 위험)
- 시퀀스 다이어그램(3장): **SVG 없이 div 92개**(shape 55 + textbox 36). 화살촉은 CSS border 삼각형, 역방향 화살표는 `transform:scaleX(-1)` — PPTX 변환 시 확인 필요

| 파일 | 크기 | 개체(종류) | 최소 글자 | 14px 미만 수 |
|---|---|---|---|---|
| cover | 3.6KB | 7 (image1 shape2 textbox4) | 14px | 0 |
| tuning-order | 10.7KB | 25 (image1 shape13 textbox11) | 13px | 1 |
| seven-stage-journey | 25.7KB | 92 (image1 shape55 textbox36) | **10px** | 27 |
| cost-by-stage | 10.8KB | 6 (… table1) | 11px | 5 |
| workload-pair | 10.2KB | 12 | 13px | 2 |
| same-plan-different-slope | 7.6KB | 18 | 13px | 3 |
| viewing-execution-plan | 11.8KB | 15 | 13px | 2 |
| reading-execution-plan | 11.8KB | 7 (… table1) | 11px | 2 |

## 5. 요구사항 대비 결함 (원문 대조)

| # | 요구 | 결과 | 비고 |
|---|---|---|---|
| 1 | 정확히 8장·순서·제목 | ✅ | |
| 2 | 내용 충실성 | ❌ | 영문 장식 라벨 추가(CHAPTER, SECTION 0 · REQUIRED, BUSINESS/DESIGN…, RESULT, PLAN, ORACLE SQL TUNING · 3-DAY COURSE). 5장에 **없는 각주 지어냄**("* 실측 환경 표기는 본문 7장…") |
| 3 | 코드·실행계획 한 글자도 불변 | ⚠️ | 5장 SQL 14줄 **완전 일치**, 7장 SQL 일치. **7장 실행계획 Id 4 줄: 강조 span이 공백 2칸씩 삼켜 열 정렬 깨짐**(`|      2 |` → `|    2 |`) |
| 4 | 줄 번호·강조 줄·토큰 색 | ✅ | |
| 5 | 각주 위첨자·하단 | ✅(형식) | `vertical-align:super` span |
| 6 | 노트 원문 그대로 | ⚠️ | 1~7장 원문 그대로. **8장은 요청에 노트가 없는데 지어냄** |
| 7 | PPTX 편집 가능 | 미확인 | 무료 플랜 내보내기 불가. 구조(data-object-type, `<table>`)는 편집 가능 개체 지향 |
| 8 | 본문 ≥14pt, 각주 ≥10pt | ❌ | 1920 캔버스 1px=0.5pt. 본문 16~22px ≈ 8~11pt, 각주 11~13px ≈ 5.5~6.5pt. **에이전트는 "모든 슬라이드에서 기준 충족"이라고 거짓 보고**(px와 pt 혼동) |
| 디자인 | 로고 | ❌ | 첨부가 없자 확인 질문 없이 **로고를 지어냄**(사각형 2개 + 회사명 글자로 된 임시 SVG) |
| 디자인 | 3장 경계 묶음 | ❌ | 레이아웃 경고를 없애려고 "WAS 프로세스"/"DBMS" 경계 사각형을 **제거**하고 칩+밑줄로 대체. opt/loop 프레임도 글자로만 |
| 디자인 | 3장 의미 | ❌ | 자기 호출 상자가 엉뚱한 생명선에(파서 호출 상자가 x=1180 — 파서 생명선은 1029), 글꼴 오타 `'Malgian Gothic'` |
| 디자인 | 8장 depth 들여쓰기·연결선 콜아웃 | ❌ | "SELECT STATEMENT (0)"처럼 숫자를 글자로 붙임, 콜아웃은 표의 열로 대체 |

## 6. 편집 화면 구성 (속성·기본값·범위)

### 6.1 워크스페이스 배치
- 머리줄: `chat-collapse-toggle` · 덱 탭(`deck-tab-<id>`, 한 프로젝트 여러 덱) · `present-btn` 발표 · `deck-export` 내보내기 · `history-toggle` 기록 · `files-toggle` 파일 · `deck-overflow-trigger`(프레젠테이션 보기 / 사본 만들기 / 스킬로 저장)
- 왼쪽 레일 `slides-v2-rail`: 썸네일 + `rail-hidden-badge-N` + `rail-mark-badge-N`(주석 수, 기본 0) + 편집 모드에서 `rail-kebab-N`(페이지 작업) · `rail-splitter`(드래그 크기, 더블 클릭 초기화)
- 아래 `canvas-footer`: 개요/노트/검증 탭 · 이전/`slide-counter`/다음 · 줌(`zoom-slider` range **10~300, step 1**, 기본=화면 맞춤 약 25%) · `zoom-fit`
- 노트 패널: 보기 모드 읽기 전용, 편집 모드에서 `notes-edit-field` 편집 가능

### 6.2 모드 전환 (`canvas-subtoolbar`, 기본 = 선택)
| 모드 | testid | 기능 | 하위 도구 |
|---|---|---|---|
| 선택 | slide-select-mode | 요소 클릭 → 메모 → 한꺼번에 에이전트 전송 | 검증 메뉴(`verify-page`/`verify-deck`), AI 버튼 `ai-edit-fix-layout`(겹침·넘침·정렬 수정), `ai-edit-polish`(스타일 유지하며 논리·레이아웃 개선). 오버레이 SVG `sdo-root is-pick` |
| 그리기 | slide-draw | 영역 표시 → 메모 → 한꺼번에 전송 | `draw-tool-pen` 펜 / `draw-tool-marker` 마커 / `draw-tool-rect` 박스, 레이어 `stage-draw-layer`(SVG) |
| 편집 | slide-advanced-edit | 직접 편집(크레딧 없음) | 아래 6.3~6.5 |

### 6.3 편집 모드 기술 구조
- iframe 문서를 `designMode="on"`, body `contenteditable=true`로 전환 + 그 위에 **Fabric.js 6.9.1** 캔버스(`lower-canvas`/`upper-canvas`)를 겹쳐 선택·이동·크기·회전 핸들 처리. 래퍼 `iframe-fabric-wrapper` 1920×1080 `transform:scale(0.2495)`
- iframe에 주입 스크립트(중국어 주석) `ContextMenuManager`: selectionchange·click·keyup으로 가장 가까운 블록 요소(p/div/h1~6/li/table/td…)를 찾아 위치 통지
- 상단 편집 도구줄(`editor-toolbar--compact`, Naive UI): 실행 취소·다시 실행(이력 없을 때 비활성) | 이미지 업로드 · 링크 삽입 · 표 삽입 · 텍스트 추가

### 6.4 텍스트 서식 도구줄 (텍스트 상자 더블클릭 시)
| 항목 | testid | 형식 | 기본값/범위 |
|---|---|---|---|
| 글꼴 | fabric-text-font-family | 드롭다운 | Default Font / SimHei / SimSun / Microsoft YaHei / Arial / Times New Roman / Georgia / Verdana — **한글 글꼴 없음** |
| 크기 | fabric-text-font-size | number + 스피너 | **min 6, max 400, 단위 CSS px**(선택 텍스트 18 표시) |
| 크기 프리셋 | fabric-font-size-presets-toggle (▾) | 드롭다운 | 8·10·12·14·16·18·20·24·28·32·36·40·48·56·64·72·80·96·120·144 |
| 글자색 | fabric-text-color | 팝오버 | 채도·명도 판 + 색상 슬라이더 + HEX 입력(복사 버튼) + 프리셋 25색(회색 7 + 파스텔 6 + 중간 6 + 진한 6) |
| B / I / U / S | fabric-text-bold/italic/underline/strikethrough | 토글 | 현재 상태 active 표시 |
| 정렬 | fabric-text-align-cycle | 순환 버튼 | 누를 때마다 정렬 전환 |
| 간격 | fabric-text-spacing | 팝오버 | 줄 간격 range **0.5~3 step 0.05**(숫자 칸 step 0.1, 기본 1.2) · 자간 range **-5~20 step 0.1**(단위 px로 추정) |

### 6.5 개체(이미지·도형) 도구줄 — 끝의 ✥▾ 확장 포함
- 버튼: 이미지 교체 · 이미지 자르기 · 이미지 재설정 · 이미지 맞추기 · `image-focus-btn` 초점 변경 · 복제(Ctrl+D) · 삭제(⌫) · **`fabric-align-menu-button` 위치 조정(✥▾)**
  - div 배경 도형(카드 배경)도 이 '이미지' 도구줄로 선택됨 → 도형 채우기·테두리 편집 도구는 없음
- ✥▾ 위치 조정 메뉴:
  - 정렬 6종(슬라이드 기준): 왼쪽 / 가로 중앙 / 오른쪽 | 위쪽 / 세로 중앙 / 아래쪽
  - 순서 4종: 앞으로(Ctrl+]) / 뒤로(Ctrl+[) / 맨 앞(Alt+Ctrl+]) / 맨 뒤(Alt+Ctrl+[) — `fabric-zorder-*`
  - 수치 입력(스테퍼 포함, min/max 없음): 너비·높이 px, **비율 잠금 버튼(기본 해제)**, X·Y px, 회전 °
  - 값은 1920×1080 슬라이드 좌표(예: 카드 290×420 @ 200,330, 회전 0)
- 오른쪽 클릭: 복사 Ctrl+C · 잘라내기 Ctrl+X · 붙여넣기 Ctrl+V · 복제 Ctrl+D · 삭제 ⌫ | 앞으로 · 뒤로 · 맨 앞 · 맨 뒤

### 6.6 기록 패널
- `slides-history-panel`: 저장 지점 목록(`history-version-N`), 항목 = "저장 지점-1 · 현재 · 2026. 10. 1. 오후 5:04:08 · 커밋 메시지". 단위는 **에이전트 작업 1건 = 덱 전체 1개**

## 6A. 모드·컨트롤 유형별 전체 검토 (2차, 17:30~17:45)

### 6A.1 선택 모드 (기본 모드)
- 클릭 단위 = 최상위 `data-object` 개체 하나. 선택하면 개체 경계에 빨간 사각형(`sdo-pending-box`, #EF4444 3px, rx 4)
- 메모 편집기 `sdo-editor`: textarea **maxlength 2000**, 취소 / 확인(글자를 입력하기 전까지 비활성)
  - 자리 표시 글과 **빠른 칩이 개체 종류에 따라 달라짐**
    - 도형·글상자: "이 도형에서 무엇을 변경해야 하나요?" + 칩 `sdo-quick-beautify` 꾸미기 · `sdo-quick-verify` 검증
    - 이미지: "이 이미지에서 무엇을 변경해야 하나요?" + 칩 `sdo-quick-replaceImage` 더 나은 이미지 · 꾸미기
- 확인 → 번호 배지가 붙은 기록(`sdo-record-N`, 빨간 원 + 흰 번호), 레일 배지 +1
- **편집 대기열** `slides-edit-queue`: "· 총 N개의 편집", 설명 "여러 페이지에 변경 사항을 표시한 후 한꺼번에 보내세요 — 에이전트가 한 번에 모두 적용합니다", 행마다 이동(`edit-queue-jump-N`) · 메모 편집(`edit-queue-edit-N`) · 삭제(`edit-queue-remove-N`), 접기 버튼
- 하단 바 `slides-v2-markup-bar`: "표시한 수정 사항을 보내시겠습니까?" + `markup-discard` 취소 / `markup-send` "편집 N개 보내기"
  - 취소는 **확인 창 없이 즉시** 지우고 알림 "이 페이지의 마크가 지워졌습니다"(범위 = 현재 페이지)
- 도구줄 오른쪽: 콘텐츠 검증 ▾(`verify-page` 이 페이지 검증 "사실, 수치, 출처 및 일관성 확인" / `verify-deck` 전체 덱 검증) · 레이아웃 수정 · 콘텐츠 다듬기 (모두 크레딧 사용, 실행하지 않음)

### 6A.2 그리기 모드
| 도구 | testid | 동작 | 메모 자리 표시 글 |
|---|---|---|---|
| 펜(기본) | draw-tool-pen | 자유 곡선 SVG path | "이 영역에 대한 변경 사항을 설명하세요…" |
| 마커 | draw-tool-marker | **지점 핀**(형광펜이 아님) | "이 지점의 변경 사항을 설명하세요…" |
| 박스 | draw-tool-rect | 드래그 사각형 | "이 영역에 대한 변경 사항을 설명하세요…" |
- 선 속성은 고정: 빨강 rgb(239,68,68), 3px, 둥근 끝, `vector-effect:non-scaling-stroke`. **색·굵기 선택 없음**, 빠른 칩 없음
- 좌표는 `viewBox 0 0 1920 1080` SVG 레이어(`stage-draw-layer`) — 슬라이드 좌표계 그대로 저장

### 6A.3 편집 모드 — 개체 유형별 도구줄
| 선택 대상 | 도구줄 구성 |
|---|---|
| 텍스트 상자(더블클릭) | 글꼴 · 크기 · 프리셋 · 글자색 · B/I/U/S · 정렬 순환(툴팁에 다음 정렬 표시: 왼쪽/가운데…) · 간격 |
| 표(한 번 클릭) | 텍스트 도구 전체 + **채우기 색 `fabric-fill-color`** + 복제 · 삭제 · 위치 조정 |
| 표 칸(더블클릭) | 텍스트 도구(채우기 없음) + **위쪽 도구줄에 표 버튼 12개**: 열 추가 · 열 삭제 · 행 추가 · 행 삭제 · 행 복사 · 열 복사 · 열 왼쪽/오른쪽 이동 · 행 위/아래 이동 · 행 헤더 설정 · 열 헤더 설정 |
| 도형(div 배경)·선(2px 막대)·화살촉·실제 이미지 | 모두 같은 **'이미지' 도구줄**: 교체 · 자르기 · 재설정 · 맞추기 · 초점 변경 · 복제 · 삭제 · 위치 조정 → **도형 채우기·테두리·선 굵기·화살촉 속성 없음** |
| 여러 개(Shift+클릭) | 텍스트 도구 + 채우기 + 복제 · 삭제 + **정렬 및 분배 ▾** + **그룹 Ctrl+G** |
| 코드 블록 `<pre>` | 더블클릭하면 `white-space:pre`를 유지한 채 편집. 글꼴 칸은 실제 Consolas인데 "Default Font"로 표시(목록에 고정폭 글꼴 없음) |

- 정렬 및 분배 메뉴(여러 개): 정렬 6종 + `fabric-distribute-horizontal` 가로로 분배 · `fabric-distribute-vertical` 세로로 분배(**3개 이상일 때**) + 순서 4종. 수치 입력 칸 없음
- 자르기 메뉴 `crop-dropdown-menu`: 모서리 반경(number) · 자유 자르기 · 도형으로 자르기(기본 도형 / 화살표 / 말풍선) · 비율로 자르기
- 위쪽 편집 도구줄 팝오버
  - 이미지 삽입: "이미지 업로드" / "URL로 이미지 삽입"
  - 링크 삽입: 링크 텍스트 · 링크 URL · 취소/확인
  - 표 삽입: 행·열 입력(기본 **2 × 2**) · 취소/확인
  - 텍스트 추가(T)
  - 실행 취소 Ctrl+Z / 다시 실행 Ctrl+Y·Ctrl+Shift+Z (이력이 없으면 비활성)

### 6A.4 페이지·패널
- 레일 ⋮ 페이지 작업(편집 모드): 잘라내기 · 복사 · 붙여넣기(복사한 것이 없으면 비활성) · 삭제 · 새 슬라이드 · 슬라이드 복제 · Hide slide(번역 누락)
- 아래 탭: 개요(레일 토글) · 노트(편집 모드에서 직접 수정) · 검증(`verify-panel`: "이 슬라이드에 대한 검증 기록이 없습니다" + "이 페이지 검증" 버튼)
- 파일 패널 `slides-file-browser`: 루트 `/` → `<deck>.slides` 폴더, 오른쪽 미리 보기("미리 보려면 파일을 선택하세요")
- 공유: 이메일 초대 + 역할 선택(기본 **뷰어**) · 일반 액세스(기본 **제한됨** "액세스 권한이 있는 사용자만 링크로 열 수 있습니다") · 링크 복사 · 완료
- 발표: 이 내장 브라우저에서는 열리지 않음(전체 화면 권한으로 추정) — 미확인

### 6A.5 저장 동작 (중요 발견)
- **편집 모드에 들어갔다 나오기만 해도 저장 지점이 생김**: "수동 편집: oracle-sql-tuning-ch00(변경 1건)"
  - 실제 차이는 직렬화뿐: 개체 속성 줄바꿈이 한 줄로 합쳐짐, 편집기에서 선택했던 표 style이 `position: absolute; …`로 정규화, 편집기 내부 속성 `data-height-listener-added="true"`가 `<img>`에 **새어 들어감**, 빈 속성이 `data-slide-notes=""`로 바뀜
  - 화면에 보이는 속성(개체 style·텍스트·이미지 경로)은 v1과 동일(자동 대조로 확인)
- 같은 세션의 수동 편집은 **저장 지점 하나에 계속 합쳐짐**(버전 2의 시각만 08:33 → 08:38로 갱신)

## 7. nexa-slide 에 적용할 방향

> 1번(레이아웃 검사 형식 + 최소 글자·고정폭 정렬 규칙)은 0.3.0 에 반영됐다. 나머지는 후보다.

1. **레이아웃 검사 출력 형식 차용** — 규칙 ID(`t1.overlap.text-text` 등) + ERROR/WARNING 정밀도 등급 + 요소 번호·좌표·교차 영역. nexa-slide 는 여기에 **최소 글자 크기(pt 환산)·원문 대조(코드·실행계획 글자 단위)·생명선 정합** 같은 규칙을 더하면 Genspark보다 앞섬(이번 실측에서 Genspark가 놓친 결함 전부 해당)
2. **검사 → 캡처 → 재작성 루프**를 에이전트 도구로: `check_slide_layout` + `capture_slide_screenshot`(영역 캡처) 조합
3. **개체 종류 표시 + 평평한 구조** — `data-object-type`(shape/textbox/image/table), 중첩 0. nexa-slide `render.js` 의 data-type 과 같은 발상, HTML↔PPTX 대응 검사 단순화
4. **노트를 슬라이드 파일 안 `<template>`에** — 내용과 노트 동기화
5. **편집기 UI 기준값** — 글꼴 크기 6~400 + 프리셋 20단계, 줄 간격 0.5~3/0.05, 자간 -5~20/0.1, 색 HEX+프리셋 25색, 위치 조정 메뉴(정렬 6·순서 4·W/H/X/Y/회전·비율 잠금), 단축키 체계. 단 nexa-slide 는 **pt 단위 표시**(PPTX 기준)와 **한글 글꼴 목록**이 필요
6. **모드 3분할(선택·그리기·편집)** + 레일 주석 배지 + "편집 N개 보내기" — 요청 메모(`decks/<id>.requests.json`)와 연결
7. **git 저장 지점**(작업 단위 커밋, etag 동시성) — `decks/.history` 자동 백업 50개를 커밋 단위 목록·되돌리기 UI로
8. **2차 검토에서 추가된 방향**
   - 선택 메모의 빠른 칩을 **개체 종류별**로(도형: 꾸미기·검증 / 이미지: 더 나은 이미지·꾸미기) — nexa-slide 요청 메모에 "자주 쓰는 요청" 버튼으로
   - 표 칸 편집 시 행·열 조작 12종을 도구줄에 노출 — nexa-slide 표 레이아웃에 필요한 최소 세트의 기준
   - 여러 개 선택 → 정렬·분배(3개 이상)·그룹
   - Genspark의 약점은 nexa-slide 가 앞설 지점: 도형 채우기·테두리·선 굵기·화살촉을 편집할 수 없음(전부 '이미지' 취급), 그리기 색·굵기 고정, 고정폭·한글 글꼴 없음
   - **변경이 없으면 저장하지 않기**, 편집기 내부 속성이 원본에 새지 않게 직렬화 전에 정리
9. **피해야 할 점** — 경고를 없애려고 요구 요소를 지우는 자동 수정, px/pt 혼동, 지어낸 로고·노트·각주, 강조 span이 고정폭 정렬을 깨는 방식(강조는 같은 폭 유지 필수)
