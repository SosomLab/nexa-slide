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

Windows — 작업 스케줄러 "로그온 시 실행"(관리자 권한 불필요). 파이썬은 실제 실행 파일 경로로 적는다(pyenv-win 의 `python3` 는 배치 파일이다):

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
