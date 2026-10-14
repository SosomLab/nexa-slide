# 인증 · 계정 · 접근 로그

허브(시작 페이지, 기본 5599)는 **로컬이어도 모든 요청에 로그인이 필요하다.** cloudflared 같은 터널은 127.0.0.1 로 들어오므로 주소로 안팎을 가를 수 없고,
허브에는 폴더 목록(`/api/fs`)·폴더 만들기·프로세스 실행(`/api/project`)·덱 저장(`/w/<이름>/`)이 있어 로그인 없이 열어 두면 원격 명령 실행과 다르지 않다.

`nexa.py start` 로 개별로 띄운 **작업 공간 서버(5600~)에는 로그인이 없다** — 같은 PC 의 터미널·Claude 세션(`save_deck`·`watch_requests`)이 그대로 쓴다.
그 포트를 직접 밖에 노출하는 것은 서비스 범위가 아니다. 밖에서 쓰려면 허브를 거친다(`/w/<이름>/` 중계).

> 운영자가 따라 할 절차(처음 띄우기 · 인증 판으로 올리기 · 사용자 관리 · 복구 · 자동 시작 · 백업 · 점검표)는 [server-admin.md](server-admin.md).

## 처음 한 번 — 관리자 만들기

관리자가 없으면 허브의 어떤 주소로 들어와도 **최초 관리자 설정 페이지**(`/setup`)가 뜬다. 여기서 만든 사용자가 **관리자**다.
관리자가 생기면 `/setup` 은 닫히고(다시 열면 로그인으로, POST 는 403) 모든 접속은 로그인 페이지(`/login`)로 간다.

> **허브를 이미 밖에 열어 둔 상태라면** 새 판으로 재시작하기 **전에** 터미널에서 관리자를 먼저 만든다 — 재시작 직후 누군가 먼저 `/setup` 을 열어 관리자를 가져가는 일을 막는다.
> ```bash
> python3 studio/auth.py add <아이디> --admin        # 비밀번호는 프롬프트에서(명령줄 인자로도 가능하나 셸 기록에 남는다)
> python3 studio/service.py restart                   # 작업 공간 밖에서 → 허브 재시작
> ```

## 로그인 · 세션

| 항목 | 내용 |
|---|---|
| 쿠키 | `nexa_sid` — `HttpOnly; SameSite=Lax; Path=/`, https 로 들어왔으면(`X-Forwarded-Proto: https`·`Cf-Visitor`) `Secure`. 쿠키에는 토큰 원문, 서버에는 sha256 만. `Lax` 인 이유: 메신저·메일의 링크로 `/w/…` 를 열어도 로그인이 이어지게 — 다른 사이트에서 보낸 상태 변경은 Lax 가 쿠키를 붙이지 않고 서버의 Origin 검사도 막는다 |
| 유효 기간 | 마지막 사용부터 `sessionDays`(기본 7일). 비밀번호를 바꾸거나 관리자가 초기화하면 그 사용자의 다른 로그인은 모두 끊긴다 |
| 실패 제한 | 클라이언트 주소 5회 실패 → 15분 잠금(429). **밖(Cloudflare 경유)에서 온 로그인은 아이디도 잠근다** — 로컬(같은 PC)에서는 아이디 잠금이 없어, 밖에서 비밀번호를 틀려 관리자를 잠가 두어도 로컬 로그인은 된다. 허브를 재시작하면 모두 풀린다 |
| CSRF | 상태 변경(POST·PUT)은 `Origin`(없으면 `Referer`)의 호스트가 `Host` 와 같아야 한다(허브는 둘 다 없는 요청도 거절) |
| Host 검사 | `127.0.0.1`·`localhost`, Cloudflare 경유(`Cf-Ray` 헤더), 사용자 설정 `publicHosts` 에 적은 호스트만. 그 밖은 400(DNS 리바인딩 차단) |
| 미인증 응답 | API·중계 API·JSON 요청은 401 `{"error":"login","login":"/login"}`, 페이지(GET)는 302 `/login?next=…`, 정적 파일·산출물(`/out/`·그림·글꼴·`/w/…`)은 401. 본문에 내용은 없다 |
| 예외(로그인 없이) | `/login`·`/setup`(페이지, CSS·JS 내장) · `GET /api/auth/state` · `POST /api/auth/login`·`/api/auth/setup` 만 |

편집기·시작 페이지는 401 을 받으면 로그인 페이지로 가고, 로그인 뒤 원래 주소로 돌아온다(`next`).

## 역할

| | user | admin |
|---|---|---|
| 시작 페이지·Studio·중계·설정 | ○ | ○ |
| 내 비밀번호 변경(`/account`) | ○ | ○ |
| 사용자 추가·삭제·비밀번호 초기화 | | ○ |
| **관리자 지정·해제** | | ○ (마지막 관리자는 내리거나 지울 수 없다, 자기 계정은 지울 수 없다) |

최초 설정으로 만든 사용자만 관리자로 시작한다. 그 뒤 관리자 지정은 관리자가 `/account` 의 사용자 관리에서 한다.
관리자가 초기화한 임시 비밀번호로 로그인하면 `/account` 로 가서 바꾸게 한다(`mustChange`).

## 어디에 저장되나 — git 에 들어가지 않는다

모두 **사용자 설정 폴더**(`paths.user_dir()` — Windows `%APPDATA%\nexa-slide`, macOS `~/Library/Application Support/nexa-slide`, Linux `~/.config/nexa-slide`)에만 있다.
엔진 저장소·작업 공간 저장소에는 아무것도 쓰지 않으므로 clone 한 PC 마다 계정이 따로다.

| 파일 | 내용 |
|---|---|
| `users.json` | `{"users": {아이디: {hash, salt, role, created, mustChange}}}` — `hashlib.scrypt`(n=2¹⁴, r=8, p=1) + 16바이트 salt |
| `hub/sessions.json` | 로그인 세션(토큰 해시 → 사용자·시각). 지우면 모두 로그아웃 |
| `hub/.studio/hub-key` | 허브 ↔ 작업 공간 서버 공유 비밀(아래) |
| `hub/logs/access-YYYY-MM-DD.log` | 접근 로그(아래) |

## 비밀번호를 잊었을 때 — 이 PC 에서만

원격에서 초기화할 길은 없다. 허브가 돌아가는 PC 의 터미널에서:

```bash
python3 studio/auth.py list                              # 사용자 목록
python3 studio/auth.py reset-password <아이디>            # 임시 비밀번호(프롬프트) — 다음 로그인에서 바꾸게 한다, 기존 로그인은 끊긴다
python3 studio/auth.py add <아이디> [--admin]             # 추가
python3 studio/auth.py role <아이디> admin|user           # 역할
python3 studio/auth.py delete <아이디>
```

관리자를 모두 잃었으면 사용자 설정 폴더의 `users.json` 을 지운다 → 다음 접속이 최초 설정 페이지가 된다(그 전에 터널을 끊거나 위의 `add --admin` 으로 바로 만든다).
`auth.py` 는 실행 중인 허브와 같은 파일을 보므로 허브를 재시작하지 않아도 바로 반영된다.

## 허브 ↔ 작업 공간 서버 — 공유 비밀

허브가 `/w/<이름>/…` 를 넘길 때 **밖에서 온 `X-Nexa-*` 헤더는 모두 버리고** `X-Nexa-Hub-Key`(공유 비밀)·`X-Nexa-User`·`X-Nexa-Role` 을 붙인다.
작업 공간 서버는 비밀이 맞을 때만 사용자를 믿는다(틀리면 403) — 변경 원장의 `actor.user`, `/api/config` 의 `user` 에 쓴다.
비밀은 `hub/.studio/hub-key` 에 처음 한 번 난수로 만들어지고(허브·작업 공간 서버 어느 쪽이 먼저 떠도 같은 파일), 허브 자신은 이 헤더를 받으면 403 이다(위조).

작업 공간 서버에 로컬로 바로 들어온 요청(헤더 없음)은 익명으로 허용한다. 다만 브라우저가 다른 사이트에서 보낸 상태 변경(`Origin` 이 다름)은 403 — CLI(Origin 없음)는 그대로.

## 접근 로그

허브와 작업 공간 서버로 들어오는 요청을 **JSON Lines** 로 남긴다 — `hub/logs/access-YYYY-MM-DD.log`(날짜별 파일, 여러 프로세스가 한 줄씩 덧붙인다).
`accessLogDays`(기본 30) 지난 파일은 하루 한 번 지운다.

```json
{"t":"2026-10-14T14:22:15.127+09:00","result":"allow","status":200,"method":"POST","path":"/api/auth/login","user":"admin","ip":"127.0.0.1","via":"local","ua":"Mozilla/5.0 …","ms":46,"server":"hub","event":"login"}
```

| 필드 | 내용 |
|---|---|
| `result` | `allow` · `deny`(401·403, 허용되지 않은 Host) · `error`(그 밖 4xx·5xx·예외) |
| `path` | 쿼리를 뺀 경로 |
| `ip` · `via` | `Cf-Connecting-IP`(Cloudflare 경유)가 있으면 그것, 아니면 연결 주소 · `cloudflare` / `hub`(중계로 들어온 작업 공간 서버) / `local` |
| `server` | `hub` 또는 작업 공간 폴더 이름 · `ws` = 중계 이름(`/w/<이름>/` 일 때) |
| `event` | 보안 이벤트 — `setup` `setup.denied` `login` `login.fail` `login.locked` `logout` `password.change` `password.fail` `users.add:<id>` `users.delete:<id>` `users.reset:<id>` `users.role:<id>` `users.denied` |
| `error` | 오류 메시지 요약(200자) |

비밀번호·쿠키·토큰·공유 비밀은 기록하지 않는다. 정적 파일과 2초 폴링(`/api/version/`·`/api/session`)의 **승인(allow)** 줄은 부피 때문에 기본으로 남기지 않는다(`accessLogStatic: true` 로 켠다). deny·error 는 항상 남는다.

## 사용자 설정(settings.json)

| 키 | 기본 | 내용 |
|---|---|---|
| `sessionDays` | 7 | 로그인 유지(마지막 사용 기준) |
| `publicHosts` | `[]` | Cloudflare 가 아닌 경로로 공개할 때 허용할 Host(`["slides.example.com"]`). Cloudflare 터널은 설정 없이 통과한다(`Cf-Ray`) |
| `accessLogDays` | 30 | 접근 로그 보관 일수 |
| `accessLogStatic` | false | 정적 파일·폴링의 승인 줄까지 남길지 |

## 밖에 열 때 권장

- 터널은 **허브 포트만** 가리키게 한다. 작업 공간 서버 포트는 열지 않는다.
- 한계: 허브는 `Cf-Ray`·`Cf-Connecting-IP` 같은 Cloudflare 헤더를 믿는다(브라우저는 사전 요청 때문에 이 헤더를 붙일 수 없다). 같은 PC 의 다른 프로그램은 이 헤더를 꾸며 로그의 IP 를 속이거나 주소 잠금을 피할 수 있다 — 로컬 프로세스는 어차피 사용자 설정 폴더의 계정 파일을 읽을 수 있으므로 위협 모델 밖이다.
- Cloudflare Access(또는 비슷한 앞단 인증)를 한 겹 더 두면 로그인 페이지 자체가 노출되지 않는다.
- 접근 로그의 `deny` 줄을 가끔 본다 — `login.fail`·`login.locked` 가 몰리면 비밀번호를 바꾼다.
- 허브 서비스를 다른 Windows 계정·시스템 서비스로 돌리면 사용자 설정 폴더가 그 계정의 것이 된다(계정·로그 위치가 달라진다).

## API

| 메서드 · 경로 | 설명 |
|---|---|
| `GET /api/auth/state` | `{mode:"hub", setup: 사용자 없음, user}` — 로그인 없이. `service.py`·`status.py` 의 허브 생존 확인에도 쓴다 |
| `POST /api/auth/setup` | `{id, password}` — 사용자가 하나도 없을 때만. 관리자로 만들고 로그인 |
| `POST /api/auth/login` | `{id, password}` → `{user, mustChange}` + 쿠키. 실패 401, 잠금 429 |
| `POST /api/auth/logout` | 세션 삭제, 쿠키 지움 |
| `GET /api/auth/me` | `{user: {id, role, mustChange}}` |
| `POST /api/auth/password` | `{current, new}` — 다른 기기 로그인은 끊고 이 기기는 새 세션 |
| `GET /api/auth/users` | (관리자) 사용자 목록 |
| `POST /api/auth/users` | (관리자) `{action: "add"\|"delete"\|"reset"\|"role", id, password?, role?}` |

`/api/config`·`/api/home` 응답에 `user: {id, role}` 이 들어간다(중계로 들어온 작업 공간 서버에서도).
