# Claude Code 설치·로그인

nexa-slide 는 편집기에서 남긴 요청을 **Claude Code** 가 받아 덱을 고친다([claude-session.md](claude-session.md)).
이 PC 에 `claude` 실행 파일이 없으면 요청은 파일에만 쌓이고 처리되지 않는다. 이 문서는 설치부터 서버에서 쓸 수 있는지 확인하기까지다.

| 쓰는 곳 | `claude` 가 필요한 PC |
|---|---|
| 수동 세션 — 터미널·VS Code·Claude Desktop 에서 열고 감시를 건다([ai-editing.md](ai-editing.md)) | 그 세션을 여는 PC |
| 웹 세션 — 시작 페이지·Studio 에서 버튼으로 세션을 띄운다(개발 중) | **허브·작업 공간 서버가 도는 PC**(브라우저가 있는 PC 가 아니다) |

> Claude Desktop 앱만 쓰는 경우에도 Code 세션은 동작하지만, 서버가 띄우는 웹 세션은 명령줄 `claude` 를 찾는다. 서버 PC 에는 아래 명령줄 설치가 필요하다.

## 1. 요구 사항

- **계정**: Claude Pro·Max·Team·Enterprise 또는 Console(API) 계정. 무료 claude.ai 플랜에는 Claude Code 가 포함되지 않는다.
- **운영체제**: Windows 10 1809+ / Windows Server 2019+, macOS 13+, Ubuntu 20.04+ · Debian 10+ · Alpine 3.19+. 메모리 4 GB 이상, 인터넷 연결.
- **Windows 권장**: [Git for Windows](https://git-scm.com/downloads/win) — Claude Code 의 Bash 도구와 **Monitor 도구**가 Git Bash 를 쓴다.
  수동 세션의 상시 감시(`watch_requests --stream` 을 Monitor 로)를 쓰려면 설치해 둔다. 없으면 PowerShell 도구로만 동작한다.

## 2. 설치

관리자 권한은 필요 없다. **현재 사용자**로 설치한다(서버를 실행할 계정과 같아야 한다 — [5절](#5-서버에서-쓸-때)).

### Windows

```powershell
# PowerShell (프롬프트가 PS C:\ 로 시작) — 권장: 기본 설치, 자동 업데이트
irm https://claude.ai/install.ps1 | iex
```

```bat
:: CMD (프롬프트에 PS 가 없음)
curl -fsSL https://claude.ai/install.cmd -o install.cmd && install.cmd && del install.cmd
```

```powershell
# 또는 WinGet — 자동 업데이트 없음(winget upgrade Anthropic.ClaudeCode)
winget install Anthropic.ClaudeCode
```

기본 설치 위치: `%USERPROFILE%\.local\bin\claude.exe`

### macOS · Linux · WSL

```bash
curl -fsSL https://claude.ai/install.sh | bash      # 권장: 기본 설치, 자동 업데이트
brew install --cask claude-code                     # 또는 Homebrew(macOS) — brew upgrade claude-code 로 갱신
```

기본 설치 위치: `~/.local/bin/claude`. Debian·Fedora·Alpine 패키지 저장소(apt·dnf·apk)로도 설치할 수 있다 — [공식 문서](https://code.claude.com/docs/en/setup#install-with-linux-package-managers).

### npm (대안)

```bash
npm install -g @anthropic-ai/claude-code            # Node.js 22 이상. sudo 로 설치하지 않는다
```

설치가 끝나면 **새 터미널**을 열어 다음 절로 확인한다(이미 열린 터미널은 PATH 가 갱신되지 않았을 수 있다).

## 3. 설치 확인

```powershell
claude --version                # 예: 2.1.267 (Claude Code)
claude doctor                   # 설치·설정 진단(세션을 시작하지 않는다)
(Get-Command claude).Source     # Windows: 실제 실행 파일 경로
```

```bash
command -v claude               # macOS·Linux: 실제 실행 파일 경로
```

`claude` 를 찾지 못하면 설치 폴더가 PATH 에 없는 것이다 — Windows 는 `%USERPROFILE%\.local\bin`, macOS·Linux 는 `~/.local/bin` 을
사용자 PATH 에 넣고 터미널을 다시 연다([공식 문제 해결](https://code.claude.com/docs/en/troubleshoot-install)).

## 4. 로그인

```bash
claude          # 처음 실행하면 브라우저가 열린다 → 계정으로 로그인 → 터미널로 돌아와 /exit
```

- 로그인 정보는 사용자 폴더에 저장된다 — Windows·Linux `~/.claude/.credentials.json`(Windows 는 `%USERPROFILE%\.claude\`), macOS 는 키체인.
  **같은 사용자 계정**으로 실행한 `claude` 는 모두 이 로그인을 쓴다.
- Console(API) 계정이면 환경변수 `ANTHROPIC_API_KEY` 로도 쓸 수 있다(처음 실행 때 이 키를 쓸지 묻는다).

비대화형 실행 확인 — 서버가 세션을 띄우는 방식과 같다(권한 질문·로그인 창 없이 끝나야 한다):

```powershell
claude -p "Reply with exactly: OK" --model opus --output-format json --max-turns 1
```

결과 JSON 의 `"is_error": false`, `"result": "OK"` 면 된다. 로그인 안내나 인증 오류가 나오면 4절 로그인을 다시 한다.

## 5. 서버에서 쓸 때

허브·작업 공간 서버가 띄우는 세션은 **서버 프로세스의 사용자·PATH·환경변수**를 그대로 물려받는다.

| 서버 실행 방식 | 필요한 것 |
|---|---|
| 로그인한 사용자가 직접 실행(`python3 studio/service.py start`, `nexa.py start`) | 4절 로그인만 하면 된다. **`CLAUDE_CODE_OAUTH_TOKEN` 설정 불필요** |
| 작업 스케줄러 "로그온 시 실행"(같은 사용자) | 위와 같다. 작업의 PATH 에 `claude` 설치 폴더가 있는지 확인(없으면 전체 경로로 지정) |
| 다른 계정·Windows 서비스(SYSTEM)·컨테이너·세션 전용 계정 | 그 계정에는 로그인 정보가 없다 → 아래 토큰 또는 API 키 |

토큰이 필요한 경우(다른 계정으로 서버를 돌릴 때):

```bash
claude setup-token                       # 로그인한 계정으로 실행 → 장기 토큰 출력(Pro·Max 등 구독 계정)
```

출력된 토큰을 서버 계정의 환경변수 `CLAUDE_CODE_OAUTH_TOKEN` 으로 둔다(또는 Console 계정의 `ANTHROPIC_API_KEY`).
토큰·키는 비밀번호와 같다 — 저장소·작업 공간·`nexa-slide.json` 에 적지 않고, 커밋되지 않는 `.env` 나 OS 사용자 환경변수에만 둔다.

주의:

- 설치하거나 PATH 를 바꾼 뒤에는 **서버를 다시 시작**해야 서버가 `claude` 를 찾는다(이미 떠 있는 프로세스의 PATH 는 그대로다).
- 자동 업데이트는 다음 실행부터 적용된다. 실행 중인 세션은 끊고 다시 시작할 때 새 버전을 쓴다.
- 여러 사람이 웹으로 쓰는 서버라면 구독 계정 하나를 공유하지 말고 Console(API) 계정·키를 쓰는 편이 맞다 — 이용 약관과 사용량 한도를 확인한다.

## 6. 문제 해결

| 증상 | 확인 |
|---|---|
| `claude` 를 찾을 수 없음 / not recognized | 새 터미널에서 다시. 그래도 없으면 3절 PATH. 서버에서만 안 되면 서버를 띄운 셸·작업 스케줄러의 PATH |
| PowerShell 에서 `'&&' is not a valid statement separator` | CMD 용 명령을 PowerShell 에 넣었다 — PowerShell 명령(`irm … \| iex`)을 쓴다 |
| CMD 에서 `'irm' is not recognized` | 반대 경우 — CMD 명령을 쓴다 |
| 로그인 창이 계속 뜸 / 인증 오류 | 서버 실행 계정과 로그인한 계정이 같은지. 다르면 5절 토큰 |
| 무료 계정이라 쓸 수 없다는 안내 | 1절 계정 요건 |
| 수동 세션에서 Monitor 를 쓸 수 없음(Windows) | Git for Windows 설치. 못 찾으면 Claude 설정 `env.CLAUDE_CODE_GIT_BASH_PATH` 에 `C:\Program Files\Git\bin\bash.exe` |
| 업데이트 확인 | `claude doctor`(마지막 업데이트 결과), 즉시 갱신은 `claude update` |

제거: 설치 방식별 명령은 [공식 문서](https://code.claude.com/docs/en/setup#uninstall-claude-code). 로그인 정보까지 지우려면 `~/.claude`·`~/.claude.json`.
