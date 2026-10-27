# 엔진 배포 - 승인한 엔진 요청을 카드 [배포] 하나로 main·운영까지 (0.22.29)

## 1. 문제

엔진 요청의 흐름은 `triage → (승인) → open → working → done → applied` 인데, **done 에서 applied 사이(병합·push·재시작)를 맡을 주체가 화면에 없었다.**
엔진 세션은 규약상 `git merge`·`git push`·`service.py` 가 막혀 있고(프롬프트 인젝션 연쇄를 끊으려는 의도 - [engine-request-design.md](engine-request-design.md) 6·8절),
허브 카드의 관리자 단추는 승인·거절·[적용됨](상태 글자만)뿐이었다. 그래서 관리자로 로그인해도 배포가 안 됐고, 요청 글로 "main 에 반영하고 push 해줘"라고 적으면
세션이 거절했다(2026-10-27 요청 #4). 운영자가 터미널에서 [server-admin.md](../server-admin.md) 9절 순서를 손으로 밟아야 했다.

## 2. 결정

- **사람 승인은 그대로, 실행만 자동.** 관리자가 카드에서 [배포…] → 계획 확인 → [배포 시작] 을 누르는 것이 승인이다. 실행은 세션이 아니라 허브가 떼어 낸 프로세스(`studio/engine_deploy.py run`)가 한다.
- 세션 권한은 바꾸지 않는다 - 배포는 로그인한 관리자의 HTTP 요청(`POST /api/engine/deploy {action: run}`)으로만 시작된다. 요청 글은 여전히 데이터다.
- [engine-request-design.md](engine-request-design.md) 10절 결정 3("적용은 관리자만, 수동")을 **"적용은 관리자만, 관리자가 누르면 자동 실행"** 으로 바꾼다(2026-10-27 사용자 "진행해줘").

## 3. 순서 (`engine_deploy.Run.run`)

| 단계 | 하는 일 | 실패하면 |
|---|---|---|
| 확인 | 운영 트리(엔진 폴더)가 `main` · `git fetch` · origin/main 새 커밋은 ff 로 받음 · `engine-dev` 가 앞섬 · 커밋하지 않은 변경이 병합 파일과 겹치지 않음 · engine-dev worktree 깨끗 | 시작 안 함(카드에 이유) |
| 병합 | 시험용 worktree(`.claude/worktrees/deploy-merge`, detached)에서 `--no-ff` 병합. 메시지 `merge: engine-dev → main - <요청 제목> (engine-request #…)` + `Deployed-by: <관리자>` | 충돌 → 중단, main 불변 |
| 시험 | 병합본에서 `run_all`. 실패한 묶음만 병합 전 main(`deploy-base`)에서 다시 돌려 **새로 생긴 실패만** 막는다(환경 탓 실패가 늘 있어도 배포가 막히지 않게). 0.22.33~: 병합 전 main 의 시험 기록(`test-baseline.json`, 3일 안)이 있으면 다시 돌리지 않고 그것과 비교한다 - 배포한 병합본의 결과가 곧 다음 배포의 기준이다. 문서(`docs/`·`*.md`)만 바뀌었으면 시험을 건너뛴다. 렌더 규칙 파일을 건드렸으면 `check_parity -W example` | 중단, main 불변 |
| 턴 대기 | 엔진 세션·작업 공간 웹 세션 하트비트 `state=running` 이 없을 때까지(최대 10분) | 중단, main 불변 |
| main 반영 | 운영 트리 `git merge --ff-only <병합 커밋>` - 병합과 재시작을 붙여서(정적 파일은 바로 나간다) | 중단 |
| 재시작 | `service.py restart`(허브) → `/api/auth/state` 생존 확인 → 떠 있던 작업 공간 서버 `service.py restart` | 허브가 안 뜨면 `git reset --keep <이전>` 후 다시 재시작 = `rolledback` |
| push | `git push origin main`(이 PC 계정의 git 인증, 묻는 창 없음) | `warn` - 운영은 새 판, 원격엔 아직 없음 |
| 적용됨 | done 요청을 `applied`(appliedCommit = 병합 커밋, engineVersion = CHANGELOG 판) → 원 요청 자동 재개(`resume_origin`) · engine-dev worktree 를 main 으로 ff | 단계 기록에 남김 |

push 를 재시작 뒤에 두는 것은 새 판이 뜨지 않을 때 원격을 되돌리지 않아도 되게 하려는 것이다.
허브가 자기를 재시작하므로 실행은 허브 밖 프로세스다(service.py 의 서버 띄우기와 같은 플래그 - 허브가 죽어도 남는다). 시작 직전 허브는 웹 엔진 세션을 먼저 끈다(턴 처리 중이면 409).

## 4. 화면·API

- 카드: 관리자에게, 완료 요청이나 engine-dev 앞선 커밋이 있으면 `완료(적용 대기) n건 · engine-dev +k 커밋 [🚀 배포 준비 ▾]`(0.22.32~ 주 색 단추). 누르면 아래로 펼쳐지는 판이 열리고 단추는 판과 이어진 [▴ 접기] 탭이 된다. 펼치면 요청·커밋·파일·막는 이유·순서 안내와 [배포 시작]. 진행 중에는 큰 단계 표시줄(확인·병합·시험·턴 대기·main 반영·재시작·push·적용됨 - 끝난 것 ✓, 지금 것 돌아감), 끝난 단계마다 한 줄과 걸린 시간, 지금 하는 단계(`deploy.json` 의 `cur` - 시험·턴 대기·재시작·push 처럼 오래 걸리는 단계를 시작할 때 기록, 끝나면 지움)와 경과 시간, 시험 묶음별 진행 막대·칩(`tests[병합본|병합 전]` = {total, names, done:[{name, ok, sec}]} - `run_all` 이 묶음마다 찍는 `-- 통과|실패 <이름> <초>s` 줄을 따라가 남김), 경과·예상 시간(`test-times.json` 의 지난 묶음 시간 합)을 2.5초마다 갱신(허브 재시작 중의 무응답은 계속 기다림). 마지막 배포는 배지(배포 완료·실패·되돌림).
- `GET /api/engine/deploy` 계획 + 마지막 기록(관리자, git fetch) · `?fetch=0` 기록만 · `POST {action: run}`(관리자) · `GET /api/engine` 에 `deploy`(관리자).
- 기록: 사용자 설정 폴더 `hub/engine/deploy.json`(마지막 1건) · 출력 `hub/engine/deploy-logs/<시각>.log` · 묶음별 시험 시간 `test-times.json` · 커밋별 실패 묶음 `test-baseline.json`(최근 20개).
- CLI: `python3 studio/engine_deploy.py plan|status|run [--no-tests] [--no-restart] [--no-push]`.

## 5. 남은 것

- **턴 직전 main 따라잡기(0.22.33~)**: 엔진 세션이 요청을 받을 때마다(`EngineProfile.prompt` → `sync_main`) `engine-dev` 가 main 보다 뒤처졌으면 받는다 - 배포 안 한 커밋이 없으면 fast-forward, 있으면 main 을 병합(`merge: main → engine-dev - 요청 처리 전 따라잡기`, 허브 이름), 충돌이면 되돌리고 그대로, worktree 에 커밋 안 한 변경이 있으면 손대지 않는다. 결과는 세션 로그(✎ / 경고). 배포 말고 터미널에서 main 에 직접 병합해도 다음 요청은 최신 main 위에서 고친다.
- `engine-dev` 하나에 요청이 쌓이므로 배포는 "완료된 것 전부" 단위다. 요청별로 골라 배포하려면 요청별 브랜치(`req-<id>`)가 필요하다.
- 시험(`run_all`)은 몇 분 걸린다(0.22.33 에서 race 2분 → 수 초, 비교 시험 재실행 생략). 가장 긴 것은 editor(시나리오 17개 × 헤드리스 Chrome, 약 3분) - 시나리오가 같은 덱·고정 Chrome 포트를 쓰므로 병렬로 돌리려면 시나리오별 작업 공간·포트가 먼저 필요하다. 급할 때는 터미널 `--no-tests` 만 있다(화면에는 없음).
