# 페이지 편집기 - 지금 상태

> 무인 개발 규칙 = [../autodev.md](../autodev.md) · 설계 = [design.md](design.md) · 결정 = [decisions.md](decisions.md) · 할 일 = [TODO.md](TODO.md) · 경과 = [../journal/](../journal/)
> 작업판 = `out/status/now.md`(저장소 main 트리) · 한 화면 보기 = `python studio/devstatus.py [--watch]` · 검증 = `python studio/tests/verify.py --level quick|full`

## 다음 세션 시작점

(2026-11-25 밤) A0 무인 체계가 끝났다: 검증 진입점 `verify.py`(quick 약 55초) · 작업판 `devboard.py` · 한 화면 보기 `devstatus.py` · 규칙 정본 `docs/dev/autodev.md`. B1 의 PG-030(모델 연산)·PG-031(입력)은 개발 세션이 끝냈고 시험 묶음 `textmodel`(quick 에 포함)·`textui` 가 run_all 에 들어갔다. **다음 = 개발 세션 PG-010(공용 뼈대 nexa-shell.js) · 협업 세션 PG-032 의 실제 IME 시험(CDP `Input.imeSetComposition`)**. 작업은 브랜치 `feat/page-editor`(worktree `.claude/worktrees/page-editor`, 협업은 `feat/page-collab` · `.claude/worktrees/page-collab`)에서.

## 결정 대기

| 무엇 | 선택지 | 추천안 | 막힌 범위 |
|---|---|---|---|
| D-P01 단어 **아래** 주석(Word 에 대응 기능 없음) | 윗주 위·아래 겹쳐 쓰기 / 줄 사이 주석 줄 / 글 상자 | (2단계에 정함) | 2단계 해설지 |
| D-P02 숨김 해제 시점 | 1단계 마감 뒤 바로 / 2단계 뒤 | 1단계 마감 보고 때 묻는다 | PG-090 |
| D-P03 운영 서버 재시작 시점 | 서버 파이썬 변경이 main 에 들어간 뒤 사용자가 정함 | 처리 중인 세션이 없을 때 한 번에 | 운영 반영 |
| 작업판·검증 기록 위치 | 저장소 main 트리 `out/` 한 곳(지금) / worktree 마다 | 한 곳 - 세션·worktree 가 같은 판을 본다(git common-dir 의 부모) | 없음(진행 중) |

## 최근 main 에 들어간 것

| 날짜 | ID | 한 줄 | 커밋 |
|---|---|---|---|
| 2026-11-25 | PG-001~003 | 무인 체계 - verify.py · devboard.py · devstatus.py · autodev.md · STATUS · journal | (병합 커밋은 journal) |
| 2026-11-25 | PG-030·031 | nexa-text 모델 연산 · 입력 처리(feat/page-editor → 함께 병합) | bafc086 · 155a20b |
| 2026-11-25 | PG-004 | 설계·결정·백로그 · `/autodev` | 5d8e3c0 |

## 아침 보고

(아직 없음 - 형식은 [../autodev.md](../autodev.md) §9)
