# -*- coding: utf-8 -*-
"""0.21.22 검증 - 시험 허브(5799)에 관리자·요청 7건을 만들고 카드 최근 5건·total, /api/engine/requests?q=, /engine 페이지를 헤드리스로 확인."""
import http.cookiejar
import json
import os
import tempfile
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import testlock  # noqa: F401 - 이 PC 에서 시험은 한 번에 하나(고정 포트·임시 폴더를 같이 쓴다, testlock.py)

for _s in (sys.stdout, sys.stderr):
    _s.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
STUDIO = Path(__file__).resolve().parents[1]  # studio/ (이 파일은 studio/tests/)
WORK = Path(os.environ.get("NEXA_TEST_DIR") or Path(tempfile.gettempdir()) / "nexa-slide-tests")  # 시험 산출물(사용자 설정·작업 공간) - 저장소 밖(허브는 엔진 안의 작업 공간을 거절한다)
for _d in (WORK / "user", WORK / "projects"):
    _d.mkdir(parents=True, exist_ok=True)
USER, PROJ, HUB_PORT = WORK / "user", WORK / "projects", 5799
BASE = f"http://127.0.0.1:{HUB_PORT}"
ENV = {**os.environ, "NEXA_SLIDE_USER_DIR": str(USER), "NEXA_SLIDE_PROJECTS": str(PROJ), "PYTHONIOENCODING": "utf-8"}
ENV.pop("NEXA_SLIDE_WORKSPACE", None)
FAILS = []


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else extra)
    if not cond:
        FAILS.append(name)


def svc(cmd):
    return subprocess.run([sys.executable, str(STUDIO / "service.py"), cmd], env=ENV, cwd=str(USER), capture_output=True, text=True, encoding="utf-8")


def client():
    jar = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def req(method, url, body=None):
        h = {"Accept": "application/json", "Origin": BASE}
        data = json.dumps(body).encode() if body is not None else None
        if data:
            h["Content-Type"] = "application/json"
        try:
            with op.open(urllib.request.Request(url, data=data, method=method, headers=h), timeout=60) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")
    return req


(USER / "settings.json").write_text(json.dumps({"hubPort": HUB_PORT, "hubProxy": True, "engine": str(STUDIO.parent)}), encoding="utf-8")
(USER / "hub" / "engine" / "requests.json").unlink(missing_ok=True)
(USER / "hub" / "engine" / ".studio" / "session.json").unlink(missing_ok=True)
try:
    print(svc("start").stdout.strip())
    (USER / "users.json").unlink(missing_ok=True)
    admin = client()
    admin("POST", BASE + "/api/auth/setup", {"id": "admin", "password": "el-test-pass-1"})
    for i in range(7):
        admin("POST", BASE + "/api/engine/requests", {"action": "add", "title": f"요청 {i + 1} {'글머리' if i % 3 == 0 else '표'}", "body": f"내용 {i + 1}"})
    admin("POST", BASE + "/api/engine/requests", {"action": "status", "id": 2, "status": "rejected"})
    st, d = admin("GET", BASE + "/api/engine")
    check("카드 recent 는 5건 · total 7", len(d.get("recent", [])) == 5 and d.get("total") == 7, (len(d.get("recent", [])), d.get("total")))
    st, d = admin("GET", BASE + "/api/engine/requests?q=" + urllib.parse.quote("글머리"))
    check("?q=글머리 → 3건", len(d.get("items", [])) == 3, len(d.get("items", [])))
    st, d = admin("GET", BASE + "/api/engine/requests?q=%235")
    check("?q=#5 → 1건(id 5)", len(d.get("items", [])) == 1 and d["items"][0]["id"] == 5, d.get("items"))
    st, d = admin("GET", BASE + "/api/engine/requests?status=rejected")
    check("?status=rejected → 1건", len(d.get("items", [])) == 1, d.get("items"))
    # 배포 계획·기록(0.22.29) - 조회만(POST run 은 이 저장소에서 실제 배포가 될 수 있어 engine_deploy_test 의 임시 저장소에서만 본다)
    st, d = admin("GET", BASE + "/api/engine/deploy")
    check("/api/engine/deploy → 계획(commits·requests·blockers·ready)", st == 200 and all(k in d for k in ("commits", "requests", "blockers", "ready", "main")), (st, str(d)[:300]))
    st, d = admin("GET", BASE + "/api/engine/deploy?fetch=0")
    check("/api/engine/deploy?fetch=0 → 마지막 배포", st == 200 and "state" in (d.get("last") or {}), (st, str(d)[:200]))
    st, d = admin("GET", BASE + "/api/engine")
    check("/api/engine 에 deploy(관리자)", "deploy" in d, list(d)[:12])
    # 허브 화면 판(0.22.30) - 화면 파일이 바뀌면 notice 의 ui 값이 바뀐다(menu.js 가 [새로 고침] 안내)
    st, d = admin("GET", BASE + "/api/engine/notice")
    ui0 = d.get("ui")
    f = HERE.parent / "lightbox.js"
    t = f.stat()
    os.utime(f, ns=(t.st_atime_ns, max(t.st_mtime_ns, int(ui0 or 0)) + 1_000_000_000))
    st, d = admin("GET", BASE + "/api/engine/notice")
    os.utime(f, ns=(t.st_atime_ns, t.st_mtime_ns))
    check("notice.ui - 허브 화면 파일이 바뀌면 값이 바뀐다", ui0 and d.get("ui") and d.get("ui") != ui0, (ui0, d.get("ui")))
    sc = {"base": BASE, "login": {"id": "admin", "password": "el-test-pass-1"}, "ignoreErrors": "fontfile|wsfonts",  # 이 PC 에 없는 글꼴(Pretendard 등)의 404 - share_test 와 같음
          "pages": [
        {"url": "/studio/home.html#start", "wait": 2500, "steps": [
            {"name": "카드 목록 5건 + 더 보기(전체 7건)", "js": "const n=document.querySelectorAll('#engList .ritem').length; const m=document.querySelector('#engList a[href=\"/engine\"]'); return n===5 && m && m.textContent.includes('7') ? true : 'n='+n+' more='+(m&&m.textContent)"}]},
        {"url": "/engine", "wait": 2000, "steps": [
            {"name": "/engine 페이지 - 7건 · 상태 칩", "js": "const n=document.querySelectorAll('#list .it').length; const chips=document.querySelectorAll('#filters [data-st]').length; return n===7 && chips>=3 ? true : 'n='+n+' chips='+chips"},
            {"name": "  검색 '글머리' → 3건 · 강조", "js": "const q=document.querySelector('#q'); q.value='글머리'; q.dispatchEvent(new Event('input',{bubbles:true})); await new Promise(r=>setTimeout(r,200)); const n=document.querySelectorAll('#list .it').length; const mk=document.querySelectorAll('#list mark').length; return n===3 && mk>=3 ? true : 'n='+n+' marks='+mk"},
            {"name": "  검색 '#5' → 1건", "js": "const q=document.querySelector('#q'); q.value='#5'; q.dispatchEvent(new Event('input',{bubbles:true})); await new Promise(r=>setTimeout(r,200)); const n=document.querySelectorAll('#list .it').length; return n===1 ? true : 'n='+n"},
            {"name": "  상태 칩 '거절' → 1건", "js": "const q=document.querySelector('#q'); q.value=''; q.dispatchEvent(new Event('input',{bubbles:true})); document.querySelector('#filters [data-st=\"rejected\"]').click(); await new Promise(r=>setTimeout(r,200)); const n=document.querySelectorAll('#list .it').length; return n===1 ? true : 'n='+n"},
            {"name": "  제목 클릭 → 내용 펼침 · 관리자 단추(삭제)", "js": "document.querySelector('#filters [data-st=\"\"]').click(); await new Promise(r=>setTimeout(r,200)); document.querySelector('#list [data-toggle=\"7\"]').click(); await new Promise(r=>setTimeout(r,200)); const it=document.querySelector('#list .it[data-id=\"7\"]'); return it.classList.contains('open') && it.querySelector('.body') && document.querySelector('#list [data-er=\"remove\"][data-id=\"2\"]') ? true : 'open='+it.className"},
            {"name": "  거절 동작(확인 창 자동 예)", "js": "window.confirm=()=>true; document.querySelector('#list [data-er=\"rejected\"][data-id=\"7\"]').click(); await new Promise(r=>setTimeout(r,1200)); const b=document.querySelector('#list .it[data-id=\"7\"] .badge'); return b && b.textContent.includes('거절') ? true : 'badge='+(b&&b.textContent)"},
            {"name": "  삭제 동작 → 6건", "js": "window.confirm=()=>true; document.querySelector('#list [data-er=\"remove\"][data-id=\"2\"]').click(); await new Promise(r=>setTimeout(r,1200)); const n=document.querySelectorAll('#list .it').length; return n===6 ? true : 'n='+n"}]}]}
    sp = WORK / "englist_scenario.json"
    sp.write_text(json.dumps(sc, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run(["node", str(HERE / "smoke.js"), str(sp)], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(HERE))
    print(r.stdout[-2500:])
    check("헤드리스 시나리오 통과", r.returncode == 0, r.stderr[-500:])
finally:
    print("  ", svc("stop").stdout.strip())
    (USER / "hub" / "engine" / "requests.json").unlink(missing_ok=True)
print("\n실패:", FAILS or "없음")
sys.exit(1 if FAILS else 0)
