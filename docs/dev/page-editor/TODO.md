# 페이지 편집기 - 백로그

- 상태 머리: `⬜ 열림` · `🚧 진행` · `✅ 끝`(날짜 · 커밋) · `⏸ 막힘`(무엇을 기다리는지). 한 줄로 고쳐 쓴다.
- 다음 일 = STATUS.md "다음 세션 시작점" → 여기의 🚧 → 의존이 풀린 ⬜ 를 위에서부터. 착수 전에 `git log --grep <ID>` 로 이미 끝났는지 본다.
- 규모: S(≤100줄) · M(≤400줄) · L(그 이상, 나눠서). 분담: 개 = 개발 세션(설계·구현) · 협 = 협업 세션(시험·실행·기록·간단 수정).

| ID | 묶음 | 할 일 | 규모 | 의존 | 분담 | 상태 |
|---|---|---|---|---|---|---|
| PG-001 | A0 | 무인 규칙 문서 `docs/dev/autodev.md` · STATUS.md · journal | S | - | 협 | ⬜ 열림 |
| PG-002 | A0 | 검증 진입점 `studio/tests/verify.py --level quick\|full`(run_all · check_parity · regress 를 감쌈, summary.md · history.tsv, 결과 넷) | M | - | 협 | ⬜ 열림 |
| PG-003 | A0 | 작업판 `studio/devboard.py` + 한 화면 보기 `studio/devstatus.py` | M | - | 협 | ⬜ 열림 |
| PG-004 | A0 | `.claude/settings.json` 허용 목록 · `/autodev` 명령 · CLAUDE.md 한 단락 | S | - | 개 | ✅ 끝 2026-11-25 |
| PG-010 | A1 | 공용 뼈대 1: `nexa-shell.js`(api · toast · setStatus · banner · openMenu) - studio.js · sheet.js 가 쓰게 | M | PG-002 | 개 | ⬜ 열림 |
| PG-011 | A1 | 공용 뼈대 2: 실행 취소 · save/scheduleSave · loadDeck/poll/applyVersion 뼈대(종류별 훅) | L | PG-010 | 개 | ⬜ 열림 |
| PG-012 | A1 | 공용 스타일 `nexa-shell.css`(머리 막대 · 상태 칩 · 배너 · 토스트 · 메뉴 · 대화 상자 · 옆 패널) | L | PG-010 | 개 | ⬜ 열림 |
| PG-013 | A1 | 공용 확대 · 그림 넣기 · 내보내기 메뉴(`nexa-export.js`) | M | PG-011 | 개 | ⬜ 열림 |
| PG-020 | A2 | 종류 등록부 `kinds.py` + 서버·허브·init·deck_admin 의 2분기를 조회로(동작 같음) | L | PG-002 | 개 | ⬜ 열림 |
| PG-021 | A2 | 화면 쪽 종류 등록(`nexa-kinds.js`): 편집기 주소 · 이름 · 아이콘 · redirect | S | PG-020 | 개 | ⬜ 열림 |
| PG-022 | A2 | 공용 "새 문서" 대화 상자 `nexa-newdoc.js`(홈 · 슬라이드 · 시트) - 어느 화면에서든 슬라이드·시트 추가 | M | PG-021 | 개 | ⬜ 열림 |
| PG-023 | A2 | 숨김 스위치(experimental.page) + page kind 최소 등록(만들기 · 목록 · 빈 편집기) | M | PG-022 | 개 | ⬜ 열림 |
| PG-030 | B1 | nexa-text 모델 연산(runs 정규화 · 넣기 · 지우기 · 쪼개기 · 합치기 · 서식 켜고 끄기) + node 단위 시험 | M | - | 개 | ✅ 끝 2026-11-25 · 시험 39사례 |
| PG-031 | B1 | nexa-text 입력(beforeinput · 선택 ↔ 모델 좌표 · 다시 그리기 · 키 이동) | L | PG-030 | 개 | ✅ 끝 2026-11-26 · 화면 시험 25단계(조합은 흉내 - 실제 IME 는 PG-032) |
| PG-032 | B1 | 한글 조합(IME) · 붙여넣기(HTML → runs) · 입력 묶음 실행 취소 + 헤드리스 시나리오 | L | PG-031 | 개 | ⬜ 열림 |
| PG-040 | B2 | `page_doc.py`(새 문서 · 검증 · 정규화) + 서버 PUT 검증 | M | PG-023 | 개 | ⬜ 열림 |
| PG-041 | B2 | `page-render.js`(블록 → DOM, 스타일 상속 풀기) | M | PG-040 | 개 | ⬜ 열림 |
| PG-042 | B2 | `page.html` · `page.js` - 공용 뼈대 위에 본문 편집 · 저장 · 다시 열기 | L | PG-011 PG-031 PG-041 | 개 | ⬜ 열림 |
| PG-043 | B2 | 서식 막대 `nexa-format.js`(글자 · 문단 · 스타일 · 글꼴/색) | L | PG-042 | 개 | ⬜ 열림 |
| PG-050 | B3 | 목록(글머리 · 번호 · 단계) | M | PG-042 | 개 | ⬜ 열림 |
| PG-051 | B3 | 표(넣기 · 행/열 · 병합 · 머리글 행 · 셀 안 편집) | L | PG-042 | 개 | ⬜ 열림 |
| PG-052 | B3 | 그림(넣기 · 크기 · 정렬) · 쪽 나누기 | M | PG-042 | 개 | ⬜ 열림 |
| PG-053 | B3 | 쪽 설정(용지 · 여백 · 방향) · 머리말/꼬리말/쪽 번호 · 쪽 경계선 | L | PG-042 | 개 | ⬜ 열림 |
| PG-054 | B3 | 인쇄 미리 보기 `page-print.html`(쪽 상자에 흘리기) | L | PG-053 | 개 | ⬜ 열림 |
| PG-060 | C1 | `export_docx.py`(문단 · 글자 · 스타일 · 목록 · 표 · 그림 · 구역 · 머리말) | L | PG-040 | 개 | ⬜ 열림 |
| PG-061 | C1 | PDF: `render_docx.ps1`(Word COM, 매크로·이벤트 끔) · Chrome 인쇄 · 내보내기 API·메뉴 | M | PG-060 PG-054 | 개 | ⬜ 열림 |
| PG-062 | C1 | 동일성 시험(화면 렌더 ↔ DOCX 구조) + Word 로 여는 검증 | M | PG-060 | 협 | ⬜ 열림 |
| PG-070 | C2 | 템플릿 형식 + 11종 + 미리 보기 | L | PG-041 | 개 | ⬜ 열림 |
| PG-071 | C2 | 추천(`hub.template_rec` 종류별) · 홈·새 문서에서 고르기 | M | PG-070 PG-022 | 개 | ⬜ 열림 |
| PG-080 | C3 | 병합(deckmerge · nexa-merge) · 작업(deckops) · diff(deckdiff) 의 blocks 지원 + 사례 파일 | L | PG-040 | 개 | ⬜ 열림 |
| PG-081 | C3 | 원장 · 변경 탭 · 제안(proposals) · AI 요청(세션 규약 문단 · save_deck 검사) | L | PG-080 | 개 | ⬜ 열림 |
| PG-082 | C3 | 두 창 시나리오 · collab_sim 페이지 덱 | M | PG-080 | 협 | ⬜ 열림 |
| PG-090 | D | 1단계 마감 보고 · 사용 설명(`docs/pages.md`) · 숨김 해제 질문 | S | 위 전부 | 협 | ⬜ 열림 |
| PG-100 | E | 2단계 계획 세분(실시간 쪽 나눔 · 구역/다단 · 개체 · 윗주 · 각주 · DOCX 가져오기 · 해설지 재현) | S | PG-090 | 개 | ⬜ 열림 |
