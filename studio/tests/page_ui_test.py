# -*- coding: utf-8 -*-
"""페이지 문서(kind = "page") 시험 - 숨김 스위치 · 만들기 · 저장 검사 · 종류별 편집기 이동 · page.html 편집(헤드리스 Chrome) · 두 창 관찰.
    python studio/tests/page_ui_test.py
- 실험 기능을 끈 작업 공간(page끔시험)과 켠 작업 공간(page시험 - nexa-slide.json "experimental": {"page": true})을 따로 만든다(포트 5667).
- 화면 단계는 smoke.js 시나리오(실제 입력 = CDP Input.insertText · dispatchKeyEvent). 판정은 상태 덤프 + 기대 값.
- 두 창(옛 판 위 다른 문단 저장)은 blocks 병합기(PG-080) 전이라 결과를 관찰만 한다(단언하지 않음 - 줄에 '관찰' 로 찍는다)."""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import testlock  # noqa: F401 - 이 PC 에서 시험은 한 번에 하나(고정 포트·임시 폴더·Chrome)
for _s in (sys.stdout, sys.stderr): _s.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
STUDIO = HERE.parent
sys.path.insert(0, str(STUDIO))
import tmpfiles  # noqa: E402

WORK = Path(os.environ.get("NEXA_TEST_DIR") or Path(tempfile.gettempdir()) / "nexa-slide-tests")
USER, PROJ, PORT = WORK / "user", WORK / "projects", 5667
B = f"http://127.0.0.1:{PORT}"
FAILS, NOTES = [], []


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else str(extra)[:600])
    if not cond:
        FAILS.append(name)


def env(ws):
    return {**os.environ, "NEXA_SLIDE_USER_DIR": str(USER), "NEXA_SLIDE_PROJECTS": str(PROJ), "PYTHONIOENCODING": "utf-8", "NEXA_SLIDE_WORKSPACE": str(ws)}


def call(method, url, body=None):
    rq = urllib.request.Request(B + url, data=None if body is None else json.dumps(body, ensure_ascii=False).encode(), method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(rq, timeout=15) as r:
            return r.status, json.loads(r.read() or b"{}"), r.headers.get("X-Deck-Version")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}"), None
        except ValueError:
            return e.code, {}, None


def workspace(name, experimental):
    ws = PROJ / name / "slides"
    if not (ws / "nexa-slide.json").is_file():
        subprocess.run([sys.executable, str(STUDIO / "init_workspace.py"), str(ws.parent), "--title", name, "--port", str(PORT)], env=env(ws), capture_output=True, text=True, encoding="utf-8")
    cfg = json.loads((ws / "nexa-slide.json").read_text(encoding="utf-8"))
    if experimental:
        cfg["experimental"] = {"page": True}
    else:
        cfg.pop("experimental", None)
    (ws / "nexa-slide.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    d = ws / "decks"
    d.mkdir(parents=True, exist_ok=True)
    for f in d.glob("pg*.json"):
        f.unlink()
    return ws


class Server:
    def __init__(self, ws):
        self.ws = ws
        e = {k: v for k, v in env(ws).items() if k != "NEXA_SLIDE_EXPERIMENTAL"}
        self.p = subprocess.Popen([sys.executable, str(STUDIO / "server.py"), "--workspace", str(ws), "--port", str(PORT)], env=e, cwd=str(ws), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(60):
            try:
                urllib.request.urlopen(B + "/api/decks", timeout=2).read(); return
            except Exception:  # noqa: BLE001
                time.sleep(0.5)

    def stop(self):
        self.p.terminate()
        try:
            self.p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.p.kill()


def deck_file(ws, i):
    return json.loads((ws / "decks" / f"{i}.json").read_text(encoding="utf-8"))


def scenario(steps_pages):
    """smoke.js 로 시나리오를 돌려 (줄들, 종료 코드)"""
    with tmpfiles.temp_dir("nx-page-") as d:
        f = Path(d) / "page_scn.json"
        f.write_text(json.dumps({"base": B, "pages": steps_pages}, ensure_ascii=False), "utf-8")
        r = subprocess.run(["node", str(HERE / "smoke.js"), str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    return [l for l in r.stdout.splitlines() if l.startswith(("OK", "FAIL"))], r.returncode


# ---------------------------------------------------------------- 화면 시나리오 조각
H = ("const E=window.NexaPageEditor;const S=E.S;const idle=()=>until(async()=>(!S.dirty&&!S.saving&&document.querySelector('#status').textContent==='저장됨'),10000);"
     "const srv=async(id)=>(await (await fetch('/api/deck/'+id,{cache:'no-store'})).json());const bid=(k)=>S.deck.blocks[k].id;"
     "const el=(id)=>document.querySelector('#ed [data-id=\"'+id+'\"]');const tx=(b)=>(b.runs||[]).map(r=>r.t).join('');"
     "const D=()=>JSON.stringify({blocks:S.deck.blocks,caret:(E.ed.selection()||{}).f,status:document.querySelector('#status').textContent});")
INS = lambda t: [{"method": "Input.insertText", "params": {"text": t}, "wait": 40}]  # noqa: E731


def KEY(k, code, vk, mods=0, text=None):
    down = {"type": "keyDown" if text else "rawKeyDown", "key": k, "code": code, "windowsVirtualKeyCode": vk, "nativeVirtualKeyCode": vk, "modifiers": mods}
    if text:
        down["text"] = text
    return [{"method": "Input.dispatchKeyEvent", "params": down, "wait": 20},
            {"method": "Input.dispatchKeyEvent", "params": {"type": "keyUp", "key": k, "code": code, "windowsVirtualKeyCode": vk, "nativeVirtualKeyCode": vk, "modifiers": mods}, "wait": 80}]


def step(name, js, pre=None, cdp=None, **kw):
    s = {"name": name, "js": js, **kw}
    if pre is not None:
        s["pre"] = H + pre + " return true;"
    if cdp:
        s["cdp"] = cdp
    return s


def page_steps(pid):
    """page.html 편집 - pid 는 새로 만든 페이지 문서(b01 제목 · b02 빈 본문)"""
    return [
        step("편집 - 본문에 글 치기 → 0.7초 뒤 저장됨 · 서버 파일의 runs",
             H + "await idle();const f=await srv('" + pid + "');const b=f.blocks.find(x=>x.id===bid(1));return tx(b)==='안녕하세요 페이지' || D();",
             pre="E.ed.focus();E.ed.select({id:bid(1),off:0});", cdp=INS("안녕하세요 페이지"), wait=200),
        step("편집 - 굵게 단추 → runs 의 b · 화면 span 굵기 700",
             H + "await idle();const b=S.deck.blocks[1];const r=b.runs.find(x=>x.b);const sp=[...el(b.id).querySelectorAll('span')].find(s=>s.textContent==='안녕');"
                 "return r&&r.t==='안녕'&&sp&&getComputedStyle(sp).fontWeight>=700 || D();",
             pre="E.ed.select({id:bid(1),off:0},{id:bid(1),off:2});document.querySelector('[data-mark=b]').click();"),
        step("편집 - 글자색·형광펜 단추 → runs 의 c·hl · 화면 색",
             H + "await idle();const b=S.deck.blocks[1];const r=b.runs.find(x=>x.t==='페이지');const sp=[...el(b.id).querySelectorAll('span')].find(s=>s.textContent==='페이지');"
                 "return r&&r.c&&r.hl&&sp&&getComputedStyle(sp).color!==getComputedStyle(el(b.id)).color&&getComputedStyle(sp).backgroundColor!=='rgba(0, 0, 0, 0)' || D()+JSON.stringify(sp&&[getComputedStyle(sp).color,getComputedStyle(sp).backgroundColor]);",
             pre="E.ed.select({id:bid(1),off:6},{id:bid(1),off:9});document.querySelector('[data-act=color]').click();E.ed.select({id:bid(1),off:6},{id:bid(1),off:9});document.querySelector('[data-act=hl]').click();"),
        step("편집 - 스타일 '제목 1'(h1) → block.style · 글자 크기 20pt(26.7px) 상당",
             H + "await idle();const b=S.deck.blocks[1];const fs=parseFloat(getComputedStyle(el(b.id)).fontSize);return b.style==='h1'&&Math.abs(fs-26.67)<1.5 || D()+' fontSize='+fs;",
             pre="E.ed.select({id:bid(1),off:1});const s=document.querySelector('#selStyle');s.value='h1';s.dispatchEvent(new Event('change',{bubbles:true}));"),
        step("편집 - 가운데 정렬 단추 → block.align · text-align",
             H + "await idle();const b=S.deck.blocks[1];return b.align==='center'&&getComputedStyle(el(b.id)).textAlign==='center' || D();",
             pre="E.ed.select({id:bid(1),off:1});document.querySelector('[data-align=center]').click();"),
        step("목록 - 번호 매기기 두 문단 → 머리 기호 1. 2. · Tab → a. · Shift+Tab → 1. 2.",
             H + "await idle();const ids=[S.deck.blocks[2].id,S.deck.blocks[3].id];const m1=ids.map(i=>el(i).dataset.marker);"
                 "E.ed.select({id:ids[1],off:0});document.querySelector('#ed').dispatchEvent(new KeyboardEvent('keydown',{key:'Tab',bubbles:true,cancelable:true}));await new Promise(r=>setTimeout(r,80));const m2=ids.map(i=>el(i).dataset.marker);"
                 "document.querySelector('#ed').dispatchEvent(new KeyboardEvent('keydown',{key:'Tab',shiftKey:true,bubbles:true,cancelable:true}));await new Promise(r=>setTimeout(r,80));const m3=ids.map(i=>el(i).dataset.marker);"
                 "return m1.join()==='1.,2.'&&m2.join()==='1.,a.'&&m3.join()==='1.,2.' || JSON.stringify({m1,m2,m3,lv:S.deck.blocks.slice(2,4).map(b=>b.list)});",
             pre="E.ed.select({id:bid(1),off:tx(S.deck.blocks[1]).length});", cdp=KEY("Enter", "Enter", 13, text="\r") + INS("첫째") + KEY("Enter", "Enter", 13, text="\r") + INS("둘째")
             + [{"method": "Runtime.evaluate", "params": {"expression": "(()=>{const S=NexaPageEditor.S;const a=S.deck.blocks[2].id,b=S.deck.blocks[3].id;NexaPageEditor.ed.select({id:a,off:0},{id:b,off:2});document.querySelector('[data-list=number]').click();})()"}, "wait": 120}]),
        step("목록 - 빈 목록 문단에서 Enter → 목록이 풀림(list 없음)",
             H + "await new Promise(r=>setTimeout(r,150));const b=S.deck.blocks[4];return b&&!b.list&&tx(b)==='' || D();",
             pre="const id=S.deck.blocks[3].id;E.ed.select({id,off:tx(S.deck.blocks[3]).length});", cdp=KEY("Enter", "Enter", 13, text="\r") + KEY("Enter", "Enter", 13, text="\r")),
        step("쪽 나누기 - Ctrl+Enter → break 블록(kind page) + 새 빈 문단",
             H + "await new Promise(r=>setTimeout(r,150));const k=S.deck.blocks.findIndex(b=>b.type==='break');return k>0&&S.deck.blocks[k].kind==='page'&&S.deck.blocks[k+1]&&S.deck.blocks[k+1].type==='p' || D();",
             pre="const b=S.deck.blocks[S.deck.blocks.length-1];E.ed.select({id:b.id,off:0});", cdp=KEY("Enter", "Enter", 13, mods=2)),
        step("실행 취소 - 이어 친 글(abc)은 한 묶음 · 다시 실행",
             H + "await new Promise(r=>setTimeout(r,100));const b0=tx(S.deck.blocks[S.deck.blocks.length-1]);E.undo();await new Promise(r=>setTimeout(r,80));const b1=tx(S.deck.blocks[S.deck.blocks.length-1]);E.redo();await new Promise(r=>setTimeout(r,80));const b2=tx(S.deck.blocks[S.deck.blocks.length-1]);"
                 "return b0==='abc'&&b1===''&&b2==='abc' || JSON.stringify({b0,b1,b2});",
             pre="const b=S.deck.blocks[S.deck.blocks.length-1];E.ed.select({id:b.id,off:0});", cdp=INS("a") + INS("b") + INS("c")),
        step("저장 - 다 저장된 뒤 서버 파일 = 화면 문서(blocks)",
             H + "await idle();const f=await srv('" + pid + "');return JSON.stringify(f.blocks)===JSON.stringify(S.deck.blocks) || JSON.stringify({srv:f.blocks.length,scr:S.deck.blocks.length});"),
    ]


def main():
    ws_off = workspace("page끔시험", False)
    ws_on = workspace("page시험", True)
    # 1. 숨김 - 끈 작업 공간
    srv = Server(ws_off)
    try:
        st, r, _ = call("POST", "/api/decks", {"action": "create", "kind": "page", "title": "숨김"})
        _, cfg, _ = call("GET", "/api/config")
        check("1 숨김 - 실험 기능을 끈 작업 공간: 페이지 만들기 400 · /api/config experimental = []", st == 400 and cfg.get("experimental") == [], json.dumps({"st": st, "r": r, "exp": cfg.get("experimental")}, ensure_ascii=False))
        # 2. 기존 종류 PUT 은 영향 없음(끈 작업 공간)
        st1, r1, _ = call("PUT", "/api/deck/pgslide", {"id": "pgslide", "title": "슬라이드", "slides": [{"id": "s1", "elements": [{"id": "e1", "type": "text", "x": 10, "y": 10, "w": 100, "h": 40, "text": "글"}]}]})
        st2, r2, _ = call("PUT", "/api/deck/pgsheet", {"id": "pgsheet", "title": "시트", "kind": "sheet", "slides": [], "sheets": [{"id": "t01", "name": "S", "cells": {"A1": 1}}]})
        check("2 기존 슬라이드·시트 PUT 은 그대로 200", st1 == 200 and st2 == 200, (st1, r1, st2, r2))
    finally:
        srv.stop()
    # 1. 켠 작업 공간
    srv = Server(ws_on)
    try:
        _, cfg, _ = call("GET", "/api/config")
        st, r, _ = call("POST", "/api/decks", {"action": "create", "kind": "page", "title": "첫 페이지"})
        pid = (r or {}).get("id") or ""
        f = deck_file(ws_on, pid) if pid and (ws_on / "decks" / f"{pid}.json").is_file() else {}
        check("1 켠 작업 공간: /api/config experimental = ['page'] · 만들기 201(또는 200) · 파일 kind page · blocks 2개",
              cfg.get("experimental") == ["page"] and st in (200, 201) and f.get("kind") == "page" and len(f.get("blocks") or []) == 2, json.dumps({"st": st, "r": r, "exp": cfg.get("experimental"), "f": f}, ensure_ascii=False)[:500])
        NOTES.append(f"만들기 응답 코드 {st} · 응답 {json.dumps(r, ensure_ascii=False)[:160]}")
        rc = subprocess.run([sys.executable, str(ws_on / "nexa.py"), "deck", "create", "pgcli", "--kind", "page", "--title", "명령으로"], env={**env(ws_on), "NEXA_SLIDE_HOME": str(STUDIO.parent)}, cwd=str(ws_on), capture_output=True, text=True, encoding="utf-8", errors="replace")
        fc = deck_file(ws_on, "pgcli") if (ws_on / "decks" / "pgcli.json").is_file() else {}
        check("1 nexa.py deck create pgcli --kind page - 파일 kind page", rc.returncode == 0 and fc.get("kind") == "page", (rc.returncode, (rc.stdout + rc.stderr)[-300:]))
        # 2. 저장 검사
        base = deck_file(ws_on, pid)
        bad1 = json.loads(json.dumps(base)); bad1["blocks"].append({"id": "x1", "type": "모르는종류"})
        bad2 = json.loads(json.dumps(base)); bad2["blocks"].append({"id": base["blocks"][0]["id"], "type": "p", "runs": []})
        s1, e1, _ = call("PUT", f"/api/deck/{pid}", bad1)
        s2, e2, _ = call("PUT", f"/api/deck/{pid}", bad2)
        good = json.loads(json.dumps(base)); good["blocks"][1]["runs"] = [{"t": "맞는 형식"}]
        s3, e3, _ = call("PUT", f"/api/deck/{pid}", good)
        check("2 형식이 틀린 page PUT(모르는 블록 종류 · id 중복) → 400 '페이지 형식 아님' · 맞는 것 200",
              s1 == 400 and s2 == 400 and "페이지 형식 아님" in str(e1.get("error")) and "페이지 형식 아님" in str(e2.get("error")) and s3 == 200, json.dumps([s1, e1, s2, e2, s3, e3], ensure_ascii=False)[:500])
        s1, _, _ = call("PUT", "/api/deck/pgslide", {"id": "pgslide", "title": "슬라이드", "slides": [{"id": "s1", "elements": []}]})
        s2, _, _ = call("PUT", "/api/deck/pgsheet", {"id": "pgsheet", "title": "시트", "kind": "sheet", "slides": [], "sheets": [{"id": "t01", "name": "S", "cells": {"A1": 1}}]})
        check("2 켠 작업 공간에서도 슬라이드·시트 PUT 200", s1 == 200 and s2 == 200, (s1, s2))
        # 긴 문서(문단 80개) - 쪽 경계선
        long_ = json.loads(json.dumps(base)); long_["id"] = "pglong"; long_["title"] = "긴 문서"
        long_["blocks"] = [{"id": f"L{k:02d}", "type": "p", "runs": [{"t": f"{k}번째 문단 - " + "가나다라마바사아자차카타파하 " * 6}]} for k in range(80)]
        sl, el_, _ = call("PUT", "/api/deck/pglong", long_)
        # 새로 만든 문서를 화면 시험용으로 다시 비운다(제목 + 빈 본문)
        st_, _, v_ = call("GET", f"/api/deck/{pid}")
        fresh = deck_file(ws_on, pid); fresh["blocks"] = [fresh["blocks"][0], {"id": "b02", "type": "p", "runs": []}]
        call("PUT", f"/api/deck/{pid}?base={v_}", fresh)
        # 3·4. 화면
        enc = lambda s: urllib.request.quote(s)  # noqa: E731
        pages = [
            {"url": f"/studio/index.html#{pid}", "wait": 2500, "steps": [step("3 이동 - 슬라이드 화면에서 페이지 문서를 열면 page.html?deck=", f"await until(async()=>location.pathname.endsWith('page.html'),6000);return location.pathname.endsWith('/page.html')&&new URLSearchParams(location.search).get('deck')==='{pid}' || location.href;")]},
            {"url": f"/studio/sheet.html?deck={pid}", "wait": 2500, "steps": [step("3 이동 - 시트 화면에서 페이지 문서를 열면 page.html?deck=", f"await until(async()=>location.pathname.endsWith('page.html'),6000);return location.pathname.endsWith('/page.html')&&new URLSearchParams(location.search).get('deck')==='{pid}' || location.href;")]},
            {"url": "/studio/page.html?deck=pgslide", "wait": 2500, "steps": [step("3 이동 - page.html 에서 슬라이드 id 를 열면 슬라이드 편집기로", "await until(async()=>!location.pathname.endsWith('page.html'),6000);return /index\\.html$|\\/studio\\/$/.test(location.pathname)&&location.hash.includes('pgslide') || location.href;")]},
            {"url": "/studio/page.html?deck=pgsheet", "wait": 2500, "steps": [step("3 이동 - page.html 에서 시트 id 를 열면 시트 편집기로", "await until(async()=>location.pathname.endsWith('sheet.html'),6000);return location.pathname.endsWith('/sheet.html')&&location.search.includes('pgsheet') || location.href;")]},
            {"url": f"/studio/page.html?deck={pid}", "wait": 2500, "steps": [
                step("3 덱 목록 메뉴(page.html) - 세 종류가 다 보이고(¶·▦·▭) 지금 문서에 ✓", "document.querySelector('#btnDecks').click();await until(async()=>document.querySelector('.menu'),4000);const t=document.querySelector('.menu').textContent;document.querySelectorAll('.menu').forEach(m=>m.remove());"
                     "return /¶/.test(t)&&/▦/.test(t)&&/▭/.test(t)&&/✓/.test(t) || t;"),
                *page_steps(pid)]},
            {"url": f"/studio/page.html?deck={pid}", "wait": 2500, "steps": [
                step("다시 열기 - 새로 고친 뒤 같은 모양(스타일 h1·가운데·굵게·목록 기호·쪽 나누기)",
                     H + "const b=S.deck.blocks;const has=(f)=>b.some(f);return b[1].style==='h1'&&b[1].align==='center'&&b[1].runs.some(r=>r.b)&&has(x=>x.list&&x.list.kind==='number')&&has(x=>x.type==='break')"
                         "&&!!document.querySelector('#ed .pg-li[data-marker=\"1.\"]') || D();")]},
            {"url": "/studio/page.html?deck=pglong", "wait": 3000, "steps": [
                step("긴 문서(문단 80개) - 쪽 경계선 수 = #pageInfo 의 n쪽 - 1 · 2쪽 이상", "const n=document.querySelectorAll('#pagelines i').length;const t=document.querySelector('#pageInfo').textContent;const k=parseInt(t);return k>=2&&n===k-1 || JSON.stringify({lines:n,info:t});")]},
        ]
        lines, rc = scenario(pages)
        for l in lines:
            print("  ", l[:700])
            if l.startswith("FAIL"):
                FAILS.append("화면: " + l[5:80])
        # 5. 두 창 - 관찰
        f0, v0 = deck_file(ws_on, pid), call("GET", f"/api/deck/{pid}")[2]
        a = json.loads(json.dumps(f0)); a["blocks"][0]["runs"] = [{"t": "창 A 가 고친 제목"}]
        sa, ra, _ = call("PUT", f"/api/deck/{pid}?base={v0}&merge=1", a)
        b = json.loads(json.dumps(f0)); k = next(i for i, x in enumerate(b["blocks"]) if i > 0 and x.get("type") == "p")
        b["blocks"][k]["runs"] = [{"t": "창 B 가 고친 문단"}]
        sb, rb, _ = call("PUT", f"/api/deck/{pid}?base={v0}&merge=1", b)
        fin = deck_file(ws_on, pid)
        tA = "".join(r.get("t", "") for r in fin["blocks"][0].get("runs") or [])
        tB = "".join(r.get("t", "") for r in fin["blocks"][k].get("runs") or [])
        obs = f"A {sa} · B {sb}(merged={rb.get('merged')} · 충돌 {len(rb.get('conflicts') or [])} {json.dumps((rb.get('conflicts') or [])[:2], ensure_ascii=False)[:200]}) · 결과 제목='{tA}' · 문단='{tB}'"
        NOTES.append("5 두 창(옛 판 위 다른 문단) 관찰: " + obs)
        print("관찰 5 두 창(옛 판 위 다른 문단):", obs)
    finally:
        srv.stop()
    for n in NOTES:
        print("  ·", n)
    print(f"\n{'전부 통과' if not FAILS else '실패: ' + ', '.join(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
