# 페이지 편집기 - 백로그

- 상태 머리: `⬜ 열림` · `🚧 진행` · `✅ 끝`(날짜 · 커밋) · `⏸ 막힘`(무엇을 기다리는지). 한 줄로 고쳐 쓴다.
- 다음 일 = STATUS.md "다음 세션 시작점" → 여기의 🚧 → 의존이 풀린 ⬜ 를 위에서부터. 착수 전에 `git log --grep <ID>` 로 이미 끝났는지 본다.
- 규모: S(≤100줄) · M(≤400줄) · L(그 이상, 나눠서). 분담: 개 = 개발 세션(설계·구현) · 협 = 협업 세션(시험·실행·기록·간단 수정).

## 요약 (2026-11-27 · main 4975c27 기준, 아래 행을 센 값)

- **47행 = 끝 29 · 진행 12 · 열림 5 · 미룸 1**(PG-020 미룸 · PG-107 은 낱말 풀이 표로 진행 중 - D-P04 결정 대기).
- **다음 순서**: ① 해설지 재현(PG-107 - 단어 아래 주석은 낱말 풀이 표로 진행, 글 범위 도형 D-P04 결정 대기) → ② 공용 뼈대(PG-109 = PG-011 · PG-012 · PG-013, nexa-format.js 는 PG-043·PG-108 과 함께) → ③ 다단 안에서 문단·표 나누기(PG-101) · 다단 브라우저 인쇄(PG-110).
- 끝난 개발 순서(사용자 지시 2026-11-26 22:3x "안 된 것·불안정한 부분 모두 개발·보완"): 인쇄 = 화면 쪽 나눔(PG-054 · af677ef) → 각주(PG-105 · 12196f5 · af677ef) → 다단 1차(PG-101 · 2422be3) → 공용화 첫 단계(PG-108 · 168ed82 · b8f3ebc · eae1b41). 해설지 템플릿 재현(PG-107)은 결정 대기.
- 2026-11-27 사용자 요청 "슬라이드·시트에도 페이지처럼 템플릿 선택과 파일 가져오기" - 새 문서 창 세 종류 통합(716e328 · 47ab604 · main c2ac0b9, 끝).

| ID | 묶음 | 할 일 | 규모 | 의존 | 분담 | 상태 |
|---|---|---|---|---|---|---|
| PG-001 | A0 | 무인 규칙 문서 `docs/dev/autodev.md` · STATUS.md · journal | S | - | 협 | ✅ 끝 2026-11-25 |
| PG-002 | A0 | 검증 진입점 `studio/tests/verify.py --level quick\|full`(run_all · check_parity · regress 를 감쌈, summary.md · history.tsv, 결과 넷) | M | - | 협 | ✅ 끝 2026-11-25 · quick 약 55초 |
| PG-003 | A0 | 작업판 `studio/devboard.py` + 한 화면 보기 `studio/devstatus.py` | M | - | 협 | ✅ 끝 2026-11-25 · out/status/now.md |
| PG-004 | A0 | `.claude/settings.json` 허용 목록 · `/autodev` 명령 · CLAUDE.md 한 단락 | S | - | 개 | ✅ 끝 2026-11-25 |
| PG-010 | A1 | 공용 뼈대 1: `nexa-shell.js`(api · toast · setStatus · banner · openMenu) - studio.js · sheet.js 가 쓰게 | M | PG-002 | 개 | ✅ 끝 2026-11-26 · main a890c88(회귀 full 통과, 덤프 3단계 같음) |
| PG-011 | A1 | 공용 뼈대 2: 실행 취소 · save/scheduleSave · loadDeck/poll/applyVersion 뼈대(종류별 훅) | L | PG-010 | 개 | ⬜ 열림 · nexa-shell.js 에 아직 없음(PG-109 로 묶어 진행) |
| PG-012 | A1 | 공용 스타일 `nexa-shell.css`(머리 막대 · 상태 칩 · 배너 · 토스트 · 메뉴 · 대화 상자 · 옆 패널) | L | PG-010 | 개 | ⬜ 열림 · 파일 없음(PG-109) |
| PG-013 | A1 | 공용 확대 · 그림 넣기 · 내보내기 메뉴(`nexa-export.js`) | M | PG-011 | 개 | ⬜ 열림 · 파일 없음(PG-109) |
| PG-020 | A2 | 종류 등록부 `kinds.py` + 서버·허브·init·deck_admin 의 2분기를 조회로(동작 같음) | L | PG-002 | 개 | ⏸ 미룸 · 지금은 분기 추가로 충분(page 갈래) - 종류가 더 늘거나 2분기 버그가 나오면 등록부로 |
| PG-021 | A2 | 화면 쪽 종류 등록(`nexa-kinds.js`): 편집기 주소 · 이름 · 아이콘 · redirect | S | PG-020 | 개 | ✅ 끝 2026-11-26 · main a890c88 |
| PG-022 | A2 | 공용 "새 문서" 대화 상자 `nexa-newdoc.js`(홈 · 슬라이드 · 시트) - 어느 화면에서든 슬라이드·시트 추가 | M | PG-021 | 개 | ✅ 끝 2026-11-26 · main a890c88(편집기 3곳) · 95e851d(홈) · 2026-11-27 세 종류 템플릿·가져오기(716e328 · main c2ac0b9) |
| PG-023 | A2 | 숨김 스위치(experimental.page) + page kind 최소 등록(만들기 · 목록 · 빈 편집기) | M | PG-022 | 개 | ✅ 끝 2026-11-26 · main a890c88 · 숨김은 3ace57c 로 풀림(기본 켬 · DR-P13) |
| PG-030 | B1 | nexa-text 모델 연산(runs 정규화 · 넣기 · 지우기 · 쪼개기 · 합치기 · 서식 켜고 끄기) + node 단위 시험 | M | - | 개 | ✅ 끝 2026-11-25 · 시험 textmodel |
| PG-031 | B1 | nexa-text 입력(beforeinput · 선택 ↔ 모델 좌표 · 다시 그리기 · 키 이동) | L | PG-030 | 개 | ✅ 끝 2026-11-26 · 시험 textui |
| PG-032 | B1 | 한글 조합(IME) · 붙여넣기(HTML → runs) · 입력 묶음 실행 취소 + 헤드리스 시나리오 | L | PG-031 | 개 · 협 | ✅ 끝 2026-11-26 · main 1b1dfb6 · 시험 textime(CDP imeSetComposition) · textui 붙여넣기 · pageui 실행 취소 묶음 |
| PG-040 | B2 | `page_doc.py`(새 문서 · 검증 · 정규화) + 서버 PUT 검증 | M | PG-023 | 개 | ✅ 끝 2026-11-26 · main a890c88 |
| PG-041 | B2 | `page-render.js`(블록 → DOM, 스타일 상속 풀기) | M | PG-040 | 개 | ✅ 끝 2026-11-26 · main a890c88 |
| PG-042 | B2 | `page.html` · `page.js` - 공용 뼈대 위에 본문 편집 · 저장 · 다시 열기 | L | PG-011 PG-031 PG-041 | 개 | ✅ 끝 2026-11-26 · main a890c88(pageui 통과) · 확대·축소 main 45d7d5e |
| PG-043 | B2 | 서식 막대 `nexa-format.js`(글자 · 문단 · 스타일 · 글꼴/색) | L | PG-042 | 개 | 🚧 **1차 끝**: 글꼴·크기·색·줄 간격·링크·찾기/바꾸기(55fd0a5 · main 38c2db4) · **공용 글자 서식 단추 `nexa-format.js`**(NexaFormat.html/bind/sync · `[data-mark]` - 페이지 서식 막대 `#fmtMarks` 6개와 슬라이드 편집 중 서식 줄 `#ftb` 가 같이 씀 · b01a5cb · 83629b9 · 시험 pageui 공용 서식 단추 · richedit) / **남은 것**: 문단·스타일·글꼴/색 단추의 공용화 · 시트 셀(PG-108) |
| PG-050 | B3 | 목록(글머리 · 번호 · 단계) | M | PG-042 | 개 | ✅ 끝 2026-11-26 · 목록 3종·단계(문단 속성, PG-042 에 포함) |
| PG-051 | B3 | 표(넣기 · 행/열 · 병합 · 머리글 행 · 셀 안 편집) | L | PG-042 | 개 | ✅ 끝 2026-11-26 · main a890c88 · 칸 합치기/나누기 7929108(main 38c2db4 · 시험 pageui 칸 합치기 3단계 · 합친 칸 DOCX 를 Word 로) |
| PG-052 | B3 | 그림(넣기 · 크기 · 정렬) · 쪽 나누기 | M | PG-042 | 개 | ✅ 끝 2026-11-26 · main 95e851d |
| PG-053 | B3 | 쪽 설정(용지 · 여백 · 방향) · 머리말/꼬리말/쪽 번호 · 쪽 경계선 | L | PG-042 | 개 | ✅ 끝 2026-11-26 · main a890c88(머리말·꼬리말은 한 줄 글 - 쪽마다 그리기는 PG-102) |
| PG-054 | B3 | 인쇄 미리 보기(쪽 상자에 흘리기) | L | PG-053 | 개 | ✅ 끝 2026-11-26 · 따로 `page-print.html` 을 두지 않고 **인쇄 = 화면 쪽 나눔 그대로**(af677ef · 4075c35 · main aa5e2c5 - 빈 자리 높이 0 + break-before page · 도형은 매인 문단 안 · @page 여백 상자 머리말·쪽 번호 · 서버 Chrome PDF = `page.html?print=1`) · 남은 다단 인쇄·쪽 아래 각주는 PG-110 |
| PG-060 | C1 | `export_docx.py`(문단 · 글자 · 스타일 · 목록 · 표 · 그림 · 구역 · 머리말) | L | PG-040 | 개 | ✅ 끝 2026-11-26 · main a890c88 |
| PG-061 | C1 | PDF: `render_docx.ps1`(Word COM, 매크로·이벤트 끔) · Chrome 인쇄 · 내보내기 API·메뉴 | M | PG-060 PG-054 | 개 | ✅ 끝 2026-11-26 · main a890c88 · 95e851d(Chrome 대체) |
| PG-062 | C1 | 동일성 시험(화면 렌더 ↔ DOCX 구조) + Word 로 여는 검증 | M | PG-060 | 협 | ✅ 끝 2026-11-26 · Word 로 열기(pageword) main a890c88 - 화면 ↔ DOCX 규칙 맞춤은 page_render_check |
| PG-070 | C2 | 템플릿 형식 + 11종 + 미리 보기 | L | PG-041 | 개 | ✅ 끝 2026-11-26 · main a890c88 |
| PG-071 | C2 | 추천(`hub.template_rec` 종류별) · 홈·새 문서에서 고르기 | M | PG-070 PG-022 | 개 | 🚧 **1차 끝**: 작업 공간 안 추천(쓴 횟수 `used` - main a890c88) · 홈·새 문서 창에서 고르기 / **남은 것**: 허브 추천 - `hub.template_rec` 는 슬라이드 템플릿만 점수를 매기고 페이지 템플릿(`pageTemplates`)은 점수 없이 목록만 |
| PG-080 | C3 | 병합(deckmerge · nexa-merge) · 작업(deckops) · diff(deckdiff) 의 blocks 지원 + 사례 파일 | L | PG-040 | 개 | 🚧 **1차 끝**: 병합·변경 비교(main a890c88 · 시험 pagemerge · pagemergejs · pagediff) / **남은 것**: deckops 의 블록 작업 - 지금 서버가 페이지 문서의 작업 저장을 400 으로 거절(DP-P08), 편집기는 통째 병합 저장 |
| PG-081 | C3 | 원장 · 변경 탭 · 제안(proposals) · AI 요청(세션 규약 문단 · save_deck 검사) | L | PG-080 | 개 | 🚧 **1차 끝**: save_deck 검사·세션 안내(main a890c88) · 요청 패널(2e5457d · main aa5e2c5) / **남은 것**: 페이지 제안(propose) - `proposals.py` 가 장·탭만 단위로 봐서 페이지는 blocks 전체가 "문서 설정" 한 항목이 된다(블록 단위로 골라 받기 없음) · 편집기의 변경 탭(page.js 에 `/api/history` 화면 없음) |
| PG-082 | C3 | 두 창 시나리오 · collab_sim 페이지 덱 | M | PG-080 | 협 | ✅ 끝 2026-11-26 · 두 창 관찰(pageui) · collab_sim 페이지 덱 simpage(8a8541d · main f437f35) · 넓히기는 PG-111 |
| PG-090 | D | 1단계 마감 보고 · 사용 설명(`docs/pages.md`) · 숨김 해제 질문 | S | 위 전부 | 협 | ✅ 끝 2026-11-26 · 숨김 해제(DR-P13 · 3ace57c) · pages.md 2절 기본 켬·끄는 법 |
| PG-100 | E | 2단계 계획 세분(실시간 쪽 나눔 · 구역/다단 · 개체 · 윗주 · 각주 · DOCX 가져오기 · 해설지 재현) | S | PG-090 | 개 | ✅ 끝 2026-11-26 · design.md 10절(9f121a3 · main 86cd7cc) + 이 표의 PG-101~109 |
| PG-101 | E | 구역·다단 - 단 설정·간격·구분선, 단 나누기(break column). DOCX `w:cols` · 화면은 쪽 안 단 흐름 | L | PG-102 | 개 | 🚧 **1차 끝**: 같은 너비 단 `page.columns {count, gap}` · 구역 나누기(`break kind section` + columns) · 단 나누기(`break kind column`) · DOCX 구역 `w:cols` · 가져오기(2422be3 · main 78a652f · 시험 pageui 다단 13단계 · pageword 구역별 단 수) / **남은 것**: 다단 안에서 문단·표 나누기(DP-P16 1차 범위 밖) · 단 구분선 · 너비가 다른 단(지금은 배치용 표 - DP-P07) · 구역 끝 단 균형 · 화면 단 선택은 1~3단(검사는 1~4) · 다단 인쇄는 PG-110 |
| PG-102 | E | 실시간 쪽 나눔 - 블록을 쪽(·단)에 흘린다: 줄 단위 분할 · 표 행 분할·머리글 반복 · 머리말/꼬리말 되풀이 · 쪽 번호 | L | - | 개 | 🚧 **1차 끝**: 빈 자리 끼우기(page-flow.js - 밀기 · 줄 사이 `.pg-gap` · 표 `tr.pg-gaprow` · 머리글 사본 `tr.pg-headrep`) · 외톨이 줄 · 쪽마다 머리말·꼬리말·쪽 번호 · 인쇄 같음(56e5c25 · f62974f · 8d39e60 · af677ef · main aa5e2c5 · 시험 pageflow · pageflowui · pageui 쪽 나눔 ①~⑪) / **남은 것**: 긴 문서 성능(지금은 바뀔 때마다 전체를 다시 잰다 - 16ms 디바운스) |
| PG-103 | E | 개체 - 글 상자·도형·선·화살표(문단에 매기, 쪽/문단 기준, 둘러싸기). DOCX 는 `wp:anchor` | L | PG-102 | 개 | 🚧 **1차 끝**: `type "shape"` 9모양(사각·둥근·타원·선·화살표·괄호 좌우·중괄호 좌우) · 문단에 매기(`anchor` · `rel page\|para` · DP-P15) · 글 상자 글 · 글 뒤(`z behind`) · DOCX wp:anchor(bcc11ba · 3cb9020 · main aa5e2c5) · Word 가져오기(b3d6d8e · main c2ac0b9) / **남은 것**: 그림 개체 · 둘러싸기(`wrap` 없음 - 지금은 겹침만) · 기본 도형이 아닌 모양 · 글 범위에 붙는 도형(D-P04) |
| PG-104 | E | 윗주(루비) | S | - | 개 | ✅ 끝 2026-11-26 · d59f281(main 38c2db4) · 시험 pageui 윗주 3단계 · pagedocx w:ruby · pageimport · pageword · 단어 **아래** 주석은 D-P01(PG-107) |
| PG-105 | E | 각주(쪽 아래) · 미주 | M | PG-102 | 개 | 🚧 **1차 끝**: 각주 - 글 조각의 `fn` · 쪽 아래 상자 · 쪽 나눔이 각주 높이를 뺌 · DOCX footnotes.xml · 가져오기(12196f5 · af677ef · main aa5e2c5 · 시험 pageui 각주 10단계 · pagewordimp) / **남은 것**: 미주 · 브라우저 인쇄의 쪽 아래 각주(지금은 문서 끝 목록 - PG-110) |
| PG-106 | E | DOCX 가져오기(문단·글자 서식·표·그림·머리말) | L | - | 개 | ✅ 끝 2026-11-26 · `import_docx.py`(main 38c2db4) · 왕복 시험 pageimport · Word 가 만든 문서 pagewordimp · 화면 pageui 가져오기 · 2단계 이상 목록은 D-P05(사람이 만든 문서로 확인 대기) |
| PG-107 | E | 해설지 템플릿 완성 - 예시 PDF 와 나란히 비교(너비가 다른 2단 · 윗주 · 떠 있는 회색 상자 · 타원·괄호·화살표) | L | PG-101 PG-103 PG-104 | 개 · 협(비교) | 🚧 진행 · D-P01(단어 아래 주석)은 추천안 = **낱말 풀이 표**로 진행(83629b9 · DP-P19 · 시험 pageui 낱말 풀이 6단계 + Word 표·테두리) / **남은 것**: D-P04(글 범위 도형) 결정 대기 · 예시 PDF 와 나란히 비교 - 2단 해설지 틀·각주 예시는 템플릿에 있음(b86e0c2) |
| PG-108 | E | nexa-text 를 슬라이드 글 상자·시트 셀에(기존 `**굵게**` 표기 ↔ runs 변환기) + 공용 서식 막대 | L | PG-043 | 개 | 🚧 **1차 끝**: 슬라이드 글·도형 글(168ed82 · main 78a652f) · 표 칸(b8f3ebc · main c2ac0b9) · 편집 중 서식 줄(eae1b41 · main 4975c27) - 덱 형식 그대로 · regress same / **남은 것**: 슬라이드 글머리·코드 요소(지금 원문 편집 - studio.js `TEXTY` 밖) · 시트 셀(sheet.js 는 nexa-text 를 쓰지 않음) · 공용 서식 막대 `nexa-format.js`(PG-043) |
| PG-109 | E | 공용 뼈대 나머지 - 요청 패널 배선 · 저장·실행 취소·덱 읽기 뼈대(PG-011) · 공용 스타일(PG-012) · 내보내기 메뉴(PG-013)를 세 화면이 같이 | L | - | 개 | 🚧 **1차 끝**: 공용 요청 패널 `nexa-reqpanel.js`(98c19d1 페이지 · 9251708 시트 - DOM id·동작 그대로 · 시험 pageui 요청 · sheetreq · sheetai) · **2차 끝**: 저장 상태기계 `nexa-doc.js`(DR-P14) - 페이지(f21af7c)·시트(c7ff9fb)·슬라이드(06e2da5) · 다시 읽기 직전 판 확인 `stillChanged`(87d3917 · e184361 · 7282aee) · **3차**: 밖의 변경 따라가기 `NexaDoc.follower`(8e2fd68 슬라이드·시트 · 시험 nexafollow 18사례) / **남은 것**: 페이지를 follower 에 연결 · 슬라이드 세션 칩·요청(SESS/RQ) 연결 · 불러오기·실행 취소 뼈대(PG-011) · 공용 스타일(PG-012) · 내보내기 메뉴(PG-013) |
| PG-110 | E | 다단 문서의 브라우저 인쇄·"PDF(화면 그대로)" 를 화면 쪽 나눔과 같게 + 브라우저 인쇄의 쪽 아래 각주 | M | PG-101 PG-105 | 개 · 협(판정) | ⬜ 열림 · 지금 Chrome PDF 쪽 수가 화면과 다름(음수 밀기가 인쇄의 쪽 나눔과 안 맞음 - DP-P17) · pageui 가 `KNOWN` 줄로 관찰 값을 남김(실패 수에 넣지 않음) → 고치면 일반 판정으로 · Word 로 내보낸 문서·Word 변환 PDF 는 이미 맞음 |
| PG-111 | E | collab_sim 페이지 덱(simpage) 넓히기 - 표 칸 · 개체 · 각주 · 구역 나누기 · 쪽 설정 편집도 섞기 | M | PG-082 | 협 | ⬜ 열림 · 지금 simpage 의 편집 = 문단 넣기 · 내 문단 글 · 지우기 · 공용 문단 글뿐(순서 바꾸기는 규칙상 뺌) |
| PG-112 | E | 개체 조작 공용화(DR-P14) - 동작 기준표(선택·이동·크기·편집·지우기 · 세 종류 비교) → `nexa-objects.js` → 슬라이드 요소 · 페이지 개체 · 시트 그림에 적용 | L | PG-109 | 개 · 협(기준표·시험) | 🚧 **1차 끝**: `nexa-objects.js`(ee3dc45 · 계산 18사례) · 페이지 개체(a522140 · 0b43875) · 시트 그림(a838578) - 기준표 = design 10-5 · 시험 pageui 개체 조작 11단계 · sheetx 그림 4단계 · 슬라이드 끌기 수식키(17d66b7 · DP-P21 · 시험 slidedrag_test) / **남은 것**: 슬라이드 요소를 모듈에 연결(손잡이·여럿 고르기·화살표·Ctrl+D 를 같은 코드로) · 틀 고정 칸과 겹칠 때 손잡이 순서 확인 · 사용자 지시 2026-11-27 21:0x |
| PG-113 | E | 요청 id 충돌 - `server.py` 의 요청 id 가 밀리초 시각(`r%Y%m%d%H%M%S` + 밀리초)이라 같은 밀리초에 만든 두 요청의 id 가 겹친다(후속 요청의 parent = 자기 id) | S | - | 개 | ✅ 끝 2026-11-28 · 겹치면 하나 뒤 번호로(6e2c783) · thread 단독 3회 + full 통과 |
