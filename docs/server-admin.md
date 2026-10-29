# 서버 관리 안내 (허브 운영자용)

허브(시작 페이지, 기본 포트 5599)를 한 PC 에 띄워 두고 웹으로 여러 사람이 쓰게 할 때, **운영자가 그 PC 에서 하는 일**을 순서대로 모았다.
규칙의 자세한 내용은 [auth.md](auth.md)(인증·계정·접근 로그), [operation.md](operation.md)(서버·작업 공간 운영), [server.md](server.md)(URL·API).

```
브라우저 ──https──▶ Cloudflare ──터널(cloudflared)──▶ 허브 127.0.0.1:5599 (로그인 필수)
                                                        └─ /w/<이름>/ 중계 ─▶ 작업 공간 서버 127.0.0.1:5600~ (로그인 없음, 밖에 열지 않는다)
```

명령은 모두 **허브가 도는 PC 의 터미널**, 엔진 폴더에서 실행한다(`python3` 는 python-pptx 가 설치된 파이썬).
계정·세션·접근 로그는 사용자 설정 폴더(Windows `%APPDATA%\nexa-slide`)에 있고, 그 폴더는 **서버를 실행한 Windows 사용자 계정**의 것이다 — 허브는 늘 같은 계정으로 띄운다.

## 1. 처음 설치해서 띄우기

1. 엔진 설치 — [install.md](install.md) (Python·`requirements.txt`).
2. 관리자 만들기 — 터미널에서 먼저 만들어 두는 것을 권한다(웹 최초 설정 페이지를 남이 먼저 여는 일이 없다).
   ```bash
   python3 studio/auth.py add <아이디> --admin      # 비밀번호는 프롬프트에서(8자 이상). 명령줄 인자로 주면 셸 기록에 남는다
   python3 studio/auth.py list                      # 확인
   ```
   터미널에서 만들지 않으면, 관리자가 없는 동안 허브의 어떤 주소로 들어와도 **최초 관리자 설정 페이지**(`/setup`)가 뜨고 거기서 만든 사용자가 관리자가 된다.
   이 경우 **터널을 연결하기 전에** 이 PC 의 브라우저(`http://127.0.0.1:5599/`)에서 먼저 만든다.
3. 허브 시작
   ```bash
   python3 studio/service.py start                  # 백그라운드 실행 → http://127.0.0.1:5599/ (작업 공간 밖에서 실행하면 허브)
   python3 studio/service.py status
   ```
4. 이 PC 의 브라우저로 `http://127.0.0.1:5599/` → 로그인 → 시작 페이지가 보이면 된다.
5. 밖에 열기 — 터널은 **허브 포트(5599)만** 가리키게 한다(작업 공간 서버 포트 5600~ 은 열지 않는다). Cloudflare 터널이면 Host 설정이 따로 필요 없다.
   다른 방식(리버스 프록시 등)으로 공개하면 사용자 설정 `publicHosts` 에 공개 호스트 이름을 적는다(없으면 400 "허용되지 않은 Host").
6. AI 세션을 쓸 계획이면 이 PC 에 Claude Code 또는 Codex CLI 를 **허브와 같은 사용자 계정**으로 설치·로그인한다 — [claude-install.md](claude-install.md) · [openai-codex.md](openai-codex.md).

## 2. 이미 밖에 열어 둔 허브를 인증 판으로 올리기

인증이 없던 판에서 올릴 때는 **순서가 중요하다** — 재시작 직후 관리자가 없으면 밖에서 먼저 `/setup` 을 열어 관리자를 가져갈 수 있다.

```bash
git pull                                            # 엔진 갱신(또는 새 판 받기)
python3 studio/auth.py add <아이디> --admin         # ① 재시작 "전에" 관리자부터
python3 studio/service.py restart                   # ② 허브 재시작(구 판에서 처음 올릴 때는 아래 "처음 한 번만")
```

- **처음 한 번만**: 인증 이전 판 허브는 새 판의 생존 확인(`/api/auth/state`)에 답하지 않아 `service.py restart`·`stop` 이 그 허브를 찾지 못한다.
  이때는 5599 를 쓰는 프로세스를 직접 끝낸 뒤 `service.py start` 한다 — Windows `Stop-Process -Id (Get-NetTCPConnection -LocalPort 5599 -State Listen).OwningProcess`,
  macOS·Linux `kill $(lsof -t -iTCP:5599 -sTCP:LISTEN)`. 한 번 새 판으로 바뀐 뒤에는 `restart` 로 된다.
- 확인: 밖의 주소(예 `https://slides.example.com/api/home`)를 로그인 없이 열면 401, 페이지는 로그인 화면이어야 한다.
- 떠 있는 작업 공간 서버들도 새 판으로 바꾼다 — 각 작업 공간에서 `python3 <작업 공간>/nexa.py restart`(또는 시작 페이지 최근 작업에서 중지 → 시작).
  허브만 새 판이고 작업 공간 서버가 옛 판이면 중계 사용자 기록 등이 빠진다.
- 허브 `start` 가 "응답이 없다"로 끝나면 엔진 파일이 판이 섞인 것이다 — 같은 판으로 맞춘다([operation.md](operation.md) 문제 해결).
- 급히 막아야 하면 먼저 터널을 끊는다 — Windows 서비스로 설치한 cloudflared 는 `Stop-Service cloudflared`(관리자 PowerShell), 다시 열 때 `Start-Service cloudflared`.

## 3. 매일 운영

| 할 일 | 명령 · 위치 |
|---|---|
| 허브 상태·주소 | `python3 studio/service.py status` · `url` |
| 허브 시작·중지·재시작 | `python3 studio/service.py start` · `stop` · `restart` (중지해도 작업 공간 서버들은 그대로 돈다) |
| 작업 공간 서버 | 시작 페이지 "최근 작업"의 시작/중지, 또는 `python3 <작업 공간>/nexa.py start` · `stop` · `status` |
| 허브 로그 | 사용자 설정 폴더 `hub/.studio/server.log` |
| 작업 공간 서버 로그 | `<작업 공간>/out/.studio/server.log` |
| 접근 로그 | 사용자 설정 폴더 `hub/logs/access-YYYY-MM-DD.log` — 하루 한 파일, `accessLogDays`(기본 30일) 지나면 자동 삭제 |
| 공유 링크 | `/account` 공유 링크 카드(관리자는 전체) 또는 `python3 studio/share.py list` · `revoke <id>` — 아래 4절 |
| 설정 위치 확인 | `python3 studio/paths.py` (사용자 설정 폴더·허브 포트·엔진 위치) |

접근 로그는 한 줄이 JSON 하나다. 거부·오류만 보기:

```powershell
Get-Content "$env:APPDATA\nexa-slide\hub\logs\access-$(Get-Date -Format yyyy-MM-dd).log" | Select-String '"result":"(deny|error)"'
```

```bash
grep -E '"result":"(deny|error)"' ~/.config/nexa-slide/hub/logs/access-$(date +%F).log      # Linux (macOS: ~/Library/Application Support/nexa-slide)
```

`login.fail`·`login.locked` 가 같은 IP·같은 아이디로 몰리면 그 계정 비밀번호를 바꾸고, 필요하면 Cloudflare 쪽에서 그 IP 를 막는다. 필드 설명은 [auth.md](auth.md#접근-로그).

### 웹 세션의 웹 검색 허용 — 보안 주의

기본은 막혀 있다. 관리자가 시작 페이지 "기준 폴더 설정 → AI 세션 전역 기본 → 웹 검색 허용"을 켜면, 그 뒤 **세션을 시작할 때마다** 관리자가 "이 세션에 웹 검색 허용"을 골라야 열린다(전역만 켜고 체크하지 않으면 그대로 막힘, 실행 중 세션은 다시 시작해야 바뀜, claude 만).

- 열리는 것: `WebSearch`·`WebFetch` 도구뿐. `curl`·`wget`·`powershell`·`mcp__*` 는 계속 거절된다.
- 위험: 세션이 슬라이드·요청 내용의 일부를 검색어나 요청 URL 에 넣어 외부로 보낼 수 있다. 사내 자료 덱에서는 켜지 않거나, 요청에 "외부에 보내도 되는 범위"를 적어 둔다.
- 흔적: 접근 로그 `event=settings.sessionAllowWeb:on|off`(설정 변경)·`session.start:<에이전트>:<모델>:web`(허용 세션 시작), 세션 턴 로그(`out/.studio/sessions/<시작 시각>/turn-N.jsonl`)에 WebFetch 대상 URL·WebSearch 검색어가 그대로 남는다 — 점검 때 본다.
- 수집 자료는 세션이 작업 공간 안 `research/<주제>.md` 에 정리하도록 프롬프트에 적혀 있다(덱 안 각주에 출처 URL).

### 웹 세션의 git·push·저장소 루트 허용 — 보안 주의

웹 검색과 같은 틀이다: 관리자가 "AI 세션 전역 기본"에서 **git 기록 허용 · push 허용 · 저장소 루트 접근**을 켠 뒤, 세션을 시작할 때마다 관리자가 체크해야 열린다(claude 만, 실행 중 세션은 다시 시작해야 바뀜). 작업 공간 설정에 같은 키를 `false` 로 두면 그 작업 공간은 끌 수 있다.

- 열리는 것: git 기록 = `git add`·`commit`·`switch`/`checkout`·`merge`·`branch`·`stash`·`tag`(+`status`·`diff`·`log`·`show`) · push = `git push`·`pull`·`fetch` · 저장소 루트 = 작업 공간을 품은 저장소 루트 아래 Read/Edit/Write(`--add-dir`).
- 켜도 막히는 것(권한 deny, 실제 실행으로 확인): 강제 push(`--force`·`-f`·`--mirror`·`--delete`·`:브랜치`) · `reset --hard` · `clean` · `rebase` · `filter-*` · `config` · `remote` · `git -C` · `worktree` · `submodule` · `restore`·`checkout -- …`(작업 내용 버리기) · `branch -D` · `tag -d` · `reflog`·`gc`, `.git/` 파일 직접 수정, 저장소 루트 밖 파일.
- **자격 증명**: push 는 서버(작업 공간 서버) 프로세스를 띄운 이 PC 사용자의 git 자격 증명(Windows 자격 증명 관리자·ssh-agent)을 그대로 쓴다 — 허브·작업 공간 서버를 그 사용자로 띄운다. 대화형 로그인 창이 뜨지 않게 `GIT_TERMINAL_PROMPT=0`·`GCM_INTERACTIVE=never` 로 실행하므로 자격 증명이 없으면 push 는 실패하고 세션은 그 출력을 reply 에 적는다.
- 커밋 작성자는 이 PC 의 `git config user.name/email`, 웹 사용자는 커밋 메시지 끝 `Requested-by: <아이디>` 트레일러로 남는다.
- 흔적: 접근 로그 `event=settings.sessionAllowGit:on|off`…·`session.start:<에이전트>:<모델>:git:push:root`, 턴 로그(`out/.studio/sessions/<시작 시각>/turn-N.jsonl`)에 git 명령 원문.
- 저장소 루트가 엔진 폴더면 열지 않는다. 작업 공간이 git 저장소 안이 아니면 git·저장소 루트 권한을 고를 수 없다.

## 4. 사용자·관리자 관리

웹: 로그인 → 왼쪽 위 메뉴(☰) → "계정"(관리자는 "계정 · 사용자 관리") → `/account`. 누구나 **내 비밀번호 변경**, 관리자는 **사용자 관리**(추가·삭제·비밀번호 초기화·관리자 지정/해제).

| 할 일 | 웹(관리자) | 이 PC 터미널 |
|---|---|---|
| 사용자 목록 | `/account` 사용자 관리 | `python3 studio/auth.py list` |
| 사용자 추가 | 추가(임시 비밀번호 → 첫 로그인에서 바꾸게 함) | `python3 studio/auth.py add <아이디> [--admin]` |
| 비밀번호 초기화 | 초기화 | `python3 studio/auth.py reset-password <아이디>` |
| 관리자 지정·해제 | 역할 변경 | `python3 studio/auth.py role <아이디> admin\|user` |
| 사용자 삭제 | 삭제 | `python3 studio/auth.py delete <아이디>` |

- 초기화하거나 비밀번호를 바꾸면 그 사용자의 다른 로그인은 모두 끊긴다. 임시 비밀번호로 들어오면 바로 바꾸게 한다.
- 마지막 관리자는 내리거나 지울 수 없고, 자기 계정은 지울 수 없다.
- 터미널 명령은 실행 중인 허브와 같은 파일을 보므로 **허브를 재시작하지 않아도** 바로 반영된다.
- **원격에서 비밀번호를 초기화하는 방법은 없다** — 웹은 관리자가 다른 사용자를 초기화하는 것까지다.

### 보기 전용 공유 링크 — 회수·로그 (0.22.25)

사용자가 Studio 에서 만든 `/s/<토큰>/` 주소는 로그인 없이 덱 1개를 보여 준다([auth.md](auth.md#보기-전용-공유-링크-02225)). 운영자가 할 일:

| 할 일 | 웹 | 이 PC 터미널 |
|---|---|---|
| 전체 목록(누가·어느 덱·만료·조회 수) | `/account` **공유 링크** 카드(관리자) | `python3 studio/share.py list` |
| 회수 | 그 줄의 [회수] | `python3 studio/share.py revoke <id>` |
| 정책 | — | `settings.json` `shareMaxDays`(기본 90) · `shareCreate: "any"\|"admin"`(기본 any) — 허브 재시작 없이 바로 반영 |

- 토큰 원문은 서버 어디에도 없다(해시만). 유출이 의심되면 회수하고 새로 만든다. 파일 `hub/share.json` 을 지우면 모든 링크가 죽는다.
- 접근 로그에서 `"user":"share:<id>"` 줄이 그 링크의 요청이다. `share.view:<id>` 가 열람, `share.denied:<id>:path` 가 허용 목록 밖 시도, `share.auth.fail`·`share.auth.locked` 가 비밀번호 실패·잠금. 한 링크에 `denied:path` 가 몰리면 링크를 뒤져 보는 사람이 있다는 뜻이니 회수한다.
- 비밀번호 잠금은 링크 id 기준(5회/15분)이라 누군가 일부러 틀리면 정상 시청자도 그 시간 동안 막힌다 — 그런 경우 새 링크를 만든다.

## 5. 복구 — 이 PC 에서만

| 상황 | 하는 일 |
|---|---|
| 내(관리자) 비밀번호를 잊었다 | `python3 studio/auth.py reset-password <아이디>` → 임시 비밀번호로 로그인 → `/account` 에서 새 비밀번호 |
| 관리자 아이디도 모른다 | `python3 studio/auth.py list` 로 역할(admin) 확인 후 위와 같이 |
| 관리자가 하나도 없다(모두 삭제·파일 손상) | `python3 studio/auth.py add <아이디> --admin`. 처음부터 다시 하려면 사용자 설정 폴더의 `users.json` 을 지운다 — 그러면 다음 접속이 최초 설정 페이지가 되므로 **터널을 먼저 끊거나** 지운 직후 `add --admin` 으로 만든다 |
| 로그인이 "잠겼다"(429) | 같은 주소에서 5회 실패 → 15분 잠금. 이 PC(로컬)에서는 아이디 잠금이 없어 바로 로그인할 수 있다. 모두 풀려면 `python3 studio/service.py restart` |
| 모든 사용자를 로그아웃시키고 싶다 | 사용자 설정 폴더의 `hub/sessions.json` 을 지운다(계정은 그대로) |
| 공유 비밀이 샜다고 의심된다 | `hub/.studio/hub-key` 를 지우고 허브와 작업 공간 서버를 모두 재시작(새 비밀이 만들어진다) |
| 400 "허용되지 않은 Host" | Cloudflare 터널이 아닌 경로로 공개했다 — 사용자 설정 `publicHosts` 에 그 호스트를 적고 재시작 |

## 6. PC 를 켜면 자동으로 띄우기 (선택)

허브는 **로그인한 그 사용자 계정**으로 띄운다. Windows 서비스(SYSTEM)·다른 계정으로 띄우면 사용자 설정 폴더가 달라져 계정·로그가 따로 생기고, AI 세션의 로그인 정보도 찾지 못한다.

Windows — 작업 스케줄러 "로그온 시 실행"(관리자 권한 불필요). 명령 하나로 켜고 끈다(작업 공간 밖에서, **운영 엔진**의 service.py 로 - 개발용 worktree 에서는 막힌다):

```powershell
python <운영 엔진>/studio/service.py autostart on       # 켜기 - 작업 'nexa-slide hub' 를 이 python.exe 실제 경로로 등록
python <운영 엔진>/studio/service.py autostart status   # 확인 - 상태 · 실행할 명령 (없으면 none)
python <운영 엔진>/studio/service.py autostart off      # 끄기
# --dry-run 을 붙이면 등록하지 않고 실행할 PowerShell 만 보인다
```

손으로 등록하려면 아래처럼 한다. 파이썬은 실제 실행 파일 경로로 적는다(pyenv-win 의 `python3` 는 배치 파일이다):

```powershell
$py  = python3 -c "import sys; print(sys.executable)"          # 실제 python.exe 경로
$eng = 'D:\Projects\nexa-slide'                                  # 엔진 폴더
$act = New-ScheduledTaskAction -Execute $py -Argument "`"$eng\studio\service.py`" start" -WorkingDirectory $env:USERPROFILE
Register-ScheduledTask -TaskName 'nexa-slide hub' -Action $act -Trigger (New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME)
# 지우기: Unregister-ScheduledTask -TaskName 'nexa-slide hub' -Confirm:$false
```

- 작업 폴더를 작업 공간 밖(사용자 폴더)으로 둔다 — 작업 공간 안에서 실행하면 허브가 아니라 그 작업 공간 서버가 뜬다.
- 절전·최대 절전을 끄거나 늘린다(잠들면 웹 접속이 끊긴다). cloudflared 는 Windows 서비스로 설치해 두면 함께 뜬다.
- macOS 는 `launchd` 사용자 에이전트(`~/Library/LaunchAgents`), Linux 는 `systemd --user` 서비스로 같은 명령(`python3 <엔진>/studio/service.py start`)을 로그인 때 실행한다.

## 7. 백업

| 대상 | 위치 | 비고 |
|---|---|---|
| 계정 | 사용자 설정 폴더 `users.json` | 비밀번호는 해시만 있다. 그래도 외부에 두지 않는다 |
| 설정 | `settings.json`(기준 폴더·최근 작업·`publicHosts` 등) | |
| 공유 링크 | `hub/share.json` | 토큰 해시만 있다. 지우면 보낸 링크가 모두 죽는다 |
| 접근 로그 | `hub/logs/` | 보관 기간이 지나면 지워지므로 오래 둘 것은 따로 옮긴다 |
| 슬라이드 | 각 작업 공간(저장소) | git 으로 관리. 자동 백업 `decks/.history/`·변경 원장 — [operation.md](operation.md#백업--복원) |

`sessions.json`·`hub-key` 는 백업하지 않아도 된다(지우면 다시 로그인·새로 생성).

## 8. 점검표

- [ ] 관리자 계정이 있다(`auth.py list`), 관리자가 둘 이상이면 한 사람이 잠겨도 복구가 쉽다
- [ ] 밖의 주소를 로그인 없이 열면 로그인 화면·401 이다
- [ ] 터널은 5599 만 가리킨다(5600~ 은 밖에서 열리지 않는다)
- [ ] 허브는 사람이 쓰는 그 사용자 계정으로 뜬다(자동 시작 포함)
- [ ] 접근 로그에 `deny` 가 몰리지 않는다
- [ ] (선택) Cloudflare Access 같은 앞단 인증을 한 겹 더 둔다
- [ ] 서버 작업 카드에 오래된 "완료(적용 대기)" 가 쌓여 있지 않다 — 9절 순서로 적용하거나 거절한다

## 9. 엔진 요청 적용 절차

엔진 개발 세션(시작 페이지 "서버 작업" 카드)은 요청을 **엔진 worktree 의 `engine-dev` 브랜치**에만 커밋하고 큐 항목을 **완료(적용 대기)** 로 둔다.
운영 트리(main)는 허브·작업 공간 서버가 실행 중인 코드이므로, 병합·배포·재시작은 운영자가 아래 순서로 한다. 흐름 그림은 [mechanism.md](mechanism.md#8-엔진-요청-큐--엔진-개발-세션-e-단계-019021).

| 위치 | 경로 |
|---|---|
| 엔진 worktree | `<엔진>/.claude/worktrees/engine-dev`(브랜치 `engine-dev`) |
| 큐 | 사용자 설정 폴더 `hub/engine/requests.json`(CLI: `python3 studio/engine_request.py list` · `show <번호>`) |

### 카드 [배포] (0.22.29~, 권장)

관리자로 로그인해 시작 페이지 "서버 요청" 카드의 **[🚀 배포 준비 ▾]**(주 색 단추, 누르면 아래로 펼쳐지고 **[▴ 접기]** 로 닫힘) → 들어갈 요청·커밋·막는 이유를 확인 → **[배포 시작]**. 아래 1~5 단계를 허브가 한 번에 한다 - 시험용 worktree 병합 → 시험(새로 생긴 실패만 막음) → 처리 중 턴 대기 → main 반영 → 허브·작업 공간 서버 재시작(안 뜨면 main 되돌림) → push → 적용됨·원 요청 재개 → engine-dev 맞춤. 진행은 카드에 단계별로(지금 하는 단계는 돌아가는 표시와 시작 시각, 0.22.32~) 보이고 기록은 사용자 설정 폴더 `hub/engine/deploy.json`·`deploy-logs/`. 설계 [engine-deploy-design.md](dev/engine-deploy-design.md). 충돌·새 시험 실패·push 실패처럼 멈춘 경우는 아래 손 절차로 마무리한다. 배포가 끝나 더 배포할 것이 없어도 카드에는 결과 배지(`배포 완료 · 시각`)와 **[지난 배포 보기 ▾]** 가 남아 지난 배포의 단계·시험 결과를 다시 볼 수 있다(0.22.42~). 엔진 세션이 시험을 돌리는 중에 배포하면 배포 시험은 그 시험이 끝날 때까지 기다린다('시험 대기', 0.22.41~ 시험 잠금).

### 순서(손으로)

1. **확인** — 카드에서 완료(적용 대기) 항목의 reply·commit·test 를 본다. 터미널에서:
   ```bash
   python3 studio/engine_request.py show <번호>              # commit · branch · test · reply
   git log --oneline main..engine-dev                         # 들어올 커밋
   git diff main...engine-dev --stat                          # 바뀐 파일
   ```
   렌더 규칙(`render.js` ↔ `common.py`·`export_pptx.py`)을 건드렸으면 `python3 studio/check_parity.py -W example`, 등록된 작업 공간의 덱은 병합 전·후 `export_pptx.py --out` 결과 슬라이드 XML 이 같아야 한다(기능 추가가 아니라면).
2. **병합** — 운영 트리(엔진 폴더, `main`)에서 병합 커밋을 남긴다. 변경 이력(`CHANGELOG`)의 판 번호를 맞춘다.
   ```bash
   git switch main
   git merge --no-ff engine-dev -m "merge: engine-dev (engine-request #<번호> - <요약>)"
   git push
   ```
   병합 순간 정적 파일(`studio/*.js`·`*.html`)은 바로 새 판이 나가고 파이썬은 재시작 전까지 옛 판이다 — 병합과 재시작을 붙여서 한다.
3. **재시작** — 처리 중인 턴이 없는지 본 뒤(시작 페이지 세션 줄·서버 작업 카드가 "처리 중"이 아님) 허브와 작업 공간 서버를 다시 띄운다. 돌고 있던 웹·엔진 세션은 끝나므로 필요하면 다시 시작한다.
   ```bash
   python3 studio/service.py restart                         # 허브
   python3 <작업 공간>/nexa.py restart                        # 떠 있는 작업 공간마다
   ```
4. **[적용됨] 표시** — 카드의 [적용됨]을 누른다(확인 창: "main 에 병합하고 서버를 재시작했나요?"). 지금 화면 버튼은 상태만 바꾸고 병합 커밋(`appliedCommit`)은 적지 않는다.
   병합 커밋까지 남기려면 엔진 저장소에서 CLI 로 `python3 studio/engine_request.py status <번호> applied --applied-commit <병합 커밋>`(원 요청 재개 알림에 그 해시가 들어간다), 또는 관리자로 로그인한 상태에서 허브 API 를 부른다:
   ```text
   POST /api/engine/requests
   {"action": "status", "id": <번호>, "status": "applied", "appliedCommit": "<병합 커밋>"}
   ```
5. **engine-dev 동기화** — 다음 엔진 세션이 최신 main 에서 시작하도록 worktree 브랜치를 main 으로 맞춘다(병합 뒤라 fast-forward 다).
   ```bash
   git -C .claude/worktrees/engine-dev merge --ff-only main
   ```
6. **원 요청 재개** — 엔진 요청을 넘긴 작업 공간의 원 요청은 자동으로 다시 열리지 않는다. 그 작업 공간 Studio 요청 탭에서 [후속 요청]("엔진에 반영됐으니 진행해 줘")으로 이어 간다.

### 사례 — 엔진 요청 #4 · #5 (2026-10-15, 0.21.1 · 0.21.2)

| 요청 | engine-dev 커밋 | main 병합(appliedCommit) | 판 |
|---|---|---|---|
| #4 content 에서 요소 좌표·앞뒤 순서·추가 요소 + 글머리/행 균등 간격(`place`·`extra`·`spread`·`rowH`) | `4f473a8` | `ee05917`(engine-dev 병합) → `7e5a819`(main) | 0.21.1 |
| #5 덱 전체 글자 크기 비율 확대(`scale_fonts` · content `fontScale`) | `4c2231c` | `52868f7`(engine-dev 병합) → `0707d1e`(main) | 0.21.2 |

두 건 모두 가정형호스피스 작업 공간 세션이 넘긴 요청(triage → 관리자 승인 → 엔진 세션 처리 → done)이고, 위 1~5 순서로 병합·재시작·[적용됨]·engine-dev 동기화를 했다.
이 사례에서는 engine-dev 를 먼저 개발 브랜치(`dev/engine-requests`)에 병합해 다른 변경과 함께 시험한 뒤 main 에 병합했다 — 개발 브랜치가 따로 돌고 있으면 그 방식이, 없으면 2단계처럼 main 에 바로 `--no-ff` 병합이 단순하다.
검증은 `check_parity`·회귀 시험과 `scale_fonts ×1.2` 뒤 `check_layout` ERROR 0.

### 주의

- 엔진 세션이 main 이나 운영 트리를 직접 고치지 않게 되어 있다(권한 · cwd = worktree). main 에 직접 커밋된 흔적이 있으면 원인을 먼저 본다.
- 세션이 넘긴 요청(triage)은 **사람이 내용을 읽고 승인**한다 — 작업 공간 요청 글이 엔진 변경 지시로 번질 수 있다(프롬프트 인젝션).
- 여러 요청을 한 번에 병합해도 되지만 [적용됨]은 요청마다 누른다.
