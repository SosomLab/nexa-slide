# -*- coding: utf-8 -*-
"""견본 내용 언어(content_i18n) 시험 - layout_samples --lang en 에 한글이 남지 않는지(사전에 있는 글), 작업 공간 서버 /api/slidetypes?lang=en 의 예시 슬라이드 글이 영어인지,
tr() 가 여러 줄·구조·경로를 바르게 다루는지."""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
for _s in (sys.stdout, sys.stderr): _s.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
STUDIO = HERE.parent
WORK = Path(os.environ.get("NEXA_TEST_DIR") or Path(tempfile.gettempdir()) / "nexa-slide-tests")
USER, PROJ, PORT = WORK / "user", WORK / "projects", 5667
WS = PROJ / "deck시험" / "slides"
ENV = {**os.environ, "NEXA_SLIDE_USER_DIR": str(USER), "NEXA_SLIDE_PROJECTS": str(PROJ), "PYTHONIOENCODING": "utf-8", "NEXA_SLIDE_WORKSPACE": str(WS)}
FAILS = []
H = re.compile(r"[가-힣]")


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else extra)
    if not cond:
        FAILS.append(name)


def hangul_strings(o, out):
    if isinstance(o, str):
        if H.search(o):
            out.append(o)
    elif isinstance(o, dict):
        for k, v in o.items():
            if k in ("mermaid", "src", "img", "notes", "source"):
                continue
            hangul_strings(v, out)
    elif isinstance(o, list):
        for v in o:
            hangul_strings(v, out)


def main():
    for d in (USER, PROJ):
        d.mkdir(parents=True, exist_ok=True)
    if not (WS / "nexa-slide.json").is_file():
        subprocess.run([sys.executable, str(STUDIO / "init_workspace.py"), str(WS.parent), "--title", "deck시험", "--port", str(PORT)], env=ENV, capture_output=True, text=True, encoding="utf-8")
    sys.path.insert(0, str(STUDIO))
    os.environ.update(ENV)
    from content_i18n import tr, content_dir, load_map
    m = load_map("en")
    check("content.en.json 읽힘(300개 이상)", len(m) >= 300, str(len(m)))
    check("tr: 여러 줄은 줄마다", tr("제목\n두 번째 줄", "en") == "Title\nsecond line" and tr("장 제목\n모르는 줄", "en") == "Chapter title\n모르는 줄")
    check("tr: 구조·경로 유지", tr({"title": "정리", "items": ["항목 1", {"img": "assets/사진.png"}], "src": "a/가.png"}, "en") == {"title": "Summary", "items": ["Item 1", {"img": "assets/사진.png"}], "src": "a/가.png"})
    check("tr: ko·모르는 언어는 그대로", tr("정리", "ko") == "정리" and tr("정리", "xx") == "정리")
    check("content_dir: 번역본 없으면 content/", content_dir(STUDIO.parent / "starters" / "weekly-report", "en").name == "content")
    r = subprocess.run([sys.executable, str(STUDIO / "layout_samples.py"), "--json", "--lang", "en"], env=ENV, cwd=str(WS), capture_output=True, text=True, encoding="utf-8", errors="replace")
    d = json.loads(r.stdout[r.stdout.index("{"):]) if "{" in r.stdout else {}
    left = []
    for v in d.values():
        hangul_strings(v.get("sample", {}), left)
    check("layout_samples --lang en: 견본 글에 한글 없음", r.returncode == 0 and d and not left, str(left[:8]))
    r = subprocess.run([sys.executable, str(STUDIO / "layout_samples.py"), "--json"], env=ENV, cwd=str(WS), capture_output=True, text=True, encoding="utf-8", errors="replace")
    d2 = json.loads(r.stdout[r.stdout.index("{"):])
    ko = []
    for v in d2.values():
        hangul_strings(v.get("sample", {}), ko)
    check("  --lang 없이는 한국어 그대로", len(ko) > 100)
    srv = subprocess.Popen([sys.executable, str(STUDIO / "server.py"), "--workspace", str(WS), "--port", str(PORT)], env=ENV, cwd=str(WS), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        base = f"http://127.0.0.1:{PORT}"
        for _ in range(60):
            try:
                urllib.request.urlopen(base + "/api/decks", timeout=2).read(); break
            except Exception:  # noqa: BLE001
                time.sleep(0.5)
        with urllib.request.urlopen(base + "/api/slidetypes?part=day1&lang=en", timeout=120) as h:
            st = json.loads(h.read())
        left = []
        for t in st["types"]:
            if t.get("slide"):
                hangul_strings([e.get("text") for e in t["slide"].get("elements", []) if e.get("text")], left)
                hangul_strings([c for e in t["slide"].get("elements", []) for row in (e.get("rows") or []) for c in row], left)
                hangul_strings([it for e in t["slide"].get("elements", []) for it in (e.get("items") or [])], left)
        left = [x for x in left if "deck시험" not in x]  # 작업 공간 제목은 데이터
        check("/api/slidetypes?lang=en: 예시 슬라이드 글에 한글 없음(유형 fields·레이아웃 자리 글 포함)", not left, str(left[:8]))
        check("  유형 이름·설명 i18n 필드 전달", all((t.get("i18n") or {}).get("en", {}).get("label") for t in st["types"]), str([t["id"] for t in st["types"] if not (t.get("i18n") or {}).get("en", {}).get("label")][:5]))
    finally:
        srv.terminate()
    print("실패:", FAILS or "없음")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
