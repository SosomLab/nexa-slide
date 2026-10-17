# 설계 메모 — 엔진 요청 검증 ④ 자동화 (전체 작업 공간 PPTX XML 회귀)

> 협업 세션 정리, 2026-10-17. 엔진 요청 큐 항목의 근거. "결정" 표시가 없는 것은 **제안**이다.
> 근거: `docs/dev/engine-request-design.md:77`(④ 원문), `:107`(필수), `:171`(남은 것), 엔진 `CLAUDE.md` 회귀 규칙.

## 1. 요구사항

엔진 요청 하나를 처리한 뒤, **등록된 모든 작업 공간의 모든 덱**을 사본에서 변경 전 엔진·변경 후 엔진으로 각각 `export_pptx --out` 하고 슬라이드 XML 이 같은지 한 명령으로 확인한다. 결과는 요청의 `done` reply 에 그대로 붙일 수 있는 요약으로.

## 2. 지금 상태 (조사 결과)

| 항목 | 사실 |
|---|---|
| ④ 정의 | 설계 문서에만 있다. 세션 규약 `.claude/commands/nexa-slide-server.md:23`, `studio/agents/engine_turn_prompt.md:17` 에는 ①·③만(check_parity·py_compile·관련 시험) |
| 작업 공간 목록 | 사용자 설정 폴더(`paths.user_dir()` `paths.py:63-72`, `NEXA_SLIDE_USER_DIR` 우선)의 **`settings.json` `recent`**(`{path,title,opened}`, 최대 30, `paths.load_settings()` `:78`) — `hub/` 아래가 아니다. 덱 목록은 `hub.workspace_info()`(`hub.py:213-225`: `<ws>/<cfg.decks>/*.json` − `*.requests.json`, `nexa-slide.json` 없으면 `workspace: False`) |
| `hub/engine/scratch/` | 문서에만 있고 코드 0건 |
| `export_pptx.py` | 덱 하나(`id`, `safe_id`)만, `--out` 이면 글꼴 기록 안 함(`:1283-1298`). 작업 공간은 `-W`/`NEXA_SLIDE_WORKSPACE`. 엔진은 **스크립트 자기 위치의 `studio/`** 를 쓰므로 트리만 바꿔 실행하면 전·후 엔진이 갈린다 |
| 비결정 요소 | `docProps/core.xml` 시각(`apply_doc_props` `:1178-1196`), `ppt/presentation.xml` 구역 id `uuid4`(`apply_sections` `:1146,1171`), zip 항목 시각. 슬라이드 XML 에서는 무작위 값 없음 |
| 비교 도구 | PPTX XML 비교 도구 없음(`deckdiff`=덱 JSON, `compare`=픽셀, `check_parity`=규칙) |
| worktree | 설계는 요청마다 `req-<id>` 지만 구현은 `.claude/worktrees/engine-dev`(브랜치 `engine-dev`) 하나에 커밋이 쌓인다(`wsession.py:213-251`) |
| `assetRoot` | 작업 공간 밖(`..`)을 가리킬 수 있다 — 폴더만 복사하면 그림이 빠진다(그림이 없으면 경고만 내고 건너뛰어 **양쪽 다 빠지면 회귀를 못 본다**) |

## 3. 설계 결정(제안)

1. **스크립트**: `studio/engine_regress.py`(가칭).
   `python3 studio/engine_regress.py [--base main] [--ws <경로>…] [--include-example] [--allow <덱>[:<장>]…] [--max-seconds 600] [--json]`.
2. **작업 공간 목록**: 기본 = `settings.json` `recent` 중 `workspace_info().workspace == True` 인 것 + 엔진 `example`. `--ws` 로 직접 지정 가능. 없는 경로는 "건너뜀" 으로 보고.
3. **기준(before)**: **`main`**(지금 운영에 적용된 엔진 = 병합 대상). `engine-dev` 에 커밋이 쌓이므로 "작업 전 HEAD" 는 이전 요청의 미병합 변경까지 포함해 기준이 흔들린다 — main 과 비교하면 "이번에 운영에 들어갈 차이 전체" 를 본다. `--base <rev>` 로 바꿀 수 있다(예: 직전 요청 커밋).
   기준 엔진은 `git archive <base> studio | tar -x -C hub/engine/scratch/engine-<짧은해시>/`(해시 같으면 재사용). after = 실행 중인 트리의 `studio/`.
4. **사본**: `hub/engine/scratch/regress-<시각>/<ws_id>/` 에 작업 공간 복사(`out/`·`.history/`·`.studio/`·`fonts/` 큰 파일 제외 — 글꼴은 XML 에 영향 없음 확인 필요, 영향 있으면 포함). `assetRoot` 가 밖이면 사본의 `nexa-slide.local.json` 에 **원래 절대 경로**를 적는다(읽기만 하므로 원본 손상 없음). 원본 작업 공간에는 아무것도 쓰지 않는다. 끝나면 사본 삭제(`--keep` 이면 남김).
5. **비교 범위**: PPTX zip 의 모든 항목을 본다 — `ppt/slides/*.xml` 과 `_rels`, `ppt/notesSlides/*`, `ppt/presentation.xml`, `ppt/media/*`(바이트 해시), `[Content_Types].xml`. 제외/정규화: `docProps/core.xml` 제외, `presentation.xml` 구역 id(`{uuid}`)는 순번으로 치환. XML 은 `xml.etree.ElementTree.canonicalize` 로 정규화 후 문자열 비교. 보고는 **슬라이드별**(덱/장 번호 + 첫 차이 줄 몇 개), 나머지 부품은 묶어서.
6. **기능 추가 예외**: 차이는 항상 보고한다. `--allow 덱[:장]` 로 "의도한 변경" 표시 → 결과에 `expected` 로 분류, 종료 코드는 0. 허용 안 된 차이는 `unexpected` → 종료 코드 1. 요청 reply 에 "의도한 변경: 덱/장 — 이유" 를 적는 것이 세션 규약.
7. **시간 한도**: 덱당 120초(하위 프로세스 timeout), 전체 `--max-seconds`(기본 600). 넘으면 남은 것은 `skipped` 로 보고하고 종료 코드 2(판정 불가). 기준 엔진과 사본은 준비 단계에서 한 번.
8. **출력**: 사람이 읽는 요약(작업 공간 n · 덱 n · 장 n · 동일/의도/예상밖/실패/건너뜀) + `--json`. 종료 코드 0 동일(또는 전부 allow) / 1 예상밖 차이 / 2 오류·시간 초과.
9. **규약 연결**: `nexa-slide-server.md` 검증 목록과 `engine_turn_prompt.md:17` 에 ④ 한 줄 — "렌더·내보내기·레이아웃(`studio/*.py`·`render.js`·템플릿)을 건드렸으면 `engine_regress.py` 실행, 결과 요약을 reply 에". 웹 엔진 세션 권한(`Bash(python3 studio/*.py *)`)으로 이미 실행 가능한지 확인. `docs/dev/engine-request-design.md` 12절·`docs/dev/tests.md` 갱신.

## 4. 완료 기준

- 엔진 변경 없이 실행하면 등록된 모든 덱이 "동일"(비결정 요소 정규화 확인 — 같은 엔진으로 두 번 내보내 비교해도 동일).
- 슬라이드 하나에 영향 주는 변경을 넣으면 그 덱/장만 `unexpected` 로 잡히고 종료 코드 1, `--allow` 로 0.
- 원본 작업 공간 파일의 mtime 이 바뀌지 않는다. 사본은 끝나면 지워진다.
- 시간 초과·덱 실패가 결과에 드러난다(조용히 통과 금지).

## 5. 시험

- `studio/tests/engine_regress_test.py`(`e4_manual_stop_test.py` 머리 본뜸, 격리 `NEXA_SLIDE_USER_DIR`): example 사본을 `recent` 에 등록 →
  (a) 변경 없음 → 0, (b) 임시 git 저장소에서 `common.py` 의 상수 하나를 바꾼 커밋을 base 와 비교 → 1 과 해당 장 보고, (c) `--allow` → 0, (d) 덱 하나를 깨진 JSON 으로 → 2, (e) 원본 mtime 불변.
- `run_all.py` `TESTS` 에 추가. 수동: 현재 PC 의 `recent`(1곳·덱 1·5장)로 실행 시간 기록.
