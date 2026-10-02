# Claude Code 세션 연결

편집기에서 남긴 요청 메모를 Claude Code 세션이 **바로** 받아 처리하게 하는 방법이다.

> 작업 공간을 만든 직후의 연결 순서, Claude 가 아닌 AI 도구(Codex CLI·Gemini CLI·Cursor 등) 연결, 고치기 반복 과정은 [ai-editing.md](ai-editing.md).

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

## 3. 처리 규약 (세션이 지킬 것)

요청 1건마다:

1. `decks/<deck>.requests.json` 에서 그 요청의 `status` 를 **`working`** 으로 — 편집기에 "세션 처리 중"이 뜬다.
2. `decks/<deck>.json` 을 고친다.
   - 파일 전체를 다시 쓰되 **원자적 쓰기**(임시 파일 → 교체), 요소 `id` 는 유지.
   - 대상은 `slide`(슬라이드 id)·`element`(요소 id, 슬라이드 안에서 유일)로 찾는다.
   - 새 슬라이드는 `layouts.build_slide()` 로 만들어 끼우면 모양 규칙이 지켜진다.
   - 내용 원본을 함께 관리한다면 `content/<deck>.json` 에도 같은 변경을 옮긴다(다음 build 때 사라지지 않게).
3. 요청의 `status` 를 **`done`**, `reply` 에 무엇을 했는지 한두 문장.
4. 할 수 없거나 확인이 필요하면 `status` 는 `open` 그대로 두고 `reply` 에 질문을 적는다(사용자가 답을 `text` 에 덧붙이면 내용이 바뀌어 다시 전달된다).

요청 파일은 서버도 쓰므로, 읽고-고치고-쓰기 사이가 길지 않게 한다(편집기가 그사이 새 요청을 추가했을 수 있다 — 쓰기 직전에 다시 읽어 합친다).

## 4. 편집기 표시

| 위치 | 표시 |
|---|---|
| 머리줄 세션 칩 | 초록 "세션 연결됨" / 파랑 "세션 처리 중 n" / 회색 "세션 연결 없음". 마우스를 올리면 세션 이름·마지막 확인 시각·대기·처리 중 수 |
| 머리줄 "요청 보내기 (n)" | 열린 요청이 있을 때만 보인다 — 누르면 즉시 전달(flush) |
| 요청 탭 | 상태 칩 대기·처리 중·완료, Claude 답변, "지금 보내기 (n)" 버튼, 연결 여부 안내 |
| 썸네일 | 슬라이드별 열린 요청 수 |

연결 판정: 하트비트가 `interval × 4 + 2`초(기본 6초) 안에 갱신되면 연결됨.

## 5. 여러 작업 공간 · 여러 세션

- **작업 공간 하나 = 감시 하나 = 세션 하나.** 각 저장소(폴더)에서 연 Claude 세션이 자기 작업 공간의 감시를 띄운다.
  세션의 작업 폴더·규칙·git 이 그 저장소라서 요청 처리와 커밋이 제자리에 남는다.
- 같은 작업 공간에 살아 있는 감시가 있으면 새 감시는 시작하지 않고 한 줄을 낸 뒤 끝난다(같은 요청이 두 세션에 가지 않게):
  `{"event": "refused", "reason": "already-watched", "pid": …, "label": "…", "last_seen": "…"}` — 다른 세션이 맡고 있다는 뜻. 꼭 넘겨받아야 하면 `--force`.
- 다른 작업 공간(다른 저장소·다른 포트)은 각자 감시를 띄우면 된다 — 상태 파일(`out/.studio/`)이 작업 공간마다 따로 있다.
