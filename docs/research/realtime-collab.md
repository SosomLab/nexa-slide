# 실시간 동시 편집 — 다른 제품의 방식과 nexa-slide 방향 (2026-10-28)

> engine-request #12 를 진행하면서 함께 정리했다. 여러 사람과 AI 세션이 같은 덱이나 시트를 동시에 고칠 때 어떻게 해야 하는지 다룬다.
> 확인하지 못한 것은 **(추정)**, 2차 출처는 **(2차)** 로 표시했다.

## 0. 요약

- 지금 방식은 **문서 한 통 + 낙관적 잠금(버전 비교 409) + 사람이 고르기**다. 자동 병합은 없고, 덮어쓰는 단위는 덱 전체다.
- **고친 결함(이번)**: AI 의 `save_deck` 은 사본을 만든 때가 아니라 *저장 직전* 버전을 `base` 로 보냈다. 그래서 AI 가 사본을 고치는 동안(수십 초~수 분) 사람이 저장한 내용이 409 없이 덮였다.
  이제 `draft_deck` 이 사본을 만든 때의 버전을 `out/.studio/draft-<덱>.base` 에 남기고, `save_deck --from <사본>` 이 그 값을 보낸다. 충돌이면 종료 코드 2 로 끝나고, 세션은 사본을 다시 만들어 사람의 변경 위에 고친다.
- 슬라이드·캔버스형 편집기는 대부분 **서버 권위 + 객체·속성 단위 LWW(나중 것이 이긴다) + 고유 id + 분수 인덱스 순서**를 쓴다. Figma, tldraw, Excalidraw, Fluid SharedTree 가 그렇다.
  글자 단위 OT/CRDT 는 긴 본문 편집기(Google Docs, Notion 오프라인)에 필요하다. nexa-slide 의 요소 트리와 셀 맵에는 Figma 식이 맞다.
- 방향은 세 단계다.
  1. 지금 구조 위에 **기준본 3-way 병합(요소·셀 단위) + SSE 푸시 + presence** 를 얹는다.
  2. **작업(op) 로그 + 서버 순서**로 바꾼다.
  3. CRDT 는 필요가 확인될 때만 들인다.

## 1. 지금 구조

| 경로 | 동작 | 한계 |
|---|---|---|
| 편집기 저장 | 0.7초 디바운스 → `PUT /api/deck/<id>?base=<mtime_ns>` 로 덱 전체 → 다르면 409 | [내 편집]을 고르면 force 로 상대 변경을 **통째로** 지운다 |
| 편집기 갱신 | 2초 폴링 `/api/version` → 편집 중이 아니면 다시 읽고, 편집 중이면 충돌 배너 | 다시 읽기가 남의 변경을 내 undo 스택에 넣어 **Ctrl+Z 가 남의 작업을 되돌린다** |
| AI 저장 | `draft_deck` 사본 → Edit → `save_deck`(PUT origin=claude) | (고침) 사본을 만든 때 기준으로 409 |
| 외부 변경 | `detect` — 서명·해시·유예·원장 꼬리 대조 → 출처 추정, `-ext` 백업 | 사후 기록이다 |
| 기록 | 원장 `decks/.history/<덱>/changes.jsonl`(장·요소 diff, origin·actor·tab) + 백업 50개 | 누가 *지금* 어디를 보는지(presence)는 없다 |
| 푸시 | 웹 세션 진행만 SSE(`Last-Event-ID` 재개). 허브 중계도 SSE 를 흘린다 | 덱 변경은 폴링뿐이다 |

## 2. 다른 제품

| 제품 | 단위 | 충돌 해소 | 권위 | presence | 다중 사용자 undo |
|---|---|---|---|---|---|
| Google Docs | 글자 범위 op | OT, 서버가 개정 순서를 정한다 | 서버 | 커서·선택·아바타 | 내 op 만 (일반 지식) |
| Google Sheets/Slides | 셀·도형 op (추정) | OT 계열(2013 Realtime API 공식 발표, 현재는 추정) | 서버 | 셀 테두리 색 | (추정) |
| M365 웹 공동 작성 | 옛 데스크톱은 단락·슬라이드·셀 잠금, 웹은 실시간 | Fluid — relay 가 매긴 순번 + LWW | 서버(relay) | 커서 | SharedTree 는 삭제를 "이동"으로 다뤄 데이터를 잃지 않는다 |
| Figma | 객체 트리의 **속성** | 속성 LWW, 서버 순서, 내 미확인 변경과 충돌하는 서버 값은 무시(깜빡임 방지) | 서버(문서마다 프로세스) | 커서·관찰 | undo 가 redo 를 고쳐 "되돌리고 다시 해도 같다" |
| tldraw sync | 레코드(도형·페이지) | 서버 권위 push/pull/rebase(CRDT 아님) | 서버(방마다 인스턴스) | presence 레코드 따로 | 로컬 |
| Excalidraw | 요소 | 요소 `version` 이 큰 쪽, 같으면 nonce (2차) | 없음(암호화 중계) | 커서 | 로컬 |
| Notion | 블록 | 온라인은 미확인, **오프라인 페이지는 CRDT** 로 옮겼다 | 서버 | 아바타 | 미확인 |
| Linear | 모델 객체 | 서버 순서 sync action 로그, checkpoint 뒤만 받는다(delta sync) | 서버 | 제한적 | 미확인 |

교훈
1. **객체가 있는 편집기는 객체·속성 단위 LWW 로 충분하다.** Figma 는 "글 편집기가 아니다"라며 OT 를 버렸다.
2. **순서는 분수 인덱스**로, 부모 이동은 부모 링크와 위치를 한 속성으로 묶는다. 배열 인덱스가 밀리는 충돌이 없다.
3. **삭제 대 수정**은 정해진 규칙으로 처리한다. Fluid 는 삭제를 이동으로 보고, Figma 는 지운 쪽 undo 버퍼에 남긴다. 데이터를 잃지 않는 쪽을 고른다.
4. **presence 는 영속 상태와 따로** 둔다. 메모리에만 두고 수십 초 소식이 없으면 지운다.

## 3. 기술

- **OT**: 중앙 서버가 순서를 정하고 동시 op 를 변환한다. 변환 함수를 맞게 만들기 어렵다.
- **CRDT**: 순서와 상관없이 같은 결과로 수렴한다. 오프라인·P2P 에 강하지만 메타데이터와 라이브러리 의존이 따라온다.
  - Yjs(MIT): Python 서버는 pycrdt/ypy-websocket 을 쓰고, Awareness(presence)가 함께 온다.
  - Automerge 3(MIT): JSON 모델, 3.0 에서 메모리를 크게 줄였다. Python 바인딩 성숙도는 미확인이다.
  - Loro(MIT): MovableList·Tree(이동 연산) — 장 순서·묶음 이동에 가장 잘 맞는다. Python 바인딩이 있다.
  - Python 쪽은 모두 **네이티브 확장**이다. "표준 라이브러리만" 원칙과 Windows 설치 경로를 다시 정해야 한다.
- **서버 권위 LWW + op 로그**: 표준 라이브러리로 된다. 지금 원장(seq, 추가 전용 JSONL)이 이미 그 모양이고, "작업 공간마다 서버 하나"가 단일 권위와 맞는다.
  한계는 같은 글 상자를 두 사람이 동시에 치면 한쪽이 진다는 것이다(Figma 도 같다).
- **패치 표현**
  - JSON Patch(RFC 6902)는 배열 인덱스 경로가 동시 삽입에 밀리므로 **id 경로**로 바꿔 쓴다. `test` 는 낙관적 조건으로 쓸 수 있다.
  - Merge Patch(RFC 7396)는 속성 묶음에는 간결하지만 배열은 통째로 바뀐다.
  - Liveblocks 도 에이전트에게 JSON Patch 를 쓰게 한다. "모델이 전체를 다시 쓰는 것보다 목표 변경 묶음이 쉽고 빠르다"는 이유다.
- **전송**
  - **SSE 로 내려보내고 POST 로 올린다** — `http.server` 로 바로 되고 허브 중계도 이미 흘린다.
  - HTTP/1.1 은 도메인당 연결이 6개라 **탭당 SSE 하나에 이벤트를 다중화**한다. 2초 폴링은 SSE 가 끊겼을 때의 안전망으로 남긴다.
  - WebSocket 은 표준 라이브러리에 없다. 끌기 중 위치 공유처럼 초당 수십 건이 필요할 때 검토한다.

## 4. AI 가 참여자일 때

- 파일을 통째로 쓰면 생기는 문제
  - 잃어버린 갱신이 생긴다(이번에 고친 것).
  - 서버는 AI 의 의도를 모르고 결과만 받으므로 병합 근거가 없다.
  - AI 턴은 몇 분이 걸려 사람의 0.7초 저장과 시간 척도가 다르고, 그만큼 충돌이 잦다.
  - 409 뒤 재시도는 토큰과 시간을 쓴다.
- 업계 패턴
  - **목표 패치**(Liveblocks)
  - **presence 로서의 AI**: 이름·아바타·"무엇을 하는 중"을 보인다(Liveblocks, Figma 에이전트).
  - **분기 후 부분 병합**: Ink & Switch Patchwork 의 봇은 분기에 변경을 쌓고, 사람이 diff 를 보며 일부만 병합한다. Google Docs 의 제안 모드도 같은 틀이다.
  - **약한 예약**: 대상 영역에 "AI 작업 중" 경고를 띄우고, 강제 잠금은 하지 않는다.
- nexa-slide 원칙
  - AI 는 **기준 버전을 들고 패치를 낸다**.
  - AI 와 사람이 같은 (요소, 속성)을 동시에 고치면 **사람이 이긴다**. 버려진 AI 변경은 reply 와 변경 탭에 남긴다.
  - AI 가 작업하는 동안 대상에 presence 를 띄운다. 요청에 이미 `working`·`element(s)`·`range` 가 있다.
  - 큰 재구성은 **제안(분기)** 으로 받아 사람이 수락한다.

## 5. 방향

### 단위
- **슬라이드**
  - 주소는 `slide.id → element.id`, 충돌 단위는 **속성**이다. 위치·크기(x,y,w,h,rot)는 한 묶음이고, 글(text·items·rows)은 속성 하나로 LWW 한다.
  - 장 속성(layout·bg·notes·hidden)은 각각 한 단위다. 순서는 나중에 분수 인덱스로 옮긴다.
- **시트**
  - 주소는 `sheet.id → 셀 키`, 충돌 단위는 **셀의 내용(v·f)과 서식**을 나눈 것이다. 한 사람은 값, 다른 사람은 색을 고쳐도 둘 다 산다.
  - 계산값 캐시는 병합하지 않고 다시 계산한다.
  - 행·열 삽입은 A1 키를 모두 밀어내므로 처음에는 단독 op(병합 금지·409)로 두고, 장기적으로 행·열에 안정 id 를 준다.

### 1단계 — 지금 구조 위에서 (표준 라이브러리, 파일 형식 그대로)
1. ✅ **AI 저장의 잃어버린 갱신 막기**(이번): draft 기준 버전을 쓴다.
2. **서버 3-way 병합 PUT**
   - 요청 형식: `PUT ?base=V&merge=1`.
   - 버전이 다르면 409 대신 `merge3(기준본, 현재 파일, 본문)` 을 한다.
   - 기준본 찾는 곳: `.history` 백업 · 원장 해시 · 서버 메모리 링 버퍼. 버전은 mtime 대신 내용 해시나 원장 seq 로 바꿔, 동기화 폴더에서 mtime 만 바뀌는 가짜 충돌을 없앤다.
   - 비교는 `deckdiff` 의 짝 맞추기(id·canon)를 재사용한다.
   - 규칙
     - 한쪽만 바꾼 속성은 그쪽을 받는다.
     - 양쪽이 같은 속성을 다르게 바꾸면: 편집기끼리는 나중 것, AI 대 사람이면 사람이 이긴다.
     - 삭제 대 수정이면 수정이 이긴다.
     - 양쪽 추가는 합친다.
   - 응답 `{merged, conflicts:[…]}` 과 원장 `action: merge` 로 버린 값을 남긴다.
   - 편집기 409 배너는 "자동 병합됨 · 충돌 n건" 알림으로 바꾼다.
3. **AI 저장도 병합**: `save_deck` 이 `merge=1` 로 보내면 409 재시도 대신 서버가 합친다. 사람 우선이고, 버린 AI 변경은 reply 에 자동으로 덧붙인다.
4. **SSE 푸시**: `GET /api/stream/<덱>`(Last-Event-ID = 원장 seq)로 저장·detect·요청 상태·웹 세션 이벤트를 **탭당 연결 하나**로 보낸다. 폴링은 안전망으로 둔다.
5. **presence**
   - `POST /api/presence/<덱>` 으로 `{tab, user, slide, sel, editing, color}` 를 보내고, 서버는 메모리에만 둔다(15초 소식 없으면 지움).
   - 다른 사람의 선택은 색 테두리와 아바타로 그린다. 시트는 셀 테두리다.
   - **AI presence**: working 요청 대상에 "Claude 처리 중"을 띄우고, 사람이 그 요소를 고치기 시작하면 경고한다.
6. **undo 최소 수정**: 외부 변경을 내 undo 스택에 넣지 않는다. 외부 변경을 되돌리는 것은 변경 탭의 "직전으로"로 보낸다.

### 2단계 — op 로그 + 서버 권위
- 저장 단위를 **id 경로 op 묶음**으로 바꾼다.
  - op 예: `set`(요소·속성) · `insert`(after) · `remove` · `move-slide`(분수 인덱스) · `cell`(탭·셀·키)
  - 서버가 seq 순서로 적용하고, 결과를 덱 파일 스냅숏으로 다시 쓴다. 그래서 PPTX·git·빌드는 그대로 돈다.
- 클라이언트
  - `since=seq` 로 놓친 op 를 받는다.
  - 확인 전 내 op 는 낙관적으로 반영한다.
  - **undo = 내 op 의 역연산**이다.
- 파일을 직접 쓰는 경로(빌드·수동 편집)는 `detect` 가 diff 로 op 를 합성한다.
- AI: `save_deck` 이 `diff(기준본, 사본)` → op 로 바꿔 보낸다. 세션의 작업 방식(사본 Edit)은 그대로다.
  큰 변경은 **제안 묶음**(`.history/<덱>/proposals/<요청>.json`)으로 저장하고, 변경 탭에서 장·요소별로 부분 수락한다.

### 3단계 — CRDT (아래 중 둘 이상이 실제 요구일 때만)
1. 긴 글 동시 타이핑의 LWW 손실이 불만으로 쌓일 때 — 그 필드만 Y.Text 로 부분 도입한다.
2. 서버 없이 오래 고치다 나중에 합쳐야 할 때.
3. 허브가 내용을 보면 안 될 때(종단 간 암호화).
4. 같은 덱을 여러 서버가 들고 있어 단일 권위가 성립하지 않을 때.

후보는 pycrdt(Yjs 호환)가 1순위이고, 트리 이동이 핵심이면 Loro 다. 덱 JSON 은 계속 스냅숏으로 내보낸다. **현재 판단: 1·2단계로 대부분 해결되므로 CRDT 는 보류한다.**

### 위험과 시험
- 위험과 대응
  - **기준본 분실**: 해시/seq 버전과 메모리 링 버퍼를 둔다. 못 찾으면 지금처럼 409.
  - **병합 결과의 레이아웃 위반**: 병합 뒤 `check_layout` 경고를 SSE 로 보낸다.
  - **`WRITE_LOCK` 경합**: 덱별 잠금으로 나누고, 병합은 잠금 밖에서 계산한 뒤 버전을 재확인(CAS)한다.
  - **SSE 연결 한도**: 탭당 하나, BroadcastChannel 로 공유한다.
  - **옛 클라이언트**: `merge=1` 이 없으면 지금 동작을 유지한다.
- 시험
  - 병합 golden: (기준, 상대, 나, 기대) 묶음
  - 무작위 속성 시험: 서로 다른 (요소, 키)면 순서와 상관없이 수렴, id 유일성
  - **잃어버린 갱신 재현 시험**: draft → 편집기 저장 → save_deck 이 409 인지 확인. 이번에 손으로 확인했고 자동 시험으로 남길 것
  - 다중 클라이언트 시뮬레이터: 파일 = 원장 재생, 해시 체인 연속
  - 브라우저 실측: 탭 2개 + 웹 세션
  - `export_pptx` XML 회귀

## 출처

- Figma multiplayer https://www.figma.com/blog/how-figmas-multiplayer-technology-works/
- Google Docs(2010) https://drive.googleblog.com/2010/09/whats-different-about-new-google-docs.html · Realtime API(2013) https://developers.googleblog.com/2013/03/build-collaborative-apps-with-google.html
- Fluid SharedTree https://devblogs.microsoft.com/microsoft365dev/fluid-framework-how-sharedtree-merges-changes · https://fluidframework.com/docs/data-structures/overview
- Office 웹 공동 작성 https://learn.microsoft.com/en-us/microsoft-365/cloud-storage-partner-program/online/scenarios/coauth
- tldraw https://tldraw.dev/docs/sync · https://tldraw.dev/reference/sync-core/TLSocketRoom
- Excalidraw https://plus.excalidraw.com/blog/building-excalidraw-p2p-collaboration-feature
- Notion 오프라인 https://notion.com/blog/how-we-made-notion-available-offline
- Linear https://linear.app/blog/scaling-the-linear-sync-engine · https://linear.app/blog/rebuilding-delta-sync-read-path
- Automerge 3 https://automerge.org/blog/automerge-3/ · Loro https://loro.dev/blog/v1.0 · https://loro.dev/docs/tutorial/tree
- Y-Sweet https://github.com/jamsocket/y-sweet · Hocuspocus https://tiptap.dev/docs/hocuspocus
- Liveblocks(AI·에이전트) https://liveblocks.io/blog/how-humans-and-ai-will-work-together-in-the-next-generation-of-apps · https://liveblocks.io/blog/introducing-feeds-and-apis-for-agent-workflows
- Ink & Switch Patchwork https://www.inkandswitch.com/patchwork/notebook/07/
- MDN EventSource(연결 6개) https://developer.mozilla.org/en-US/docs/Web/API/EventSource
- RFC 6902 https://www.rfc-editor.org/rfc/rfc6902 · RFC 7396 https://www.rfc-editor.org/rfc/rfc7396
