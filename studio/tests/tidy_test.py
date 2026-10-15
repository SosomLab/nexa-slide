# -*- coding: utf-8 -*-
"""작업 공간 정리·보관(studio/tidy.py) 시험 - 시험용 작업 공간에 산출물·참조 없는 그림·고아 첨부·세션 로그를 심고
scan 보고 → clean(옮김) → restore → clean → purge → archive(zip 제외 규칙) 를 CLI(nexa.py 와 같은 env)로 확인하고,
작업 공간 서버(5667)의 GET/POST /api/tidy 와 요청 첨부 삭제(discard·update) 도 확인한다."""
import json
import os
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
WS = PROJ / "tidy시험" / "slides"
ENV = {**os.environ, "NEXA_SLIDE_USER_DIR": str(USER), "NEXA_SLIDE_PROJECTS": str(PROJ), "PYTHONIOENCODING": "utf-8", "NEXA_SLIDE_WORKSPACE": str(WS)}
FAILS = []
PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da63f8cfc0f01f0005000201e4ae07ea0000000049454e44ae426082")


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else extra)
    if not cond:
        FAILS.append(name)


def run(*args):
    r = subprocess.run([sys.executable, str(STUDIO / "tidy.py"), *args], env=ENV, cwd=str(WS), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout + r.stderr


def fixture():
    for d in (USER, PROJ):
        d.mkdir(parents=True, exist_ok=True)
    if not (WS / "nexa-slide.json").is_file():
        subprocess.run([sys.executable, str(STUDIO / "init_workspace.py"), str(WS.parent), "--title", "tidy시험", "--port", str(PORT)], env=ENV, capture_output=True, text=True, encoding="utf-8")
    (WS / "decks").mkdir(exist_ok=True)
    (WS / "assets" / "images").mkdir(parents=True, exist_ok=True)
    (WS / "assets" / "images" / "used.png").write_bytes(PNG)
    (WS / "assets" / "images" / "orphan.png").write_bytes(PNG)
    (WS / "assets" / "images" / "diagram.png").write_bytes(PNG); (WS / "assets" / "images" / "diagram.mmd").write_text("flowchart LR\n A-->B", encoding="utf-8")
    deck = {"title": "t", "slides": [{"id": "s1", "elements": [{"id": "e01", "type": "image", "x": 0, "y": 0, "w": 100, "h": 100, "src": "assets/images/used.png"}]}]}
    (WS / "decks" / "t1.json").write_text(json.dumps(deck, ensure_ascii=False), encoding="utf-8")
    (WS / "decks" / "t1.requests.json").write_text(json.dumps([{"id": "r1", "status": "open", "text": "x", "attachments": [{"path": "out/attach/t1/keep.png", "name": "keep.png"}]}]), encoding="utf-8")
    (WS / "out" / "attach" / "t1").mkdir(parents=True, exist_ok=True)
    (WS / "out" / "attach" / "t1" / "keep.png").write_bytes(PNG); (WS / "out" / "attach" / "t1" / "orphan.png").write_bytes(PNG)
    (WS / "out" / "attach" / "gone").mkdir(parents=True, exist_ok=True); (WS / "out" / "attach" / "gone" / "a.png").write_bytes(PNG)
    (WS / "out" / "t1.pptx").write_bytes(b"PK" + b"\0" * 100); (WS / "out" / "t1.pdf").write_bytes(b"%PDF" + b"\0" * 50)
    (WS / "out" / "t1").mkdir(exist_ok=True); (WS / "out" / "t1" / "slide-01.png").write_bytes(PNG)
    (WS / "out" / ".studio" / "sessions" / "20261015-1200").mkdir(parents=True, exist_ok=True); (WS / "out" / ".studio" / "sessions" / "20261015-1200" / "turn-1.jsonl").write_text("{}", encoding="utf-8")
    (WS / "out" / ".studio" / "server.json").write_text("{}", encoding="utf-8")
    (WS / "decks" / ".history" / "t1").mkdir(parents=True, exist_ok=True); (WS / "decks" / ".history" / "t1" / "b.json").write_text(json.dumps({"slides": [{"elements": [{"type": "image", "src": "assets/images/orphan.png"}]}]}), encoding="utf-8")
    (WS / "nexa-slide.local.json").write_text("{}", encoding="utf-8")


def main():
    fixture()
    code, out = run("scan", "--json")
    rep = json.loads(out[out.index("{"):]) if "{" in out else {}
    check("scan 실행", code == 0 and rep.get("items") is not None, out[-300:])
    by = {}
    for it in rep.get("items", []):
        by.setdefault(it["category"], []).append(it["path"])
    check("output: pptx·pdf·렌더 폴더", {"out/t1.pptx", "out/t1.pdf", "out/t1"} <= set(by.get("output", [])), str(by.get("output")))
    check("image: orphan·diagram 만(used 는 제외, .mmd 는 png 의 짝)", set(by.get("image", [])) == {"assets/images/orphan.png", "assets/images/diagram.png"}, str(by.get("image")))
    kept = [it for it in rep.get("items", []) if it.get("kept")]
    check("백업이 참조하는 orphan.png 는 kept 표시", any(k["path"] == "assets/images/orphan.png" for k in kept), str(kept))
    check("attach: 고아 파일·없는 덱 폴더", set(by.get("attach", [])) == {"out/attach/t1/orphan.png", "out/attach/gone"}, str(by.get("attach")))
    check("log: 세션 로그 폴더", by.get("log") == ["out/.studio/sessions/20261015-1200"], str(by.get("log")))
    check("backup: .history", "decks/.history/t1" in by.get("backup", []), str(by.get("backup")))
    check("실행 상태 파일(server.json)은 대상 아님", not any("server.json" in p for ps in by.values() for p in ps))
    # clean(기본 범주) → 옮김 · 원 자리 비움 · kept 그림은 남음
    code, out = run("clean", "--only", "output,attach,log,image", "--json")
    r = json.loads(out[out.index("{"):])
    check("clean 옮김", code == 0 and r["moved"] >= 6 and r["dest"] and r["dest"].startswith("out/.tidy/"), out[-300:])
    check("  pptx 사라짐 · used.png 남음 · kept(orphan.png) 남음", not (WS / "out" / "t1.pptx").exists() and (WS / "assets" / "images" / "used.png").exists() and (WS / "assets" / "images" / "orphan.png").exists())
    check("  diagram.png 와 .mmd 짝이 같이 옮겨짐", not (WS / "assets" / "images" / "diagram.png").exists() and not (WS / "assets" / "images" / "diagram.mmd").exists())
    stamp = r["dest"].rsplit("/", 1)[-1]
    code, out = run("restore", "--stamp", stamp)
    check("restore 되돌림", code == 0 and (WS / "out" / "t1.pptx").exists() and (WS / "assets" / "images" / "diagram.mmd").exists(), out[-200:])
    code, out = run("clean", "--only", "output", "--json")
    code2, out2 = run("purge")
    check("purge 비움", code2 == 0 and not (WS / "out" / ".tidy").exists(), out2[-200:])
    # archive - 기본 제외 규칙
    code, out = run("archive", "--out", str(WORK / "tidy-archive.zip"), "--json")
    r = json.loads(out[out.index("{"):]) if "{" in out else {}
    zp = Path(r.get("zip", ""))
    check("archive zip 생성", code == 0 and zp.is_file(), out[-300:])
    if zp.is_file():
        names = zipfile.ZipFile(zp).namelist()
        check("  decks·assets·nexa-slide.json 포함, out/·.history·local.json 제외", any(n.endswith("decks/t1.json") for n in names) and any(n.endswith("assets/images/used.png") for n in names)
              and not any("/out/" in n for n in names) and not any(".history" in n for n in names) and not any(n.endswith("nexa-slide.local.json") for n in names), str([n for n in names if "out/" in n or "history" in n][:5]))
    code, out = run("archive", "--all", "--out", str(WORK / "tidy-archive-all.zip"), "--json")
    r = json.loads(out[out.index("{"):]) if "{" in out else {}
    if Path(r.get("zip", "")).is_file():
        names = zipfile.ZipFile(r["zip"]).namelist()
        check("  --all 은 out/attach 포함, 실행 상태 server.json 제외", any("out/attach/t1/keep.png" in n for n in names) and not any(n.endswith(".studio/server.json") for n in names))
    # 서버 API - 작업 공간 서버 직접 접속(로컬 = 운영자)
    srv = subprocess.Popen([sys.executable, str(STUDIO / "server.py"), "--workspace", str(WS), "--port", str(PORT)], env=ENV, cwd=str(WS), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        base = f"http://127.0.0.1:{PORT}"
        for _ in range(60):
            try:
                urllib.request.urlopen(base + "/api/decks", timeout=2).read(); break
            except Exception:  # noqa: BLE001
                time.sleep(0.5)

        def req(method, path, body=None):
            h = {"Accept": "application/json", "Origin": base, "Content-Type": "application/json"}
            with urllib.request.urlopen(urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None, method=method, headers=h), timeout=60) as r:
                return json.loads(r.read())
        d = req("GET", "/api/tidy")
        check("GET /api/tidy 보고", d.get("ok") and "summary" in d, str(d)[:200])
        d = req("POST", "/api/tidy", {"action": "clean", "categories": ["log"]})
        check("POST /api/tidy clean", d.get("ok") and d.get("moved", 0) >= 1 and "report" in d, str(d)[:200])
        d = req("POST", "/api/tidy", {"action": "purge"})
        check("POST /api/tidy purge", d.get("ok"), str(d)[:200])
        # 요청 첨부 - 초안 지우기(discard)·첨부 바꾸기(update)가 파일을 지운다
        (WS / "out" / "attach" / "t1").mkdir(parents=True, exist_ok=True)
        (WS / "out" / "attach" / "t1" / "d1.png").write_bytes(PNG); (WS / "out" / "attach" / "t1" / "d2.png").write_bytes(PNG)
        items = req("POST", "/api/requests/t1", {"action": "add", "status": "draft", "slide": "s1", "text": "초안", "attachments": [{"path": "out/attach/t1/d1.png", "name": "d1.png", "type": "image/png", "size": 1}]})
        rid = next((x["id"] for x in items if x.get("text") == "초안"), None)
        items = req("POST", "/api/requests/t1", {"action": "update", "id": rid, "attachments": [{"path": "out/attach/t1/d2.png", "name": "d2.png", "type": "image/png", "size": 1}]})
        check("update 로 빠진 첨부 d1 삭제·d2 유지", not (WS / "out" / "attach" / "t1" / "d1.png").exists() and (WS / "out" / "attach" / "t1" / "d2.png").exists())
        req("POST", "/api/requests/t1", {"action": "discard"})
        check("discard 로 초안 첨부 d2 삭제", not (WS / "out" / "attach" / "t1" / "d2.png").exists())
    finally:
        srv.terminate()
    print("실패:", FAILS or "없음")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
