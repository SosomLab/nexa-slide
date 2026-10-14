# Claude Code 세션 연결

편집기에서 남긴 요청 메모를 Claude Code 세션이 **바로** 받아 처리하게 하는 방법이다.

> 작업 공간을 만든 직후의 연결 순서, Claude 가 아닌 AI 도구(Codex CLI·Gemini CLI·Cursor 등) 연결, 고치기 반복 과정은 [ai-editing.md](ai-editing.md).
> **웹 세션**(허브에서 [세션 시작] — 서버가 `claude -p` 를 턴마다 실행, 같은 규약·같은 파일·같은 표시)은 [dev/web-session-design.md](dev/web-session-design.md). 웹 세션이 살아 있으면 아래 수동 감시는 `{"event":"refused","reason":"web-session"}` 으로 거절된다(`--takeover` 로도 서버를 끊지 않는다) — 허브나 세션 칩에서 끊은 뒤 시작한다.

```
편집기 ──(요청 남기기 / 지금 보내기)──▶ decks/<id>.requests.json · out/.studio/flush.json
                                              │
                    watch_requests.py --stream (세션이 Monitor 로 실행, 1초마다 확인)
                       │  ├─ 하트비트 → out/.studio/session.json ──▶ /api/session ──▶ 편집기 "세션 연결됨"
                       │  └─ 요청 묶음 → JSON 한 줄 출력
                       ▼
               Claude Code 세션(알림) ──▶ status=working → 덱 JSON 수정 → status=done + reply
                                              │
                                     편집기가 2초 안에 덱·요청 다시 불러옴
```

## 1. 감시 시작 (세션에서)

Claude Code 의 **Monitor** 도구로 상시 스트림을 건다. 표준 출력 한 줄 = 알림 하나.

```
Monitor
  command:     python3 <엔진>/studio/watch_requests.py --workspace <작업 공간> --stream --takeover --label "<세션 이름>"
  description: nexa-slide 요청 (<작업 공간>)
  timeout_ms:  1800000          # 최대 30분 — {"event":"ttl"} 또는 만료 알림이 오면 같은 명령으로 다시 건다
```

실행기를 쓰는 저장소라면 `python3 <작업 공간>/nexa.py watch_requests --stream`.

- `--stream` 은 기본 **1780초(`--ttl`) 뒤 스스로 끝나며** `{"event": "ttl"}` 한 줄을 낸다. Monitor 가 만료되면 셸만 끝나고
  python 이 남아 하트비트만 쓰는 "가짜 연결"(편집기는 연결됨인데 요청이 어디에도 가지 않음)이 생기기 때문이다(Windows 실측).
- `--takeover`: 같은 작업 공간에 살아 있는 이전 감시(위와 같이 남은 것 포함)를 끝내고 넘겨받는다. 다시 걸 때 붙여 둔다.
- Monitor 를 쓸 수 없는 환경: 1회 모드(`--stream` 없이)를 Bash 백그라운드로 실행한다. 요청이 생기면 목록을 출력하고 끝나므로, 처리 후 다시 건다.
- 세션을 닫거나 Monitor 가 만료되면 하트비트가 끊겨 편집기에 몇 초 안에 "세션 연결 없음"이 뜬다. 그동안 남긴 요청은 파일에 남아 있다가 다음 감시 때 전달된다.

## 2. 이벤트 형식

```json
{"event": "requests", "reason": "quiet", "count": 2,
 "items": [{"deck": "ch00", "id": "r2026…", "slide": "s05", "element": "e03", "text": "표를 두 장으로"}]}
```

| reason | 언제 |
|---|---|
| `quiet` | 마지막 변경 뒤 `--quiet`초(기본 8) 동안 조용할 때 — 메모를 이어 남길 시간을 준다 |
| `flush` | 편집기 "지금 보내기" — 기다리지 않고 바로. 새 요청이 없으면 열린 요청 전체를 다시 보낸다 |

한 번 보낸 요청은 내용이 바뀌거나 다시 열릴(done → open) 때까지 다시 보내지 않는다.

요청 상태는 `draft`(편집기 초안 — 감시가 보내지 않음) → `open`(보냄) → `working` → `done`. 편집기 "요청 N개 보내기"가 초안을 open 으로 바꾸고 즉시 전달한다.
그리기 모드 요청에는 `region` 이 붙는다 — 슬라이드 좌표(1280×720): `{"kind": "rect", "box": [x, y, w, h]}` · `{"kind": "pen", "points": [[x, y], …], "box": [...]}` · `{"kind": "pin", "points": [[x, y]]}`.
영역 요청은 그 좌표와 겹치는 요소들을 대상으로 처리한다(`element` 는 null).
**후속 요청**(편집기 [후속 요청])이면 `parent`(바로 앞 요청 id)·`thread`(대화의 뿌리 요청 id)와 `context: [{id, status, text, reply, attachments?}…]` 가 붙는다 — 같은 대화의 앞선 요청·답이 오래된 순(최근 6개, 항목당 800자, 첨부는 경로만)이고 이번 요청은 항목 자신의 `text` 다. 대상(`slide`·`element`·`region`)은 따로 주지 않으면 원 요청에서 물려받는다. 앞선 요청의 상태는 바꾸지 않는다.

**첨부**가 있으면 `attachments: [{path, name, type, size}]` 가 붙는다 — 편집기에서 클립보드 그림(Ctrl+V)·끌어다 놓기·📎 로 올린 파일로, 작업 공간 안 `out/attach/<덱>/…` 에 있다(git 제외).
세션은 **먼저 Read 로 열어 본다**(그림은 내용을 보고, 글 파일은 읽어서) — 참고 디자인·캡처·손그림·자료. 그림을 슬라이드에 넣는 요청이면 `image` 요소의 `src` 에 그 경로를 그대로 쓴다.

## 3. 처리 규약 (세션이 지킬 것)

요청 1건마다:

1. `decks/<deck>.requests.json` 에서 그 요청의 `status` 를 **`working`** 으로 — 편집기에 "세션 처리 중"이 뜬다.
2. `decks/<deck>.json` 을 고친다.
   - **서버가 떠 있으면 `nexa.py save_deck <덱> --from <새 덱 파일> --request <요청 id> --note "…"` 로 저장한다** - 변경 원장에 "Claude(정확)" 로 남고
     백업·충돌 검사(409 = 편집기가 그 사이 저장함 → 다시 읽어 합치거나 `--force`)도 서버가 한다([change-ledger.md](change-ledger.md)).
     서버가 없을 때만 직접 쓴다(그때도 `save_deck` 이 원자적으로 쓰고 원장 줄을 남긴다). 파일을 직접 덮어쓰면 "Claude 추정" 또는 "외부" 로 기록된다.
   - 요소 `id` 는 유지.
   - 대상은 `slide`(슬라이드 id)·`element`(요소 id, 슬라이드 안에서 유일)로 찾는다.
   - 새 슬라이드는 `layouts.build_slide()` 로 만들어 끼우면 모양 규칙이 지켜진다.
   - 내용 원본을 함께 관리한다면 `content/<deck>.json` 에도 같은 변경을 옮긴다(다음 build 때 사라지지 않게).
3. 요청의 `status` 를 **`done`**, `reply` 에 무엇을 했는지 한두 문장.
4. 할 수 없거나 확인이 필요하면 `status` 는 `open` 그대로 두고 `reply` 에 질문을 적는다. **사용자에게 고르게 하거나 묻는 reply 면 `done` 으로 하지 않는다**(웹 세션은 질문으로 끝나는 reply 인데 `done` 이면 경고 이벤트를 남긴다). 사용자는 편집기 **[후속 요청]** 으로 답하고, 그 답은 아래 `context` 가 붙은 새 요청으로 온다.

요청 파일은 서버도 쓰므로, 읽고-고치고-쓰기 사이가 길지 않게 한다(편집기가 그사이 새 요청을 추가했을 수 있다 — 쓰기 직전에 다시 읽어 합친다).

## 4. 편집기 표시

| 위치 | 표시 |
|---|---|
| 머리줄 세션 칩 | 초록 "세션 연결됨" / 파랑 "세션 처리 중 n" / 회색 "세션 연결 없음". 마우스를 올리면 세션 이름·마지막 확인 시각·대기·처리 중 수 |
| 머리줄 "요청 보내기 (n)" | 열린 요청이 있을 때만 보인다 — 누르면 즉시 전달(flush) |
| 요청 탭 | 상태 칩 대기·처리 중·완료, Claude 답변, "지금 보내기 (n)" 버튼, 연결 여부 안내 |
| 썸네일 | 슬라이드별 열린 요청 수 · 내 편집이 아닌 변경 "변경 N" |
| 변경 탭 | 원장 - 세션이 바꾼 장·요소가 Claude 배지(정확/추정)와 요청 id 로 남는다 |

연결 판정: 하트비트가 `interval × 4 + 2`초(기본 6초) 안에 갱신되면 연결됨.

## 5. 웹 세션 — 서버가 세션을 띄운다

터미널을 열지 않고 **허브(시작 페이지)나 Studio 의 세션 칩에서 [세션 시작]** 을 누르면, 그 작업 공간 서버가 AI CLI(`claude` 또는 `codex`)를 **요청 묶음마다 한 턴씩** 실행해 위 규약 그대로 처리한다(`studio/wsession.py`, 설계 [dev/web-session-design.md](dev/web-session-design.md)).

| | 수동 세션(1~5절) | 웹 세션 |
|---|---|---|
| 시작 | 터미널에서 Claude Code 를 열고 Monitor 로 `watch_requests --stream` | 허브 최근 작업 [세션 시작] / Studio 세션 칩 ▾ → "웹 세션 시작…"(에이전트·모델 선택, 서버가 꺼져 있으면 허브가 먼저 띄움) |
| 요청 전달 | Monitor 알림 → 세션이 처리 | 서버가 같은 판정(`requests_core`)으로 묶음을 만들어 `claude -p`(stdin 프롬프트 = `studio/agents/turn_prompt.md` + 요청 JSON)를 실행 |
| 권한 | 작업 공간 `.claude/settings.json`(사람이 승인 창에서 판단) | 엔진 권한 템플릿(`agents/permissions.json` workspace+web)을 `--settings` 로, `--restricted --permission-mode dontAsk` — 작업 공간 안 Read/Edit/Write 와 `python3 nexa.py …` 만. 물음은 모두 거절. **웹 검색**은 기본 막힘 — 관리자가 전역 `sessionAllowWeb` 을 켜고 시작 창에서 "이 세션에 웹 검색 허용"을 고른 세션(claude 만)에서만 `WebSearch`·`WebFetch` 가 열린다(칩·세션 줄에 "웹 허용", 접근 로그 `session.start:…:web`, 턴 로그에 요청 URL). 그 세션의 턴 프롬프트에는 출처 URL 기록·수집 자료는 작업 공간 **루트** `research/<주제>.md`(`content/` 안이 아님 — 거기는 덱 원본) 보관·검색어에 내부 정보 금지 규칙이 덧붙는다. **git·저장소 루트**도 같은 틀 — 전역 `sessionAllowGit`·`sessionAllowPush`·`sessionRepoRoot` 를 켜고 시작 창에서 고른 세션만 git 기록(`add`·`commit`·`switch`·`merge`…)·push·저장소 루트 문서 읽기·쓰기(`--add-dir`)가 열린다. 강제 push·`reset --hard`·`clean`·`rebase`·`config`·`remote`·`git -C`·`restore` 등은 켜도 거절. 커밋 작성자는 이 PC 의 git 사용자, 메시지 끝에 `Requested-by: <세션 시작 사용자>` 트레일러. git 이 대화형으로 묻지 않게 `GIT_TERMINAL_PROMPT=0`·`GCM_INTERACTIVE=never`·`GIT_MERGE_AUTOEDIT=no` |
| 저장 | `save_deck` | 같다 — `draft_deck`(사본+줄 번호) → Edit → `save_deck --from`. 원장 `actor.user` = 세션을 시작한 사용자 |
| 표시 | 칩 "세션 연결됨" | 칩 "웹 세션 · 모델 · 사용자", 칩 메뉴의 진행 패널(SSE: 턴 시작·도구·글·턴 끝·경고), 턴 로그, 모델 바꾸기(실행 중이면 턴이 끝난 뒤), 세션 중지 |
| 끝 | 세션 종료·Monitor 만료 | [세션 중지]·유휴 `sessionIdleMinutes`(60분)·서버 종료 — 실행 중 턴의 프로세스 트리까지 끝낸다. 턴 한도 `sessionTurnMinutes`(20분) |
| 함께 쓰기 | 웹 세션이 살아 있으면 `watch_requests` 는 `{"event":"refused","reason":"web-session"}` (`--takeover` 로도 서버를 끊지 않는다) | 수동 감시가 살아 있으면 시작을 거절한다 |

- 처리하지 못한 요청은 서버가 `open` 으로 두고 `reply` 에 "세션이 처리하지 못했습니다: <사유>" 를 적는다(침묵 실패 없음).
- 로그: `out/.studio/sessions/<시작 시각>/turn-N.jsonl`(CLI 출력 원문)·`session.log`, 접근 로그 `event=session.*`. 이 PC 의 동시 웹 세션 수는 `sessionMax`(3).
- 서비스 유형 `codex` 는 [openai-codex.md](openai-codex.md) 5절(미확인). 설치·로그인은 [claude-install.md](claude-install.md).

## 6. 여러 작업 공간 · 여러 세션

- **작업 공간 하나 = 감시 하나 = 세션 하나.** 각 저장소(폴더)에서 연 Claude 세션이 자기 작업 공간의 감시를 띄운다.
  세션의 작업 폴더·규칙·git 이 그 저장소라서 요청 처리와 커밋이 제자리에 남는다.
- 같은 작업 공간에 살아 있는 감시가 있으면 새 감시는 시작하지 않고 한 줄을 낸 뒤 끝난다(같은 요청이 두 세션에 가지 않게):
  `{"event": "refused", "reason": "already-watched", "pid": …, "label": "…", "last_seen": "…"}` — 다른 세션이 맡고 있다는 뜻. 꼭 넘겨받아야 하면 `--force`.
- 다른 작업 공간(다른 저장소·다른 포트)은 각자 감시를 띄우면 된다 — 상태 파일(`out/.studio/`)이 작업 공간마다 따로 있다.
