# -*- coding: utf-8 -*-
"""엔진 요청 ↔ 원 요청 연결 시험 - 작업 공간 서버(5667)에 덱·요청을 두고, 세션 요청(from.ws·deck·request)을 큐에 넣으면 원 요청에 engineRequest 가 적히고(link_origin),
done → engineNote 알림, applied → status open 으로 재개(resume_origin), rejected → 거절 알림을 확인한다. 서버가 꺼진 경우(파일 직접)도 확인."""
import json
import os
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
USER, PROJ, PORT = WORK / "user-englink", WORK / "projects", 5667
WS = PROJ / "englink시험" / "slides"
ENV = {**os.environ, "NEXA_SLIDE_USER_DIR": str(USER), "NEXA_SLIDE_PROJECTS": str(PROJ), "PYTHONIOENCODING": "utf-8", "NEXA_SLIDE_WORKSPACE": str(WS)}
FAILS = []


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else extra)
    if not cond:
        FAILS.append(name)


def main():
    for d in (USER, PROJ):
        d.mkdir(parents=True, exist_ok=True)
    (USER / "hub" / "engine").mkdir(parents=True, exist_ok=True)
    (USER / "hub" / "engine" / "requests.json").unlink(missing_ok=True)
    if not (WS / "nexa-slide.json").is_file():
        subprocess.run([sys.executable, str(STUDIO / "init_workspace.py"), str(WS.parent), "--title", "englink시험", "--port", str(PORT)], env=ENV, capture_output=True, text=True, encoding="utf-8")
    (WS / "decks").mkdir(exist_ok=True)
    (WS / "decks" / "el.json").write_text(json.dumps({"title": "연결", "slides": [{"id": "s1", "elements": [{"id": "e01", "type": "text", "x": 0, "y": 0, "w": 100, "h": 40, "text": "a"}]}]}, ensure_ascii=False), encoding="utf-8")
    (WS / "decks" / "el.requests.json").write_text(json.dumps([{"id": "r1", "slide": "s1", "status": "open", "text": "새 레이아웃 필요", "reply": "", "created": "2026-10-16T00:00:00"}]), encoding="utf-8")
    os.environ.update(ENV)
    sys.path.insert(0, str(STUDIO))
    import engine_requests as q
    srv = subprocess.Popen([sys.executable, str(STUDIO / "server.py"), "--workspace", str(WS), "--port", str(PORT)], env=ENV, cwd=str(WS), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        base = f"http://127.0.0.1:{PORT}"
        for _ in range(60):
            try:
                urllib.request.urlopen(base + "/api/decks", timeout=2).read(); break
            except Exception:  # noqa: BLE001
                time.sleep(0.5)

        def reqs():
            with urllib.request.urlopen(base + "/api/requests/el", timeout=20) as r:
                return json.loads(r.read())
        it = q.add("새 레이아웃", "이유", kind="session", ws=str(WS), ws_id="englink", request="r1", deck="el", slide="s1")
        ok = q.link_origin(it)
        r1 = reqs()[0]
        check("link_origin → 원 요청 engineRequest (서버 경유)", ok and r1.get("engineRequest") == it["id"], str(r1)[:200])
        q.update(it["id"], status="open", by="admin"); q.update(it["id"], status="working", by="dev")
        q.update(it["id"], status="done", by="dev", commit="abc1234")
        r1 = reqs()[0]
        check("done → engineNote 알림 · status 는 open 그대로", r1.get("status") == "open" and "처리됨" in (r1.get("engineNote") or "") and "abc1234" in r1["engineNote"], str(r1)[:200])
        # 원 요청이 그 사이 done 이 됐다고 치고 applied 로 재개
        urllib.request.urlopen(urllib.request.Request(base + "/api/requests/el", data=json.dumps({"action": "update", "id": "r1", "status": "done"}).encode(), method="POST", headers={"Content-Type": "application/json", "Origin": base}), timeout=20).read()
        q.update(it["id"], status="applied", by="admin", appliedCommit="main9")
        r1 = reqs()[0]
        check("applied → 원 요청 status open 으로 재개 · engineNote 적용됨", r1.get("status") == "open" and "적용됨" in (r1.get("engineNote") or "") and "main9" in r1["engineNote"], str(r1)[:200])
        it2 = q.add("둘째", "", kind="session", ws=str(WS), ws_id="englink", request="r1", deck="el", slide="s1")
        q.update(it2["id"], status="rejected", by="admin", reply="범위 밖")
        r1 = reqs()[0]
        check("rejected → engineNote 거절 사유", "거절됨" in (r1.get("engineNote") or "") and "범위 밖" in r1["engineNote"], str(r1)[:200])
        # 0.22.27 - 서버 경유 등록: POST /api/engine_request(로컬) 와 CLI(작업 공간 안이면 서버로) - Codex 샌드박스가 큐 파일(작업 공간 밖)을 못 써서 멈추던 결함
        rq = urllib.request.Request(base + "/api/engine_request", data=json.dumps({"title": "API 경유", "body": "본문", "request": "r1", "deck": "el", "slide": "s1"}).encode("utf-8"),
                                    method="POST", headers={"Content-Type": "application/json", "Origin": base, "X-Nexa-Session-User": "tester"})
        with urllib.request.urlopen(rq, timeout=20) as r:
            d = json.loads(r.read())
        it4 = d.get("item") or {}
        check("POST /api/engine_request → triage · from.kind session · user", d.get("ok") and it4.get("status") == "triage" and (it4.get("from") or {}).get("kind") == "session" and (it4.get("from") or {}).get("user") == "tester", str(d)[:300])
        check("  note(세션 꺼짐 안내) 포함", "note" in d)
        check("  원 요청 engineRequest 가 새 번호로", reqs()[0].get("engineRequest") == it4.get("id"))
        cr = subprocess.run([sys.executable, str(STUDIO / "engine_request.py"), "add", "--title", "CLI 경유", "--body", "본문", "--request", "r2-cli", "--deck", "el"],  # r1 은 위 항목에 합쳐지므로(같은 원 요청 덧붙임) 다른 id
                            env={**ENV, "NEXA_SLIDE_USER": "cli-user"}, cwd=str(WS), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        it5 = max(q.load(), key=lambda x: x["id"])
        check("CLI add(작업 공간 안·서버 떠 있음) → 서버 경유로 등록 · user", cr.returncode == 0 and it5.get("title") == "CLI 경유" and (it5.get("from") or {}).get("user") == "cli-user" and "직접 쓴다" not in cr.stderr, cr.stdout + cr.stderr)
    finally:
        srv.terminate(); srv.wait(timeout=10)
    # 서버가 꺼진 경우 - 파일 직접
    time.sleep(1)
    it3 = q.add("셋째", "", kind="session", ws=str(WS), ws_id="englink", request="r1", deck="el", slide="s1")
    ok = q.link_origin(it3)
    r1 = json.loads((WS / "decks" / "el.requests.json").read_text(encoding="utf-8"))[0]
    check("서버 꺼짐 → 파일 직접 engineRequest", ok and r1.get("engineRequest") == it3["id"], str(r1)[:200])
    print("실패:", FAILS or "없음")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
