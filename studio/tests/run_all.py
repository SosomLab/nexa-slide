# -*- coding: utf-8 -*-
"""nexa-slide 시험 모음 실행기 - 격리된 허브(5799)·작업 공간을 띄워 API·화면(헤드리스 Chrome)·세션 수명을 확인한다. docs/dev/tests.md

    python3 studio/tests/run_all.py                 # 기본 묶음(claude 가 필요한 것은 뺀다)
    python3 studio/tests/run_all.py --sessions      # 웹 세션 시험(c2 - claude CLI·로그인 필요)까지
    python3 studio/tests/run_all.py smoke e4        # 이름 일부로 고르기
    python3 studio/tests/run_all.py --exact e3 deck # 이름 그대로 고르기(엔진 배포가 실패 묶음만 다시 돌릴 때)
    NEXA_TEST_DIR=<폴더>                            # 시험 산출물 자리(기본 <임시 폴더>/nexa-slide-tests - 저장소 밖이어야 한다)

순서가 뜻이 있다: smoke 가 데모 작업 공간(_work/projects/nexa-slide-demo)을 만들고 thread 가 그것을 쓴다.
필요: Python 3.10+, Chrome(헤드리스 화면 시험), Node(헤드리스 실행기·i18n 검사). 운영 포트(5599·5600~)는 쓰지 않는다(5799·565x·5799).
"""
import argparse
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import testlock  # noqa: F401 - 이 PC 에서 시험은 한 번에 하나(고정 포트·임시 폴더를 같이 쓴다, testlock.py)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import tmpfiles  # noqa: E402
TESTS = [  # (이름, 실행, 설명, claude 필요)
    ("i18n", ["node", "i18n_check.js"], "i18n.js 문법·중복 키·번역 표본", False),
    ("smoke", [sys.executable, "smoke_run.py"], "허브·Studio 헤드리스 클릭 스모크(데모 작업 공간 생성)", False),
    ("codex", [sys.executable, "codex_adapter_test.py"], "Codex 어댑터 - turn_cmd 인자·host 있는 실행 파일·windows.sandbox·{shell} 프롬프트(설치 불필요)", False),
    ("engcommit", [sys.executable, "engine_commit_test.py"], "엔진 세션 - 허브 대신 커밋(commit auto)·세션이 되돌린 open 은 다시 보내지 않음", False),
    ("pulse", [sys.executable, "pulse_test.py"], "처리 중 턴의 맥박(wsession.pulse) - 긴 도구 동안 지금 도구·경과·프로세스 생존(가짜 에이전트)", False),
    ("guard",[sys.executable, "settings_guard_test.py"], "paths.remember 가드 - 임시 폴더 작업 공간은 격리 없이는 최근 작업에 올리지 않음", False),
    ("reqcli", [sys.executable, "engine_request_cli_test.py"], "엔진 요청 CLI - --body-file/stdin·래퍼에 잘린 값 거부·applied --applied-commit·--reply-file", False),
    ("regress", [sys.executable, "engine_regress_test.py"], "엔진 회귀(검증 ④) - 복제 엔진에서 변경 없음 0 · 토큰 변경 1(장별) · --allow · 깨진 덱 2 · 원본 불변", False),
    ("wizard", [sys.executable, "template_wizard_test.py"], "회사 템플릿 마법사(0.22.26) - palette 파생·/api/project template·작업 공간 파일 3종·resolve_tokens·PPTX srgbClr·거부·금지 키·권한·git status 불변", False),
    ("e3", [sys.executable, "e3_manual_test.py"], "수동 엔진 세션(watch_engine_requests) 상태·거절", False),
    ("e4", [sys.executable, "e4_manual_stop_test.py"], "수동 세션 수명 - 파이프 닫힘·takeover·웹 끊기", False),
    ("share", [sys.executable, "share_test.py"], "보기 전용 공유 링크(/s/<토큰>/) - 만들기·열람(노트·숨김 장 없음)·허용 목록·비밀번호 잠금·회수·만료·로그에 토큰 없음", False),
    ("englist", [sys.executable, "englist_test.py"], "서버 작업 목록 - 카드 5건·검색 API·/engine 페이지", False),
    ("editor", [sys.executable, "editor_ui_test.py"], "편집기 UI - 그림·도형·차트·묶음·표·링크·그림자·삽입 패널·팔레트·발표자 보기(scenarios/*.json)", False),
    ("tidy", [sys.executable, "tidy_test.py"], "작업 공간 정리·보관(tidy.py) - 보고·옮김·되돌림·비움·zip, 요청 첨부 정리 API", False),
    ("enginetidy", [sys.executable, "engine_tidy_test.py"], "엔진 개발 영역 정리(engine_tidy) - 고아 첨부·worktree 사본·회귀 사본·오래된 로그·시험용 worktree, 남길 것·배포 중 건너뜀", False),
    ("deck", [sys.executable, "deck_test.py"], "덱 관리(deck_admin) - 짧은 해시 id·복제·시작 덱·목록, /api/decks copy·start", False),
    ("merge", [sys.executable, "deckmerge_test.py"], "덱·시트 3-way 병합(deckmerge, 동시 편집 1단계) - 요소·속성·셀 단위, 삭제 대 수정, 순서, 수식 계산값 골든", False),
    ("mergesave", [sys.executable, "merge_save_test.py"], "병합 저장(PUT ?merge=1·save_deck) - 편집기 둘·AI 대 사람(사람 우선)·원장 evidence·--no-merge 409·no-base·시트 셀", False),
    ("ops", [sys.executable, "deckops_test.py"], "작업(op) 저장(deckops, 동시 편집 3-4) - 저장본 → 지금 차이를 작업으로·남의 변경 위에 얹기(수정 > 삭제·되살리기·버리기) 골든 - 화면 nexa-merge.js 와 같음", False),
    ("sim", [sys.executable, "collab_sim.py", "--seed", "1"], "다중 창 시뮬레이터(collab_sim, 동시 편집 3-5) - 창 3개가 무작위 편집을 작업 저장·PUT 병합으로 섞어 보내도 자기 몫을 잃지 않고 같은 문서로 모임(덱·시트)", False),
    ("tmpfiles", [sys.executable, "tmpfiles_test.py"], "임시 파일(tmpfiles) - temp_dir·process_dir 정리, 엔진 이름·하루 넘은 것만 쓸어내기(다른 앱 nexa-* 제외), engine_tidy temp 범주, 상태 경고", False),
    ("ledger", [sys.executable, "ledger_verify_test.py"], "원장 재생(ledger verify, 동시 편집 3-5) - 사슬·백업·작업 저장 재생·끝, 변조 감지, 백업 삭제, replay 크기 한도·시트 struct, 요소 순서·quiet 줄, /api/changes 에 replay 없음", False),
    ("textmodel", ["node", "nexa_text_check.js"], "글 편집 엔진 nexa-text 모델 연산(runs 정규화·넣기·지우기·쪼개기·합치기·서식) - 페이지 편집기 B1", False),
    ("pagedoc", [sys.executable, "page_doc_test.py"], "페이지 문서 page_doc.py - 새 문서·검사·정규화 - 페이지 편집기 B2", False),
    ("pagerender", ["node", "page_render_check.js"], "페이지 렌더 page-render.js - 블록 → 화면(스타일·목록·표·그림) 규칙 - 페이지 편집기 B2", False),
    ("pageflow", ["node", "page_flow_check.js"], "페이지 쪽 나눔 계산 page-flow.js plan - 밀기·문단 줄 나눔·표 행 나눔·외톨이 줄 - 페이지 편집기 PG-102", False),
    ("pageflowui", [sys.executable, "page_flow_ui_test.py"], "페이지 쪽 나눔 화면 page-flow.js - 빈 자리 끼우기(밀기·빈 줄·빈 행)·글 편집 유지·걷기 - 헤드리스 Chrome - PG-102", True),
    ("pagedocx", [sys.executable, "page_docx_test.py"], "페이지 DOCX 내보내기 export_docx.py - 구조(XML) 사례 - 페이지 편집기 C1", False),
    ("pagetpl", [sys.executable, "page_templates_test.py"], "페이지 템플릿 11종 page_templates.py - 형식·미리 보기·만들기 - 페이지 편집기 C2", False),
    ("pagemerge", [sys.executable, "pagemerge_test.py"], "페이지 문서 병합(deckmerge) - 블록·표·쪽 설정·머리말·스타일 단위 - 페이지 편집기 C3", False),
    ("pagemergejs", ["node", "pagemerge_check.js"], "페이지 문서 병합 화면판(nexa-merge.js) - pagemerge 와 같은 사례", False),
    ("pagediff", [sys.executable, "pagediff_test.py"], "페이지 문서 변경 비교 deckdiff.diff_page - 페이지 편집기 C3", False),
    ("pageword", [sys.executable, "page_word_test.py"], "페이지 DOCX 를 Word 로 열기(템플릿 11종·종합 문서·PDF) - Word 가 없거나 사용자 Word 가 떠 있으면 SKIP", False),
    ("hubpage", [sys.executable, "hub_page_test.py"], "첫 문서로 페이지 - init_workspace --kind page · 허브(실험 꺼짐/켬) 계획·만들기 · 시작 페이지 종류 단추(격리 허브 5799)", False),
    ("pageimport", [sys.executable, "page_import_test.py"], "Word 문서 가져오기 import_docx - 우리 내보내기와 왕복 - 페이지 편집기", False),
    ("pagewordimp", [sys.executable, "page_word_import_test.py"], "Word(COM)가 만든 .docx 가져오기 - 스타일·서식·목록·표 병합·그림·머리말·경고(Word 없으면 SKIP)", False),
    ("pageui", [sys.executable, "page_ui_test.py"], "페이지 문서 화면(헤드리스 Chrome) - 숨김 스위치·만들기·저장 검사·종류별 이동·page.html 편집·두 창 관찰", False),
    ("textui", [sys.executable, "nexa_text_ui_test.py"], "글 편집 엔진 nexa-text 입력(헤드리스 Chrome · contenteditable 호스트 · 파일로 연다) - 페이지 편집기 B1", False),
    ("textime", [sys.executable, "nexa_text_ime_test.py"], "글 편집 엔진 nexa-text 한글 조합(CDP Input.imeSetComposition·insertText·dispatchKeyEvent 로 실제 조합 이벤트) - 페이지 편집기 PG-032", False),
    ("autostart", [sys.executable, "autostart_test.py"], "허브 자동 시작(service.py autostart) - 로그온 시 실행 명령·worktree·작업 공간 거절(이 PC 설정은 바꾸지 않음)", False),
    ("struct", [sys.executable, "sheet_struct_test.py"], "시트 행·열 구조 작업(sheet_struct, 동시 편집 3-2) - 셀 키·병합·너비·틀 고정·수식 참조(열 전체·행 전체·H2#) 골든 - 화면 shiftAxis 와 같음(sheetstruct_test)", False),
    ("deploy", [sys.executable, "engine_deploy_test.py"], "엔진 배포(engine_deploy) - 계획·병합 커밋·push·적용됨·충돌 시 main 불변·겹치는 미커밋 변경·새 실패만 막는 시험 비교(임시 저장소)", False),
    ("englink", [sys.executable, "engine_link_test.py"], "엔진 요청 ↔ 원 요청 연결(engineRequest 배지)·done 알림·applied 자동 재개", False),
    ("content_i18n", [sys.executable, "content_i18n_test.py"], "견본 내용 언어(content_i18n) - layout_samples --lang en · /api/slidetypes?lang=en · tr()", False),
    ("sheetcalc", [sys.executable, "sheetcalc_test.py"], "시트 수식 계산기(sheet_calc·sheetcalc.js 같은 사례 174개 - 집계·조건·조회·글·날짜·배열·넘침·표·다른 탭·순환 참조)", False),
    ("vba", ["node", "vba_test.js"], "VBA 실행기(vba.js) - 셀에서 부르는 Function·제어문·배열·Range·ByRef·내장 함수·못 쓰는 문법은 엑셀 값 유지", False),
    ("tplrec", [sys.executable, "template_rec_test.py"], "템플릿 추천 점수(0.25.15) - 사용 ×10 · 미리 보기 ×3 · 비슷한 색 ×2 · 중복 묶음", False),
    ("pptstart", [sys.executable, "pptx_start_test.py"], "PPT 파일로 시작(0.25.14) - 새로 만들기 deckFrom → init_workspace --pptx-import → 가져온 덱이 첫 덱", False),
    ("vbasafe", [sys.executable, "vba_safety_test.py"], "VBA 보안(0.25.8) - 위험 코드 검사 화면·Python 같음, 내보내기는 늘 소스로 다시 쓴 프로젝트(p-code 버림)·--no-macros·깨진 프로젝트는 매크로 없이", False),
    ("pyshim", [sys.executable, "py_shims_test.py"], "세션 python3 대리 파일(0.25.19) - 스토어 대리 실행기가 PATH 앞에 있어도 cmd·PowerShell·Git Bash 의 python3 = 서버 파이썬", False),
    ("sheetfont", [sys.executable, "sheet_font_test.py"], "시트 글꼴(0.25.18) - 문서 fontPreset·셀 font(역할·이름) → xlsx 글꼴, 가져오기는 칸 글꼴을 되살린다", False),
    ("sheetrt", [sys.executable, "sheet_roundtrip_test.py"], "시트 엑셀 왕복(내보내기 → 가져오기 - 값·수식·서식·병합·숨김·유효성·조건부 서식·메모·넘침·표)", False),
    ("fetch", [sys.executable, "fetch_asset_test.py"], "공개 웹 파일 가져오기(fetch_asset, 엔진 요청 #17) - https·공인 주소만·리다이렉트 재검사·크기·assets/·fonts/ 만·내용 검사·--force 백업·--brand·웹 검색 허용 세션만(인터넷 접속 없음)", False),
    ("runs", [sys.executable, "runs_test.py"], "인라인 강조 겹치기(runs) - Python·render.js 같은 결과", False),
    ("effect", [sys.executable, "effect_test.py"], "그림 프레임 효과(effect·effectLevel) - PPTX XML(softEdge·glow·roundRect·ellipse·테두리)·render.js CSS", False),
    ("tableobj", [sys.executable, "tableobj_test.py"], "표 객체(table-obj, 0.22.17) - 리졸버 우선순위·span·변환 왕복·PPTX 셀 서식", False),
    ("uxpack", [sys.executable, "uxpack_test.py"], "편집 편의 묶음(0.22.14) - 검사 대비·대체 텍스트, PPTX descr, 유인물·노트 PDF(Chrome)", False),
    ("chart", [sys.executable, "chart_test.py"], "차트(0.22.13) - 누적 가로·100% 누적·콤보(보조 축)·축 제목·숫자 형식 PPTX XML·render.js", False),
    ("docstruct", [sys.executable, "docstruct_test.py"], "문서 구조·마무리(0.22.11) - 숨김·섹션·문서 속성·테두리 점선·액자 색·SVG·글 표기(취소선·첨자·형광펜·글자 링크) PPTX XML·render.js", False),
    ("race", [sys.executable, "race_test.py"], "서버 시작 경쟁(잠금)", False),
    ("c4", [sys.executable, "c4_doc_test.py"], "웹 세션이 첨부 Word·Excel·PDF 를 읽어 답하는 실제 턴(claude · 표본 문서 NEXA_TEST_DOCS)", True),
    ("thread", [sys.executable, "thread_test.py"], "후속 요청(대화) 문맥·턴 프롬프트", False),
    ("c3", [sys.executable, "c3_git_test.py"], "웹 세션 git·push·저장소 루트 권한(허용) + 실제 턴(claude)", True),
    ("c3b", [sys.executable, "c3b_git_deny_test.py"], "웹 세션 git 권한(거절) + 실제 턴(claude)", True),
    ("c2", [sys.executable, "c2_web_test.py"], "웹 세션 실제 턴(claude CLI 필요)", True),
]


def leak_check(before):
    """시험 뒤 새로 남은 것(tmpfiles.PATTERNS) - 방금 끝난 자식이 아직 지우는 중일 수 있어 2초까지 다시 본다."""
    for _ in range(5):
        leaked = sorted(tmpfiles.leftovers() - before)
        if not leaked:
            return []
        time.sleep(0.4)
    return leaked


def main():
    ap = argparse.ArgumentParser(description="nexa-slide 시험 모음")
    ap.add_argument("names", nargs="*", help="이름 일부로 고르기(비우면 기본 묶음)")
    ap.add_argument("--sessions", action="store_true", help="claude 가 필요한 시험도")
    ap.add_argument("--exact", action="store_true", help="이름 일부가 아니라 그대로 고른다(e3 가 c3·c3b 를 끌어오지 않게)")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    work = Path(os.environ.get("NEXA_TEST_DIR") or Path(tempfile.gettempdir()) / "nexa-slide-tests")  # 저장소 밖 - 허브는 엔진 안의 작업 공간을 거절한다
    work.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "NEXA_TEST_DIR": str(work)}
    env.pop("NEXA_SLIDE_WORKSPACE", None)
    hit = (lambda n, t: n == t) if a.exact else (lambda n, t: n in t)
    picked = [t for t in TESTS if (not a.names or any(hit(n, t[0]) for n in a.names)) and (a.sessions or not t[3])]
    print(f"== 묶음 {len(picked)}개: {' '.join(t[0] for t in picked)}", flush=True)
    swept, busy = tmpfiles.sweep()  # 앞선 실행이 시간 초과·Ctrl+C 로 끝나 남긴 것(하루 넘은 tmpfiles.PATTERNS)
    if swept or busy:
        print(f"== Temp 잔여물 정리: 지움 {swept} · 사용 중 {busy}", flush=True)
    results = []
    for name, cmd, desc, _ in picked:
        print(f"\n== {name} · {desc}", flush=True)
        t0 = time.time()
        before = tmpfiles.leftovers()
        r = subprocess.run(cmd, cwd=str(HERE), env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        out = (r.stdout or "") + (r.stderr or "")
        marks = [l for l in out.splitlines() if l.startswith(("OK", "FAIL", "실패", "전부 통과", "SKIP")) or "오류" in l]
        tail = marks[-12:]
        tail = [l for l in marks[:-12] if l.startswith("FAIL")][:12] + tail  # 끝 12줄 밖의 FAIL 줄도 보인다 - 실패 뒤에 OK 가 길게 이어지면 "실패 2" 만 남고 어느 단계인지 안 보였다
        print("\n".join("   " + l for l in tail) if tail else out[-600:])
        rc = r.returncode
        if rc and tail and not any(l.startswith(("FAIL", "실패")) for l in tail):  # 판정 줄 없이 끝났다(예외·강제 종료) - 마지막 출력을 보인다
            print("   -- 판정 줄 없이 끝남(rc %s) · 마지막 출력:\n%s" % (rc, "\n".join("      " + l for l in out.strip().splitlines()[-12:])))
        leaked = leak_check(before)
        if leaked:  # 누수 시험 - 시험이 Temp 에 남긴 것(docs/dev/temp-files-design.md). 지우고 실패로
            print(f"   FAIL 임시 파일 누수 {len(leaked)}개: {', '.join(leaked[:5])}{' …' if len(leaked) > 5 else ''} - studio/tmpfiles.py 로 만들고 지운다")
            for n in leaked:
                tmpfiles.remove(tmpfiles.root() / n)
            rc = rc or 1
        results.append((name, rc, time.time() - t0))
        print(f"-- {'통과' if rc == 0 else '실패'} {name} {time.time() - t0:.0f}s", flush=True)  # 묶음마다 바로 - 엔진 배포가 이 줄로 진행을 보인다
    print("\n---- 결과")
    for name, rc, dt in results:
        print(f"{'통과' if rc == 0 else '실패'}  {name:8s} {dt:5.0f}s")
    bad = [n for n, rc, _ in results if rc]
    print("\n전부 통과" if not bad else f"\n실패: {', '.join(bad)}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
