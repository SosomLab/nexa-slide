# 변경 탭을 서버 원장으로 키우는 0.16.0 설계

편집기의 "변경" 탭이 어제 바뀐 내용을 보여 주지 못하는 이유는 그 기록이 **브라우저 메모리에만, 최근 30건, 화면을 연 동안만** 남기 때문이다(`studio/studio.js:152-153`, `198-205`). 보존하려면 서버가 덱 파일의 모든 쓰기를 **덱당 추가 전용 원장 `decks/.history/<덱>/changes.jsonl`** 에 한 줄씩 적고(기본 1,000건, `nexa-slide.json` 으로 조정), 편집기는 그 원장을 받아 기존 변경 탭 자리에 그리면 된다. 원장의 한 줄은 "누가(출처 editor/claude/build/external + 확신도) · 언제 · 어느 백업에서 어느 버전으로 · 장과 요소 단위로 무엇을" 바꿨는지를 지금 JS `diffDeck` 이 만드는 항목 모양 그대로 담는다. 출처는 네 지점에서 적는다 - 편집기 저장은 `PUT /api/deck` 안에서 정확히, Claude 세션은 새 CLI `save_deck.py` 로 같은 PUT 을 타면 정확히, 파일을 직접 썼으면 서버가 2초 폴링에서 발견해 하트비트·`working` 요청으로 "Claude(추정)" 로 귀속하고, 어느 것도 아니면 "외부" 로 남긴다. 비교 로직은 Python 으로 1:1 이식해 서버 한 곳에서만 돌리고, 이식 시점에 현 JS 출력으로 만든 golden fixture 로 동일성을 못 박은 뒤 JS 쪽 diff 는 제거한다. 변경 탭에는 출처 필터·"최근 수정 대상" 표·묶음 목록·백업 복원 버튼이 들어가고, 기록 탭(백업 50개 목록)은 그대로 둔다. 아래는 이 설계를 바로 구현할 수 있는 수준의 스키마·결정 트리·API·화면·순서·검증·위험이다. 코드 사실의 `file:line` 은 nexa-slide 0.15.3(커밋 `dbeed11`, 조사용 워크트리 `D:\Projects\kiros33\_wt\nexa-slide-ledger`) 기준이며 경로를 생략한 파일은 `studio/` 아래다.

## 지금 변경 탭은 메모리 30건이고 기록 탭은 백업 50개다

사용자 요구 ①의 답은 코드에 그대로 있다. 변경 탭의 기록은 `S.changes` 배열이고, 주석이 설계 의도를 "기록은 이 화면을 연 동안만 유지(최근 30건)" 라고 밝힌다(`studio.js:152-153`). `recordChange()` 는 `S.changes.unshift(rec); S.changes.length = Math.min(S.changes.length, 30)` 으로 30건을 넘기면 자르고, 시각은 `new Date().toTimeString().slice(0, 8)` 즉 날짜 없는 `HH:MM:SS` 만 남긴다(`studio.js:198-205`). 브라우저를 새로 고치거나 다른 날 열면 `S.changes` 는 빈 배열에서 시작하므로 **어제 변경은 구조적으로 보일 수 없다**. 기록이 생기는 경로도 하나뿐이다 - 2초 폴링 `poll()` 이 `/api/version` 의 `deck`(파일 `st_mtime_ns`) 과 `S.version` 이 다르고 내 편집이 없을 때 `reloadExternal()` 을 불러 옛 덱 복제본과 새 덱을 `diffDeck` 으로 비교한다(`studio.js:136-150`, `220-227`). 그러니 편집기가 닫혀 있던 사이에 Claude 나 build 가 바꾼 것은 전·후 비교 대상(옛 덱)이 없어 처음부터 기록되지 않는다.

요구 ②의 범위 차이도 명확하다. 기록 탭은 서버 `api_get_history` 가 `decks/.history/<id>/*.json` 을 이름 역순으로 나열한 **파일 단위 백업 목록**이고, 종류는 파일명 끝이 `-build` 면 `build`, 아니면 `save` 두 가지다(`server.py:474-490`). 백업은 편집기 `PUT` 때 서버가 덮어쓰기 직전 파일을 `copy2` 로 복사하고(`server.py:117-126`), build 가 덮어쓰기 전에 `-build.json` 으로 복사하는(`build_deck.py:170-173`) 것이라 **"무엇이 바뀌었는지" 는 없고 "그 시점 파일 전체" 만 있다**. 반면 변경 탭은 **밖에서 바뀐 것만** 장·요소 단위 diff 로 보여 주되 복원은 못 한다. 둘을 합치면 "편집기 저장·build 는 기록 탭에, 외부 변경은 변경 탭에, 사용자 자신의 편집은 어디에도 diff 로 남지 않는다" 가 현재 상태다.

| | 기록 탭 (0.15.3) | 변경 탭 (0.15.3) | 변경 탭 (0.16.0 제안) |
|---|---|---|---|
| 근거 | `.history/<덱>/*.json` 백업 파일 | 메모리 `S.changes` | `.history/<덱>/changes.jsonl` 원장 |
| 담는 변경 | 편집기 저장 전 · build 전 스냅샷 | 편집기가 열려 있을 때 밖에서 바뀐 것 | 편집기 저장 · Claude · build · 외부 전부 |
| 단위 | 파일 전체 | 장 · 요소 (글자 전→후 60자) | 장 · 요소 (같은 모양) + 출처 · 확신도 |
| 보존 | 50개 (`HISTORY_KEEP`, `server.py:74`) | 30건, 새로 고치면 소멸 | 덱당 1,000건 (설정), 재시작 후 유지 |
| 복원 | 가능 (`onHistClick`, `studio.js:1035-1042`) | 불가 | 백업이 남아 있는 항목은 가능 |
| 출처 | save / build 두 종류 | 없음("밖에서") | editor / claude / build / external + 확신도 |

백업 50개 상한을 유지하기로 했으므로, 원장은 **백업이 지워진 뒤에도 "무엇이 바뀌었는지" 요약이 남는 유일한 장소**가 된다. 실측으로 교재 작업 공간 `ppt/decks/.history/ch00/` 은 정확히 50개 파일이고 가장 오래된 것이 `20260930-114855-321101-build.json` 이라 ch00 은 약 2주치 백업만 남아 있다 - 자동 저장이 잦은 날에는 하루 안에 50개가 돌 수 있으니, "어제 변경" 의 보존 책임은 원장이 진다.

## 선례가 가리키는 다섯 가지 설계 원칙

성숙한 편집기들은 이 문제를 비슷한 모양으로 풀었다. 첫째, **한 시간축에 출처 필터**다. VS Code Timeline 은 Git 커밋과 로컬 저장을 한 목록에 두고 툴바 필터로 소스를 전환한다 ([VS Code Docs](https://code.visualstudio.com/docs/getstarted/userinterface)). 둘째, **빠른 자동 저장은 묶는다**. VS Code 로컬 기록은 `workbench.localHistory.mergeWindow` 10초 안의 변경을 마지막 항목에 병합하고 파일당 50개를 남기며 ([VS Code Docs](https://code.visualstudio.com/docs/getstarted/userinterface)), Notion 은 활성 편집 중 10분마다·마지막 편집 2분 뒤 버전을 만들고 ([Notion Help](https://www.notion.com/help/duplicate-delete-and-restore-content)), Google Docs 는 수정본을 "때때로 병합" 하되 이름 붙인 버전은 병합하지 않는다 ([Google Docs Help](https://support.google.com/docs/answer/190843)). Excel Show Changes 는 대량 편집을 카드 한 장으로 접고 "See changes" 로 펼친다 ([Microsoft Support](https://support.microsoft.com/en-us/office/show-changes-that-were-made-in-a-workbook-978ceea7-bbf6-4337-bca7-22e7cc9892e8)). 셋째, **사람과 자동화는 시각적으로 구분하고 색은 고정**한다 - Word 의 작성자 색이 열 때마다 바뀌는 것은 반대 교훈이다 ([Microsoft Support](https://support.microsoft.com/en-au/office/change-the-track-changes-color-48c80bb3-458c-4abb-8e21-25f9bac47484)), 활동 피드 가이드는 actor-동사-대상-시각 문형과 전/후 값, 사람 대 시스템 이벤트의 구분을 권한다 ([saasui.design](https://www.saasui.design/blog/saas-activity-feed-audit-log-ux-patterns)). 넷째, **AI 표기는 실제로 AI 가 쓴 변경에만** 붙인다. VS Code 가 `git.addAICoAuthor` 기본값을 all 로 바꿨다가 반발로 off 로 되돌린 사례가 그 근거다 ([microsoft/vscode #314311](https://github.com/microsoft/vscode/issues/314311)). 다섯째, **"만든 주체" 와 "적용 경로" 를 분리**한다 - Git 이 author 와 committer 를 나누는 것처럼 ([Pro Git 2.3](https://git-scm.com/book/en/v2/Git-Basics-Viewing-the-Commit-History)), "Claude 세션이 요청 r20261014… 을 처리해 서버 PUT 으로 저장했다" 와 "build 가 content 에서 덱을 재생성했다" 는 다른 축의 정보다.

슬라이드 편집기에 가장 직접 대응하는 선례는 PowerPoint 의 "수정된 슬라이드 썸네일 파란 점 + 개체 색 테두리 + 재열기 배너" 로, 기준점이 "내가 마지막으로 연 이후" 다 ([Microsoft Support](https://support.microsoft.com/en-au/office/see-revisions-made-by-other-people-be85ca29-5e57-405b-b9e3-ed8b5289d1a0)). 현재 nexa-slide 의 썸네일 배지·개요 배지·캔버스 점선 세 소비자(`studio.js:309`, `1022`, `419-420`)가 이미 같은 구조이므로, 원장 도입 뒤에도 이 세 곳은 `chgOf(sid)` 가 `undefined | Set<요소 id>` 를 돌려 준다는 계약만 지키면 수정 없이 동작한다. 외부 변경을 전용 라벨로 구분하는 공식 UI 는 JetBrains·VS Code 문서에 없고(JetBrains 는 "IDE 안·밖 변경을 모두 기록" 한다고만 적는다 - [JetBrains Help](https://www.jetbrains.com/help/idea/local-history.html)), AI 가 단독 author 인 버전 항목의 선례도 없으므로, 이 두 지점은 선례 없이 우리가 정한다.

## 원장은 덱당 JSONL 한 파일, 줄은 지금 변경 탭의 항목 모양을 그대로 담는다

원장 위치는 `decks/.history/<덱>/changes.jsonl` 이다. 이유가 셋이다. `backup()` 의 가지치기가 `h.glob("*.json")` 전체를 이름순 정렬해 50개만 남기므로(`server.py:124-126`) 확장자 `.jsonl` 은 그 glob 에 걸리지 않고, `api_get_history` 의 `?f=` 경로 검사가 `p.suffix != ".json"` 이면 404 를 내므로(`server.py:475-480`) 원장이 백업 API 로 노출되지 않으며, 작업 공간 `.gitignore` 템플릿이 `decks/.history/` 를 제외하므로(`init_workspace.py:455-461`, 실측 `ppt/.gitignore` 동일) git 에 들어가지 않는다. 잠금 파일은 원장 옆이 아니라 `out/.studio/ledger-<덱>.lock` 에 둔다 - 이미 하트비트 `session.json`·`flush.json`·`activity.json` 이 있는 상태 폴더(`common.py:120`)이고, Windows 의 파일 락은 mandatory 라 원장 파일 자체를 잠그면 락을 모르는 뷰어·백신이 공유 위반을 받을 수 있다 ([portalocker Platform Behaviour](https://portalocker.readthedocs.io/en/latest/platforms.html)).

줄 하나는 다음과 같다(실제로는 `ensure_ascii=False, separators=(",", ":")` 한 줄).

```json
{"v": 1, "seq": 412, "ts": "2026-10-14T09:12:33.481+09:00", "deck": "ch03",
 "kind": "change",
 "origin": "claude", "confidence": "inferred", "action": "save",
 "actor": {"label": "sql-tutorial 세션", "tab": null, "request": "r20261014091201123", "note": null},
 "evidence": {"heartbeat_age_s": 0.8, "working": ["r20261014091201123"], "watcher_state": "busy"},
 "before": {"ver": "1791938640147489500", "size": 48213, "hash": "sha256:…", "backup": "20261014-091233-481099.json"},
 "after":  {"ver": "1791938655012345600", "size": 48502, "hash": "sha256:…"},
 "summary": {"수정": 1, "추가": 0, "삭제": 0, "이동": 0},
 "items": [{"sid": "s12", "idx": 11, "kind": "수정", "moved": null, "title": "정규화 3단계",
            "els": [{"id": "t2", "kinds": ["글자"], "before": "제2정규형까지", "after": "제3정규형까지"}],
            "extra": ["노트"]}]}
```

| 필드 | 뜻 · 규칙 |
|---|---|
| `v` | 줄 스키마 버전. 읽기는 weak schema - 모르는 필드는 무시, 없는 필드는 기본값, 필드 이름·의미는 바꾸지 않는다 ([InfoQ, Greg Young](https://www.infoq.com/news/2017/07/versioning-event-sourcing)) |
| `seq` | 덱 안 단조 증가 정수. 락 안에서 마지막+1. 압축으로 줄이 지워져도 재할당하지 않는다. 정렬 기준은 `ts` 가 아니라 `seq`(시계 역행 대비) |
| `ts` | 기록 시각, 오프셋 포함 ISO 8601 밀리초(`datetime.now().astimezone().isoformat(timespec="milliseconds")`). 현 변경 탭의 `HH:MM:SS` 는 여기서 잘라 쓴다 |
| `kind` | `change`(내용이 바뀜) · `touch`(mtime 만 바뀌고 해시 동일 - 기본은 기록하지 않음, 설정으로 켬) · `note`(사용자 라벨·보정 메모, 선택) |
| `origin` | `editor` · `claude` · `build` · `external` 네 값 고정 |
| `confidence` | `exact`(API 로 들어와 출처가 선언됨) · `inferred`(정황으로 추정) · `unknown`(external 전용) |
| `action` | `save` · `restore`(기록·원장에서 되돌리기) · `build` · `detect`(서버가 폴링에서 발견) · `startup`(서버 기동 시 재대조) |
| `actor` | `label` = 하트비트의 세션 라벨(`watch_requests.py:138-147`) 또는 편집기 탭 표시명, `tab` = 편집기 탭 id, `request` = 처리 중 요청 id, `note` = 저장자가 보낸 한 줄 |
| `evidence` | `inferred` 일 때만. 추정 근거를 그대로 보존해 화면 툴팁에 보인다 |
| `before` / `after` | `ver` = `str(st_mtime_ns)`(현 `ver()`, `server.py:82-86`), `size`, `hash` = 파일 바이트 sha256. `before.backup` 은 그 저장 직전 상태를 담은 백업 파일명(있으면). `after.hash` 가 다음 줄의 `before.hash` 와 이어지는 체인이 끊기면 "원장이 모르는 변경이 있었다" 는 신호 |
| `summary` | `chgSummary()` 와 같은 kind 별 개수(`studio.js:215-218`) - 목록 머리줄용 |
| `items` | 현 `diffDeck` 출력과 **동일한 모양**(`studio.js:169-197`): `{sid, idx, kind, moved, title, els:[{id, kinds, before, after, gone?}], extra, gone?}`. 요소 수가 200 을 넘는 항목은 앞 200 개만 두고 `truncated: n` 을 붙인다 |

`items` 를 요약형(`{added, removed, moved, changed}`)이 아니라 변경 탭 항목 모양 그대로 저장하는 이유는 두 가지다. `renderChanges()`·`rebuildMarks()`·`onChangesClick()` 이 이 모양을 그대로 소비하므로(`studio.js:207-252`) 편집기 재작성 폭이 가장 작고, 백업이 50개 상한으로 지워진 뒤에도 "글자 전→후 60자" 가 남아 사용자가 무엇이 바뀌었는지 읽을 수 있다 - Fowler 가 말한 "이벤트가 차이 자체가 아니면 되돌리기에 필요한 정보를 처리 시점에 저장하라" 의 축소판이다 ([martinfowler.com](https://martinfowler.com/eaaDev/EventSourcing.html)).

쓰기 규약은 `studio/ledger.py` 한 모듈로 모은다. `append(deck, entry)` 는 ① 잠금 파일에 `msvcrt.locking(LK_NBLCK)` / `fcntl.flock(LOCK_EX|LOCK_NB)` 를 `os.name` 으로 분기해 걸고(비차단 + 자체 타임아웃 5초 루프 - `LK_LOCK` 은 1초 간격 10회라는 고정 정책이라 쓰지 않는다 - [Python msvcrt](https://docs.python.org/3/library/msvcrt.html)), ② 파일 끝이 `\n` 으로 끝나지 않으면 `\n` 하나를 먼저 써 찢어진 조각을 격리하고, ③ `os.open(O_WRONLY|O_CREAT|O_APPEND|O_BINARY)` 로 열어 한 줄을 `os.write` 반환값 루프로 쓴다. POSIX 는 `O_APPEND` 의 오프셋 이동과 쓰기를 한 원자 단계로 규정하지만 ([POSIX write()](https://pubs.opengroup.org/onlinepubs/9699919799/functions/write.html)) Windows CRT `_O_APPEND` 는 "쓰기 전 포인터를 끝으로 옮긴다" 만 문서화돼 있으므로 ([MS Learn _open](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/open-wopen)) 프로세스 간 원자성은 락이 책임진다. 읽기 `read(deck)` 는 `b"\n"` 으로 나눠 줄마다 `json.loads` 하고, **마지막 조각이 비어 있지 않은데 파싱되지 않으면 찢어진 줄로 버리며** 중간 줄 실패는 경고 후 건너뛴다 - jsonlines 가 마지막 종결자를 권고하되 요구하지 않기 때문이다 ([jsonlines.org](https://jsonlines.org/)). `fsync` 는 매 줄 하지 않는다. 덱 파일과 백업이 1차 진실이고 원장은 그 색인이며, 전원 장애로 마지막 줄이 사라지면 기동 시 재대조가 메운다. 저장소에 `msvcrt`·`fcntl` 선례가 없으므로(`grep` 0건) 이 잠금 헬퍼는 새로 쓴다. 서버 안 스레드 경쟁은 기존 `WRITE_LOCK`(`server.py:74-77`) 이 그대로 막는다. 같은 모듈에 `atomic_write` 를 `server.py:97-114` 에서 옮겨 와 build 도 쓰게 한다 - 지금 build 는 `out.write_text` 로 비원자적으로 덱을 쓴다(`build_deck.py:174`).

## 기록 시점은 네 곳이고 출처 판정은 결정 트리 하나다

덱 파일 `decks/<id>.json` 을 쓰는 코드는 서버 `api_put_deck`, `build_deck.main`, 데모 복사 `hub.demo` 세 곳뿐이고(`server.py:343-363`, `build_deck.py:170-177`, `hub.py:460-468`), 문서상 "밖에서" 쓰는 주체는 Claude 세션의 직접 쓰기(`docs/claude-session.md:61-62`)와 사람의 백업 수동 복사(`docs/operation.md:74`)다. 그래서 원장 기록 지점은 다음 네 곳이면 전부 덮인다.

**(1) `PUT /api/deck/<id>` - 편집기 저장과 Claude 의 서버 경유 저장.** `api_put_deck` 은 `WRITE_LOCK` 안에서 `cur = ver(p)` 로 충돌을 검사하고 `backup(i)` 후 `atomic_write` 한다(`server.py:354-363`). 여기에 ① 쓰기 전 옛 파일 바이트를 읽어 `before = {ver, size, hash, backup: 방금 만든 백업 파일명}` 과 옛 덱 객체를 얻고, ② 쿼리 `origin`(기본 `editor`) · `request` · `note` · `action`(기본 `save`) 과 헤더 `X-Nexa-Tab` 을 읽어, ③ `atomic_write` 뒤 `after` 를 stat·해시하고 `deckdiff.diff_deck(old, new)` 로 `items` 를 만들어 `ledger.append` 한다. 순서는 **백업 → 덱 교체 → 원장 추가** 로 고정한다. 중간에 죽으면 "덱은 바뀌었는데 줄이 없는" 상태만 생기고 이는 기동 재대조가 메우지만, 반대 순서면 "줄은 있는데 덱은 옛것" 이 되어 해시 체인이 거짓이 된다 - SQLite 가 저널 헤더의 페이지 수를 flush 뒤에만 바꾸는 것과 같은 논리다 ([SQLite Atomic Commit](https://www.sqlite.org/atomiccommit.html)). `origin` 쿼리는 `editor` · `claude` 만 받고 그 외 값은 400 이다. `items` 가 비면(해시 동일) 줄을 쓰지 않는다 - 편집기는 이미 `body === S.savedJson` 이면 PUT 자체를 생략하지만(`studio.js:99`) 서버도 멱등하게 둔다. 409 충돌 응답 경로에서는 아무것도 기록하지 않는다. 마지막으로 서버 메모리 `LAST[deck] = {ver, size, hash, obj}` 를 락 안에서 갱신한다 - 이것이 **서버가 새로 갖게 되는 유일한 상태**이고 자기 쓰기를 외부 변경으로 오판하지 않게 하는 장치다(Visual Studio 의 `IgnoreFileChanges` 참조 카운트와 같은 역할 - [MSDN](https://msdn.microsoft.com/en-us/library/bb135587(v=vs.110))).

**(2) `build_deck.py` - 빌드.** `--out` 이 아닌 경로에서 L170-177 사이에 넣는다. 백업 `-build.json` 을 만든 뒤 옛 덱을 읽어 두고, `atomic_write` 로 덱을 쓰고, `origin: "build", confidence: "exact", action: "build", actor: {note: "build_deck --force" 등 인자}` 와 `diff_deck(tidy(old), tidy(new))` 결과를 `ledger.append` 한다. 서버가 떠 있어도 build 는 자식 프로세스이므로(`hub.py:34-41`, `init_workspace.py:102-118`) 원장에 직접 쓴다 - 교차 프로세스 안전은 위 잠금 헬퍼가 담당한다. build 가 자기 줄을 남기지 않으면 서버가 build 결과를 external 로 오판하므로 **이 기록은 선택이 아니라 (3) 의 정확도 전제**다.

**(3) `GET /api/version/<id>` - 외부 변경 발견.** 편집기가 2초마다 부르는 이 핸들러(`server.py:365-366`, `studio.js:1574`)에서 `os.stat` 서명 `(st_mtime_ns, st_size)` 를 `LAST[deck]` 과 비교한다. 다르면 파일을 읽어 sha256 을 구하고, 해시도 다르면 외부 변경 후보다. mtime 만 믿지 않는 이유는 FAT 2초·exFAT 10ms 해상도, "핸들이 모두 닫히기 전에는 쓰기 시각이 완전히 갱신되지 않는다" 는 NTFS 동작 ([MS Learn File Times](https://learn.microsoft.com/en-us/windows/win32/sysinfo/file-times)), `touch`·`tar` 가 임의로 되돌리는 mtime, 같은 tick 의 저장-빌드-저장을 구별 못 하는 `make` 의 문제 때문이다 ([apenwarr.ca](https://apenwarr.ca/log/20181113)). 후보가 생기면 **곧바로 external 로 적지 않고 다음 폴링까지 유예(약 2초)** 한다 - build 나 `save_deck.py` 가 덱을 쓴 뒤 자기 줄을 추가하기 전 틈에 폴링이 끼어들 수 있기 때문이다. 유예 뒤 원장 꼬리를 락 안에서 다시 읽어 `after.hash == 현재 해시` 인 줄이 이미 있으면 `LAST` 만 갱신하고 끝낸다. 없으면 아래 결정 트리로 출처를 정해 `action: "detect"` 줄을 쓴다. 이때 `before` 는 `LAST[deck]` 이고 `items` 는 `LAST[deck].obj` 와 현재 덱의 diff 다. 외부 쓰기는 이미 파일을 덮었으므로 "덮이기 직전 상태" 는 서버 메모리에만 남는다 - 그 상태를 `.history/<덱>/<시각>-ext.json` 으로 저장해 `before.backup` 에 적는다. 이것은 "Claude 가 망쳤으니 직전으로" 복원을 가능하게 하는 유일한 길이며, 백업 50개 상한을 유지하기로 했으므로 이 파일도 같은 상한 안에서 함께 깎인다(기록 탭 종류에 `ext` 추가).

**(4) 서버 기동 재대조.** 서버가 꺼진 사이의 변경은 아무도 보지 못한다. 기동 시(또는 덱이 처음 요청될 때) 원장 마지막 유효 `change` 줄의 `after.hash` 와 현재 파일 해시가 다르면 `origin: "external", confidence: "unknown", action: "startup"` 줄을 한 건 쓴다. `before.backup` 은 `.history/<덱>/*.json` 50개의 해시를 계산해 마지막 줄 `after.hash` 와 일치하는 파일이 있으면 그것으로 삼아 `items` 를 만들고, 없으면 `items: null` 로 "상세 없음" 을 표시한다. 그 사이 여러 번 바뀌었어도 한 건으로 요약되는 것은 불가피하다.

출처 판정 결정 트리는 (3) 에서만 분기한다. (1)(2)(4) 는 출처가 선언되거나 고정이다.

```
PUT /api/deck 로 들어왔나?
├─ 예 → origin = 쿼리 origin (editor | claude), confidence = exact            … (1)
└─ 아니오 (폴링에서 발견, 유예 뒤에도 해시 일치 줄 없음)
   ├─ session_status().connected 이고
   │  decks/<덱>.requests.json 에 status == "working" 요청이 있다
   │     → origin = claude, confidence = inferred,
   │       actor.request = 그 요청 id(들), actor.label = 하트비트 label,
   │       evidence = {heartbeat_age_s, working:[…], watcher_state}
   ├─ connected 이고 working 은 없지만 activity().watcher.state == "busy"
   │     → origin = claude, confidence = inferred, evidence = {watcher_state, source, prompt 80자}
   └─ 그 밖 → origin = external, confidence = unknown
```

`session_status()` 는 하트비트 `out/.studio/session.json` 의 `ts` 로 `connected = not stopped and age <= interval*4+2` 를 판정하고 모든 요청 파일의 `open`·`working` 을 집계한다(`watch_requests.py:86-99`). `activity()` 는 `session_hook.py` 가 쓰는 `activity.json` 의 세션별 `state(idle|busy|unknown) · source(chat|auto) · prompt · watcher · last` 를 모아 감시 세션 하나를 `watcher` 로 고른다(`server.py:144-167`, `session_hook.py:59-80`). 이번에 `session_hook.py` 를 읽어 확인한 바, `activity.json` 의 세션 항목에는 **라벨이 없고 Claude `session_id` 와 상태만** 있다 - 그러므로 원장에 적을 세션 이름은 하트비트의 `label`(`watch_requests --label "<세션 이름>"`, 기본 `NEXA_SLIDE_SESSION` 또는 "Claude Code", `watch_requests.py:120`) 하나이고, 두 번째 가지(busy 만 있음)에는 `activity().watcher.id`(세션 id 앞 8자) 를 함께 적어 둔다. 두 가지 모두 정황 증거이므로 화면에는 반드시 "추정" 을 붙이고 근거를 툴팁에 그대로 보여 준다 - Copilot 공동 저자 자동 부착 논란이 보여 준 대로, 쓰지 않은 AI 를 표기하면 신뢰를 잃는다 ([heise.de](https://heise.de/-11279554)). 세션이 요청과 무관하게 대화로 덱을 고치는 경우(`docs/claude-session.md` 가 허용)는 `working` 이 없어 두 번째 가지나 external 로 떨어진다 - 이것이 Claude 가 **서버 경유 저장을 기본으로 삼아야 하는 이유**다.

요구 ③(사용자 자신의 편집 포함)은 (1) 로 해결된다. 편집기는 로드 시 `sessionStorage` 의 `nexaTab` 이 없으면 `crypto.randomUUID()` 를 만들어 저장하고(새 탭·창은 새 세션이라 자연히 다른 id - [MDN sessionStorage](https://developer.mozilla.org/en-US/docs/Web/API/Window/sessionStorage)) 모든 `api()` 호출에 `X-Nexa-Tab` 헤더로 보낸다(`api()` 헬퍼는 지금 `Content-Type` 만 붙인다 - `studio.js:35-40`). 현재 편집기·서버 어디에도 창 식별자가 없으므로(`clientId|tabId|sessionStorage|X-Client` grep 0건) 이것은 새로 만든다. 기록 탭에서 되돌리기(`onHistClick` → `save(true)`, `studio.js:1035-1042`)와 변경 탭의 복원은 `?action=restore&note=<백업 파일명>` 을 붙여 보내 `action: "restore"` 로 남긴다 - Figma 가 복원 전·후를 각각 체크포인트로 남겨 "복원 취소" 를 가능하게 하는 것과 같다 ([Figma Help](https://help.figma.com/hc/en-us/articles/360038006754)).

요구 ④(최근 수정 대상 확인)는 원장을 슬라이드 축으로 접으면 된다. 서버 `GET /api/changes/<id>?recent=1` 이 원장 전체(최대 1,000줄)를 훑어 **슬라이드 id 마다 가장 최근에 그 장을 건드린 줄** 하나씩 `{sid, title, idx(현재 덱 기준으로 다시 계산), seq, ts, origin, confidence, actor, kinds(합집합)}` 를 돌려주고, 편집기는 그것을 탭 상단 표로 그린다. 과거 항목의 `idx` 는 지금 순서와 다를 수 있으므로 이동은 `onChangesClick` 이 이미 하듯 `S.deck.slides.findIndex(s => s.id === sid)` 로 id 기준으로 한다(`studio.js:249`). "Claude 가 어제 s12 를 고쳤고 내가 오늘 아침 s03 을 고쳤다" 가 이 표 한 눈에 보이는 것이 ④의 목표다.

## 묶음은 저장 때 정하지 않고 읽을 때 계산한다

편집기는 편집 0.7초 뒤 자동 저장하므로(`studio.js:92-93`) 글자 하나를 고칠 때마다 원장 줄이 생길 수 있다. 원장은 **디스크에 쓰인 모든 변경을 한 줄씩 그대로** 적고(외부 쓰기와의 순서를 보존해야 하므로 서버 쪽 디바운스는 두지 않는다), 묶음은 표시 계층이 한다. 규칙은 스트림 처리의 세션 윈도와 같다 - 연속한 두 줄 `e[i-1], e[i]` 가 ① `origin` 과 `actor.tab` 이 같고 ② `ts(e[i]) - ts(e[i-1]) <= G` 이며 ③ `e[i]` 가 경계 사건이 아니면 같은 묶음이다. Flink 세션 윈도가 "간격이 gap 보다 가까운 창을 병합" 하는 정의 그대로다 ([Flink Windows](https://nightlies.apache.org/flink/flink-docs-stable/docs/dev/datastream/operators/windows/)). 고정 창(매 1분 경계)은 한 번의 끌기가 경계에 걸려 둘로 쪼개지므로 쓰지 않는다. 경계 사건은 `action in (build, restore, detect, startup)`, `origin` 전환, 요청 `done` 전환(원장 줄의 `actor.request` 가 바뀔 때), 사용자가 이름을 붙인 줄(`kind: note` 로 뒤에 붙는 라벨)이다 - Google 이 이름 붙인 버전을 병합에서 빼는 것과 같다 ([Google Docs Help](https://support.google.com/docs/answer/190843)). G 의 기본값은 60초로 두고 `nexa-slide.json` 의 `ledger.groupGap` 으로 15~600초 조정한다. 벤더 가운데 수치를 공개한 것은 VS Code 10초와 Notion 10분/2분뿐이라 그 사이 값은 우리 결정이다.

묶음의 `items` 는 1차 구현에서 **줄별 `items` 의 id 단위 합집합**으로 만든다 - 같은 `sid` 는 하나로, 같은 요소 `id` 는 `kinds` 합집합, `before` 는 첫 줄의 before, `after` 는 마지막 줄의 after, 추가 후 삭제된 요소는 `gone` 으로 남긴다. 이것은 "순 변경" 의 근사이므로 응답에 `approx: true` 를 붙여 화면이 "묶음 요약(근사)" 이라 적게 한다. 정확한 순 diff 는 묶음 첫 줄의 `before.backup` 파일이 남아 있고 끝 상태(다음 묶음 첫 줄의 `before.backup`, 또는 가장 최근 묶음이면 현재 덱)가 있을 때 서버가 `diff_deck` 으로 다시 계산할 수 있는데, 백업 50개 상한 때문에 보장되지 않으므로 2차 구현(`?group=exact`)으로 미룬다. 묶음 식별자는 묶음 첫 줄의 `seq` 로 하고, 편집기의 묶음 숨기기 토글(`data-chg-tg`, `studio.js:236,245`)은 `n` 대신 이 `seq` 를 키로 쓴다.

## 비교 로직은 Python 으로 1:1 이식하고 golden fixture 로 동일성을 못 박은 뒤 JS 는 지운다

`diffDeck`·`diffEl`·`short`·`GEO`·`TXT`·`slideTitle` 은 `studio.js:154-197`, `1016-1019` 에 있고 Python 대응물이 거의 다 있다. `Render.plain`(`render.js:49-65`) 은 `common.plain`(`common.py:336`) 이, 숫자 표기 정리는 `tidy()`(`build_deck.py:108-116`) 가 맡는다. 새 모듈 `studio/deckdiff.py` 에 다음을 그대로 옮긴다.

`short(v, n=60)` 은 문자열이 아니면 `json.dumps(v, ensure_ascii=False, separators=(",", ":"))`(None 은 `""`), `plain` 적용, `re.sub(r"\s+", " ", t).strip()`, 60자 초과 시 `t[:60] + "…"`. JS 의 `length`·`slice` 는 UTF-16 코드 유닛 기준이라 서로게이트 쌍이 있는 글자(이모지)에서 Python `len` 과 어긋날 수 있다 - 교재 덱에 그런 글자가 있는지 확인하지 않았으므로 fixture 에 이모지 케이스를 넣고, 다르면 JS 쪽을 코드포인트 기준으로 보는 대신 **Python 결과를 정본** 으로 삼는다(JS 는 곧 지워진다). `diffEl` 은 키 합집합에서 `id` 를 빼고 값이 다르면 GEO → "위치·크기", TXT → "글자"(첫 TXT 키의 before/after 만), `src` → "그림", 그 밖 → "모양" 으로 분류한다. `kinds` 의 순서는 "a 의 키 순서 → b 에만 있는 키" 를 지킨다. `diff_deck` 은 슬라이드·요소를 id 로 짝 맞추고, 양쪽에 있는 장을 옛 순서로 늘어놓은 새 인덱스 열 `seq` 에 대해 **엄격 증가 patience LIS(`tails`/`prev` 로 마지막 `tails` 원소에서 역추적)** 를 구해 그 밖의 장만 `moved: [oi+1, i+1]` 로 둔다. 항목 순서는 새 덱 순서로 추가·수정·이동, 그 뒤 옛 덱 순서로 삭제(`gone: true`), `kind` 는 `els` 나 `extra` 가 있으면 "수정"(이동과 겹치면 수정 우선, `moved` 는 별도 유지), `extra` 는 노트 → 레이아웃 → 바탕 → 부 순서 고정. 동률 길이 LIS 가 여럿일 때 어느 것을 고르는지는 이 역추적 세부에 달려 있으므로 알고리즘을 바꾸지 말고 그대로 옮긴다 - Vue 3 의 `getSequence` 도 같은 LIS 로 "움직이지 않은 노드" 를 고르고 나머지를 이동으로 처리하며 ([vuejs/core renderer.ts](https://raw.githubusercontent.com/vuejs/core/refs/heads/main/packages/runtime-core/src/renderer.ts)), React 식 `lastPlacedIndex` 휴리스틱은 "마지막을 맨 앞으로" 옮긴 경우 나머지 전부를 이동으로 표시해 요약용으로는 더 나쁘다 ([facebook/react ReactChildFiber.js](https://raw.githubusercontent.com/facebook/react/main/packages/react-reconciler/src/ReactChildFiber.js)).

동등성 비교가 가장 큰 함정이다. JS 는 `JSON.stringify(a[k]) === JSON.stringify(b[k])` 로 비교하는데(`studio.js:161`) 이는 키 삽입 순서에 민감하고(`Object.keys` 순서 - [MDN JSON.stringify](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/JSON/stringify)), Python `json.dumps` 는 `1.0` 을 `1.0` 으로 쓰는 반면 JS 는 `1` 로 쓴다 ([Python json](https://docs.python.org/3/library/json.html)). build 가 Python dict 순서로 쓴 덱을 편집기가 JS 객체 순서로 다시 저장하면 같은 내용이 "모양 변경" 으로 잡힐 수 있다. 그래서 Python 쪽 동등성은 `canon(v)` = 정수값 float → int 로 바꾼 뒤 `json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)` 문자열 비교로 정의한다. `tidy()` 의 소수 둘째 자리 반올림은 쓰지 않는다 - 그것은 빌드 비교용이고, 원장은 `x: 10.004 → 10.001` 도 변경으로 보는 것이 맞다. 이 정의는 현 JS 와 **키 순서만 다른 동일 객체** 에서 결과가 달라지는데(JS 는 "다름", Python 은 "같음"), 그 차이는 가짜 변경을 없애는 방향이므로 의도된 개선으로 CHANGELOG 에 적는다.

동일성 보장 절차는 세 단계다. 첫째, 0.16.0 작업 브랜치에서 `studio.js` 의 IIFE 안에 있는 다섯 함수를 임시로 `studio/deckdiff.js`(`render.js` 처럼 `module.exports` 를 가진 CommonJS 겸용 파일) 로 꺼낸다 - 지금은 IIFE 라 `check_parity.py` 식 `require` 가 불가능하다(`check_parity.py:21-29`). 둘째, Python 생성기가 `example/decks/demo.json` 과 교재 덱 `ppt/decks/ch00.json` 을 재료로 (old, new) 쌍 fixture 를 만든다 - 빈 덱, 동일, 장 추가·삭제, 인접 두 장 스왑, 블록 이동 `[3,4,0,1,2]`, 완전 역순, 맨 앞↔맨 끝, 요소 추가·삭제·글자·위치·그림·모양, 노트·레이아웃·바탕·부 변경, 키 순서만 다른 동일 요소, `1` 대 `1.0`, 60자 경계·한글·이모지 글자, 요소 200개 초과. 셋째, 새 도구 `studio/check_changes.py` 가 node 로 `deckdiff.js` 를, Python 으로 `deckdiff.py` 를 돌려 `first_diff` 방식으로 비교하고(check_parity 와 같은 보고 형식), 키 순서·`1.0` 두 케이스만 "의도된 차이" 로 허용 목록에 둔다. 통과하면 JS 출력을 `tests/fixtures/deckdiff/*.json` 에 golden 으로 굳히고, `studio.js` 에서 다섯 함수와 `recordChange` 의 비교 호출을 제거한다(`slideTitle` 은 개요 탭도 쓰므로 유지 - `studio.js:1022`). 이후 diff 는 서버 Python 한 곳에서만 돌아가므로 "JS 와의 동일성" 은 이식 시점에 한 번 증명하고 끝나며, 이후 회귀는 fixture 대비 Python 단독 검사다. 추가로 `random.Random(seed)` 로 순열·삽입·삭제를 만들어 "removed ∪ stable ∪ moved = old ids", "added ∪ stable ∪ moved = new ids", "LIS 길이 = n - |moved|" 를 수천 회 검사하는 속성 테스트를 Python 에 둔다.

## API 는 PUT 확장 하나와 GET 하나, 그리고 버전 응답 필드 하나다

| 메서드 · 경로 | 변경 내용 |
|---|---|
| `PUT /api/deck/<id>?base=&force=&origin=&request=&note=&action=` + 헤더 `X-Nexa-Tab` | 기존 `base`·`force`(`server.py:352-353`) 유지. `origin` ∈ {editor(기본), claude}, `action` ∈ {save(기본), restore}, `request` 는 요청 id, `note` 는 200자. 성공 응답에 `seq`(방금 쓴 원장 줄) 추가: `{ok, version, updated, seq}` |
| `GET /api/version/<id>` | 응답에 `changes: ver(changes.jsonl)` 추가(요청 파일과 같은 mtime_ns 방식). 이 핸들러가 외부 변경 발견·유예·기록도 수행한다. `LAST` 갱신과 `ledger.append` 만 `WRITE_LOCK` 으로 감싼다(현재 락 없음 - `server.py:177` 사용처 참조) |
| `GET /api/changes/<id>` | 원장 조회. 쿼리 `limit`(기본 50) · `before=<seq>`(그 이전 페이지) · `origin=editor,claude`(쉼표 목록) · `slide=<sid>` · `group=1`(묶음으로 반환, `approx: true`) · `since=<seq>`(그 뒤 줄만 - 폴링 증분용). 각 줄에 서버가 `backupExists: bool` 을 붙여 준다(`os.path.exists`, 50개 상한으로 지워졌을 수 있음). 응답 `{ok, deck, latest: <마지막 seq>, keep: 1000, entries|groups: […]}` |
| `GET /api/changes/<id>?recent=1` | 슬라이드별 최근 변경 1건씩(위 ④) |
| `GET /api/changes/<id>?seq=N` | 한 줄 상세. `before.backup` 과 다음 줄의 `before.backup`(또는 현재 덱) 이 모두 있으면 `diff_deck` 을 다시 계산해 `items` 를 정확한 값으로 돌려준다(`exact: true`) |
| `POST /api/changes/<id>` `{seq, label}` | 선택 - `kind: "note"` 줄을 덧붙여 묶음 경계와 이름을 만든다(Google "Name this version"·JetBrains "Put Label" 대응). 원장 줄은 수정하지 않는다 |
| `GET /api/history/<id>` | 그대로. `kind` 에 `ext`(외부 변경 직전 스냅샷) 추가 |

Claude 세션용 CLI `studio/save_deck.py <덱> [--from <파일>] [--request <id>] [--note "…"]` 를 추가한다. `common.running_server()` 로 서버를 찾아(`common.py:124-159`) 있으면 `GET /api/deck/<id>` 의 `X-Deck-Version` 을 `base` 로 삼아 `PUT …?origin=claude&request=&note=` 를 보내고 409 면 "편집기가 그 사이 저장했습니다 - 다시 읽어 합치거나 `--force`" 라고 안내한다. 서버가 없으면 `ledger.atomic_write` 로 덱을 쓰고 `origin: "claude", confidence: "exact", action: "save"` 줄을 직접 추가한다(이 경로는 세션이 자기 정체를 스스로 선언하므로 `inferred` 가 아니다). 실행기 `nexa.py` 는 `studio/<이름>.py` 를 그대로 찾으므로(`init_workspace.py:150-156`) 교재에서는 `python ppt/nexa.py save_deck ch03 --from /tmp/ch03.json --request r2026…` 로 부른다. 세션이 저장 직전 `X-Deck-Version` 을 `base` 로 보내면 편집기와 같은 409 규칙을 공유하게 되어, 지금 §3 방식(직접 쓰기)의 "충돌 검사 없는 덮어쓰기" 도 함께 사라진다. 이는 LSP 가 서버→클라이언트 편집을 `workspace/applyEdit` 한 통로로 일원화하는 구조와 같다 ([LSP 3.17 applyEdit](https://raw.githubusercontent.com/microsoft/language-server-protocol/gh-pages/_specifications/lsp/3.17/workspace/applyEdit.md)).

## 변경 탭은 자리와 소비자를 그대로 두고 안쪽만 바꾼다

요구 ⑤대로 별도 화면은 없다. 탭 버튼 `<button class="chip" data-tab="chg" …>변경 <span class="cnt" id="chgCnt">` 과 패널 `#tab-chg`(`index.html:411, 416`), 클릭 위임 `$("#tab-chg").addEventListener("click", onChangesClick)`(`studio.js:1475`), CSS 블록(`index.html:141-156`) 을 유지하고 `renderChanges()` 안을 다시 짠다. 패널 구성은 위에서 아래로 다음과 같다.

머리 `.sec` 에 "변경 - <덱>" 과 안내문, 그 아래 **출처 필터 세그먼트** `전체 | 내 편집 | Claude | 빌드 | 외부` 를 검사 탭의 `#chkFilter`(`span.seg > button[data-v].on`, `studio.js:945, 960`, CSS `index.html:238`) 패턴으로 두고 선택값을 `LS.set("chgFilter", v)` 로 기억한다(`LS` 헬퍼 `studio.js:19-20`; `S.tab` 과 달리 필터는 기억할 가치가 있다). "내 편집" 은 `origin === "editor" && actor.tab === 내 탭 id` 이고, 다른 탭의 편집기 저장은 "내 편집" 밖이지만 editor 배지로 보인다. 그 아래 **"최근 수정 대상" 표** - 최근 8장을 `장 번호·제목 | 출처 배지 | 상대 시각 | 종류` 로 그리고 행에 `data-csid` 를 달아 기존 `[data-csid]` 처리(`studio.js:247-249`)로 이동시킨다. 오른쪽 패널용 표 CSS 는 없으므로(`#fontDlg td`·`#help td` 만 - `index.html:310, 313`) `.chg-tbl td { padding: 4px 6px; border-bottom: 1px solid var(--tone2) }` 를 새로 둔다. 그 아래 **묶음 목록** - 묶음 머리 `.chg-h` 에 `<b>HH:MM</b>`(제목 속성에 절대 시각·오프셋), 출처 배지, 행위자(`actor.label` 또는 "탭 6f1c"), `chgSummary` 요약, "추정" 이면 `evidence` 를 툴팁으로, 오른쪽 끝에 기존 숨기기 토글과 **"이 직전으로 되돌리기"** 버튼(`backupExists` 가 거짓이면 비활성 + "백업이 50개 상한으로 지워졌습니다"). 항목·요소 줄은 기존 `.chg-it`/`.chg-el`/`.chg-tx` 그대로다. 복원 버튼은 `onHistClick` 의 다섯 줄(`GET /api/history/<id>?f=` → `snapshot()` → `S.deck` 교체 → `afterChange(true)` → `save(true)`) 을 `restoreFrom(file)` 함수로 빼내 공유하고 `save(true)` 에 `action=restore&note=<file>` 을 붙인다. 목록 끝에는 "더 보기(`before=<seq>`)" 와 "기록의 시작" 표시를 둔다(활동 피드 가이드의 끝 표시 - [saasui.design](https://www.saasui.design/blog/saas-activity-feed-audit-log-ux-patterns)).

출처 배지는 행위 종류 색과 축이 섞이지 않도록 별도 클래스 `.org.<origin>` 로 둔다. 기존 `.chg-it .k` 기본 파랑 `#D6E3FF/#0B2E6B` 은 "수정·이동", `.k.추가` 는 `--okc/--ok`, `.k.삭제` 는 `#FFDAD6/#93000A` 로 **행위 종류** 를 뜻한다(`index.html:152-153`). 출처는 editor = `--okc/--ok`(저장됨 칩과 같은 초록), claude = `--infoc/--info`(세션 "처리 중" 칩·`.hist .k.build` 와 같은 파랑), build = `--warnc/--warn`(호박), external = `--tone2/--ink2`(회색) 으로 토큰(`index.html:14-18`)만 쓴다. `inferred` 는 배지 글자 뒤에 "추정" 을 붙이고 점선 테두리로 구분한다. 색은 세션마다 바뀌지 않게 고정한다는 것이 Word 의 교훈이다.

카운터와 표시 규칙은 "내가 마지막으로 본 이후" 모델로 바꾼다. 편집기는 변경 탭을 열거나 "표시 지우기" 를 누를 때 `LS.set("chgSeen-<덱>", latest seq)` 를 저장하고, `#chgCnt` 는 `seq > seen` 이면서 "내 편집" 이 아닌 줄이 건드린 슬라이드 수다. `rebuildMarks()`(`studio.js:207-214`) 는 그 집합만으로 `S.chgMark[deck][sid] = Set<요소 id>` 를 만들어 세 소비자(썸네일 "변경 N" 배지 `studio.js:309`, 개요 배지 `1022`, 캔버스 파란 점선 `419-420`) 가 **외부·Claude·빌드·다른 탭의 변경만** 표시하게 한다 - 내 편집에 점선이 붙으면 신호가 사라진다. 묶음별 숨기기 토글은 세션 전용 상태로 남긴다(기존 `shown`). Google 의 "마지막으로 본 이후 파란 점" 과 PowerPoint 의 썸네일 점이 이 모델의 선례다 ([Google Docs Help](https://support.google.com/docs/answer/190843); [Microsoft Support](https://support.microsoft.com/en-au/office/see-revisions-made-by-other-people-be85ca29-5e57-405b-b9e3-ed8b5289d1a0)).

편집기 흐름 변경은 다음 다섯 곳이다. `poll()`(`studio.js:136-150`) 에 `if (r.data.changes !== S.chgVersion) await loadChanges()` 를 `requests` 분기(142행)와 같은 식으로 넣는다 - 이것이 없으면 편집기 자신의 저장이 변경 탭에 나타나지 않는다. `loadChanges()` 는 `GET /api/changes/<id>?group=1&limit=50` 결과로 `S.changes` 를 교체하고 `rebuildMarks(); renderChanges(); renderAll()` 을 한다. `reloadExternal()`(`220-227`) 은 `clone(S.deck)` 보관과 `recordChange` 를 버리고 `loadDeck` 뒤 `loadChanges()` 를 기다려 최신 묶음으로 `notice()` 를 띄운다(안내문의 "Ctrl+Z 로 되돌릴 수 있습니다" 는 `loadDeck(id, true)` 가 `snapshot()` 을 하므로 그대로 참 - `studio.js:117-135`). `loadDeck()` 의 `if (S.tab === "hist") loadHist()` 옆에 `chg` 분기를 더한다. 초기화 1475행에서 `loadChanges()` 를 한 번 부른다. `save()`(`95-113`) 성공 응답의 `seq` 로 `S.lastSavedSeq` 를 갱신해 "내 편집" 판정의 보조로 쓴다.

## 보존은 1,000건 상한과 압축, 백업은 50개 그대로

보존 설정은 `nexa-slide.json` 의 `"ledger": {"keep": 1000, "groupGap": 60, "recordTouch": false}` 이고 `common.CONFIG` 로 읽는다. 압축은 `ledger.append` 가 줄 수를 세어 `keep + 100` 을 넘을 때만 돈다(히스테리시스로 매 저장마다 다시 쓰지 않게). 락을 쥔 채 전체를 읽어 **최근 `keep` 줄을 그대로** `changes.jsonl.tmp` 에 쓰고 `os.fsync` 후 `os.replace` 하되, Windows 에서는 백신·인덱서가 핸들을 쥐어 WinError 5/32 가 날 수 있으므로 50→800ms 지수 백오프 5회를 감싼다 - CPython 트래커와 SQLite Windows 백엔드가 같은 이유로 재시도를 둔다 ([bugs.python.org msg27448](https://bugs.python.org/msg27448); [sqlite.org c20aca0661](https://sqlite.org/src/info/c20aca0661)). 기존 `atomic_write` 의 `PermissionError` 5회 재시도(`server.py:97-114`)와 같은 태도다. 오래된 줄은 요약 없이 버린다 - 사용자가 1,000건을 정했고 압축 시점에 그 줄의 백업은 이미 50개 상한으로 사라졌을 가능성이 높아 재계산 재료도 없다. `seq` 는 이어 간다. 1,000줄의 크기는 글자 전후 60자·요소 200개 상한으로 줄당 수 KB 이내이므로 수 MB 를 넘지 않는다. 압축은 모든 줄을 최신 `v` 로 upcast 해 다시 쓸 기회이기도 하다(Arkency 의 copy-and-replace - [Arkency](https://blog.arkency.com/4-strategies-when-you-need-to-change-a-published-event/)).

백업 50개 상한(`HISTORY_KEEP`) 은 그대로 두되 두 가지가 달라진다. `-ext.json`(외부 변경 직전 스냅샷) 이 같은 폴더에 추가되어 상한을 함께 나누고, 원장 줄의 `before.backup` 은 "있을 수도 없을 수도 있는 파일" 이 되어 서버가 `backupExists` 로 알려 준다. 가지치기가 `last-build.json` 을 사실상 지키는 것은 이름 정렬의 우연("l" > 숫자)이고 `-build.json` 도 함께 깎이는 것은 코드에 종류 구분이 없기 때문인데(`server.py:124-126`), 이번 변경은 그 동작을 건드리지 않는다 - 보존 정책을 두 단으로 나누는 것(VS Code 50개/256KB, JetBrains 5 작업일, git reflog 90일/30일 - [git-reflog](https://git-scm.com/docs/git-reflog)) 은 남은 결정으로 미룬다. 기록 탭 안내문과 변경 탭 안내문에는 "장기 보관 대체가 아니다" 를 JetBrains 처럼 명시한다.

## 처리 규약 문서는 §3 2번 한 줄이 바뀌고 다섯 문서가 따라간다

`docs/claude-session.md` §3 의 2번 항목 "파일 전체를 다시 쓰되 원자적 쓰기(임시 파일 → 교체), 요소 `id` 는 유지"(`docs/claude-session.md:56-67`) 를 "**서버가 떠 있으면 `nexa.py save_deck <덱> --from <파일> --request <요청 id>` 로 저장한다 - 원장에 Claude 로 남고 백업·충돌 검사(409)도 서버가 한다. 서버가 없을 때만 직접 원자적 쓰기(이때도 `save_deck` 이 원장 줄을 남긴다). 요소 `id` 는 유지**" 로 바꾼다. 1번(`working`)·3번(`done` + `reply`)·`content/` 동기화 문장은 그대로다 - `content/` 와 덱의 동기화는 여전히 세션 몫이며 원장 범위 밖이다. 같은 문구가 작업 공간 CLAUDE.md 템플릿(`init_workspace.py:320-321, 334`) 과 교재 `ppt/CLAUDE.md` 의 "요청 처리 규약" 줄에 있으므로 셋을 함께 고친다. `docs/server.md` API 표(`docs/server.md:39-60`) 와 `server.py` 머리 docstring(`server.py:13-33`) 에 `PUT … ?origin=&request=&note=&action=` 설명과 `GET /api/changes/<id>` 행을 더하고 `/api/version` 응답 필드에 `changes` 를 적는다(`docs/server.md:44`). `docs/operation.md` 백업 표(`docs/operation.md:66-75`) 에 `changes.jsonl`(덱당 1,000줄, 원장) 과 `<시각>-ext.json`(외부 변경 직전, 50개에 포함) 행을 더하고 `out/.studio/ledger-<덱>.lock` 을 상태 파일 목록에 적는다. `docs/editor.md` "기록 · 발표 · 저장" 절의 변경 탭 설명("밖에서 바뀐 내용")을 "편집기·Claude·빌드·외부의 모든 변경, 출처 배지, 최근 수정 대상, 되돌리기" 로 바꾼다. README 문서 표(`README.md:94-97`) 의 `server.md`·`operation.md`·`claude-session.md` 설명에 "변경 원장" 을 넣는다. `CHANGELOG.md` 는 `## 0.16.0 - <날짜> · 변경 원장 - 편집기·Claude·빌드·외부 변경을 덱당 1,000건 보존` 머리글로 시작하고 끝에 "검증:" 글머리를 둔다(`CHANGELOG.md:3-7` 관행). `server_version = "nexa-slide/0.2"`(`server.py:194`) 는 CHANGELOG 와 연동되지 않으니 건드리지 않는다. 엔진 CLAUDE.md 가 문서·주석을 한국어로 쓰라 하고 0.15.1~0.15.3 이 "-" 를 쓰므로 새 문구에 em dash 는 넣지 않는다 - 다만 `studio.js` 의 기존 안내 문자열(예: `reloadExternal` 의 notice, 변경 탭 제목 `studio.js:226, 231`)에는 em dash 가 남아 있어 재작성하는 문자열은 "-" 로 바꾼다.

## 구현은 여섯 단계, 검증은 열네 시나리오다

구현 순서는 의존 방향을 따른다. **1단계** `studio/ledger.py`(잠금·append·read·compact·canon·hash·`atomic_write` 이동) 와 `studio/deckdiff.py`(이식) 를 쓰고 `deckdiff.js` 추출 → fixture 생성 → `check_changes.py` 동일성 통과 → golden 고정. 이 단계는 서버를 건드리지 않아 독립 검증이 가능하다. **2단계** `server.py` - `api_put_deck` 기록, `LAST` 상태, `api_get_version` 의 발견·유예·기록, 기동 재대조, `api_get_changes`, `/api/version.changes`, `-ext.json`, `api_get_history` 의 `ext`. **3단계** `build_deck.py` - `atomic_write` 교체와 build 줄. **4단계** `save_deck.py` 와 `claude-session.md` §3·CLAUDE.md 템플릿·`ppt/CLAUDE.md`. **5단계** `studio.js`/`index.html` - 탭 id 헤더, `loadChanges`, `poll` 분기, `renderChanges` 재작성(필터·표·묶음·배지·복원), `rebuildMarks` 의 seen 기준, JS diff 제거. **6단계** 문서·CHANGELOG·0.16.0. 2단계가 끝나면 편집기를 바꾸기 전에도 원장이 쌓이므로 `GET /api/changes` 를 curl 로 확인하면서 5단계를 진행할 수 있다.

검증은 저장소 관행(단위 테스트 프레임워크 없음, `check_parity`·PPTX XML 동일·`check_layout` ERROR 0·예제 작업 공간 - `docs/operation.md:7-20`, 엔진 CLAUDE.md) 에 맞춘다. 서버 시나리오는 엔진 폴더 안 `example/` 로는 할 수 없으므로(허브로 뜬다 - `common.py:61-64`) 허브 "데모" 로 복사한 작업 공간이나 `init_workspace.py --flat` 작업 공간에서 수동으로 돈다.

| # | 시나리오 | 기대 |
|---|---|---|
| 1 | 편집기에서 글자 하나 고치고 0.7초 대기 | 줄 1개, `origin=editor, exact, action=save`, `actor.tab` = 내 탭, `items` 에 그 요소 "글자" 전→후, `before.backup` 존재 |
| 2 | 같은 내용으로 Ctrl+S | 편집기가 PUT 생략(기존 동작) - 줄 없음. `save(true)` 로 강제해도 해시 동일이면 줄 없음 |
| 3 | 두 탭에서 같은 덱 편집 | 다른 `actor.tab`, 두 번째 탭의 저장은 첫 탭 변경 탭에 "editor" 배지로, "내 편집" 필터에서는 빠짐. 늦게 저장한 쪽은 409 - 원장 줄 없음 |
| 4 | `save_deck ch03 --from … --request r…` (서버 켜짐) | `origin=claude, exact`, `actor.request` 채움, 편집기 2초 안에 재로딩 + notice, 썸네일 "변경" 배지 |
| 5 | 세션이 요청을 `working` 으로 두고 파일을 직접 원자적 쓰기 | 유예 1회 뒤 `origin=claude, inferred, action=detect`, `evidence.working` 에 그 id, `-ext.json` 생성, 배지 "Claude 추정" |
| 6 | 하트비트 없이(감시 중지) 파일을 수동 복사로 덮어쓰기 | `origin=external, unknown`, 회색 배지, `items` 는 메모리 `LAST` 와의 diff |
| 7 | 서버 켜진 채 `build_deck ch03 --force` | `origin=build, exact` 1줄만(external 중복 없음 - 유예·해시 매칭 확인), `-build.json` 백업, 편집기 재로딩 |
| 8 | 서버 끄고 편집·빌드 뒤 서버 재시작 | 기동 시 `action=startup, external, unknown` 1줄, 백업 중 해시 일치 파일이 있으면 `items` 채움, 없으면 `items: null` |
| 9 | 백업이 50개를 넘도록 저장한 뒤 오래된 줄 | `backupExists:false`, 복원 버튼 비활성, `items` 는 그대로 읽힘 |
| 10 | 1,100번 저장(스크립트) | 압축 뒤 1,000줄, `seq` 연속(재할당 없음), 마지막 줄 해시 = 현재 파일 해시 |
| 11 | 변경 탭 복원 버튼 | `action=restore, note=<백업명>` 줄 추가, 그 줄의 `items` 가 복원 diff, Ctrl+Z 가능 |
| 12 | 원장 마지막 줄을 반쯤 잘라 저장 후 조회 | 찢어진 줄 무시, 다음 append 가 `\n` 격리 후 정상 추가 |
| 13 | `check_changes.py` fixture 전수 | 키 순서·`1.0` 허용 목록 외 차이 0 |
| 14 | 회귀 | `check_parity -W example` 동일, 교재 덱 `export_pptx --out` 슬라이드 XML 전후 동일(덱 내용을 건드리지 않는 기능), `check_layout` ERROR 수 변화 없음 |

CHANGELOG "검증:" 한 줄에는 13·14 와 "데모 작업 공간에서 editor/claude(exact)/claude(inferred)/build/external 다섯 경로의 원장 줄 확인" 을 적는다.

## 남은 결정과 위험

결정이 필요한 것은 다섯이다. 첫째, **묶음 간격 G 의 기본값**(제안 60초)과 "묶음 숨기기" 상태를 세션 전용으로 둘지. 둘째, **`-ext.json` 이 백업 50개 상한을 함께 쓰는 것**을 받아들일지 - 외부 변경이 잦으면 편집기 저장 백업이 더 빨리 밀린다(대안은 상한을 종류별로 나누는 것이지만 "50개 유지" 결정과 충돌한다). 셋째, **기록 탭의 장래** - 변경 탭이 복원까지 하게 되면 기록 탭은 "백업 파일 원본 목록" 으로 남는데, 0.16.0 에서는 두 탭을 모두 유지하고 통합은 사용 뒤 판단한다. 넷째, **`kind: note`(이름 붙이기) 와 `?seq=N` 정확 diff** 를 0.16.0 에 넣을지 0.16.1 로 미룰지 - 둘 다 핵심 경로가 아니며 선례(5개 제품 모두 사용자 명명 체크포인트 제공)는 넣는 쪽을 지지한다. 다섯째, **`check_changes.py` 의 허용 목록 두 건**(키 순서·`1.0`)을 "의도된 개선" 으로 확정할지.

위험은 다음과 같다. **추정 오귀속** - 세션이 `working` 인 동안 사람이 파일을 수동 복사하면 "Claude 추정" 으로 적힌다. 원장은 불변이므로 고치지 않고, 화면의 "추정" 표기와 툴팁 근거로 완화하며, 세션이 `save_deck` 을 쓰면 추정 자체가 줄어든다. **유예 창의 빈틈** - build 가 덱을 쓰고 자기 줄을 더하는 데 2초 이상 걸리면(백신 지연 등) external 중복 줄이 생길 수 있다. 해시 매칭이 뒤늦게 발견되면 서버가 `kind: note` 로 "seq N 은 build 로 확인됨" 을 덧붙이는 보정을 2차에 둔다. **Windows 교체 실패** - `os.replace` 가 WinError 5/32 를 내는 빈도·조건의 실측 기록이 저장소에 없다(코드 주석 `server.py:105`, `watch_requests.py:82` 만). 재시도 백오프와 "실패 시 다음 append 에서 재시도" 로 막되, 압축 실패가 저장 실패로 번지지 않게 압축 예외는 로그만 남기고 PUT 은 성공시킨다. **OneDrive 안의 작업 공간** - 동기화 클라이언트가 핸들을 쥐거나 mtime 을 바꾸는 사례가 보고되지만 공식 문서는 없다 ([Microsoft Support](https://support.microsoft.com/en-us/onedrive/troubleshoot-onedrive-error-this-file-can-t-be-synced)); 해시 비교가 mtime 만 바뀐 경우를 `touch` 로 걸러 준다. **탭 id 복제** - `window.open`/`target=_blank` 로 연 페이지는 `opener` 의 `sessionStorage` 복사본을 받아 두 탭이 같은 id 를 가질 수 있다 ([MDN sessionStorage](https://developer.mozilla.org/en-US/docs/Web/API/Window/sessionStorage)); 편집기 안에 그런 링크는 없지만 `rel="noopener"` 를 기본으로 두고 서버가 같은 id 의 PUT 이 겹치면 경고 로그를 남긴다. **원장 크기와 폴링 비용** - `/api/version` 은 2초마다 돌므로 stat 서명 비교까지만 하고 해시·diff 는 서명이 달라졌을 때만 계산해야 한다. `recent=1` 과 `group=1` 은 1,000줄 전체를 읽으므로 서버가 덱별 파싱 결과를 `changes.jsonl` 의 mtime_ns 로 캐시한다. **`activity.json` 의 한계** - 세션 라벨이 없고 세션 id 와 상태만 있어(`session_hook.py:59-80`), 감시 세션이 아닌 다른 Claude 세션이 덱을 직접 고치면 `othersBusy` 로만 보인다 - 그 경우도 "Claude 추정" 으로 묶되 `evidence` 에 `othersBusy` 를 적는다. **`content/` 불일치** - 원장은 덱 파일만 보므로 세션이 `content/` 동기화를 빠뜨려도 알 수 없다. 이는 `build_deck` 의 `edited_slides()` 보호(`build_deck.py:159-169`) 가 다음 빌드에서 잡는 기존 장치에 맡긴다.

## 결론

이 설계의 핵심은 "변경 탭을 서버 원장의 뷰로 바꾸되, 원장 줄이 지금 JS 가 만드는 항목 모양을 그대로 담게 해 편집기의 소비자 세 곳과 CSS 를 거의 건드리지 않는다" 는 선택이다. 그 덕에 diff 는 Python 한 곳으로 모이고 JS 와의 동일성 문제는 이식 시점의 fixture 한 번으로 끝난다. 두 번째 핵심은 출처 귀속의 정확도가 **Claude 세션이 서버를 경유하느냐**에 달려 있다는 점이다 - 결정 트리의 `inferred` 가지는 안전망일 뿐이고, `save_deck.py` 와 §3 한 줄 수정이 실제 품질을 결정한다. 세 번째는 서버가 처음으로 상태(`LAST`)를 갖게 된다는 것이다. 지금까지 nexa-slide 서버는 폴링마다 stat 만 했는데, 자기 쓰기와 외부 쓰기를 구분하려면 "내가 마지막으로 쓴 것" 을 기억해야 하고, 그 기억이 끊기는 지점(재시작)을 재대조가 메운다. 이 세 가지를 받아들이면 "어제 누가 어느 장을 고쳤나" 는 변경 탭 상단 표 한 줄로 답해지고, 백업 50개가 돌아도 원장 1,000건이 그 답을 지킨다.
