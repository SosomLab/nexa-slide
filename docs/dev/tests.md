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
| codex | `codex_adapter_test.py` | 0.22.22 - Codex 어댑터: `turn_cmd` 가 wsession 의 키워드 인자를 모두 받음, Windows 에서 `codex-code-mode-host.exe` 가 있는 실행 파일(앱 동봉) 우선, `config.toml` 의 `[windows] sandbox` 옮겨 적기, 턴 프롬프트 `{shell}` 자리·어댑터별 안내. Codex 설치·로그인 없이 돈다 | - |
| reqcli | `engine_request_cli_test.py` | 0.22.24 - 엔진 요청 CLI: `--body-file <파일>`·`-`(stdin)로 여러 줄·`< > \| &` 본문 보존, pyenv-win 래퍼에 잘린 값(`\|\| goto :error`) 거부, `status applied --applied-commit`(옛 `--commit` 도 appliedCommit), `--reply-file` | - |
| regress | `engine_regress_test.py` | 0.22.24 - 엔진 요청 검증 ④ `engine_regress.py`: 엔진을 `git clone --local` 로 복제해(저장소 밖) example 사본을 `recent` 에 등록하고 (a) 변경 없음 → 0 (b) `lecture` 토큰 하나 변경 → demo 7장 모두 unexpected·1 (c) `--allow demo` 0 / `demo:1` 1 (d) 깨진 덱 → failed·2 (e) 원본 mtime 불변 (g) 사본 삭제·`--keep`·기준 엔진 재사용 | python-pptx |
| e3 | `e3_manual_test.py` | 수동 엔진 세션(`watch_engine_requests`) - 1회·stream 하트비트, `/api/engine` state=manual, 웹 엔진 세션 시작 거절, already-watched | |
| e4 | `e4_manual_stop_test.py` | 수동 세션 수명 - 읽는 쪽이 닫히면 종료(`procutil.StdoutWatch`), `--takeover` 가 이전 감시를 끝냄, 웹 [끊기](`/api/engine/session stop`), 작업 공간 `watch_requests` 도 같음 | |
| englist | `englist_test.py` | 서버 작업 카드 최근 5건·`total`, `GET /api/engine/requests?q=`·`?status=`, `/engine` 페이지(검색·강조·상태 칩·펼치기·거절·삭제) | Node, Chrome |
| editor | `editor_ui_test.py` + `scenarios/*.json` | 편집기 UI — 시험용 작업 공간(덱 4개)을 만들어 작업 공간 서버(5667)를 띄우고 시나리오를 돌린다: 그림 삽입(API·Ctrl+V·끌어다 놓기), 삽입 패널(도형·다이어그램·차트·아이콘 타일), 표 행·열 단추·글머리 감지 스위치, 묶기/풀기, 링크·그림자·자르기 속성·발표자 보기, 명령 팔레트·접는 절·스마트 가이드, 글꼴 세트 선택 상자 넘침, 요청 기록 창(퍼지·단어 단위·정규식 토글) | Node, Chrome |
| tidy | `tidy_test.py` | 작업 공간 정리·보관(`tidy.py`) — 산출물·참조 없는 그림(백업 참조 표시)·고아 첨부·세션 로그·백업 보고, clean(옮김)·restore·purge, archive zip 제외 규칙, 작업 공간 서버 `/api/tidy`, 요청 첨부 삭제(discard·update) | - |
| deck | `deck_test.py` | 덱 관리(`deck_admin`) — 짧은 해시 id 생성, 복제(content 포함), 시작 덱(`startDeck`)·목록 ★, 작업 공간 서버 `/api/decks` copy·start | - |
| (수동) shift_bench | `shift_bench.py <작업 공간> <preset|->` | 글 세로 위치 대조 — 상자·타원(흰 글)을 크기×줄 높이로 깔고 PowerPoint 렌더와 브라우저 캡처의 글자 세로 중심 차이를 재 `shift = size×(a×lh+b)` 를 맞춘다(보정이 맞으면 a≈0·b≈0, 잔차 ±1px) | PowerPoint, Chrome, Pillow |
| runs · effect | `runs_test.py` · `effect_test.py` | 인라인 강조 겹치기(`common.runs` ↔ `render.runs`, 취소선·첨자·형광펜·글자 링크 포함) · 그림 프레임 효과 PPTX XML·CSS | Node |
| docstruct | `docstruct_test.py` | 0.22.11~12 - 숨김 슬라이드(`show=0`)·구분(섹션 `p14:sectionLst`)·문서 속성·도형 테두리 점선(`prstDash`)·액자 색·SVG 그림(`svgBlip`)·글 표기 PPTX XML, 표 셀별 채움·테두리·격자 PPTX·render.js | Node |
| (editor) ux3 | `scenarios/ux3_test.json` | 0.22.15 - 내용 유지 유형 전환·섹션 접기·자동 정리·넘침 경고·차트 데이터 표 | editor 묶음 |
| (editor) ux6 | `scenarios/ux6_test.json` | 0.22.18 - 표 이동 띠·✥ 손잡이·행/열 띠 선택·경계 끌기·줄무늬·행 높이 맞춤·그림 톤·도형 빛 | editor 묶음 |
| tableobj | `tableobj_test.py` | 0.22.17 - 표 객체 리졸버 우선순위·span·변환 왕복·PPTX 셀 서식(크기·세로·여백·기울임·테두리·병합). 편집기 쪽은 `scenarios/ux5_test.json`(셀 클릭·Shift/Ctrl·채움·자동 변환·셀 편집·Tab·행 삽입·병합·렌더 표로 변환·표 객체 타일) | Node |
| uxpack | `uxpack_test.py` | 0.22.14 - 검사 대비(t6)·대체 텍스트(t7), PPTX `descr`, 유인물·노트 PDF(Chrome). 편집기 쪽은 `scenarios/ux2_test.json`(찾기/바꾸기·서식 복사·가져오기·노트 칩·alt·펜) | Node·Chrome |
| chart | `chart_test.py` | 0.22.13 - 누적 가로·100% 누적·콤보(`c:lineChart`, 보조 축 둘째 `c:valAx`)·축 제목·숫자 형식(`formatCode`) PPTX XML, render.js 같은 종류 SVG·`chartFmt`·`comboLines` | Node |
| race | `race_test.py` | 서버 동시 시작 경쟁(`START_LOCK`) | |
| c4 | `c4_doc_test.py` | 웹 세션이 첨부 Word·Excel·PDF 를 읽어 답하는 실제 턴. 표본 문서 `real.xlsx`·`report.pdf` 는 저장소에 없다 — `NEXA_TEST_DOCS=<폴더>` 로 주고, 없으면 SKIP | claude CLI(`--sessions`) |
| thread | `thread_test.py` | 후속 요청(대화) 문맥(`thread_context`)·턴 프롬프트 | smoke 가 만든 데모 작업 공간 |
| c3 · c3b | `c3_git_test.py` · `c3b_git_deny_test.py` | 웹 세션 git 기록·push·저장소 루트 권한(허용/거절 설정) — 권한 템플릿 확인 뒤 실제 턴까지 | git, claude CLI(`--sessions`) |
| c2 | `c2_web_test.py` | 웹 세션이 실제로 `claude -p` 턴을 돌려 요청을 처리 | claude CLI(`--sessions`) |

**헤드리스 실행기 `smoke.js`**: `node smoke.js <시나리오.json>` — `{base, login?, pages: [{url, wait?, steps: [{name, js}]}]}`. `js` 는 페이지 안에서 평가되는 식(`await` 가능, `return` 이 있으면 그대로) — `false` 면 FAIL, 문자열은 설명으로 출력(OK). 콘솔 error/예외가 하나라도 있으면 그 페이지 FAIL. Chrome 경로는 파일 머리의 `CHROME`, 디버그 포트 9333.

렌더 동일성은 별도: `python3 studio/check_parity.py -W example`(render.js ↔ common/export_pptx), `python3 studio/export_pptx.py --selftest --workspace example`, PowerPoint 가 있으면 `render_pptx.ps1`·`compare.py` 로 픽셀 대조([mechanism.md](../mechanism.md)). 줄바꿈 대조는 `pwsh -File studio/lines_pptx.ps1 -Pptx out/<덱>.pptx`(PowerPoint COM 으로 글 상자마다 실제 줄 수를 JSON 으로) 와 브라우저의 `.rs-p` 높이/줄 높이를 비교한다.

시험을 더하려면: `studio/tests/<이름>_test.py` 를 만들고(머리는 `e4_manual_stop_test.py` 를 본뜬다 — `STUDIO = parents[1]`, `WORK`/`USER`/`PROJ`, `check()`), `run_all.py` 의 `TESTS` 에 한 줄 넣는다.
