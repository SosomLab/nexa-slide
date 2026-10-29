# -*- coding: utf-8 -*-
"""편집기 UI 헤드리스 시험 - 시험용 작업 공간을 만들어(덱 4개) 작업 공간 서버(5667)를 띄우고 scenarios/*.json 을 smoke.js 로 돌린다.
그림 삽입(API·Ctrl+V·끌어다 놓기) · 도형/다이어그램 메뉴 · 표 행·열 단추·글머리 감지 스위치 · 묶기/풀기 · 링크/그림자/자르기 속성·발표자 보기 · 삽입 패널·명령 팔레트·스마트 가이드 · 글꼴 세트 선택 상자."""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import testlock  # noqa: F401 - 이 PC 에서 시험은 한 번에 하나(고정 포트·임시 폴더를 같이 쓴다, testlock.py)

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
SHAPES = ["triangle", "rtTriangle", "diamond", "parallelogram", "trapezoid", "pentagon", "hexagon", "octagon", "rightArrow", "leftArrow", "upArrow", "downArrow", "leftRightArrow", "chevron", "homePlate", "star5", "plus", "callout", "roundCallout", "can", "cube", "flowChartProcess", "flowChartDecision", "flowChartDocument", "flowChartInputOutput"]
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
        "tbl2test": {"title": "표 띠", "slides": [{"id": "s1", "elements": [{"id": "e01", "type": "table", "x": 60, "y": 60, "w": 500, "h": 100, "rows": [["열 1", "열 2"], ["값", "값"]], "colW": [1, 1], "size": 16}, {"id": "e02", "type": "text", "x": 60, "y": 300, "w": 500, "h": 60, "text": "글", "size": 20}]}]},
        "grptest": {"title": "묶음", "slides": [{"id": "s1", "elements": [{"id": "e01", "type": "text", "x": 60, "y": 60, "w": 400, "h": 60, "text": "글", "size": 20}, {"id": "e02", "type": "rect", "x": 60, "y": 200, "w": 300, "h": 100, "fill": "surface-container"}]}]},
        "shapetest": {"title": "도형", "slides": [{"id": "s1", "elements": [{"id": f"e{i + 1:02d}", "type": "shape", "shape": n, "x": 40 + (i % 7) * 170, "y": 40 + (i // 7) * 165, "w": 150, "h": 110, "text": "가", "size": 14, "fill": "primary-container"} for i, n in enumerate(SHAPES)]}]},
        "fxtest": {"title": "효과", "slides": [{"id": "s1", "elements": [
            {"id": "e01", "type": "text", "x": 60, "y": 30, "w": 1100, "h": 40, "text": "효과", "size": 22},
            {"id": "e02", "type": "rect", "x": 80, "y": 120, "w": 260, "h": 120, "text": "링크 상자", "fill": "surface-container", "radius": "r-m", "shadow": True, "link": "#2"},
            {"id": "e05", "type": "image", "x": 940, "y": 100, "w": 280, "h": 160, "src": "assets/images/t.png", "crop": [0.3, 0, 0.3, 0], "opacity": 0.5}]},
            {"id": "s2", "notes": "둘째 노트", "elements": [{"id": "f01", "type": "text", "x": 60, "y": 30, "w": 800, "h": 40, "text": "둘째", "size": 22}]}]},
    }
    decks["zsheetfill"] = {"title": "채우기", "kind": "sheet", "slides": [], "sheets": [{"id": "t01", "name": "채우기", "cells": {  # 시트 채우기 핸들(sheetfill_test) - 이름이 맨 뒤로 가게(다른 시나리오가 첫 덱·다음 덱을 고른다)
        "B3": 1, "C3": 4, "B5": "항목1", "B7": {"v": 46323, "fmt": "yyyy-mm-dd"}, "B9": "월", "B11": 5,
        "A13": 1, "A14": 2, "A15": 3, "A16": 4, "B13": 10, "C13": {"f": "=A13*B13"}}}]}
    decks["zsheetx"] = {"title": "엑셀 기능", "kind": "sheet", "slides": [], "sheets": [{"id": "t01", "name": "매출", "cells": {  # 시트 엑셀 기능(sheetx_test)
        "A1": {"v": "지역", "b": True}, "B1": {"v": "매출", "b": True}, "A2": "서울", "B2": 1200, "A3": "부산", "B3": 800, "A4": "대구", "B4": 500, "A5": "광주", "B5": 300,
        "D1": "메모", "D2": "서울 지점", "D3": "부산 지점"}}]}
    big = {f"{chr(65 + c)}{r + 1}": (r * 10 + c if c else f"행{r + 1}") for r in range(2000) for c in range(10)}  # 큰 시트 - 가상 스크롤(sheetbig_test)
    decks["zsheetbig"] = {"title": "큰 시트", "kind": "sheet", "slides": [], "sheets": [{"id": "t01", "name": "큰", "freeze": "A2", "cells": big,
                          "merges": ["D1400:D1460", "F10:G12"], "hiddenRows": ["1501"]}]}
    decks["zlinktest"] ={"title": "시트 연결", "slides": [{"id": "s1", "elements": [{"id": "e01", "type": "text", "x": 60, "y": 30, "w": 600, "h": 40, "text": "시트 연결", "size": 24}]}]}  # sheetlink_test(원본은 zsheetx)
    for n in range(12):  # 그림 많은 덱(12장 × 6장 그림) - lazy 로딩·재시도 시험
        (WS / "assets" / "images" / f"m{n}.png").write_bytes(PNG)
    decks["imgmany"] = {"title": "그림 많음", "slides": [{"id": f"s{si + 1:02d}", "elements": [{"id": f"i{si + 1:02d}{k}", "type": "image", "x": 40 + k * 200, "y": 120, "w": 180, "h": 120, "src": f"assets/images/m{(si + k) % 12}.png"} for k in range(6)]} for si in range(12)]}
    (WS / "decks").mkdir(parents=True, exist_ok=True)
    for k, v in decks.items():
        (WS / "decks" / f"{k}.json").write_text(json.dumps(v, ensure_ascii=False, indent=1), encoding="utf-8")
        (WS / "decks" / f"{k}.requests.json").unlink(missing_ok=True)


DECK_REF = re.compile(r"deck=([a-z][a-z0-9]+)|#([a-z][a-z0-9]+)/\d|/api/[a-z]+/([a-z][a-z0-9]+)")


def decks_of(text):
    """시나리오가 가리키는 덱 id(편집기 #덱/장 · 시트 ?deck= · /api/…/덱)."""
    return {a or b or c for a, b, c in DECK_REF.findall(text)}


def report(lane, out, err):
    """smoke.js 출력(## RESULT 줄로 나뉨)을 시나리오별 OK/FAIL 로."""
    buf, seen = [], set()
    for l in out.splitlines():
        if l.startswith("## RESULT "):
            name, verdict = l.split()[2], l.split()[3]
            seen.add(name)
            print(f"-- {name} ({l.split()[-1]})")
            for b in buf:
                print("  " + b[:160])
            check(f"시나리오 {Path(name).stem}", verdict == "OK", "\n".join(b for b in buf if b.startswith("FAIL"))[-400:])
            buf = []
        elif l.startswith(("OK", "FAIL", "==")):
            buf.append(l)
    for sc in lane:
        if sc.name not in seen:  # 실행기가 도중에 죽었다
            check(f"시나리오 {sc.stem}", False, (err or out)[-400:])


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
        # 갈래마다 smoke.js 하나(Chrome 한 번, 시나리오마다 새 브라우저 컨텍스트). 시트 덱(z…)만 쓰는 갈래와 슬라이드 덱만 쓰는 갈래는 동시에,
        # 둘 다 쓰는 시나리오는 그 뒤에 혼자 - 같은 덱을 두 시나리오가 동시에 고치지 않게(205초 → 157초)
        lanes = {"sheet": [], "slide": [], "both": []}
        for sc in sorted((HERE / "scenarios").glob("*.json")):
            z = {d.startswith("z") for d in decks_of(sc.read_text(encoding="utf-8"))}
            lanes["both" if z == {True, False} else "sheet" if z == {True} else "slide"].append(sc)
        for wave in (("sheet", "slide"), ("both",)):
            procs = [(lanes[k], subprocess.Popen(["node", str(HERE / "smoke.js"), *map(str, lanes[k])], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                  text=True, encoding="utf-8", errors="replace", cwd=str(HERE))) for k in wave if lanes[k]]
            for lane, p in procs:
                out, err = p.communicate()
                report(lane, out or "", err or "")
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
