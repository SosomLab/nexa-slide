# 시험 모음 (`studio/tests/`)

엔진을 고친 뒤 돌리는 자동 시험. 모두 **격리된** 허브(포트 5799)·작업 공간(`<임시 폴더>/nexa-slide-tests/` — 저장소 밖이어야 한다, 허브가 엔진 안의 작업 공간을 거절하므로)을 띄우므로 운영 서버(5599·5600~)와 사용자 설정 폴더를 건드리지 않는다. 세션 규약의 검증 단계(엔진 요청 처리 → `check_parity` + 관련 시험)에서 쓴다.

```bash
python3 studio/tests/run_all.py              # 기본 묶음(약 5분) - claude 가 필요한 것은 뺀다
python3 studio/tests/run_all.py smoke e4     # 이름 일부로 고르기
python3 studio/tests/run_all.py --sessions   # 실제 claude 턴을 도는 것(c2·c3·c3b·c4)까지 - claude CLI 설치·로그인 필요
NEXA_TEST_DIR=/tmp/nexa-tests python3 studio/tests/run_all.py   # 산출물 자리를 밖으로
```

| 이름 | 파일 | 확인하는 것 | 필요 |
|---|---|---|---|
| i18n | `i18n_check.js` | `i18n.js` 문법 · 사전 중복 키 · 번역 표본 | Node |
| smoke | `smoke_run.py` + `smoke.js` | 허브 로그인 → 시작 페이지·Studio(중계)의 주요 단추 50여 단계를 헤드리스 Chrome 으로 눌러 본다(콘솔 오류 0). 데모 작업 공간을 만든다 | Node, Chrome |
| e3 | `e3_manual_test.py` | 수동 엔진 세션(`watch_engine_requests`) - 1회·stream 하트비트, `/api/engine` state=manual, 웹 엔진 세션 시작 거절, already-watched | |
| e4 | `e4_manual_stop_test.py` | 수동 세션 수명 - 읽는 쪽이 닫히면 종료(`procutil.StdoutWatch`), `--takeover` 가 이전 감시를 끝냄, 웹 [끊기](`/api/engine/session stop`), 작업 공간 `watch_requests` 도 같음 | |
| englist | `englist_test.py` | 서버 작업 카드 최근 5건·`total`, `GET /api/engine/requests?q=`·`?status=`, `/engine` 페이지(검색·강조·상태 칩·펼치기·거절·삭제) | Node, Chrome |
| editor | `editor_ui_test.py` + `scenarios/*.json` | 편집기 UI — 시험용 작업 공간(덱 4개)을 만들어 작업 공간 서버(5667)를 띄우고 시나리오를 돌린다: 그림 삽입(API·Ctrl+V·끌어다 놓기), 삽입 패널(도형·다이어그램·차트·아이콘 타일), 표 행·열 단추·글머리 감지 스위치, 묶기/풀기, 링크·그림자·자르기 속성·발표자 보기, 명령 팔레트·접는 절·스마트 가이드, 글꼴 세트 선택 상자 넘침, 요청 기록 창(퍼지·단어 단위·정규식 토글) | Node, Chrome |
| tidy | `tidy_test.py` | 작업 공간 정리·보관(`tidy.py`) — 산출물·참조 없는 그림(백업 참조 표시)·고아 첨부·세션 로그·백업 보고, clean(옮김)·restore·purge, archive zip 제외 규칙, 작업 공간 서버 `/api/tidy`, 요청 첨부 삭제(discard·update) | - |
| race | `race_test.py` | 서버 동시 시작 경쟁(`START_LOCK`) | |
| c4 | `c4_doc_test.py` | 웹 세션이 첨부 Word·Excel·PDF 를 읽어 답하는 실제 턴. 표본 문서 `real.xlsx`·`report.pdf` 는 저장소에 없다 — `NEXA_TEST_DOCS=<폴더>` 로 주고, 없으면 SKIP | claude CLI(`--sessions`) |
| thread | `thread_test.py` | 후속 요청(대화) 문맥(`thread_context`)·턴 프롬프트 | smoke 가 만든 데모 작업 공간 |
| c3 · c3b | `c3_git_test.py` · `c3b_git_deny_test.py` | 웹 세션 git 기록·push·저장소 루트 권한(허용/거절 설정) — 권한 템플릿 확인 뒤 실제 턴까지 | git, claude CLI(`--sessions`) |
| c2 | `c2_web_test.py` | 웹 세션이 실제로 `claude -p` 턴을 돌려 요청을 처리 | claude CLI(`--sessions`) |

**헤드리스 실행기 `smoke.js`**: `node smoke.js <시나리오.json>` — `{base, login?, pages: [{url, wait?, steps: [{name, js}]}]}`. `js` 는 페이지 안에서 평가되는 식(`await` 가능, `return` 이 있으면 그대로) — `false` 면 FAIL, 문자열은 설명으로 출력(OK). 콘솔 error/예외가 하나라도 있으면 그 페이지 FAIL. Chrome 경로는 파일 머리의 `CHROME`, 디버그 포트 9333.

렌더 동일성은 별도: `python3 studio/check_parity.py -W example`(render.js ↔ common/export_pptx), `python3 studio/export_pptx.py --selftest --workspace example`, PowerPoint 가 있으면 `render_pptx.ps1`·`compare.py` 로 픽셀 대조([mechanism.md](../mechanism.md)). 줄바꿈 대조는 `pwsh -File studio/lines_pptx.ps1 -Pptx out/<덱>.pptx`(PowerPoint COM 으로 글 상자마다 실제 줄 수를 JSON 으로) 와 브라우저의 `.rs-p` 높이/줄 높이를 비교한다.

시험을 더하려면: `studio/tests/<이름>_test.py` 를 만들고(머리는 `e4_manual_stop_test.py` 를 본뜬다 — `STUDIO = parents[1]`, `WORK`/`USER`/`PROJ`, `check()`), `run_all.py` 의 `TESTS` 에 한 줄 넣는다.
