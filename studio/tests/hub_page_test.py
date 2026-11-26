# -*- coding: utf-8 -*-
"""첫 문서로 페이지(실험 기능) - init_workspace --kind page · 허브 계획·만들기 · 시작 페이지(home.html) 종류 단추.
    python studio/tests/hub_page_test.py
- CLI: 임시 폴더(tmpfiles)에 --kind page --page-template report → 시작 문서 kind page·template report·startDeck·experimental.page / --starter 와 같이 쓰면 거절 / 없는 템플릿은 오류.
- 허브(격리 5799 - 운영 허브 5599 는 건드리지 않는다): NEXA_SLIDE_EXPERIMENTAL=-page 로 끄고 띄우면(기본은 켬 - DR-P13) /api/home experimental·pageTemplates 가 비고 kind page 계획·만들기 거절, 종류 단추 2개.
  NEXA_SLIDE_EXPERIMENTAL=page 로 띄우면 템플릿 11종 · 만들기 → 작업 공간 · 시작 문서가 page.html 로 열림 · 종류 단추 3개 · 페이지를 고르면 슬라이드 템플릿 영역이 숨고 칩 11개 · 계획 요청 본문에 kind page·pageTemplate."""
import http.cookiejar
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

import testlock  # noqa: F401 - 이 PC 에서 시험은 한 번에 하나(고정 포트 5799·Chrome)
for _s in (sys.stdout, sys.stderr): _s.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
STUDIO = HERE.parent
sys.path.insert(0, str(STUDIO))
import tmpfiles  # noqa: E402

WORK = Path(os.environ.get("NEXA_TEST_DIR") or Path(tempfile.gettempdir()) / "nexa-slide-tests")
USER, PROJ, PORT = WORK / "user", WORK / "projects", 5799
B = f"http://127.0.0.1:{PORT}"
FAILS = []
BASE_ENV = {k: v for k, v in os.environ.items() if k not in ("NEXA_SLIDE_WORKSPACE", "NEXA_SLIDE_EXPERIMENTAL")}
BASE_ENV.update({"NEXA_SLIDE_USER_DIR": str(USER), "NEXA_SLIDE_PROJECTS": str(PROJ), "PYTHONIOENCODING": "utf-8"})


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else str(extra)[:600])
    if not cond:
        FAILS.append(name)


def run(args, env=None, cwd=None):
    r = subprocess.run([sys.executable, *map(str, args)], env=env or BASE_ENV, cwd=str(cwd or USER), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    return r.returncode, r.stdout + r.stderr


def cli():
    with tmpfiles.temp_dir("nx-pgws-") as d:
        ws = Path(d) / "문서함"
        rc, out = run([STUDIO / "init_workspace.py", ws, "--title", "페이지 작업 공간", "--kind", "page", "--page-template", "report"], cwd=d)
        root = ws / "slides" if (ws / "slides" / "nexa-slide.json").is_file() else ws
        cfg = json.loads((root / "nexa-slide.json").read_text(encoding="utf-8")) if (root / "nexa-slide.json").is_file() else {}
        sd = cfg.get("startDeck")
        doc = json.loads((root / "decks" / f"{sd}.json").read_text(encoding="utf-8")) if sd and (root / "decks" / f"{sd}.json").is_file() else {}
        content = [p for p in (root / "content").rglob("*") if p.is_file()] if (root / "content").is_dir() else []
        check("CLI --kind page --page-template report - 시작 문서 kind page · template report · startDeck · experimental.page · content 원본 없음",
              rc == 0 and doc.get("kind") == "page" and doc.get("template") == "report" and (cfg.get("experimental") or {}).get("page") is True and not content,
              json.dumps({"rc": rc, "out": out[-300:], "startDeck": sd, "kind": doc.get("kind"), "tpl": doc.get("template"), "exp": cfg.get("experimental"), "content": [str(p.name) for p in content][:5]}, ensure_ascii=False))
        rc2, out2 = run([STUDIO / "init_workspace.py", Path(d) / "둘", "--title", "x", "--kind", "page", "--starter", "lecture"], cwd=d)
        check("CLI --kind page --starter … 는 거절", rc2 != 0, (rc2, out2[-200:]))
        rc3, out3 = run([STUDIO / "init_workspace.py", Path(d) / "셋", "--title", "x", "--kind", "page", "--page-template", "없는템플릿"], cwd=d)
        check("CLI 없는 템플릿 이름은 오류 메시지", rc3 != 0 and "없는템플릿" in out3, (rc3, out3[-200:]))


class Hub:
    def __init__(self, experimental):
        self.env = dict(BASE_ENV)
        self.env["NEXA_SLIDE_EXPERIMENTAL"] = "page" if experimental else "-page"  # 기본이 켬이라(RELEASED) 끈 상태는 명시한다
        USER.mkdir(parents=True, exist_ok=True)
        PROJ.mkdir(parents=True, exist_ok=True)
        s = USER / "settings.json"
        cfg = json.loads(s.read_text(encoding="utf-8")) if s.is_file() else {}
        cfg.update({"hubPort": PORT, "hubProxy": True, "engine": str(STUDIO.parent)})
        s.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
        (USER / "users.json").unlink(missing_ok=True)
        print("  ", run([STUDIO / "service.py", "start"], env=self.env)[1].strip()[-160:])
        self.jar = http.cookiejar.CookieJar()
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.req("POST", "/api/auth/setup", {"id": "admin", "password": "hubpage-pass-123"})

    def req(self, method, url, body=None):
        h = {"Accept": "application/json", "Origin": B, "Content-Type": "application/json"}
        rq = urllib.request.Request(B + url, data=json.dumps(body, ensure_ascii=False).encode() if body is not None else None, method=method, headers=h)
        try:
            with self.op.open(rq, timeout=180) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read() or b"{}")
            except ValueError:
                return e.code, {}

    def stop(self):
        print("  ", run([STUDIO / "service.py", "stop"], env=self.env)[1].strip()[-160:])


def scenario(pages):
    with tmpfiles.temp_dir("nx-hubpg-") as d:
        f = Path(d) / "hub_page_scn.json"
        f.write_text(json.dumps({"base": B, "login": {"id": "admin", "password": "hubpage-pass-123"}, "pages": pages}, ensure_ascii=False), "utf-8")
        r = subprocess.run(["node", str(HERE / "smoke.js"), str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    lines = [l for l in r.stdout.splitlines() if l.startswith(("OK", "FAIL"))]
    for l in lines:
        print("  ", l[:600])
        if l.startswith("FAIL"):
            FAILS.append("화면: " + l[5:70])


KINDS = "const kinds=()=>[...document.querySelectorAll('#fKind [data-kind]')].map(b=>b.dataset.kind);"
WRAP = ("if(!window.__of){window.__of=window.fetch.bind(window);window.__plans=[];window.fetch=async(u,o={})=>{if(String(u).includes('/api/project')&&o.body){try{const b=JSON.parse(o.body);if(b.action==='plan')window.__plans.push(b);}catch(e){}}"
        "return window.__of(u,o);};}")


def main():
    cli()
    hub = Hub(False)
    try:
        st, h = hub.req("GET", "/api/home")
        check("허브(꺼짐) - /api/home experimental = [] · pageTemplates = []", st == 200 and h.get("experimental") == [] and h.get("pageTemplates") == [], json.dumps({k: h.get(k) for k in ("experimental", "pageTemplates")}, ensure_ascii=False))
        s1, r1 = hub.req("POST", "/api/project", {"action": "plan", "title": "꺼짐 페이지", "kind": "page", "pageTemplate": "report"})
        s2, r2 = hub.req("POST", "/api/project", {"action": "create", "title": "꺼짐 페이지", "kind": "page", "pageTemplate": "report"})
        check("허브(꺼짐) - kind page 계획·만들기 거절", s1 >= 400 and s2 >= 400, json.dumps([s1, r1, s2, r2], ensure_ascii=False)[:400])
        scenario([{"url": "/studio/home.html#new", "wait": 2500, "steps": [
            {"name": "home(꺼짐) - 종류 단추 2개(슬라이드·시트, 전과 같음)", "js": KINDS + "await until(async()=>kinds().length,4000);return kinds().join()==='deck,sheet' || JSON.stringify(kinds());"}]}])
    finally:
        hub.stop()
    hub = Hub(True)
    try:
        st, h = hub.req("GET", "/api/home")
        names = [t.get("name") for t in h.get("pageTemplates") or []]
        check("허브(켬) - /api/home experimental = ['page'] · 템플릿 11종", h.get("experimental") == ["page"] and len(names) == 11, json.dumps({"exp": h.get("experimental"), "names": names}, ensure_ascii=False))
        sp, rp = hub.req("POST", "/api/project", {"action": "plan", "title": "허브 페이지 시험", "kind": "page", "pageTemplate": "minutes"})
        check("허브(켬) - kind page 계획 200", sp == 200, json.dumps(rp, ensure_ascii=False)[:300])
        sc, rc_ = hub.req("POST", "/api/project", {"action": "create", "title": "허브 페이지 시험", "kind": "page", "pageTemplate": "minutes"})
        url = (rc_ or {}).get("url") or ""
        check("허브(켬) - 만들기 → 작업 공간 · 주소", sc == 200 and url, json.dumps(rc_, ensure_ascii=False)[:300])
        pages = [{"url": "/studio/home.html#new", "wait": 2500, "steps": [
            {"name": "home(켬) - 종류 단추 3개 · 페이지를 고르면 슬라이드 템플릿 영역(#deckOpts)이 숨고 템플릿 칩 11개 · 계획 요청 본문에 kind page·pageTemplate",
             "js": WRAP + KINDS + "await until(async()=>kinds().length===3,5000);const k=kinds();window.__k0=k.join();if(k.length<3){document.querySelector('#fKind [data-kind=deck]').click();await new Promise(r=>setTimeout(r,300));window.__k1=kinds().join();return JSON.stringify({처음:window.__k0,슬라이드_누른_뒤:window.__k1});}const pb=document.querySelector('#fKind [data-kind=page]');if(!pb)return JSON.stringify({k,fKind:!!document.querySelector('#fKind'),hash:location.hash});pb.click();await until(async()=>document.querySelectorAll('#pageOpts [data-ptpl]').length,4000);"
                   "const chips=document.querySelectorAll('#pageOpts [data-ptpl]').length,hidden=getComputedStyle(document.querySelector('#deckOpts')).display==='none';"
                   "document.querySelector('#fTitle').value='계획 시험';document.querySelector('#fTitle').dispatchEvent(new Event('input',{bubbles:true}));const vb=document.querySelector('#pageOpts [data-ptpl=vocab]');if(!vb)return JSON.stringify({k,chips,names:[...document.querySelectorAll('#pageOpts [data-ptpl]')].map(x=>x.dataset.ptpl)});vb.click();"
                   "await until(async()=>window.__plans.some(b=>b.kind==='page'&&b.pageTemplate==='vocab'),8000);const p=window.__plans.slice(-1)[0]||{};"
                   "return k.join()==='deck,sheet,page'&&chips===11&&hidden&&p.kind==='page'&&p.pageTemplate==='vocab' || JSON.stringify({k,chips,hidden,plan:p});"}]}]
        # 홈 화면에서 페이지 + 템플릿 '보고서' 로 만들기 → 만들기 본문에 pageTemplate report · 시작 문서 template report(d4392f6 전에는 본문에서 빠졌다).
        # 만들기 응답은 시험이 받아 두고 화면에는 실패로 돌려준다(작업 공간 주소로 넘어가면 단계가 끊긴다)
        pages.append({"url": "/studio/home.html#new", "wait": 2500, "steps": [
            {"name": "home(켬) - 페이지 + '보고서' 템플릿으로 [만들기] → 만들기 본문 kind page · pageTemplate report → 만든 시작 문서 kind page · template report",
             "timeout": 150000,
             "js": KINDS + "if(!window.__cf){window.__cf=window.fetch.bind(window);window.fetch=async(u,o={})=>{let b=null;try{b=o.body&&JSON.parse(o.body);}catch(e){}const r=await window.__cf(u,o);"
                   "if(String(u).includes('/api/project')&&b&&b.action==='create'){let j={};try{j=await r.clone().json();}catch(e){}window.__cres={body:b,st:r.status,data:j};return new Response(JSON.stringify({ok:false,error:'시험 - 이동 막음'}),{status:409,headers:{'Content-Type':'application/json'}});}return r;};}"
                   "await until(async()=>kinds().length===3,5000);document.querySelector('#fKind [data-kind=page]').click();await until(async()=>document.querySelector('#pageOpts [data-ptpl=report]'),4000);"
                   "document.querySelector('#pageOpts [data-ptpl=report]').click();const t=document.querySelector('#fTitle');t.value='홈 보고서 시험';t.dispatchEvent(new Event('input',{bubbles:true}));await new Promise(r=>setTimeout(r,1500));"
                   "document.querySelector('#fGo').click();await until(async()=>window.__cres,120000);const c=window.__cres||{};const url=(c.data||{}).url||'';"
                   "if(!url)return JSON.stringify({body:c.body,st:c.st,data:c.data});const base=new URL(url,location.href).pathname.replace(/\/$/,'');"
                   "const ds=await (await window.__cf(base+'/api/decks',{cache:'no-store'})).json();const lst=Array.isArray(ds)?ds:(ds.decks||[]);const sd=lst.find(x=>x.start)||lst[0]||{};"
                   "const d=sd.id&&await (await window.__cf(base+'/api/deck/'+sd.id,{cache:'no-store'})).json();"
                   "return c.body.kind==='page'&&c.body.pageTemplate==='report'&&c.st===200&&d&&d.kind==='page'&&d.template==='report' || JSON.stringify({body:{kind:c.body.kind,pageTemplate:c.body.pageTemplate},st:c.st,url,decks:lst.map(x=>[x.id,x.kind,x.start]),kind:d&&d.kind,tpl:d&&d.template});"}]})
        if url:
            rel = url.replace(B, "") if url.startswith("http") else url
            pages.append({"url": rel, "wait": 3500, "steps": [
                {"name": "만든 작업 공간 - 시작 문서가 page.html 로 열림(kind page · template minutes)",
                 "js": "await until(async()=>location.pathname.endsWith('page.html'),8000);const id=new URLSearchParams(location.search).get('deck');const base=location.pathname.replace(/\\/studio\\/page\\.html$/,'');"
                       "const d=id&&await (await fetch(base+'/api/deck/'+id,{cache:'no-store'})).json();return location.pathname.endsWith('page.html')&&d&&d.kind==='page'&&d.template==='minutes' || JSON.stringify({href:location.href,kind:d&&d.kind,tpl:d&&d.template});"}]})
        scenario(pages)
    finally:
        hub.stop()
    print(f"\n{'전부 통과' if not FAILS else '실패: ' + ', '.join(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
