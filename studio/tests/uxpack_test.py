# -*- coding: utf-8 -*-
"""편집 편의 묶음(0.22.14) 시험 - 레이아웃 검사의 대비(t6)·대체 텍스트(t7) 규칙, 그림 alt 의 PPTX descr, 유인물·노트 PDF(Chrome 이 있을 때),
표 데이터 칸 탭 구분(render.js 가 아닌 studio.js 함수라 여기서는 서버 쪽만). 편집기 UI 쪽은 scenarios/ux2_test.json(editor 묶음)."""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path
for _s in (sys.stdout, sys.stderr): _s.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
STUDIO = HERE.parent
WORK = Path(os.environ.get("NEXA_TEST_DIR") or Path(tempfile.gettempdir()) / "nexa-slide-tests")
USER, PROJ, PORT = WORK / "user", WORK / "projects", 5667
WS = PROJ / "uxpack시험" / "slides"
ENV = {**os.environ, "NEXA_SLIDE_USER_DIR": str(USER), "NEXA_SLIDE_PROJECTS": str(PROJ), "PYTHONIOENCODING": "utf-8", "NEXA_SLIDE_WORKSPACE": str(WS)}
FAILS = []
PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da63f8cfc0f01f0005000201e4ae07ea0000000049454e44ae426082")


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else extra)
    if not cond:
        FAILS.append(name)


def main():
    for d in (USER, PROJ):
        d.mkdir(parents=True, exist_ok=True)
    if not (WS / "nexa-slide.json").is_file():
        subprocess.run([sys.executable, str(STUDIO / "init_workspace.py"), str(WS.parent), "--title", "uxpack시험", "--port", str(PORT)], env=ENV, capture_output=True, text=True, encoding="utf-8")
    (WS / "assets" / "images").mkdir(parents=True, exist_ok=True)
    (WS / "assets" / "images" / "t.png").write_bytes(PNG)
    deck = {"title": "편의 시험", "slides": [
        {"id": "s01", "notes": "첫 장 노트", "elements": [
            {"id": "e1", "type": "text", "x": 80, "y": 80, "w": 600, "h": 60, "size": 24, "text": "대비 낮음", "color": "#FFFF99", "fill": "#FFFFFF"},
            {"id": "e2", "type": "text", "x": 80, "y": 160, "w": 600, "h": 60, "size": 24, "text": "대비 충분", "color": "#111111", "fill": "#FFFFFF"},
            {"id": "e3", "type": "image", "x": 80, "y": 260, "w": 200, "h": 150, "src": "assets/images/t.png"},
            {"id": "e4", "type": "image", "x": 320, "y": 260, "w": 200, "h": 150, "src": "assets/images/t.png", "alt": "시험 그림"}]},
        {"id": "s02", "elements": [{"id": "t", "type": "text", "x": 80, "y": 80, "w": 600, "h": 60, "text": "둘째"}]},
        {"id": "s03", "elements": [{"id": "t", "type": "text", "x": 80, "y": 80, "w": 600, "h": 60, "text": "셋째"}]},
        {"id": "s04", "hidden": True, "elements": [{"id": "t", "type": "text", "x": 80, "y": 80, "w": 600, "h": 60, "text": "숨김"}]},
    ]}
    (WS / "decks").mkdir(exist_ok=True)
    (WS / "decks" / "ux.json").write_text(json.dumps(deck, ensure_ascii=False), encoding="utf-8")
    # 검사 - t6 대비 · t7 대체 텍스트
    r = subprocess.run([sys.executable, str(STUDIO / "check_layout.py"), "--workspace", str(WS), "ux", "--json"], env=ENV, capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        txt = r.stdout.strip()
        res = json.loads(txt[txt.index("{"):]) if txt and not txt.startswith("[") else json.loads(txt)
        res = res[0] if isinstance(res, list) else res
    except Exception:  # noqa: BLE001
        res = {}
        check("check_layout --json 실행", False, (r.stderr or r.stdout)[-400:])
    if res:
        iss = res.get("issues", [])
        t6 = [i for i in iss if i["rule"] == "t6.contrast.low"]
        t7 = [i for i in iss if i["rule"] == "t7.alt.missing"]
        check("t6 대비 낮음 - e1 만(흰 바탕 연노랑), e2 는 아님", [i["elements"] for i in t6] == [["e1"]], str([(i["elements"], i.get("ratio")) for i in t6]))
        check("t7 대체 텍스트 없음 - e3 만, INFO", [i["elements"] for i in t7] == [["e3"]] and all(i["severity"] == "INFO" for i in t7), str(t7))
        check("요약에 infos, errors·warnings 에 INFO 안 섞임", res.get("infos") == len(t7) and res.get("warnings", 0) >= 1)
    # PPTX - alt → descr
    r = subprocess.run([sys.executable, str(STUDIO / "export_pptx.py"), "ux", "--out", "out/ux.pptx"], env=ENV, cwd=str(WS), capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("export_pptx 성공", r.returncode == 0 and (WS / "out" / "ux.pptx").is_file(), (r.stderr or r.stdout)[-300:])
    if (WS / "out" / "ux.pptx").is_file():
        with zipfile.ZipFile(WS / "out" / "ux.pptx") as z:
            x = z.read("ppt/slides/slide1.xml").decode("utf-8")
        check("그림 대체 텍스트 descr - alt 있는 그림만, 없는 그림은 빈 값(파일 이름 아님)", 'descr="시험 그림"' in x and 'descr="t.png"' not in x, str(re.findall(r'descr="[^"]*"', x)))
    # 유인물·노트 PDF(Chrome 헤드리스) - 서버 API
    import shutil
    chrome = next((b for b in [r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"] if Path(b).exists()), None) or shutil.which("chrome") or shutil.which("google-chrome") or shutil.which("msedge")
    if not chrome:
        print("SKIP 유인물·노트 PDF - Chrome/Edge 없음")
    else:
        srv = subprocess.Popen([sys.executable, str(STUDIO / "server.py"), "--workspace", str(WS), "--port", str(PORT)], env=ENV, cwd=str(WS), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            base = f"http://127.0.0.1:{PORT}"
            for _ in range(60):
                try:
                    urllib.request.urlopen(base + "/api/decks", timeout=2).read(); break
                except Exception:  # noqa: BLE001
                    time.sleep(0.5)
            for lay, tag in (("h3", "-handout3"), ("notes", "-notes"), ("h6", "-handout6")):
                req = urllib.request.Request(f"{base}/api/export/ux?pdf=1&layout={lay}", method="POST", data=b"{}", headers={"Content-Type": "application/json"})
                try:
                    d = json.loads(urllib.request.urlopen(req, timeout=240).read())
                except Exception as e:  # noqa: BLE001
                    d = {"error": str(e)}
                f = WS / "out" / f"ux{tag}.pdf"
                check(f"PDF layout={lay} - Chrome 으로 {f.name} 생성 · 받는 이름에 꼬리", d.get("ok") and d.get("via") == "chrome" and f.is_file() and f.stat().st_size > 1000 and d.get("name", "").endswith(f"{tag}.pdf"), str(d)[:300])
        finally:
            srv.terminate()
    print("실패:", FAILS or "없음")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
