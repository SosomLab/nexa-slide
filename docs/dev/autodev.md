# 무인 개발 규칙 (페이지 편집기)

> 사람 없이 한 사이클씩 개발을 이어 가는 규칙의 **정본**. 실행 명령은 `.claude/commands/autodev.md`(`/autodev`, 연속은 `/loop /autodev`)이고, 이 문서와 어긋나면 이 문서가 맞다.
> 설계 = [page-editor/design.md](page-editor/design.md) · 결정 = [decisions.md](page-editor/decisions.md) · 할 일 = [TODO.md](page-editor/TODO.md) · 지금 상태 = [STATUS.md](page-editor/STATUS.md) · 경과 = [journal/](journal/)
> 바탕: 전역 규칙(`~/.claude/CLAUDE.md` §1~4 - 세션 분담 · 세마포어 · 흐름으로 묶기) · nexa-sql `docs/claude-batch-flow.md`(수준 · 결과 넷 · 요약 · 모니터링) · m4plan `docs/15` §2-5(자리 비움 결정) · §2-8(결정 창구).

## 1. 기준은 파일이다

- 세션은 대화 기억이 아니라 **파일로 이어진다**. 새 세션·다시 깨어난 세션은 늘 `STATUS.md` 맨 위 "다음 세션 시작점" → `TODO.md` 의 🚧 → 의존이 풀린 ⬜ 순으로 읽고 시작한다.
- 착수 전에 `git log --grep <ID>` 로 그 일이 이미 끝났는지 본다(다른 세션이 했을 수 있다).
- 진행 상황은 작업판(`studio/devboard.py` → `out/status/now.md`)에, 판정은 검증 요약(`out/verify/<시각>/summary.md`)에, 경과는 journal 에 남긴다.

## 2. 결정 - 기다리지 않고 추천안으로

- 설계에 없는 판단이 필요하면 **추천안으로 진행**하고 `decisions.md` 의 "추천안으로 진행" 표에 `DP-Pnn` 한 줄(결정 · 근거 · 되돌리기)을 남긴다. 사용자가 확인하면 `DR` 로 옮긴다(행을 고치지 않고 새 행).
- 그 결정에 걸리지 않는 일은 계속한다. 걸리는 일뿐이면 STATUS "결정 대기"에 적고 다음 일로 간다.
- 사용자에게 묻는 것은 한 창구(사용자와 대화 중인 세션)에서 **묶어서** 묻는다: 질문 하나 = 결정 하나, 배경 · 선택지와 영향 · 추천안(첫 선택지)과 이유.
- 개발·협업 세션 사이의 판단 요청은 `[결정 요청] <무엇> — <선택지 · 추천안 · 근거> — <막힌 범위>` 로 보내고, 받은 쪽도 답을 기다리는 동안 추천안으로 간다.

## 3. 멈추는 것

하지 않고 STATUS "결정 대기"에 적은 뒤 의존이 없는 다음 일로 간다(`.claude/commands/autodev.md` §2 와 같다).

- 운영 허브·작업 공간 서버 재시작 · `engine_deploy` · 강제 push · `reset --hard` · 브랜치/worktree/파일 삭제 · 전역 설정(`~/.claude`) · 다른 저장소.
- 숨김 스위치(`experimental.page`) 해제 · 확정 결정(DR) 뒤집기 · **판정 기준 낮추기**(시험을 지우거나 기대값을 실패에 맞추기, 비교 범위 좁히기, 허용 오차 늘리기). 기준을 높이는 쪽은 바로 해도 된다.
- 같은 일이 **두 번 연속** 실패하면 그 행을 ⏸ 로 두고 증상(단계 · 기대 · 실제)을 STATUS 에 적은 뒤 다른 행으로 간다.

## 4. 한 사이클

1. **바깥 변경**: `git fetch origin` → `git status`(내가 만들지 않은 변경) → `git log --oneline HEAD..origin/main`. 새 커밋이 있으면 작업 브랜치에 `git merge origin/main` 부터.
2. **고르기**: TODO 의 그 행을 🚧, 작업판에 시작 - `python studio/devboard.py start <ID> <작업자> "<제목>" <예상 분> --where "이 PC · worktree <이름>"`.
3. **분담**: TODO 의 "분담"대로. 협 행은 협업 세션에(`SendMessage` - 절차 이름 + 수준 + 원하는 출력 형식을 한 번에), 협업 세션이 없으면 Opus 서브에이전트로. 맡긴 일은 맡긴 쪽이 작업판에 대신 적는다(`--by <자기>`), 맡기자마자 응답을 확인해 `ack`, 그 뒤 10분마다 진행 증거(`step … --seen --ev "<새 커밋·산출물>"`).
4. **구현**: 작업 브랜치의 worktree 에서만. 운영 트리(main)와 `engine-dev`(서버 세션 배포 대상)는 직접 고치지 않는다. 남의 파일은 `[SEM 요청]` → `[SEM 승인]` 뒤에만.
5. **검증**: §5. 요약만 읽고, 실패한 단계의 첫 오류 5줄 → 모자라면 그 단계 로그만 연다.
6. **병합**: §7.
7. **기록**: TODO 상태 머리(`✅ 끝 <날짜> · <커밋>`) · STATUS "다음 세션 시작점"·"최근 main 에 들어간 것" · journal 한 단락 · 작업판 `done`.

## 5. 품질 문

| 바꾼 것 | 검증 |
|---|---|
| 새 모듈·화면 고유 파일·문서 | `python studio/tests/verify.py --level quick` |
| 공용 모듈(nexa-merge·nexa-live·menu 등) · 서버(`server.py`·`hub.py`) · 렌더 규칙 · 병합·원장 | `--level full` |
| 렌더 규칙(`render.js` ↔ `common.py`·`export_pptx.py`) | `full` 의 parity · regress(등록된 작업 공간 덱의 PPTX XML 이 main 과 같음) |

- `verify.py` 결과 넷: **PASS** · **FAIL** · **SKIP**(판정 불가 - 통과가 아니다, 메모에 이유) · **TIMEOUT**(상한 = 이력 중앙값 × 3, 시험 잠금 대기는 뺀다). 종료 코드 = 실패 단계 수. 실패해도 끝까지 간다(`--fail-fast` 는 선택).
- quick = 바뀐 `.py` 컴파일(경고도 실패) · 바뀐 `.js` `node --check` · `check_parity -W example` · run_all 의 브라우저 없는 빠른 묶음. full = 앞의 셋 + run_all 기본 묶음 전체 + `engine_regress`.
- 회귀의 뜻: 기능 추가가 아니면 run_all 통과 · 슬라이드·시트 동작 같음 · PPTX 슬라이드 XML 같음. 공용화(A1)는 동작을 바꾸지 않는다.
- 화면·동작 판정은 눈으로 보지 않고 **상태 덤프 + 기대 문자열**(헤드리스 시나리오 `studio/tests/scenarios/*.json` · `smoke.js`)로, 재실행 가능한 파일로 쌓는다.

## 6. 모니터링

- **작업판** `out/status/now.md`(저장소 main 트리 아래 한 곳 - worktree 가 여러 개여도 같은 판): 진행 중 표(무엇 · 누가 · 어디서 · 시작 · 경과 · n/N · 지금 단계 · 예상 종료 · PID) · 최근 끝난 일. 맨 위에 ✗ 첫 실패 · ⚠ 멈춤 의심(신호 3분 없음 또는 예상의 3배) · ⏰ 확인할 때(대리 기록 10분) · 응답 미확인 · 진행 없음(증거 두 번 같음).
- 5분 넘게 걸릴 일(시험·측정·위임)은 시작 전에 `start`, 단계가 바뀔 때 `step <n>/<N>`, 끝나면 `done ok|fail|skip`. `verify.py` 는 스스로 적는다(30초마다 신호).
- **한 화면 보기** `python studio/devstatus.py [--watch]`: 작업판 + nexa-slide 프로세스(PID · 시작 · 트리) + worktree 별 브랜치·앞/뒤·미커밋 + 시험 잠금 + 마지막 검증 요약.
- 상태를 묻는 대화(폴링)는 쓰지 않는다. 예외 = 이 PC 밖의 작업자(원격·클라우드) - 맡긴 세션이 10분마다 진행 증거를 확인해 적는다.

## 7. 병합 (nexa-slide 방식)

1. 작업 브랜치에서 커밋 - 메시지에 `<ID>`, 자기 파일만 경로를 지정(`git commit -- <파일>…`), 커밋 전 `git status --short` 로 낯선 파일 확인.
2. `git fetch origin` → main 트리에서 `git pull --ff-only origin main` → `git merge --no-ff <작업 브랜치>`(메시지 "merge: <브랜치> → main - …", 한국어) → `git push origin main`.
3. 작업 브랜치를 `git merge --ff-only origin/main` 으로 맞춰 push(`engine-dev` 도). 그래야 다음 확인 때 `HEAD..origin/main` 에 바깥 변경만 보인다.
4. 충돌은 양쪽 의도를 살려 풀고 검증을 다시 돌린다. 병합 뒤 서버 재시작이 필요한 변경(서버 파이썬)이어도 **재시작하지 않고** STATUS "결정 대기"에 적는다(정적 js·문서는 바로 나간다).
5. 페이지 기능은 완성 전 숨김(`experimental.page`)이라 단계마다 main 에 병합해도 운영 사용자에게 보이지 않는다(DR-P11).

## 8. 세션 재개

- 컨텍스트가 줄었거나 새로 깨어났으면: STATUS "다음 세션 시작점" 한 단락 → 작업판(`devstatus.py`)에서 내 이름으로 진행 중인 일 → `git log --oneline -5` · `git status` 로 미커밋 변경 확인 → 이어서.
- 작업판에 내 일이 "진행 중"인데 실제로는 끝났으면 `done` 으로 닫는다(남겨 두면 멈춤 의심이 뜬다).

## 9. 아침 보고

사용자가 돌아왔을 때 STATUS 의 "아침 보고" 자리를 이 형식으로 갱신하고, 대화에는 결론부터 짧게 쓴다.

```
## 아침 보고 - <날짜 시각> (지난 보고 이후)
- main 에 들어간 것: <ID · 한 줄 · 커밋> …
- 시험: verify <수준> <결과>(<시각>) · run_all <n/N>
- 추천안으로 정한 것(DP): <DP-Pnn · 한 줄> … (확인해 주시면 DR 로)
- 결정 대기: <무엇 · 선택지 · 추천안> …
- 막힘(⏸): <ID · 증상> …
- 다음 일: <ID · 한 줄>
```
