# 변경 원장 - 누가 언제 어느 장을 바꿨나

0.16.0 부터 서버는 덱 파일 `decks/<덱>.json` 에 일어난 **모든 쓰기**를 덱당 추가 전용 원장에 한 줄씩 남긴다. 편집기의 **변경** 탭은 그 원장을 보여 주는 화면이다.
원장은 작업 공간(슬라이드를 만드는 폴더·저장소) 안에 있고 엔진에는 아무것도 남지 않는다.

```
decks/.history/<덱>/changes.jsonl     원장 - 한 줄 = 한 변경. 덱당 최근 1,000건(설정 ledger.keep)
decks/.history/<덱>/<시각>.json        편집기 저장 직전 백업(기존)        ┐
decks/.history/<덱>/<시각>-build.json  build 덮어쓰기 직전 백업(기존)      ├ 합쳐 최근 50개
decks/.history/<덱>/<시각>-ext.json    밖에서 바뀌기 직전 상태(0.16.0 추가) ┘
out/.studio/ledger-<덱>.lock           교차 프로세스 잠금(서버 · build_deck · save_deck). 내용 없음
```

`.history/` 는 작업 공간 `.gitignore` 에 있으므로 원장도 git 에 들어가지 않는다. 장기 보관을 대신하지 않는다 - 덱 JSON 자체를 git 으로 관리한다.

## 기록 탭과 변경 탭

| | 기록 탭 | 변경 탭 |
|---|---|---|
| 근거 | 백업 파일 50개 | 원장 1,000건 |
| 담는 것 | 그 시점 덱 파일 전체 | 장·요소 단위로 무엇이 바뀌었나 + 누가(출처) |
| 보존 | 50개가 돌면 사라진다 | 백업이 사라진 뒤에도 "글자 전→후 60자" 요약이 남는다 |
| 되돌리기 | 가능 | 그 변경 직전 백업이 남아 있을 때만("직전으로") |

0.15.3 까지 변경 탭은 브라우저 메모리(최근 30건, 화면을 연 동안)뿐이라 어제 변경이 보이지 않았고, 편집기 자신의 저장은 어디에도 diff 로 남지 않았다.

## 출처(origin) 네 가지

| 배지 | origin | 뜻 | 확신도 |
|---|---|---|---|
| 편집기(초록) | `editor` | 편집기 저장. **이 창**("나")과 **다른 창**을 탭 id 로 구분 | exact |
| Claude(파랑) | `claude` | Claude 세션이 `save_deck` 으로 서버에 저장 | exact |
| Claude 추정(파랑 점선) | `claude` | 세션이 파일을 직접 썼는데 세션이 연결돼 있고 처리 중(`working`) 요청이 있거나 작업 중 | inferred - 툴팁에 근거 |
| 빌드(호박) | `build` | `build_deck --force` | exact |
| 외부(회색) | `external` | 어느 것도 아님(파일 수동 복사 등) · 서버가 꺼진 사이의 변경(`startup`) | unknown |

추정은 정황 증거다. 세션이 `working` 인 동안 사람이 파일을 복사하면 "Claude 추정" 으로 적힌다. 원장은 고치지 않고 표시로 알린다. Claude 세션이 `save_deck` 을 쓰면 추정 자체가 줄어든다 - [claude-session.md](claude-session.md) §3.

### 출처 판정

```
PUT /api/deck 로 들어왔나?
├─ 예 → origin = ?origin (editor | claude), exact
└─ 아니오 (2초 폴링에서 파일이 바뀐 것을 발견, 1.5초 유예 뒤에도 원장 꼬리에 같은 해시의 줄이 없음)
   ├─ 세션 연결됨 + 그 덱에 working 요청 → claude, inferred (요청 id · 세션 라벨 · 하트비트 나이를 evidence 에)
   ├─ 세션 연결됨 + 감시 세션이 작업 중(activity) → claude, inferred
   ├─ 다른 Claude 세션이 작업 중(othersBusy)   → claude, inferred
   └─ 그 밖                                   → external, unknown
```

파일 변경은 mtime 이 아니라 **(mtime_ns, size) 서명 → sha256** 으로 판정한다. mtime 만 바뀐 것(touch·동기화)은 기록하지 않는다(`ledger.recordTouch: true` 면 `touch` 줄).
유예 1.5초는 build·save_deck 이 덱을 쓴 뒤 자기 줄을 더하기 전에 폴링이 끼어드는 것을 막는다. 서버가 꺼진 사이의 변경은 다음 기동 때 한 줄(`startup`)로 요약된다 - 직전 상태를 담은 백업이 있으면 상세, 없으면 상세 없음.

## 변경 탭

- **필터** 전체 · 내 편집 · 다른 창 · Claude · 빌드 · 외부(선택은 브라우저에 기억).
- **최근 수정 대상** - 슬라이드별로 마지막에 그 장을 건드린 변경 한 건(출처·상대 시각·종류). 누르면 그 장으로.
- **묶음 목록** - 같은 출처·같은 창에서 60초(`ledger.groupGap`) 안에 이어진 저장은 한 묶음("저장 N회(요약)"). 빌드·되돌리기·외부 변경·요청 전환은 경계. 장마다 수정·추가·삭제·이동(순서 a → b), 요소마다 글자·위치·크기·모양·그림·추가·삭제와 글자 전 → 후.
- **직전으로** - 그 변경 직전 백업으로 되돌린다(`action: restore` 로 원장에 남고 Ctrl+Z 가능). 백업이 50개 상한으로 지워졌으면 비활성.
- **표시** - 내 편집이 아닌 변경은 썸네일 "변경 N" 배지 · 개요 배지 · 캔버스 파란 점선. "표시 지우기" 가 지금까지를 확인한 것으로 기억(브라우저별)하고 **"모두 다시 표시"** 로 되돌린다. 묶음마다 **숨기기/표시** - 내 편집 묶음도 "표시" 를 누르면 점선으로 보인다(기본은 표시 안 함).
- 비교 규칙은 서버 `studio/deckdiff.py` 한 곳. 키 순서만 다른 같은 객체와 `1` 대 `1.0` 은 변경으로 보지 않는다(0.15.3 JS 와 다른 점 - 가짜 변경 제거).

## 설정 (`nexa-slide.json`)

```json
"ledger": {"keep": 1000, "groupGap": 60, "recordTouch": false}
```

| 키 | 기본 | 뜻 |
|---|---|---|
| `keep` | 1000 | 덱당 보존 줄 수(최소 50). `keep + 100` 을 넘으면 최근 `keep` 줄만 남기고 압축. `seq` 는 다시 매기지 않는다 |
| `groupGap` | 60 | 묶음 간격 초(15~600) |
| `recordTouch` | false | 내용이 같고 mtime 만 바뀐 것도 `touch` 줄로 남길지 |

## 원장 줄 형식 (v1)

```json
{"v":1,"seq":412,"ts":"2026-10-14T09:12:33.481+09:00","deck":"ch03","kind":"change",
 "origin":"claude","confidence":"inferred","action":"detect",
 "actor":{"label":"sql-tutorial 세션","tab":null,"request":"r20261014091201123","note":null},
 "evidence":{"heartbeat_age_s":0.8,"working":["r20261014091201123"],"watcher_state":"busy"},
 "before":{"ver":"1791938640147489500","size":48213,"hash":"sha256:…","backup":"20261014-091233-481099-ext.json"},
 "after":{"ver":"1791938655012345600","size":48502,"hash":"sha256:…"},
 "summary":{"수정":1,"추가":0,"삭제":0,"이동":0},"fields":[],
 "items":[{"sid":"s12","idx":11,"kind":"수정","moved":null,"title":"정규화 3단계",
           "els":[{"id":"t2","kinds":["글자"],"before":"제2정규형까지","after":"제3정규형까지"}],"extra":["노트"]}]}
```

- `kind` change · touch. `action` save · restore · build · detect(폴링에서 발견) · startup(기동 재대조).
- `before.hash` → `after.hash` 가 다음 줄로 이어지지 않으면 원장이 모르는 변경이 있었다는 뜻이다(기동 재대조가 메운다).
- `fields` 는 장 밖(덱 수준) 키 변경(title · fontPreset 등). `items` 는 요소 200개까지(`truncated`). `items: null` 은 직전 상태를 몰라 상세가 없다는 뜻.
- 읽을 때 모르는 필드는 무시하고 없는 필드는 기본값으로 본다. 찢어진 마지막 줄(전원 장애)은 버린다.

## API

| 메서드 · 경로 | 설명 |
|---|---|
| `PUT /api/deck/<id>?origin=editor\|claude&action=save\|restore&request=&note=&label=` + 헤더 `X-Nexa-Tab` | 기존 `base`·`force` 그대로. 응답 `{ok, version, updated, seq}`. 내용이 같으면 `seq: null` |
| `GET /api/version/<id>` | 응답에 `changes`(원장 파일 버전). 이 호출이 밖에서 바뀐 덱을 발견·기록한다 |
| `GET /api/changes/<id>` | `?limit=50&before=<seq>&since=<seq>&origin=editor,claude&slide=<sid>` → `{entries[…, backupExists], latest, keep, more}` |
| `GET /api/changes/<id>?group=1&recent=1` | 묶음 `groups[{seq, last, ts, ts_end, origin, confidence, actor, count, approx, summary, items, backup, backupExists}]` + 슬라이드별 최근 `recent[{sid, title, idx, exists, kind, kinds, seq, ts, origin, confidence, actor}]` |
| `GET /api/changes/<id>?seq=N` | 한 줄 |
| `GET /api/history/<id>` | 종류에 `ext` 추가 |

## Claude 세션 - `save_deck`

```bash
python3 <작업 공간>/nexa.py save_deck <덱> --from <새 덱 JSON> [--request <요청 id>] [--note "한 줄"] [--label "<세션 이름>"] [--force]
```

서버가 떠 있으면 `GET /api/deck` 의 `X-Deck-Version` 을 `base` 로 `PUT …?origin=claude` 를 보낸다 - 백업·충돌 검사(409)·원장 기록을 서버가 한다. 409 면 편집기가 그 사이 저장한 것이니 다시 읽어 합치거나 `--force`.
서버가 없으면 직접 백업·원자적 쓰기 후 원장에 `claude · exact` 줄을 남긴다. 종료 코드 0 저장 · 2 충돌 · 1 오류.

## 운용

- 원장을 지우려면 `changes.jsonl` 을 지우면 된다(다음 쓰기부터 seq 1). 백업과 독립이다.
- 다른 PC 로 작업 공간을 복사하면 원장도 따라간다(`.history` 를 함께 복사했을 때). 서버는 기동 때 마지막 줄과 파일을 맞춰 본다.
- 잠금을 5초 안에 얻지 못하면 그 저장은 원장 없이 끝나고 서버 로그에 남는다(덱 저장 자체는 성공). 다음 기동 재대조가 메운다.
- OneDrive 등 동기화 폴더에서는 mtime 만 바뀌는 일이 잦다 - 해시가 같으면 기록하지 않으므로 영향 없다.
- 검증 도구: `python3 studio/check_changes.py`(비교 규칙 golden 33건 + 속성 검사 3,000회), `--js` 로 0.15.3 JS 기준과 대조.

설계 근거와 선례는 [research/change-ledger-design.md](research/change-ledger-design.md), 개발 과정은 [dev/0.16.0-change-ledger.md](dev/0.16.0-change-ledger.md).
