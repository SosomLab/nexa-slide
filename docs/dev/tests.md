# 시험 모음 (`studio/tests/`)

엔진을 고친 뒤 돌리는 자동 시험. 모두 **격리된** 허브(포트 5799)·작업 공간(`<임시 폴더>/nexa-slide-tests/` — 저장소 밖이어야 한다, 허브가 엔진 안의 작업 공간을 거절하므로)을 띄우므로 운영 서버(5599·5600~)와 사용자 설정 폴더를 건드리지 않는다. 세션 규약의 검증 단계(엔진 요청 처리 → `check_parity` + 관련 시험)에서 쓴다.

```bash
python3 studio/tests/run_all.py              # 기본 묶음 62개(pageflowui 포함 - ef0ed53, 약 17~19분, 2026-11-27 verify 이력) - claude 가 필요하다고 표시한 것은 뺀다
python3 studio/tests/run_all.py smoke e4     # 이름 일부로 고르기
python3 studio/tests/run_all.py --exact e3   # 이름 그대로(엔진 배포의 비교 시험) - 묶음마다 `-- 통과|실패 <이름> <초>s` 를 바로 찍는다
python3 studio/tests/run_all.py --sessions   # 표시한 5개(c2·c3·c3b·c4·pageflowui)까지 66개 - c2·c3·c3b·c4 는 실제 claude 턴, claude CLI 설치·로그인 필요
NEXA_TEST_DIR=/tmp/nexa-tests python3 studio/tests/run_all.py   # 산출물 자리를 밖으로
python studio/tests/verify.py --level quick|full   # 검증 진입점(무인 개발) - 요약 표만 본다(아래 "검증 진입점")
```

`run_all.py` 의 `TESTS` 는 66개이고, 그중 네 번째 값(claude 필요)이 참인 5개(`c2`·`c3`·`c3b`·`c4`·`pageflowui`)는 `--sessions` 를 줄 때만 돈다. `pageflowui` 는 claude 를 쓰지 않는 헤드리스 Chrome 시험인데 지금 그렇게 표시돼 있어 기본 묶음·`verify.py --level full` 에서 빠진다.

| 이름 | 파일 | 확인하는 것 | 필요 |
|---|---|---|---|
| i18n | `i18n_check.js` | `i18n.js` 문법 · 사전 중복 키 · 번역 표본 | Node |
| smoke | `smoke_run.py` + `smoke.js` | 허브 로그인 → 시작 페이지·Studio(중계)의 주요 단추 50여 단계를 헤드리스 Chrome 으로 눌러 본다(콘솔 오류 0). 데모 작업 공간을 만든다 | Node, Chrome |
| codex | `codex_adapter_test.py` | 0.22.22 - Codex 어댑터: `turn_cmd` 가 wsession 의 키워드 인자를 모두 받음, Windows 에서 `codex-code-mode-host.exe` 가 있는 실행 파일(앱 동봉) 우선, `config.toml` 의 `[windows] sandbox` 옮겨 적기, 턴 프롬프트 `{shell}` 자리·어댑터별 안내. Codex 설치·로그인 없이 돈다 | - |
| engcommit | `engine_commit_test.py` | 0.22.27 - 엔진 세션 턴 뒤 처리: 세션이 `--commit auto` 로 done 하면 허브가 worktree 변경을 대신 커밋하고 해시를 적음(`EngineProfile.commit_for`, 임시 저장소·worktree), 변경 없으면 커밋 없음 · 세션이 스스로 open 으로 되돌린 항목은 큐가 다시 보내지 않고 사람이 손대면(reply 등 updated 변화) 다시 보냄(`EngineQueueSource.returned_by_session`) · 0.22.28 (d) 세션이 끊긴 채 남은 `working` 을 새 세션 시작(`check_start` → `engine_requests.reclaim_stale`) 때 `open` 으로 되돌리고 새 세션이 받음(`awaiting` 아님) (e) 세션용 실행 파일 `.nexa/engine_request.py status` 가 큐 대신 `.nexa/outbox/` 에 적고 턴 끝에 `EngineProfile.apply_outbox` 가 반영 | git |
| pulse | `pulse_test.py` | 0.22.38 - 처리 중 턴의 맥박(`WebSession.pulse`, `/api/engine/session/pulse`): 가짜 에이전트(도구 하나를 3초 '실행'하는 NDJSON)로 한 턴을 돌려 도구 중 `tool{name·summary·sec}`·`alive`·`turnSec`, 결과 뒤 `tool` 없음, 프로세스가 끝나면 `alive` 거짓, 처리 중이 아니면 `{state}` 만, `info().pulse` | - |
| guard | `settings_guard_test.py` | 0.22.24 - `paths.remember` 가드: OS 임시 폴더 안 작업 공간은 `NEXA_SLIDE_USER_DIR` 격리가 없으면 실제 `settings.json` recent 에 올리지 않는다(APPDATA/XDG 를 임시로 바꿔 하위 프로세스로 확인) | - |
| reqcli | `engine_request_cli_test.py` | 0.22.24 - 엔진 요청 CLI: `--body-file <파일>`·`-`(stdin)로 여러 줄·`< > \| &` 본문 보존, pyenv-win 래퍼에 잘린 값(`\|\| goto :error`) 거부, `status applied --applied-commit`(옛 `--commit` 도 appliedCommit), `--reply-file` | - |
| regress | `engine_regress_test.py` | 0.22.24 - 엔진 요청 검증 ④ `engine_regress.py`: 엔진을 `git clone --local` 로 복제해(저장소 밖) example 사본을 `recent` 에 등록하고 (a) 변경 없음 → 0 (b) `lecture` 토큰 하나 변경 → demo 7장 모두 unexpected·1 (c) `--allow demo` 0 / `demo:1` 1 (d) 깨진 덱 → failed·2 (e) 원본 mtime 불변 (g) 사본 삭제·`--keep`·기준 엔진 재사용 | python-pptx |
| wizard | `template_wizard_test.py` | 0.22.26 - 회사 템플릿 마법사(엔진 요청 #3): `palette` 파생·대비 단위 시험, `POST /api/project {action: template}` → example 사본(저장소 밖)에 `templates/<이름>/template.json`·`assets/brand/logo.png`·`nexa-slide.json` 3종, `resolve_tokens` 색 일치, `export_pptx --out` 의 `srgbClr` 에 primary, 엔진 이름·PNG 아님·없는 세트 거부, 금지 키(tokens·sizes·check·design) 무시·경고, 엔진과 같은 이름 폴더 무시, 전용 글꼴 파일 → `fonts/`+`fontPresets`, 비관리자 권한(최근 작업만), 작업 공간 서버의 `/api/templates`·`/api/home`·`/api/preview` 에 회사 템플릿, 엔진 저장소 `git status` 불변 | python-pptx |
| e3 | `e3_manual_test.py` | 수동 엔진 세션(`watch_engine_requests`) - 1회·stream 하트비트, `/api/engine` state=manual, 웹 엔진 세션 시작 거절, already-watched | |
| share | `share_test.py` | 0.22.25 - 보기 전용 공유 링크(엔진 요청 #2): example 사본을 허브로 열고 관리자가 `POST /api/share` → 로그인 없이 `/s/<토큰>/` 200 · `/api/deck` 응답에 `notes`·숨김 장 없음 · `tokens.json`·`fontcss`(접두 붙은 `/wsfonts/`)·덱이 참조한 그림 200 · 허용 밖 경로(`/api/decks`·다른 덱·`nexa-slide.json`·`index.html`)와 POST/PUT 403 · 비밀번호 링크 오답 5회 → 429 잠금, 정답 → 쿠키 → 200 · 회수 410 · 만료(`share.json` 의 `expires` 과거) 410 · 잘못된 토큰 404 와 본문 같음 · 일반 사용자 own 만·남의 링크 회수 403·`shareCreate: admin` 403 · 접근 로그에 토큰 원문 없음·이벤트 있음 · (Chrome 있으면) `view.html` 콘솔 오류 0 | (Chrome·Node 는 선택) |
| e4 | `e4_manual_stop_test.py` | 수동 세션 수명 - 읽는 쪽이 닫히면 종료(`procutil.StdoutWatch`), `--takeover` 가 이전 감시를 끝냄, 웹 [끊기](`/api/engine/session stop`), 작업 공간 `watch_requests` 도 같음 | |
| englist | `englist_test.py` | 서버 작업 카드 최근 5건·`total`, `GET /api/engine/requests?q=`·`?status=`, `/engine` 페이지(검색·강조·상태 칩·펼치기·거절·삭제) | Node, Chrome |
| editor | `editor_ui_test.py` + `scenarios/*.json` | 편집기 UI — 시험용 작업 공간(덱 4개)을 만들어 작업 공간 서버(5667)를 띄우고 시나리오를 돌린다: 그림 삽입(API·Ctrl+V·끌어다 놓기), 삽입 패널(도형·다이어그램·차트·아이콘 타일), 표 행·열 단추·글머리 감지 스위치, 묶기/풀기, 링크·그림자·자르기 속성·발표자 보기, 명령 팔레트·접는 절·스마트 가이드, 글꼴 세트 선택 상자 넘침, 요청 기록 창(퍼지·단어 단위·정규식 토글) | Node, Chrome |
| tidy | `tidy_test.py` | 작업 공간 정리·보관(`tidy.py`) — 산출물·참조 없는 그림(백업 참조 표시)·고아 첨부·세션 로그·백업 보고, clean(옮김)·restore·purge, archive zip 제외 규칙, 작업 공간 서버 `/api/tidy`, 요청 첨부 삭제(discard·update) | - |
| enginetidy | `engine_tidy_test.py` | 엔진 개발 영역 정리(`engine_tidy.py`) — 고아 첨부·worktree 첨부 사본(끝난 요청만)·회귀 사본·임시 파일·최근 N개 밖 로그·시험용 worktree 보고, 남길 것(열린 요청 첨부·새 파일·기준 엔진 사본·outbox) 제외, 고른 범주만 지움, 배포 중이면 로그·worktree 건너뜀(격리 사용자 설정 폴더) | - |
| deck | `deck_test.py` | 덱 관리(`deck_admin`) — 짧은 해시 id 생성, 복제(content 포함), 시작 덱(`startDeck`)·목록 ★, 작업 공간 서버 `/api/decks` copy·start | - |
| vba | `vba_test.js` | 0.25.3 - VBA 실행기(`vba.js`): 셀에서 부르는 Function·제어문·배열·Range 인자·ByRef·내장 함수, 못 쓰는 문법은 엑셀 저장값 유지(25가지) · 0.25.8 보안 한도(배열·문자열·깊이·Like 폭주·깨진 모듈)·Worker 주고받기(pack·serve)·계산 중(Pending) 칸은 저장값 유지 | Node |
| tplrec | `template_rec_test.py` + `scenarios/tplrec_test.json` | 0.25.15 - 템플릿 추천: 점수(사용·미리 보기·비슷한 색 순서, 중복 묶음), 시작 페이지 추천 7개 + 회사 템플릿 만들기 + 더 보기(양식·템플릿 탭) | - |
| pptstart | `pptx_start_test.py` | 0.25.14 - PPT 파일로 시작: 계획(`--pptx-import`, 시작용 내용 빠짐·이상한 이름 무시·시트 제외), 만들기(가져온 덱이 첫 덱·content 원본 없음), 시작용 교안과 함께면 거절 | python-pptx |
| pyshim | `py_shims_test.py` | 0.25.19 - 세션 PATH 맨 앞 python3·python 대리 파일(procutil.py_shims): cmd·PowerShell·Git Bash 에서 python3 = 서버의 파이썬 | - |
| tmpfiles | `tmpfiles_test.py` | 임시 파일(`tmpfiles.py`): `temp_dir` 정상·예외 모두 지움, `process_dir` 프로세스 끝에 지움, `leftovers`·`sweep` 은 엔진 이름·하루 넘은 것만(다른 앱 `nexa-*` 제외), `engine_tidy` `temp` 범주 보고·지움, `status.py --json` 의 `temp` | - |
| sheetfont | `sheet_font_test.py` + `scenarios/sheetfont_test.json` | 0.25.18 - 시트 글꼴: 문서 fontPreset → xlsx 기본 글꼴, 셀 font(역할 mono·heading·이름) → 글꼴 이름, 세트 없으면 엑셀 기본, 가져오기 칸 글꼴. 화면: 글꼴 상자·문서 글꼴 세트 칩 | - |
| vbasafe | `vba_safety_test.py` | 0.25.8 - VBA 보안: 위험 코드 검사 화면(vba.js)·Python 같은 결과, 내보내기는 늘 소스로 다시 쓴 프로젝트(p-code·`__SRP_` 버림, 판 0xFFFF), `--no-macros` → .xlsx, 깨진 프로젝트는 매크로 없이(시험 안에서 만든 프로젝트) | Node |
| (수동) xlsm_crosscheck | `xlsm_crosscheck.py <원본.xlsm> [--keep 폴더] [--no-excel]` | 0.25.2~ - 가져오기 → Python·JS(+VBA) 계산 = 엑셀 저장값 → 내보내기 → 다시 가져오기(문서 같음) → VBA 모듈 소스 · 칸 서식(`xlsx_styles.py`) · 엑셀이 있으면 원본·저장본을 COM 으로 다시 계산해 수식·값·숨김·필터·이름·그림·열 너비·행 높이 대조(`xlsm_dump.ps1`), VBA 고친 판을 엑셀이 계산하는지까지. 원본은 읽기만 | Node, (엑셀은 선택) |
| (수동) shift_bench | `shift_bench.py <작업 공간> <preset|->` | 글 세로 위치 대조 — 상자·타원(흰 글)을 크기×줄 높이로 깔고 PowerPoint 렌더와 브라우저 캡처의 글자 세로 중심 차이를 재 `shift = size×(a×lh+b)` 를 맞춘다(보정이 맞으면 a≈0·b≈0, 잔차 ±1px) | PowerPoint, Chrome, Pillow |
| runs · effect | `runs_test.py` · `effect_test.py` | 인라인 강조 겹치기(`common.runs` ↔ `render.runs`, 취소선·첨자·형광펜·글자 링크 포함) · 그림 프레임 효과 PPTX XML·CSS | Node |
| docstruct | `docstruct_test.py` | 0.22.11~12 - 숨김 슬라이드(`show=0`)·구분(섹션 `p14:sectionLst`)·문서 속성·도형 테두리 점선(`prstDash`)·액자 색·SVG 그림(`svgBlip`)·글 표기 PPTX XML, 표 셀별 채움·테두리·격자 PPTX·render.js | Node |
| (editor) opsave · sheetops | `scenarios/opsave_test.json` · `sheetops_test.json` | 0.25.24 - 큰 문서의 화면 저장 = 작업 저장(`POST /api/ops`) · 두 창 · 지운 요소 고침 · 실패 시 `PUT ?merge=1` · 문턱 200KB(UTF-8 바이트) · 저장하는 사이 더 고침(f - 첫 작업 응답이 온 순간의 dirty 로 판정) | editor 묶음 |
| (editor) richedit | `scenarios/richedit_test.json` | 슬라이드 글 편집 = 공용 글 편집 엔진 `nexa-text`(PG-108) - 보이는 서식으로 편집·표기 그대로 보존·Ctrl+B·Enter·표기로 못 적는 서식 알림·도형 글·실행 취소, 표 칸 편집(Tab), 글 편집 중 서식 줄 | editor 묶음 |
| (editor) switch_save | `scenarios/switch_save_test.json` | 저장이 가는 중에 다른 덱으로 넘어가도 앞 덱의 남은 편집을 잃지 않고 다음 저장이 409 가 아님(226d768 재현) | editor 묶음 |
| (editor) 그 밖 | `scenarios/*.json` | `editor_ui_test.py` 가 `scenarios/` 의 시나리오 파일을 모두 한 번에 돌린다 - 시트(`sheet*_test`)·원장(`ledgerorder_test`)·실시간(`live_test`)·병합 편집(`merge_edit_test`)·제안(`proposal_test`)·요청 기록(`reqhist_test`) 등 | editor 묶음 |
| (editor) ux3 | `scenarios/ux3_test.json` | 0.22.15 - 내용 유지 유형 전환·섹션 접기·자동 정리·넘침 경고·차트 데이터 표 | editor 묶음 |
| (editor) ux6 | `scenarios/ux6_test.json` | 0.22.18 - 표 이동 띠·✥ 손잡이·행/열 띠 선택·경계 끌기·줄무늬·행 높이 맞춤·그림 톤·도형 빛 | editor 묶음 |
| tableobj | `tableobj_test.py` | 0.22.17 - 표 객체 리졸버 우선순위·span·변환 왕복·PPTX 셀 서식(크기·세로·여백·기울임·테두리·병합). 편집기 쪽은 `scenarios/ux5_test.json`(셀 클릭·Shift/Ctrl·채움·자동 변환·셀 편집·Tab·행 삽입·병합·렌더 표로 변환·표 객체 타일) | Node |
| uxpack | `uxpack_test.py` | 0.22.14 - 검사 대비(t6)·대체 텍스트(t7), PPTX `descr`, 유인물·노트 PDF(Chrome). 편집기 쪽은 `scenarios/ux2_test.json`(찾기/바꾸기·서식 복사·가져오기·노트 칩·alt·펜) | Node·Chrome |
| chart | `chart_test.py` | 0.22.13 - 누적 가로·100% 누적·콤보(`c:lineChart`, 보조 축 둘째 `c:valAx`)·축 제목·숫자 형식(`formatCode`) PPTX XML, render.js 같은 종류 SVG·`chartFmt`·`comboLines` | Node |
| merge | `deckmerge_test.py` | 덱·시트 3-way 병합(`deckmerge`, 동시 편집 1단계) - 요소·속성·셀 단위, 삭제 대 수정, 순서, 수식 계산값 골든 | - |
| mergesave | `merge_save_test.py` | 병합 저장(`PUT ?merge=1`·`save_deck`) - 편집기 둘·AI 대 사람(사람 우선)·원장 evidence·`--no-merge` 409·no-base·시트 셀 · 0.25.26 시트 구조 작업 뒤 옛 판 저장 | - |
| ops | `deckops_test.py` | 작업(op) 저장(`deckops`, 동시 편집 3-4) - 저장본 → 지금 차이를 작업으로·남의 변경 위에 얹기(수정 > 삭제·되살리기·버리기) 골든, 화면 `nexa-merge.js` 와 같음 | - |
| sim | `collab_sim.py --seed 1` | 다중 창 시뮬레이터(동시 편집 3-5) - 창 3개가 무작위 편집을 작업 저장·PUT 병합으로 섞어 보내도 자기 몫을 잃지 않고 같은 문서로 모임(덱·시트), 끝에 원장 재생 | - |
| ledger | `ledger_verify_test.py` | 0.25.25 - 원장 재생(`ledger verify`) - 사슬·백업·작업 저장 재생·끝, 변조 감지, 백업 삭제, replay 크기 한도·시트 struct, 요소 순서·quiet 줄, `/api/changes` 에 replay 없음 | - |
| struct | `sheet_struct_test.py` | 시트 행·열 구조 작업(`sheet_struct`, 동시 편집 3-2) - 셀 키·병합·너비·틀 고정·수식 참조 골든, 화면 `shiftAxis` 와 같음 | - |
| autostart | `autostart_test.py` | 허브 자동 시작(`service.py autostart`) - 로그온 시 실행 명령·worktree·작업 공간 거절(이 PC 설정은 바꾸지 않음) | - |
| deploy | `engine_deploy_test.py` | 엔진 배포(`engine_deploy`) - 계획·병합 커밋·push·적용됨·충돌 시 main 불변·겹치는 미커밋 변경·새 실패만 막는 시험 비교(임시 저장소) | git |
| englink | `engine_link_test.py` | 엔진 요청 ↔ 원 요청 연결(engineRequest 배지)·done 알림·applied 자동 재개 | - |
| content_i18n | `content_i18n_test.py` | 견본 내용 언어(`content_i18n`) - `layout_samples --lang en` · `/api/slidetypes?lang=en` · `tr()` | - |
| sheetcalc | `sheetcalc_test.py` | 시트 수식 계산기(`sheet_calc`·`sheetcalc.js` 같은 사례 174개) | Node |
| sheetrt | `sheet_roundtrip_test.py` | 시트 엑셀 왕복(내보내기 → 가져오기 - 값·수식·서식·병합·숨김·유효성·조건부 서식·메모·넘침·표) | - |
| fetch | `fetch_asset_test.py` | 0.25.27 - 공개 웹 파일 가져오기(`fetch_asset`) - https·공인 주소만·리다이렉트 재검사·크기·`assets/`·`fonts/` 만·내용 검사·`--force` 백업·`--brand`·웹 검색 허용 세션만(인터넷 접속 없음) | - |
| textmodel | `nexa_text_check.js` | 글 편집 엔진 `nexa-text` 모델 연산(runs 정규화·넣기·지우기·쪼개기·합치기·서식) | Node |
| textui | `nexa_text_ui_test.py` | `nexa-text` 입력(헤드리스 Chrome · contenteditable 호스트 · 파일로 연다) | Chrome |
| textime | `nexa_text_ime_test.py` | `nexa-text` 한글 조합(CDP `Input.imeSetComposition`·`insertText`·`dispatchKeyEvent` 로 실제 조합 이벤트) - PG-032 | Chrome |
| pagedoc | `page_doc_test.py` | 페이지 문서 `page_doc.py` - 새 문서·검사·정규화 | - |
| pagerender | `page_render_check.js` | 페이지 렌더 `page-render.js` - 블록 → 화면(스타일·목록·표·그림) 규칙 | Node |
| pageflow | `page_flow_check.js` | 페이지 쪽 나눔 계산 `page-flow.js` plan - 밀기·문단 줄 나눔·표 행 나눔·외톨이 줄(PG-102) | Node |
| pageflowui | `page_flow_ui_test.py` | 쪽 나눔 화면 `page-flow.js` - 서버 없이 `page_flow_page.html` 을 파일로 열어 빈 자리 끼우기(밀기·빈 줄·빈 행)·글 편집 유지·걷기(PG-102). **지금 `--sessions` 에서만 돈다**(위) | Chrome |
| pagedocx | `page_docx_test.py` | 페이지 DOCX 내보내기 `export_docx.py` - 구조(XML) 사례 | - |
| pagetpl | `page_templates_test.py` | 페이지 템플릿 11종 `page_templates.py` - 형식·미리 보기·만들기 | - |
| pagemerge · pagemergejs | `pagemerge_test.py` · `pagemerge_check.js` | 페이지 문서 병합(`deckmerge`) - 블록·표·쪽 설정·머리말·스타일 단위 · 화면판(`nexa-merge.js`)이 같은 사례 | (js 는 Node) |
| pagediff | `pagediff_test.py` | 페이지 문서 변경 비교 `deckdiff.diff_page` | - |
| pageword | `page_word_test.py` | 페이지 DOCX 를 Word 로 열기(템플릿 11종·종합 문서·PDF) - Word 가 없거나 사용자 Word 가 떠 있으면 SKIP | (Word 는 선택) |
| hubpage | `hub_page_test.py` | 첫 문서로 페이지 - `init_workspace --kind page` · 허브(켬/끔) 계획·만들기 · 시작 페이지 종류 단추(격리 허브 5799) | - |
| pageimport | `page_import_test.py` | Word 문서 가져오기 `import_docx` - 우리 내보내기와 왕복 | - |
| pagewordimp | `page_word_import_test.py` | Word(COM)가 만든 .docx 가져오기 - 스타일·서식·목록·표 병합·그림·머리말·경고(Word 없으면 SKIP) | (Word 는 선택) |
| pageui | `page_ui_test.py` | 페이지 문서 화면(헤드리스 Chrome · 포트 5667) - 숨김 스위치(끈 작업 공간)·만들기·저장 검사·종류별 이동·`page.html` 편집(쪽 설정·표·내보내기·그림·서식·병합)·쪽 나눔·인쇄·도형/글 상자·AI 요청 패널·다단·각주·확대/축소·새 문서 창(템플릿·파일 가져오기)·두 창. 다단 문서의 Chrome PDF 쪽 수 차이는 `KNOWN`(아래) | Chrome |
| race | `race_test.py` | 서버 동시 시작 경쟁(`START_LOCK`) | |
| c4 | `c4_doc_test.py` | 웹 세션이 첨부 Word·Excel·PDF 를 읽어 답하는 실제 턴. 표본 문서 `real.xlsx`·`report.pdf` 는 저장소에 없다 — `NEXA_TEST_DOCS=<폴더>` 로 주고, 없으면 SKIP | claude CLI(`--sessions`) |
| thread | `thread_test.py` | 후속 요청(대화) 문맥(`thread_context`)·턴 프롬프트 | smoke 가 만든 데모 작업 공간 |
| c3 · c3b | `c3_git_test.py` · `c3b_git_deny_test.py` | 웹 세션 git 기록·push·저장소 루트 권한(허용/거절 설정) — 권한 템플릿 확인 뒤 실제 턴까지 | git, claude CLI(`--sessions`) |
| c2 | `c2_web_test.py` | 웹 세션이 실제로 `claude -p` 턴을 돌려 요청을 처리 | claude CLI(`--sessions`) |

**헤드리스 실행기 `smoke.js`**(0.24.1): `node smoke.js <시나리오.json> [<시나리오.json> …]`
- 시나리오 = `{base, login?: {id, password}, ignoreErrors?, pages: [{url, wait?, steps: [{name, js, wait?, dump?, shot?}]}]}`.
- **여러 시나리오를 한 번에** - Chrome 은 한 번만 띄우고, 시나리오마다 **새 브라우저 컨텍스트**(저장소·쿠키 분리)에서 돈다. `editor_ui_test.py` 는 `scenarios/*.json` 을 한 번에 넘긴다.
- **`page.wait` 은 상한** - 페이지에 들어간 뒤 네트워크가 조용해지면(진행 중 요청 0 이 250ms) 그보다 일찍 첫 단계로 넘어간다. 편집기면 슬라이드가 그려질 때까지 기다린다.
- **단계 `js`** 는 페이지 안에서 평가되는 식(`await` 가능, `return` 이 있으면 그대로). 결과가 `false` 거나 **문자열이면 FAIL**(문자열 = 실패 사유, 200자까지 출력) - 결과 글을 그대로 보이려면 `dump: true`. `shot: "<경로>"` 는 그 단계 뒤 화면을 PNG 로.
- **`until(() => 조건, 최대ms = 5000)`** - 단계 안에서 쓸 수 있다. 조건이 참이 될 때까지 50ms 마다 다시 보고(예외는 거짓으로), 참이면 그 값을, 시간이 지나면 `false` 를 돌려준다. 고정 `setTimeout` 대신 쓴다(참이 되면 바로 넘어간다). 저장 결과 확인은 `await until(async () => (await (await fetch('/api/deck/…')).json()).…)`.
- 콘솔 error·예외가 하나라도 있으면 그 페이지 FAIL. 기본으로 빼는 것: favicon·`net::ERR_ABORTED`·알림·그림·글꼴 파일 404, 그 밖은 시나리오 `ignoreErrors`(정규식 글).
- 시나리오마다 **`## RESULT <파일 이름> OK|FAIL <실패 수>`** 줄을 찍는다(`editor_ui_test.py` 가 이 줄로 시나리오별 결과를 모은다). 종료 코드는 하나라도 실패면 1.
- 단계 `js` 를 한 줄 주석(`// …`)으로 끝내지 않는다 - 실행기가 감싸는 닫는 괄호와 같은 줄이 되면 주석이 된다(0.24.1 에서 실행기 쪽도 줄바꿈을 넣었다).
- Chrome 경로는 파일 머리의 `CHROME`, 디버그 포트는 실행마다 9333~11332 중 하나(앞선 실행의 Chrome 에 붙지 않게).

렌더 동일성은 별도: `python3 studio/check_parity.py -W example`(render.js ↔ common/export_pptx), `python3 studio/export_pptx.py --selftest --workspace example`, PowerPoint 가 있으면 `render_pptx.ps1`·`compare.py` 로 픽셀 대조([mechanism.md](../mechanism.md)). 줄바꿈 대조는 `pwsh -File studio/lines_pptx.ps1 -Pptx out/<덱>.pptx`(PowerPoint COM 으로 글 상자마다 실제 줄 수를 JSON 으로) 와 브라우저의 `.rs-p` 높이/줄 높이를 비교한다.

**시험 잠금(0.22.41)**: 시험들은 고정 포트(5799·5667·9333 등)와 같은 임시 폴더를 쓰므로 둘이 동시에 돌면 서로의 서버에 물어 엉뚱하게 실패한다(엔진 배포 ↔ 엔진 세션). 그래서 이 PC 에서 시험 실행은 한 번에 하나다 - `run_all.py` 와 각 시험 파일이 머리에서 `import testlock` 으로 `<임시 폴더>/nexa-slide-tests.lock` 을 잡고, 잡혀 있으면 `== 대기 · …` 를 찍고 기다린다(최대 `NEXA_TEST_LOCK_WAIT` 초, 기본 2400). 잡은 프로세스가 죽으면 저절로 풀린다.

시험을 더하려면: `studio/tests/<이름>_test.py` 를 만들고(머리는 `e4_manual_stop_test.py` 를 본뜬다 — `STUDIO = parents[1]`, `WORK`/`USER`/`PROJ`, `check()`, **`import testlock`**), `run_all.py` 의 `TESTS` 에 한 줄 넣는다. OS 임시 폴더는 `tmpfiles.temp_dir(prefix)`(with 블록) 또는 `tmpfiles.process_dir(prefix)`(끝날 때 지움)로만 만든다 - 직접 `mkdtemp` 금지, 그 안의 파일은 닫고 끝낸다.

**임시 파일 누수 시험**: `run_all.py` 가 시험마다 전후로 Temp 의 엔진 이름(`tmpfiles.PATTERNS`)을 비교해 새로 남은 것이 있으면 `FAIL 임시 파일 누수 …` 로 그 시험을 실패로 하고 지운다. 시작 때는 하루 넘은 잔여물을 쓸어낸다. Temp 에 쌓이면 로그온이 느려진다(smoke.js 프로필 2,000개 → 4~5분, [temp-files-design.md](temp-files-design.md)).

**서버 프로세스 누수 시험**: `run_all.py` 는 묶음마다 전후로 **이 엔진 사본의** `studio/server.py` 로 떠 있는 프로세스(명령줄에 그 경로가 든 python)를 세어, 새로 남은 것이 있으면(방금 내린 서버를 3초까지 기다린 뒤) `FAIL 서버 프로세스 누수 n개(pid …)` 로 그 묶음을 실패로 한다. 프로세스는 내리지 않고 알리기만 한다 - 그 시험의 정리 경로(작업 공간 `nexa.py stop`)를 고친다. 다른 worktree·운영 엔진의 서버는 경로가 달라 세지 않고, 프로세스 목록을 못 읽으면 판정하지 않는다. 남은 서버 찾기·내리기는 [operation.md](../operation.md#포트프로세스-점검).

**`KNOWN` 줄**: 시험이 알려진 한계를 `KNOWN <설명>` 으로 찍으면 실패로 치지 않고 `run_all` 요약에 그 줄이 그대로 보인다(판정 줄 `OK`·`FAIL`·`SKIP`·`KNOWN`). 지금은 `pageui` 의 "다단 문서 Chrome PDF 쪽 수 ≠ 화면 쪽 수"(DP-P17) 하나다.

## 검증 진입점 - `verify.py`

무인 개발([autodev.md](autodev.md))이 읽는 요약 하나. `python studio/tests/verify.py --level quick|full [--fail-fast]`.

| 수준 | 단계(싼 것부터, 실패해도 끝까지) |
|---|---|
| `quick` | `pycompile`(바뀐 .py, 경고도 실패) · `nodecheck`(바뀐 .js) · `parity`(`check_parity -W example`) · `runall-quick`(브라우저 없이 도는 빠른 묶음 - `verify.py` 의 `QUICK` 목록, 약 1분) |
| `full` | `pycompile` · `nodecheck` · `parity` · `runall`(기본 묶음 전체) · `regress`(`engine_regress` - 등록된 작업 공간 덱의 PPTX XML 이 main 과 같은가) |

- "바뀐 파일" = `origin/main` 과 갈라진 뒤 바뀐 것 + 미커밋·새 파일.
- 결과는 `PASS`·`FAIL`·`SKIP`(판정 불가 - 통과가 아니다)·`TIMEOUT`(상한 = 최근 3회 중앙값 × 3, 최소 120초·최대 3600초, 이력이 없으면 단계별 기본값. testlock 대기 시간은 뺀다 → 그 단계 프로세스 트리만 끈다).
- 출력: `<공용 루트>/out/verify/<시각>/summary.md`(단계가 끝날 때마다 덧붙임 · FAIL/TIMEOUT 아래 첫 오류 5줄) · `<단계>.log` · `out/verify/history.tsv`. 표준 출력은 요약 표만, 종료 코드 = 실패 단계 수. 진행은 작업판(`studio/devboard.py` → `out/status/now.md`).
- 자체 점검용 환경 변수: `NEXA_VERIFY_INJECT="parity=fail,pycompile=sleep:30"`(일부러 실패·지연) · `NEXA_VERIFY_LIMIT="pycompile=5"`(상한 초).
