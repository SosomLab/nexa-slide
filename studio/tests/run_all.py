# -*- coding: utf-8 -*-
"""nexa-slide 시험 모음 실행기 - 격리된 허브(5799)·작업 공간을 띄워 API·화면(헤드리스 Chrome)·세션 수명을 확인한다. docs/dev/tests.md

    python3 studio/tests/run_all.py                 # 기본 묶음(claude 가 필요한 것은 뺀다)
    python3 studio/tests/run_all.py --sessions      # 웹 세션 시험(c2 - claude CLI·로그인 필요)까지
    python3 studio/tests/run_all.py smoke e4        # 이름 일부로 고르기
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

HERE = Path(__file__).resolve().parent
TESTS = [  # (이름, 실행, 설명, claude 필요)
    ("i18n", ["node", "i18n_check.js"], "i18n.js 문법·중복 키·번역 표본", False),
    ("smoke", [sys.executable, "smoke_run.py"], "허브·Studio 헤드리스 클릭 스모크(데모 작업 공간 생성)", False),
    ("e3", [sys.executable, "e3_manual_test.py"], "수동 엔진 세션(watch_engine_requests) 상태·거절", False),
    ("e4", [sys.executable, "e4_manual_stop_test.py"], "수동 세션 수명 - 파이프 닫힘·takeover·웹 끊기", False),
    ("englist", [sys.executable, "englist_test.py"], "서버 작업 목록 - 카드 5건·검색 API·/engine 페이지", False),
    ("editor", [sys.executable, "editor_ui_test.py"], "편집기 UI - 그림·도형·차트·묶음·표·링크·그림자·삽입 패널·팔레트·발표자 보기(scenarios/*.json)", False),
    ("tidy", [sys.executable, "tidy_test.py"], "작업 공간 정리·보관(tidy.py) - 보고·옮김·되돌림·비움·zip, 요청 첨부 정리 API", False),
    ("deck", [sys.executable, "deck_test.py"], "덱 관리(deck_admin) - 짧은 해시 id·복제·시작 덱·목록, /api/decks copy·start", False),
    ("englink", [sys.executable, "engine_link_test.py"], "엔진 요청 ↔ 원 요청 연결(engineRequest 배지)·done 알림·applied 자동 재개", False),
    ("runs", [sys.executable, "runs_test.py"], "인라인 강조 겹치기(runs) - Python·render.js 같은 결과", False),
    ("effect", [sys.executable, "effect_test.py"], "그림 프레임 효과(effect·effectLevel) - PPTX XML(softEdge·glow·roundRect·ellipse·테두리)·render.js CSS", False),
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
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    work = Path(os.environ.get("NEXA_TEST_DIR") or Path(tempfile.gettempdir()) / "nexa-slide-tests")  # 저장소 밖 - 허브는 엔진 안의 작업 공간을 거절한다
    work.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "NEXA_TEST_DIR": str(work)}
    env.pop("NEXA_SLIDE_WORKSPACE", None)
    picked = [t for t in TESTS if (not a.names or any(n in t[0] for n in a.names)) and (a.sessions or not t[3])]
    results = []
    for name, cmd, desc, _ in picked:
        print(f"\n== {name} · {desc}", flush=True)
        t0 = time.time()
        r = subprocess.run(cmd, cwd=str(HERE), env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        out = (r.stdout or "") + (r.stderr or "")
        tail = [l for l in out.splitlines() if l.startswith(("OK", "FAIL", "실패", "전부 통과", "SKIP")) or "오류" in l][-12:]
        print("\n".join("   " + l for l in tail) if tail else out[-600:])
        results.append((name, r.returncode, time.time() - t0))
    print("\n---- 결과")
    for name, rc, dt in results:
        print(f"{'통과' if rc == 0 else '실패'}  {name:8s} {dt:5.0f}s")
    bad = [n for n, rc, _ in results if rc]
    print("\n전부 통과" if not bad else f"\n실패: {', '.join(bad)}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
