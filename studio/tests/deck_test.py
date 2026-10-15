# -*- coding: utf-8 -*-
"""덱 관리(deck_admin) 시험 - 짧은 해시 id 로 만들기·복제·시작 덱·목록(CLI) 과 작업 공간 서버 /api/decks(copy·start) 를 확인한다."""
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


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else extra)
    if not cond:
        FAILS.append(name)


def cli(*args):
    r = subprocess.run([sys.executable, str(STUDIO / "deck_admin.py"), *args], env=ENV, cwd=str(WS), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout + r.stderr).strip()


def main():
    for d in (USER, PROJ):
        d.mkdir(parents=True, exist_ok=True)
    if not (WS / "nexa-slide.json").is_file():
        subprocess.run([sys.executable, str(STUDIO / "init_workspace.py"), str(WS.parent), "--title", "deck시험", "--port", str(PORT)], env=ENV, capture_output=True, text=True, encoding="utf-8")
    for f in (WS / "decks").glob("*.json"):
        f.unlink()
    code, out = cli("create", "--title", "첫 덱")
    m = re.search(r"decks[\\/]([a-z][0-9a-f]{7})\.json", out)
    check("create - id 없이 만들면 짧은 해시 id(8자)", code == 0 and m, out[-200:])
    i1 = m.group(1) if m else ""
    d = json.loads((WS / "decks" / f"{i1}.json").read_text(encoding="utf-8")) if i1 else {}
    check("  덱 안 id·제목", d.get("id") == i1 and d.get("title") == "첫 덱", str({k: d.get(k) for k in ("id", "title")}))
    code, out = cli("create", "named", "--title", "이름 준 덱")
    check("create - id 를 주면 그대로", code == 0 and (WS / "decks" / "named.json").is_file(), out[-200:])
    code, out = cli("copy", i1, "--title", "둘째 덱")
    m2 = re.search(r"→ ([a-z][0-9a-f]{7}) ", out)
    check("copy - 새 해시 id·제목", code == 0 and m2 and m2.group(1) != i1, out[-200:])
    i2 = m2.group(1) if m2 else ""
    if i2:
        d2 = json.loads((WS / "decks" / f"{i2}.json").read_text(encoding="utf-8"))
        check("  복제본 id·제목·슬라이드 수", d2.get("id") == i2 and d2.get("title") == "둘째 덱" and len(d2.get("slides", [])) == len(d.get("slides", [])))
    code, out = cli("start", i2)
    cfg = json.loads((WS / "nexa-slide.json").read_text(encoding="utf-8"))
    check("start - nexa-slide.json startDeck", code == 0 and cfg.get("startDeck") == i2, out[-200:])
    code, out = cli("list")
    check("list - ★ 표시", code == 0 and any(l.startswith("★") and i2 in l for l in out.splitlines()), out[-300:])
    code, out = cli("start")
    cfg = json.loads((WS / "nexa-slide.json").read_text(encoding="utf-8"))
    check("start 해제", code == 0 and "startDeck" not in cfg, out[-200:])
    # 서버 API
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
        r = req("POST", "/api/decks", {"action": "create", "title": "API 덱"})
        check("API create(id 없이)", r.get("ok") and re.fullmatch(r"[a-z][0-9a-f]{7}", r.get("id", "")), str(r)[:200])
        i3 = r.get("id")
        r = req("POST", "/api/decks", {"action": "copy", "id": i3, "title": "API 복제"})
        check("API copy", r.get("ok") and r.get("id") != i3 and any(x["id"] == r.get("id") and x["title"] == "API 복제" for x in r.get("decks", [])), str(r)[:200])
        r = req("POST", "/api/decks", {"action": "start", "id": i3})
        lst = req("GET", "/api/decks")
        check("API start → /api/decks start 표시", r.get("ok") and any(x["id"] == i3 and x.get("start") for x in lst) and sum(1 for x in lst if x.get("start")) == 1, str(lst)[:300])
        r = req("POST", "/api/decks", {"action": "start", "id": ""})
        lst = req("GET", "/api/decks")
        check("API start 해제", r.get("ok") and not any(x.get("start") for x in lst))
    finally:
        srv.terminate()
    print("실패:", FAILS or "없음")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
