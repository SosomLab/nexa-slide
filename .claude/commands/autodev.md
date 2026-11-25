---
description: 페이지 편집기 무인 개발을 한 사이클 진행한다 - 상태를 읽고 다음 일을 골라 구현·검증·병합·기록까지. /loop /autodev 로 연속 실행
---
페이지 편집기 개발을 **사람 없이 한 사이클** 진행한다. 규칙의 정본은 `docs/dev/autodev.md`, 설계는 `docs/dev/page-editor/design.md` 다.

**0. 상태를 읽는다**(대화 기억이 아니라 파일이 기준이다)
- `docs/dev/page-editor/STATUS.md` 맨 위 "다음 세션 시작점" → `TODO.md` 의 🚧 → 의존이 풀린 ⬜ 를 위에서부터 하나.
- `git fetch origin` → `git status` → `git log --oneline HEAD..origin/main`. 새 커밋이 있으면 작업 브랜치(`feat/page-editor`, worktree `.claude/worktrees/page-editor`)에 `git merge origin/main` 부터.
- 고른 ID 가 이미 끝났는지 `git log --grep <ID>` 로 확인한다.
- `ListAgents` 로 협업 세션을 찾는다. 있으면 분담표(TODO 의 "분담")대로 넘기고, 없으면 Opus 서브에이전트로 돌린다.

**1. 한 사이클**
1. TODO 의 그 행을 🚧 로, 작업판에 시작을 적는다(`studio/devboard.py start`).
2. 설계에 없는 판단이 필요하면 **기다리지 않고 추천안으로 진행**하고 `decisions.md` 에 DP 행을 한 줄 남긴다.
3. 구현(작업 브랜치의 worktree 에서만 - 운영 트리 main 과 `engine-dev` 는 직접 고치지 않는다).
4. 검증 `python studio/tests/verify.py --level quick`(공용 모듈·서버를 건드렸으면 `full`) - **요약만** 읽고 실패한 단계의 원 로그만 연다.
5. 통과하면 커밋(`<ID>` 를 메시지에) → `git pull --ff-only origin main` 뒤 main 에 `--no-ff` 병합 → push → 작업 브랜치를 `git merge --ff-only origin/main` 으로 맞춰 push.
6. 기록: TODO 상태 머리 · STATUS "다음 세션 시작점" · journal 한 단락 · 작업판 종료.

**2. 멈추는 것**(하지 않고 STATUS "결정 대기"에 적은 뒤 다음 일로 간다)
- 운영 허브·작업 공간 서버 재시작 · `engine_deploy` · 강제 push · `reset --hard` · 브랜치/worktree/파일 삭제 · 전역 설정(`~/.claude`) · 다른 저장소.
- 숨김 스위치(`experimental.page`) 해제 · 확정 결정(DR) 뒤집기 · 판정 기준 낮추기(시험을 지우거나 기대값을 실패에 맞추기).
- 같은 일이 **두 번 연속** 실패하면 그 행을 ⏸ 로 두고 증상을 STATUS 에 적은 뒤 의존이 없는 다른 행으로 간다.

**3. 끝낼 때** - 사용자 보고는 결론 먼저: 이번 사이클에 main 에 들어간 것 · 시험 결과 · 추천안으로 정한 것(DP) · 결정 대기 · 다음 일. `/loop` 로 돌고 있으면 다음 깨움을 잡는다(진행 중인 위임이 있으면 20~30분, 없으면 바로 다음 사이클).
