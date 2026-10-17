# OpenAI(Codex)로 쓰기

nexa-slide 의 편집기·빌드·PPTX 내보내기는 AI 없이 동작한다. AI 는 **편집기에서 남긴 요청을 받아 덱을 고치는 일**에만 쓴다.
기본 안내는 Claude Code 기준이지만([claude-install.md](claude-install.md)), OpenAI 계정을 쓰는 사람은 **Codex CLI** 로 같은 일을 할 수 있다.

| 방식 | Claude Code | Codex CLI |
|---|---|---|
| 수동 세션 — 사람이 도구를 열고 요청을 처리시킨다 | 상시 감시(Monitor) — `/nexa-slide-session` · `/nexa-slide-server` | **스킬 한 줄** `$nexa-slide-session` · `$nexa-slide-server` — 1회 대기 반복(아래 3절) |
| 웹 세션 — 시작 페이지·Studio 버튼으로 서버가 세션을 띄운다 | 확인됨 | **확인됨(0.22.22, Windows)** — 서비스 유형 `codex` 로 같은 화면에서(아래 5절) |

> **Windows 에서 먼저 볼 것(0.22.22 실측)**: chocolatey·npm 으로 깐 `codex.exe` 는 옆에 `codex-code-mode-host.exe` 가 없어 **명령을 하나도 실행하지 못한다**("Code Mode is unavailable … fail closed").
> **Codex 데스크톱 앱**을 설치하면 `%LOCALAPPDATA%\OpenAI\Codex\bin\<해시>\codex.exe` 에 host 가 함께 들어오고, 엔진은 이것을 자동으로 우선 쓴다(사용자 설정 `agentPaths.codex` 가 있으면 그것). 직접 쓸 때도 이 경로의 `codex.exe` 를 쓰거나 PATH 앞에 둔다.
> 또 이 PC 에서는 기본 Windows 샌드박스(unelevated)가 `CreateProcess` 실패를 내고, 앱이 준비한 **elevated 샌드박스**(`~/.codex/config.toml` 의 `[windows] sandbox = "elevated"`)만 동작했다 — 엔진은 그 값을 읽어 `-c windows.sandbox=…` 로 넘긴다.

## 1. 설치

```powershell
# Windows PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://chatgpt.com/codex/install.ps1 | iex"
```

```bash
curl -fsSL https://chatgpt.com/codex/install.sh | sh    # macOS · Linux (같은 명령으로 업데이트)
npm install -g @openai/codex                            # 또는 npm
brew install --cask codex                               # 또는 Homebrew(macOS)
```

새 터미널에서 `codex --version` 으로 확인한다. 찾지 못하면 설치 폴더가 PATH 에 없는 것이다(설치 스크립트가 알려 주는 위치를 사용자 PATH 에 넣는다).

## 2. 로그인

| 방법 | 명령 | 과금 |
|---|---|---|
| ChatGPT 계정(Plus·Pro·Business·Edu·Enterprise) | `codex login` → 브라우저 로그인 | 요금제에 포함 |
| API 키 | `printenv OPENAI_API_KEY \| codex login --with-api-key` (PowerShell: `$env:OPENAI_API_KEY \| codex login --with-api-key`) | API 사용량 |
| 화면 없는 서버 | `codex login --device-auth`(ChatGPT 보안 설정에서 디바이스 코드 로그인을 먼저 켠다) 또는 다른 PC 에서 로그인한 `~/.codex/auth.json` 복사 | — |

- 확인: `codex login status` · 로그아웃: `codex logout`
- 로그인 정보는 `CODEX_HOME`(기본 `~/.codex`)의 `auth.json` 또는 OS 자격 증명 저장소에 있다. 비밀번호와 같으니 저장소·작업 공간에 두지 않는다.
- 여러 사람이 웹으로 쓰는 서버라면 개인 ChatGPT 계정을 공유하지 말고 API 키를 쓴다(자동화에는 API 키가 기본 권장).

## 3. 수동 세션 — 지금 바로 쓰는 방법

새 작업 공간에는 Codex 가 자동으로 읽는 **`AGENTS.md`** 와 **스킬** `.codex/skills/nexa-slide-session/`·`nexa-slide-server/`(0.22.22) 가 있다. 옛 작업 공간은
`python3 nexa.py update_launcher`(또는 `python3 <엔진>/studio/init_workspace.py <작업 공간>`)가 없는 파일만 만든다. 저장소형이면 루트에도 같은 스킬을 둔다(Codex 는 cwd 의 `.codex/skills` 를 읽는다).

```powershell
cd '<작업 공간>'
python3 nexa.py start          # 편집기 서버(이미 떠 있으면 생략)
codex                          # 대화형으로 연다
```

대화창에 **`$nexa-slide-session`** 한 줄(또는 `/skills` 에서 고른다) — Claude Code 의 `/nexa-slide-session` 과 같은 일이다. 스킬이 하는 것:
`python3 nexa.py watch_requests --label "Codex" --agent codex --ttl 600` 로 **요청이 올 때까지 기다렸다가**(편집기 칩은 "수동 세션 · Codex") 요청 묶음 JSON 을 받아 끝나면 → 규약대로 처리(working → `draft_deck` → `apply_patch` → `save_deck` → done+reply) → 같은 명령을 다시. 600초 동안 요청이 없으면 `{"event":"ttl"}` 로 끝나고 다시 건다.
서버 작업(엔진 요청 큐)은 **`$nexa-slide-server`** — `watch_engine_requests --wait --ttl 600`(요청이 생기면 한 건 내고 끝남, 없으면 `expired`) 로 같은 반복을 하고 엔진 worktree 에서 처리한다. 엔진 저장소에서 연 Codex 에는 저장소의 `.codex/skills/nexa-slide-server/` 가 같은 스킬이다.

스킬 없이 손으로 하려면 대화창에 붙여 넣는다:

```text
이 폴더는 nexa-slide 슬라이드 작업 공간이야. AGENTS.md 와 CLAUDE.md 를 먼저 읽어(같은 규칙이 너에게도 적용돼).
편집기 요청을 이렇게 처리해 줘.
1) python3 nexa.py watch_requests --label "codex" 를 실행해. 요청이 생기면 JSON 목록을 출력하고 끝난다.
2) 요청마다: decks/<덱>.requests.json 의 그 요청 status 를 "working" →
   덱을 고친 새 파일을 만들고 python3 nexa.py save_deck <덱> --from <새 파일> --request <요청 id> --note "<한 줄>" 로 저장 →
   같은 변경을 content/<덱>.json 에도 → status "done", reply 에 한두 문장. 모르면 status 는 "open" 그대로, reply 에 질문.
3) 끝나면 1) 을 다시 실행해. 내가 멈추라고 할 때까지 반복해.
```

- 편집기 머리줄 칩은 감시가 기다리는 동안 "세션 연결됨", 처리 중에는 "세션 처리 중 n" 이 된다. Claude Code 전용 활동 표시(훅)는 없다.
- **권한**: 파일 수정과 명령 실행이 필요하다. `/permissions` 에서 작업 공간 쓰기를 허용한다(샌드박스 `workspace-write` — 쓰기가 작업 공간 폴더 안으로 제한된다).
- **로컬 서버 접속**: `save_deck` 은 떠 있는 편집기 서버(127.0.0.1)에 저장을 요청한다. 샌드박스가 네트워크를 막아 실패하면 `config.toml` 의
  `[sandbox_workspace_write]` 에 `network_access = true` 를 두거나, 그때만 승인한다. 서버가 꺼져 있으면 `save_deck` 이 직접 쓴다.
- **git 저장소 밖 폴더**: Codex 는 기본으로 git 저장소를 요구한다. 작업 공간이 저장소 밖이면 `git init` 하거나 비대화형 실행에 `--skip-git-repo-check`.
- 모델: 대화형에서 `/model`, 설정은 `~/.codex/config.toml` 의 `model = "<모델 ID>"`(계정에서 쓸 수 있는 모델).

## 4. 비대화형 실행 확인

서버가 세션을 띄우는 방식과 같다 — 화면 없이 끝나야 한다.

```bash
cd '<작업 공간>'
codex exec --sandbox workspace-write "Reply with exactly: OK"
codex exec --json --sandbox workspace-write "Reply with exactly: OK"    # JSON Lines 이벤트(thread.started · turn.completed · error …)
codex exec resume --last "다음 요청"                                    # 직전 세션 이어 가기(특정 세션: codex exec resume <SESSION_ID>)
```

- 진행 상황은 표준 오류, 마지막 답만 표준 출력으로 나온다(`-o <파일>` 로 마지막 답만 파일에).
- 한 번만 키를 쓰려면 `CODEX_API_KEY` 를 그 실행에만 준다.
- 정확한 옵션은 설치한 버전의 `codex exec --help` 로 확인한다(버전마다 바뀐다 — 예: `--full-auto` 는 없어졌다).

## 5. 웹 세션에서 서비스 유형 바꾸기

웹 세션(허브 시작 페이지·Studio 세션 칩의 [세션 시작])은 **서비스 유형(`claude` / `codex`)만 바꾸면 같은 화면·같은 처리 규약**으로 동작한다 — 서버가 턴마다 그 CLI 를 실행한다([claude-session.md](claude-session.md) 5절, 설계 [dev/web-session-design.md](dev/web-session-design.md)).
`codex` 어댑터(`studio/agents/codex.py`)는 **2026-10-17 Windows(codex-cli 0.163 · ChatGPT 로그인 · 모델 `gpt-6-luna`)에서 작업 공간 웹 세션 턴을 끝까지 확인했다** — 셸로 안내 파일·덱을 읽고, 요청 파일을 고쳐 답을 남겼다. 설치가 없으면 시작 창에서 비활성(이 문서 안내).
시작 창의 모델 칸에는 계정에서 쓸 수 있는 모델 ID 를 적는다(기본 목록 `gpt-6-luna`, 관리자가 전역 설정 `sessionModels.codex` 로 바꾼다).

| 항목 | `claude` (확인됨) | `codex` (확인됨 · Windows) |
|---|---|---|
| 실행 파일 | `claude`(PATH) — 사용자 설정 `agentPaths.claude` 로 지정 가능 | `agentPaths.codex` → PATH 의 `codex` → (Windows) 데스크톱 앱 동봉 `codex.exe`. PATH 판 옆에 `codex-code-mode-host.exe` 가 없으면 앱 동봉 판을 우선 |
| 설치·로그인 확인 | `claude --version` · `claude auth status`(JSON, 턴을 쓰지 않음) | `codex --version` · `codex login status` |
| 한 턴 | `claude -p --output-format stream-json --verbose --model <m> --permission-mode dontAsk --permission-prompts none --restricted --tools "Read,Edit,Write,Glob,Grep,Bash" --settings <권한 JSON> --strict-mcp-config --max-turns <n>`(프롬프트는 stdin) | `codex exec --json --sandbox workspace-write -m <m> -c approval_policy="never" -c sandbox_workspace_write.network_access=true [-c windows.sandbox="elevated"] --ignore-user-config --skip-git-repo-check -`(프롬프트는 stdin). Windows 샌드박스 값은 사용자 `config.toml` 의 `[windows] sandbox` 를 옮겨 적는다(없으면 elevated) |
| 턴 프롬프트의 도구 낱말 | Read/Edit/Write 도구 | 같은 프롬프트에 `{shell}` 자리로 "Read 는 셸 읽기, Edit 는 `apply_patch`" 안내를 넣는다(`CodexAgent.shell_note`) — 없으면 Codex 가 "파일 도구가 없다"며 멈춘다(실측) |
| 이어 가기 | `--resume <session_id>`(`system/init` 의 `session_id`) | `codex exec resume <thread_id> -`(`thread.started` 의 `thread_id`) |
| 모델 | 별칭 `opus`·`sonnet`·`haiku` 또는 전체 ID | 계정에서 쓸 수 있는 모델 ID(목록은 관리자가 전역 설정 `sessionModels.codex` 에) |
| 쓰기 범위 | 엔진 권한 템플릿(`studio/agents/permissions.json` workspace+web)을 `--settings` 로 — 작업 공간 안 Read/Edit/Write, 명령은 `python3 nexa.py …` 만 | `--sandbox workspace-write`(cwd = 작업 공간 안만 쓰기), 네트워크는 `save_deck` 의 127.0.0.1 저장을 위해 켬 |
| 읽는 안내 파일 | `CLAUDE.md` | `AGENTS.md` |
| 출력 파싱 | stream-json(`system`·`assistant`·`result`) | NDJSON(`thread.started`·`turn.started/completed/failed`·`item.*`·`error`) |
| 서버 계정이 다를 때 인증 | `CLAUDE_CODE_OAUTH_TOKEN` 또는 `ANTHROPIC_API_KEY` | `OPENAI_API_KEY`(→ `codex login --with-api-key`) 또는 `CODEX_HOME` 의 `auth.json` |
| 금지(어떤 설정으로도 넣지 않음) | `--dangerously-skip-permissions`·`bypassPermissions` | `--sandbox danger-full-access`·`--approve-for-me` |

서비스 유형·모델은 **전역(사용자 설정 `sessionAgent`·`sessionModel`, 관리자만) < 작업 공간 설정(`nexa-slide.local.json`/`nexa-slide.json` 의 같은 키) < 세션 시작 창의 선택** 순이고 모두 화면에서 바꾼다(시작 창의 "이 작업 공간 기본으로 저장").
`codex` 를 처음 쓸 때는 작업 공간 하나로 `python3 nexa.py draft_deck`·`save_deck` 흐름이 끝까지 가는지 턴 로그(Studio 세션 칩 → 턴 로그)로 확인한다 — 옵션 이름이 설치된 판과 다르면 `probe` 가 `--help` 로 알아내 경고한다.
