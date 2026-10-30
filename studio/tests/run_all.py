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
    ("sheetrt", [sys.executable, "sheet_roundtrip_test.py"], "시트 엑셀 왕복(내보내기 → 가져오기 - 값·수식·서식·병합·숨김·유효성·조건부 서식·메모·넘침·표)", False),
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
    results = []
    for name, cmd, desc, _ in picked:
        print(f"\n== {name} · {desc}", flush=True)
        t0 = time.time()
        r = subprocess.run(cmd, cwd=str(HERE), env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        out = (r.stdout or "") + (r.stderr or "")
        tail = [l for l in out.splitlines() if l.startswith(("OK", "FAIL", "실패", "전부 통과", "SKIP")) or "오류" in l][-12:]
        print("\n".join("   " + l for l in tail) if tail else out[-600:])
        results.append((name, r.returncode, time.time() - t0))
        print(f"-- {'통과' if r.returncode == 0 else '실패'} {name} {time.time() - t0:.0f}s", flush=True)  # 묶음마다 바로 - 엔진 배포가 이 줄로 진행을 보인다
    print("\n---- 결과")
    for name, rc, dt in results:
        print(f"{'통과' if rc == 0 else '실패'}  {name:8s} {dt:5.0f}s")
    bad = [n for n, rc, _ in results if rc]
    print("\n전부 통과" if not bad else f"\n실패: {', '.join(bad)}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
