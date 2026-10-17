# 설계 메모 — 보기 전용 공유 링크 (협업 세션 정리, 2026-10-17)

> 엔진 요청 큐에 넣은 항목의 근거 자료. "결정" 표시가 없는 것은 **제안**이다 — 개발 세션이 다르게 판단하면 이유를 남기고 바꾼다.
> 후보 출처: `docs/dev/feature-comparison.md:71-73,149`, `docs/dev/web-session-design.md:280`.

## 1. 요구사항

- 로그인 없이 토큰 URL 하나로 **덱 1개를 보기만** 한다(외부 검토자·청중).
- 만료 필수, 비밀번호 선택, 만든 사람·관리자가 회수.
- 편집·요청·세션·내보내기 같은 쓰기는 전부 막는다. 발표자 노트는 보이지 않는다.

## 2. 지금 구조 (조사 결과)

| 항목 | 위치 |
|---|---|
| 허브·작업 공간 서버 모두 `server.py` 의 `H` — `dispatch`(`:437`) → `host_ok` → hub-key 검사(`:441-447`) → 허브면 `authenticate`(`:456`) → `_route`(`:537`) | `studio/server.py` |
| 로그인 면제는 `AUTH_FREE`(`:372`) **정확히 일치만** — 접두 매칭 없음 | |
| 역할은 `admin`·`user` 뿐, viewer 없음 | `auth.py:126,165` |
| 세션 토큰: `secrets.token_urlsafe(32)`, 파일엔 sha256 만(`_tok_hash` `auth.py:232`), 비밀번호 scrypt, 실패 잠금 `_FAILS`(`auth.py:178-202`) | `studio/auth.py` |
| 중계 `/w/<ws>/…` → `proxy()`(`server.py:578-633`), `authenticate` **뒤**에 실행 — 정적 파일까지 로그인 필요. 대상은 `hub.proxy_target`(`hub.py:627`)·`ws_by_id`(`hub.py:73`, 사용자 설정 `recent` 에서만) | |
| 중계 시 `X-Nexa-*` 제거 후 `X-Nexa-Hub-Key`·`User`·`Role` 부착(`server.py:595-601`) | |
| 보기 페이지: `presenter.html`(노트 포함), `print.html`(`layout=notes…`), `slide.html`(한 장) — 모두 GET 만. Studio 에는 읽기 전용 모드 없음 | `studio/` |
| 덱 JSON(`/api/deck/<id>`)에 `notes` 가 그대로 있다 | |
| `api_get_fontcss`(`server.py:1816-1841`)가 접두 없는 `url("/wsfonts/…")` 를 낸다 — 중계·공유 경로에서 허브로 새는 문제(미검증) | |
| 접근 로그: `auth.log_access` ← `H.access_log`(`server.py:516-534`), 이벤트는 핸들러가 `self._event` 에 넣는다 | |

## 3. 설계 결정(제안)

1. **저장**: 사용자 설정 폴더 `hub/share.json`(users.json 과 분리 — 수명·회수 단위가 다르다, 백업 대상에 추가).
   `{links:{<id>:{tokenHash, ws(작업 공간 경로), wsId, deck, by, created, expires, pw:{hash,salt}|null, revoked:null|{by,t}, views, lastView}}}`.
   토큰 원문은 만들 때 한 번만 보여 주고 sha256 만 저장(세션과 같은 방식). 파일 잠금은 `filelock.py`.
2. **주소**: 허브 `/s/<토큰>/` — `AUTH_FREE` 에 접두 규칙 `/s/` 를 추가(`authenticate` 전 분기). 토큰 검증 → 만료·회수 확인 → (비밀번호 있으면) 쿠키 `nexa_share` (`Path=/s/<토큰>/`, HttpOnly, SameSite=Lax, 만료=링크 만료와 세션 7일 중 짧은 쪽).
3. **열어 주는 페이지**: 새 `studio/view.html` — 전체 화면 슬라이드 넘기기(키보드·터치·쪽 번호), 노트·편집 UI 없음, `render.js` 재사용. 발표자 보기·Studio 는 열지 않는다. (선택) 링크 옵션 `allowPdf` 일 때 PDF 받기 — 이미 만든 `out/<deck>.pdf` 만, 새로 만들지 않음.
4. **중계와의 관계**: `/s/<토큰>/…` 는 허브가 **허용 목록**만 해당 작업 공간 서버로 중계(기존 `proxy()` 재사용, 사용자 헤더는 `X-Nexa-User: share:<id>`, `X-Nexa-Role: viewer`).
   허용 목록(GET 만): `view.html`·`render.js`·`i18n*.js`·`tokens.json`·`code_langs.json`·`fonts.css`, `/api/deck/<그 덱>`(응답에서 `notes`·`hidden` 슬라이드 제거는 **허브에서** 걸러 낸다), `/api/fontcss`·`/api/fontfile/*`·`/wsfonts/*`, 덱이 참조하는 에셋 경로. 그 밖 경로·모든 POST/PUT 은 403.
   `fontcss` 의 절대 경로는 `X-Forwarded-Prefix` 를 읽어 접두를 붙이도록 고친다(지금 보내기만 하고 읽는 곳 없음 — `/w/` 중계도 같이 좋아진다).
5. **만들기·회수 UI**: Studio 머리줄 내보내기 ▾(`exportMenu` `studio.js:1156`) 아래 "공유 링크…" → 대화상자(만료 1/7/30일·직접, 비밀번호, PDF 허용, 만들기 → 링크 복사; 아래에 이 덱의 링크 목록·[회수]). 허브 경유(로그인 사용자)일 때만 보인다. 관리자는 `account.html` 에 "공유 링크" 카드(전체 목록·회수).
   API(허브): `GET/POST /api/share`(목록·만들기), `POST /api/share/<id>`(revoke). 만들기는 로그인 사용자 누구나, 회수는 만든 사람·관리자 — **정책 확인 필요**(아래 6).
6. **만료 한도**: 기본 7일, 최대 `shareMaxDays`(전역 설정, 기본 90). 영구 링크 없음.
7. **접근 로그 이벤트**: `share.create:<id>`, `share.revoke:<id>`, `share.view:<id>`(페이지 열 때 1회, `views` 증가), `share.auth.fail:<id>`, `share.denied:<id>:<사유 expired|revoked|path|method>`. 토큰 원문은 로그에 남기지 않는다(`docs/auth.md:101`) — 경로도 `/s/<id>` 로 바꿔 적는다.
8. **비밀번호 실패 잠금**: `_FAILS` 를 링크 id 키로 재사용(5회/15분).

## 4. 완료 기준

- 로그인 없이 `/s/<토큰>/` 로 덱이 보이고, 노트·숨김 슬라이드가 응답에 없다.
- 만료·회수 뒤 410(또는 안내 페이지), 잘못된 토큰 404 — 존재 여부를 구분해 흘리지 않는다(둘 다 같은 안내).
- 허용 목록 밖 GET·모든 쓰기 403, 같은 토큰으로 다른 덱·다른 작업 공간 접근 불가.
- 글꼴이 공유 경로에서 실제로 적용된다(허브로 새지 않음).
- 문서: `docs/auth.md` 공유 링크 절, `docs/editor.md` 대화상자, `server-admin.md` 회수·로그. i18n(ko/en).

## 5. 시험

- `studio/tests/share_test.py`(가칭): 임시 사용자 설정 폴더 + example 작업 공간으로 허브를 띄워 — 만들기→열람(200, notes 없음)→허용 밖 경로·POST 403→비밀번호 오답 5회 잠금→회수 뒤 거부→만료(시계 주입) 거부.
- 접근 로그에 토큰 원문이 없는지 grep.
- 수동: 시크릿 창에서 링크 열기, 휴대폰 폭 확인.
