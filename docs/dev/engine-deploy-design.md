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
허브가 자기를 재시작하므로 실행은 허브 밖 프로세스다(service.py 의 서버 띄우기와 같은 플래그 - 허브가 죽어도 남는다). 시작할 때 턴 처리 중이면 409. 웹 엔진 세션은 병합·시험 동안 그대로 두고(그사이 요청을 계속 처리), '턴 마무리 대기' 단계가 끝나면 허브가 끈다(`server._deploy_stop_engine`, 이유 `deploy`) - service.py 가 허브를 강제 종료하면 세션의 자식 프로세스가 남기 때문이다. 배포 프로세스는 하트비트가 꺼지길 최대 20초 기다린 뒤 재시작한다. 0.22.39 까지는 시작하자마자 껐다 - 시험 중에 세션이 끊긴 것처럼 보였다(요청 #11). 배포가 실패로 끝나면 세션은 그대로다.

## 4. 화면·API

- 카드: 관리자에게, 완료 요청이나 engine-dev 앞선 커밋이 있으면 `완료(적용 대기) n건 · engine-dev +k 커밋 [🚀 배포 준비 ▾]`(0.22.32~ 주 색 단추). 누르면 아래로 펼쳐지는 판이 열리고 단추는 판과 이어진 [▴ 접기] 탭이 된다. 펼치면 요청·커밋·파일·막는 이유·순서 안내와 [배포 시작]. 진행 중에는 큰 단계 표시줄(확인·병합·시험·턴 대기·main 반영·재시작·push·적용됨 - 끝난 것 ✓, 지금 것 돌아감), 끝난 단계마다 한 줄과 걸린 시간, 지금 하는 단계(`deploy.json` 의 `cur` - 시험·턴 대기·재시작·push 처럼 오래 걸리는 단계를 시작할 때 기록, 끝나면 지움)와 경과 시간, 시험 묶음별 진행 막대·칩(`tests[병합본|병합 전]` = {total, names, done:[{name, ok, sec}]} - `run_all` 이 묶음마다 찍는 `-- 통과|실패 <이름> <초>s` 줄을 따라가 남김), 경과·예상 시간(`test-times.json` 의 지난 묶음 시간 합)을 2.5초마다 갱신(허브 재시작 중의 무응답은 계속 기다림). 마지막 배포는 배지(배포 완료·실패·되돌림).
- `GET /api/engine/deploy` 계획 + 마지막 기록(관리자, git fetch) · `?fetch=0` 기록만 · `POST {action: run}`(관리자) · `GET /api/engine` 에 `deploy`(관리자).
- 기록: 사용자 설정 폴더 `hub/engine/deploy.json`(마지막 1건) · 출력 `hub/engine/deploy-logs/<시각>.log` · 묶음별 시험 시간 `test-times.json` · 커밋별 실패 묶음 `test-baseline.json`(최근 20개).
- CLI: `python3 studio/engine_deploy.py plan|status|run [--no-tests] [--no-restart] [--no-push]`.

## 5. 시험 실패 분류 (0.22.37)

배포 판의 시험 칩: ✓ 통과 · **! 기존 실패**(노랑 - 병합 전 main 에서도 실패, `tests.병합본.known`, 막지 않음) · **✕ 새 실패**(빨강 - 배포를 막는다).
0.22.33~36 배포에서 늘 보이던 smoke·editor·thread 실패는 모두 시험 환경 탓이었다.

| 분류 | 증상 | 원인 | 조치 |
|---|---|---|---|
| 글꼴 없음 | smoke·editor `콘솔 오류: 404 /api/fontfile/Pretendard-*` | 이 PC 에 Pretendard 미설치 - 대체 글꼴로 그려짐 | `smoke.js` 기본 무시 목록에 `api/fontfile/`·`wsfonts` |
| 포트 충돌 | thread `server.json 없음` · 로그 `포트 5600 를 쓸 수 없다` | 운영 작업 공간 서버가 설정 포트를 씀 | 시험 서버는 `--port auto` |
| 앞 묶음 연쇄 | 앞 묶음이 데모 작업 공간을 못 만들면 뒤 묶음도 실패 | `run_all` 순서 의존(smoke → thread) | 앞 묶음 원인을 고친다 |
| 시험 동시 실행 (0.22.41) | 0.22.37~39 배포: content_i18n `/api/slidetypes?lang=en … ['ui시험']` · uxpack `PDF … HTTP Error 404` | 배포 시험(00:27~)과 같은 시각 엔진 세션이 요청 #10 검증으로 `run_all`(00:30~)을 돌렸다. 시험들은 고정 포트(5667·5799·9333)와 같은 임시 폴더를 쓰므로 세션 쪽 editor 의 `ui시험` 서버가 5667 을 잡고 있었고, 배포 쪽 서버는 포트를 못 잡은 채 남의 서버에 물었다(그 서버엔 덱 `ux` 가 없어 404) | **시험 잠금**(`tests/testlock.py`) - 이 PC 에서 시험 실행은 하나씩. 뒤에 온 쪽은 `== 대기 · …` 를 찍고 기다린다(배포 판은 '시험 대기'로 보임, 기다린 시간은 시험 제한 30분에 넣지 않음). OS 파일 잠금이라 잡은 프로세스가 죽으면 저절로 풀린다 |
| 한때의 흔들림 (0.22.41) | 다시 돌리면 통과하는 새 실패 | 시간·Chrome 타이밍 등 | 새 실패만 병합본에서 **한 번 더**(`재시도` 묶음) - 통과하면 `tests.병합본.flaky`(노랑 '다시 돌려 통과'), 막지 않음, 기준(`test-baseline.json`)에는 다시 돌려도 실패한 것만 |

시험이 하나씩 도므로, 엔진 세션이 시험 중일 때 배포를 누르면(또는 그 반대) 뒤에 온 쪽은 앞 시험이 끝날 때까지(약 5분) 기다린다 - 엉뚱한 실패 대신 기다림으로 바뀐다.

## 6. 남은 것

- **턴 직전 main 따라잡기(0.22.33~)**: 엔진 세션이 요청을 받을 때마다(`EngineProfile.prompt` → `sync_main`) `engine-dev` 가 main 보다 뒤처졌으면 받는다 - 배포 안 한 커밋이 없으면 fast-forward, 있으면 main 을 병합(`merge: main → engine-dev - 요청 처리 전 따라잡기`, 허브 이름), 충돌이면 되돌리고 그대로, worktree 에 커밋 안 한 변경이 있으면 손대지 않는다. 결과는 세션 로그(✎ / 경고). 배포 말고 터미널에서 main 에 직접 병합해도 다음 요청은 최신 main 위에서 고친다.
- **도구 한도로 끊긴 요청(0.22.34~)**: 엔진 세션 턴이 `error_max_turns` 로 끝나면 같은 Claude 대화(`--resume`)에 "이어서 마무리하라 + 남은 변경 목록"을 넣어 `engineContinue`(2)번까지 이어 간다. 그래도 못 끝내면 요청을 open·awaiting 으로 되돌리고 reply 에 까닭(한도 n회·이어 하기 횟수)과 worktree 에 남은 변경을 적는다. 카드의 **[다시 수행]**(관리자 `status open` - awaiting 만 푼다)으로 다시 보내면 같은 대화로 이어 가고, 턴 프롬프트에도 남은 변경을 "이 요청 것이면 이어서, 다른 요청 것이면 손대지 말고 open" 으로 알린다. 터미널: `python3 studio/engine_request.py status <id> open --by <이름>`.
- `engine-dev` 하나에 요청이 쌓이므로 배포는 "완료된 것 전부" 단위다. 요청별로 골라 배포하려면 요청별 브랜치(`req-<id>`)가 필요하다.
- 시험(`run_all`)은 몇 분 걸린다(0.22.33 에서 race 2분 → 수 초, 비교 시험 재실행 생략). 가장 긴 것은 editor(시나리오 17개 × 헤드리스 Chrome, 약 3분) - 시나리오가 같은 덱·고정 Chrome 포트를 쓰므로 병렬로 돌리려면 시나리오별 작업 공간·포트가 먼저 필요하다. 급할 때는 터미널 `--no-tests` 만 있다(화면에는 없음).
