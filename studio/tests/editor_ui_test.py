# -*- coding: utf-8 -*-
"""편집기 UI 헤드리스 시험 - 시험용 작업 공간을 만들어(덱 4개) 작업 공간 서버(5667)를 띄우고 scenarios/*.json 을 smoke.js 로 돌린다.
그림 삽입(API·Ctrl+V·끌어다 놓기) · 도형/다이어그램 메뉴 · 표 행·열 단추·글머리 감지 스위치 · 묶기/풀기 · 링크/그림자/자르기 속성·발표자 보기 · 삽입 패널·명령 팔레트·스마트 가이드 · 글꼴 세트 선택 상자."""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    _s.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
STUDIO = HERE.parent
WORK = Path(os.environ.get("NEXA_TEST_DIR") or Path(tempfile.gettempdir()) / "nexa-slide-tests")
for _d in (WORK / "user", WORK / "projects"):
    _d.mkdir(parents=True, exist_ok=True)
USER, PROJ, PORT = WORK / "user", WORK / "projects", 5667
WS = PROJ / "ui시험" / "slides"
ENV = {**os.environ, "NEXA_SLIDE_USER_DIR": str(USER), "NEXA_SLIDE_PROJECTS": str(PROJ), "PYTHONIOENCODING": "utf-8", "NEXA_SLIDE_WORKSPACE": str(WS)}
FAILS = []
SHAPES = ["triangle", "rtTriangle", "diamond", "parallelogram", "trapezoid", "pentagon", "hexagon", "octagon", "rightArrow", "leftArrow", "upArrow", "downArrow", "leftRightArrow", "chevron", "homePlate", "star5", "plus", "callout", "roundCallout", "can", "cube"]
PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da63f8cfc0f01f0005000201e4ae07ea0000000049454e44ae426082")


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else extra)
    if not cond:
        FAILS.append(name)


def fixture():
    if not (WS / "nexa-slide.json").is_file():
        subprocess.run([sys.executable, str(STUDIO / "init_workspace.py"), str(WS.parent), "--title", "ui시험", "--port", str(PORT)], env=ENV, capture_output=True, text=True, encoding="utf-8")
    (WS / "assets" / "images").mkdir(parents=True, exist_ok=True)
    (WS / "assets" / "images" / "t.png").write_bytes(PNG)
    decks = {
        "numtest": {"title": "번호", "slides": [{"id": "s1", "elements": [{"id": "e01", "type": "text", "x": 60, "y": 40, "w": 600, "h": 40, "text": "제목", "size": 24}, {"id": "e02", "type": "bullets", "x": 60, "y": 120, "w": 560, "h": 300, "size": 20, "items": ["1. 첫째", "2. 둘째"]}]}]},
        "tbltest": {"title": "표·글머리", "slides": [{"id": "s1", "elements": [{"id": "e01", "type": "table", "x": 60, "y": 60, "w": 500, "h": 100, "rows": [["열 1", "열 2"], ["값", "값"]], "colW": [1, 1], "size": 16}, {"id": "e02", "type": "bullets", "x": 60, "y": 300, "w": 500, "h": 200, "size": 20, "items": ["1. 첫째", "2. 둘째"]}]}]},
        "shapetest": {"title": "도형", "slides": [{"id": "s1", "elements": [{"id": f"e{i + 1:02d}", "type": "shape", "shape": n, "x": 40 + (i % 7) * 170, "y": 40 + (i // 7) * 200, "w": 150, "h": 110, "text": "가", "size": 14, "fill": "primary-container"} for i, n in enumerate(SHAPES)]}]},
        "fxtest": {"title": "효과", "slides": [{"id": "s1", "elements": [
            {"id": "e01", "type": "text", "x": 60, "y": 30, "w": 1100, "h": 40, "text": "효과", "size": 22},
            {"id": "e02", "type": "rect", "x": 80, "y": 120, "w": 260, "h": 120, "text": "링크 상자", "fill": "surface-container", "radius": "r-m", "shadow": True, "link": "#2"},
            {"id": "e05", "type": "image", "x": 940, "y": 100, "w": 280, "h": 160, "src": "assets/images/t.png", "crop": [0.3, 0, 0.3, 0], "opacity": 0.5}]},
            {"id": "s2", "notes": "둘째 노트", "elements": [{"id": "f01", "type": "text", "x": 60, "y": 30, "w": 800, "h": 40, "text": "둘째", "size": 22}]}]},
    }
    (WS / "decks").mkdir(parents=True, exist_ok=True)
    for k, v in decks.items():
        (WS / "decks" / f"{k}.json").write_text(json.dumps(v, ensure_ascii=False, indent=1), encoding="utf-8")
        (WS / "decks" / f"{k}.requests.json").unlink(missing_ok=True)


def main():
    fixture()
    srv = subprocess.Popen([sys.executable, str(STUDIO / "server.py"), "--workspace", str(WS), "--port", str(PORT)], env=ENV, cwd=str(WS), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/decks", timeout=2).read()
                break
            except Exception:  # noqa: BLE001
                time.sleep(0.5)
        else:
            check("작업 공간 서버 시작", False, "5667 응답 없음")
            return
        for sc in sorted((HERE / "scenarios").glob("*.json")):
            r = subprocess.run(["node", str(HERE / "smoke.js"), str(sc)], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(HERE))
            out = r.stdout or ""
            lines = [l for l in out.splitlines() if l.startswith(("OK", "FAIL", "=="))]
            print(f"-- {sc.name}")
            for l in lines:
                print("  " + l[:160])
            check(f"시나리오 {sc.stem}", r.returncode == 0, (r.stderr or out)[-400:])
    finally:
        srv.terminate()
        try:
            srv.wait(5)
        except subprocess.TimeoutExpired:
            srv.kill()
    print("\n실패:", FAILS or "없음")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
