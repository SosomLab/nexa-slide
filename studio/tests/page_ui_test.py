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
        cfg["experimental"] = {"page": False}  # 기본이 켬이라(RELEASED) 끈 상태는 명시한다
    (ws / "nexa-slide.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    d = ws / "decks"
    d.mkdir(parents=True, exist_ok=True)
    for f in d.glob("*.json"):  # 시험 전용 작업 공간 - 지난 실행의 문서(추천 횟수 등)가 남지 않게
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


PS = "const q=(s)=>document.querySelector(s);const setv=(id,v)=>{const e=q(id);e.value=v;e.dispatchEvent(new Event('change',{bubbles:true}));};"


def token_steps():
    """템플릿 토큰(tokens.json)의 글꼴·색 - 제목 1(h1 = font title → 토큰 heading)의 글꼴 · 글자색 단추가 아닌 accent 토큰 값"""
    return [step("토큰 - 제목 1 문단의 글꼴 = tokens.json fonts.heading.css 의 첫 글꼴 · 토큰 accent 는 primary 값(기본 #c8553d 아님)",
                 H + "const t=await (await fetch('tokens.json',{cache:'no-store'})).json();const h=S.deck.blocks.find(b=>b.style==='h1');if(!h)return 'h1 없음';"
                     "const ff=getComputedStyle(el(h.id)).fontFamily;const want=((t.fonts||{}).heading||{}).css||'';const first=want.split(',')[0].replace(/[\"']/g,'').trim();"
                     "const prim=(t.colors||{}).primary||'';return !!first&&ff.replace(/[\"']/g,'').includes(first)&&prim&&prim.toLowerCase()!=='#c8553d' || JSON.stringify({ff,want,prim});")]


def setup_steps(pid):
    """쪽 설정 대화 상자 - A4 가로 · 여백 30/30/20/20 · 머리말 오른쪽 · 쪽 번호 아래 가운데"""
    return [
        step("쪽 설정 - A4 가로·여백 30/30/20/20·머리말 '문서 머리'(오른쪽)·쪽 번호 아래 가운데 → #paper 297mm · 서버 page · #pgHeader",
             H + PS + "q('[data-act=setup]').click();await until(async()=>q('#psOk'),3000);setv('#psSize','A4');setv('#psOrient','landscape');setv('#psMt',30);setv('#psMb',30);setv('#psMl',20);setv('#psMr',20);"
                      "q('#psHeader').value='문서 머리';setv('#psHeaderAlign','right');setv('#psNum','footer-center');q('#psOk').click();await idle();"
                      "const w=q('#paper').getBoundingClientRect().width/(96/25.4);const f=await srv('" + pid + "');const pg=f.page;"
                      "return !q('#psOk')&&Math.abs(w-297)<3&&pg.orient==='landscape'&&pg.margin.t===30&&pg.margin.b===30&&pg.margin.l===20&&pg.margin.r===20&&pg.header.blocks[0].align==='right'"
                      "&&pg.number.show===true&&pg.number.pos==='footer-center'&&/문서 머리/.test(q('#pgHeader').textContent) || JSON.stringify({w,page:pg,head:q('#pgHeader').textContent,open:!!q('#psOk')});"),
        step("쪽 설정 - 여백이 지나치게 크면(왼쪽·오른쪽 100) 오류 글이 뜨고 닫히지 않음 · Esc 로 닫힘",
             H + PS + "q('[data-act=setup]').click();await until(async()=>q('#psOk'),3000);setv('#psMl',100);setv('#psMr',100);setv('#psOrient','portrait');q('#psOk').click();await new Promise(r=>setTimeout(r,150));"
                      "const err=q('#psErr').textContent,open=!!q('#psOk');document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));await new Promise(r=>setTimeout(r,150));"
                      "return /여백/.test(err)&&open&&!q('#psOk')&&S.deck.page.orient==='landscape' || JSON.stringify({err,open,after:!!q('#psOk'),orient:S.deck.page.orient});"),
        step("쪽 설정 - 실행 취소로 되돌아감(세로) · 다시 실행(가로)",
             H + "E.undo();await new Promise(r=>setTimeout(r,120));const a=S.deck.page.orient;E.redo();await new Promise(r=>setTimeout(r,120));const b=S.deck.page.orient;await idle();"
                 "return a!=='landscape'&&b==='landscape' || JSON.stringify({a,b});"),
    ]


def table_steps(pid):
    """표 - 넣기(prompt 2×3) · 칸 안 편집 · Tab · 칸 안 서식 · 칸 안 목록 막음 · 오른쪽 클릭 메뉴 · 실행 취소 · 칸 안 한글 조합"""
    T = "const tb=()=>S.deck.blocks.find(b=>b.type==='table');const cells=()=>[...document.querySelectorAll('#ed .pg-cell')];const ctext=(c)=>((c.blocks||[])[0]&&(c.blocks[0].runs||[]).map(r=>r.t).join(''))||'';"
    menu = lambda label, cell="#ed table td,#ed table th": ("{const td=document.querySelector('" + cell + "');td.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true,clientX:200,clientY:200}));"  # noqa: E731
                          "await until(async()=>document.querySelector('.menu'),2000);const mb=[...document.querySelectorAll('.menu button')].find(b=>b.textContent.includes('" + label + "'));if(!mb)return 'no menu item " + label + "';mb.click();await new Promise(r=>setTimeout(r,150));}")
    return [
        step("표 - [표] → '2×3' → table 블록(행 2·열 3·첫 행 머리글)",
             H + T + "window.prompt=()=>'2×3';E.ed.select({id:bid(1),off:0});document.querySelector('[data-act=table]').click();await new Promise(r=>setTimeout(r,200));const t=tb();"
                     "return t&&t.rows.length===2&&t.cols.length===3&&t.rows.every(r=>r.cells.length===3)&&t.rows[0].head===true || D();"),
        step("표 - 첫 칸에 글 치기 → 그 칸 runs · 표 요소가 다시 만들어지지 않음 · 본문 문단은 그대로 · 실행 취소 기록 1개만 늘어남",
             H + T + "await idle();const t=tb();const c=t.rows[0].cells[0];return window.__tblEl===document.querySelector('#ed table')&&ctext(c)==='칸글'&&tx(S.deck.blocks[1])===window.__b1&&S.undo.length-window.__u<=1 "
                     "|| JSON.stringify({same:window.__tblEl===document.querySelector('#ed table'),cell:ctext(c),b1:[tx(S.deck.blocks[1]),window.__b1],undo:[window.__u,S.undo.length]});",
             pre=T + "window.__tblEl=document.querySelector('#ed table');window.__b1=tx(S.deck.blocks[1]);window.__u=S.undo.length;cells()[0].focus();", cdp=INS("칸") + INS("글"), wait=200),
        step("표 - Tab → 다음 칸으로 초점",
             H + T + "await new Promise(r=>setTimeout(r,120));return document.activeElement===cells()[1] || JSON.stringify({active:document.activeElement&&document.activeElement.className,idx:cells().indexOf(document.activeElement)});",
             pre=T + "cells()[0].focus();", cdp=KEY("Tab", "Tab", 9)),
        step("표 - 칸 안에서 굵게 단추 → 그 칸 runs 의 b",
             H + T + "await idle();const c=tb().rows[0].cells[1];return (c.blocks[0].runs||[]).some(r=>r.b&&r.t==='굵게') || JSON.stringify(c.blocks);",
             pre=T + "cells()[1].focus();", cdp=INS("굵게") + [{"method": "Runtime.evaluate", "params": {"expression": "(()=>{const h=[...document.querySelectorAll('#ed .pg-cell')][1];const sel=getSelection();sel.selectAllChildren(h.querySelector('[data-id]')||h);document.dispatchEvent(new Event('selectionchange'));})()"}, "wait": 120},
                                                              {"method": "Runtime.evaluate", "params": {"expression": "document.querySelector('[data-mark=b]').click()"}, "wait": 150}]),
        step("표 - 칸 안에서 목록 단추 → '표 칸 안에서는 아직' 토스트 · 목록 안 생김",
             H + T + "await new Promise(r=>setTimeout(r,150));const t=document.querySelector('#toast').textContent;return /표 칸 안에서는 아직/.test(t)&&!S.deck.blocks.some(b=>b.list&&b.type==='table') || t;",
             pre=T + "cells()[1].focus();", cdp=[{"method": "Runtime.evaluate", "params": {"expression": "document.querySelector('[data-list=bullet]').click()"}, "wait": 120}]),
        step("표 - 오른쪽 클릭 메뉴: 아래에 행 넣기(행 3) · 오른쪽에 열 넣기(열 4, 모든 행 4칸) · 행 지우기(행 2) · 머리글 행 끄기",
             H + T + menu("아래에 행 넣기") + "const r3=tb().rows.length;" + menu("오른쪽에 열 넣기") + "const c4=tb().cols.length,all4=tb().rows.every(r=>r.cells.length===4);" + menu("행 지우기", "#ed table tr:last-child td") + "const r2=tb().rows.length;"
                     + menu("머리글 행") + "const head=!!tb().rows[0].head;return r3===3&&c4===4&&all4&&r2===2&&!head || JSON.stringify({r3,c4,all4,r2,head});"),
        step("표 - 칸 안 한글 조합 '한' 이 한 번만",
             H + T + "await idle();const c=tb().rows[1].cells[0];const t=ctext(c);return t==='한' || JSON.stringify(c.blocks);",
             pre=T + "document.querySelector('#ed table tr:nth-child(2) .pg-cell').focus();", cdp=[{"method": "Input.imeSetComposition", "params": {"text": x, "selectionStart": len(x), "selectionEnd": len(x)}, "wait": 30} for x in ("ㅎ", "하", "한")] + INS("한"), wait=200),
        step("표 - 표 지우기 → blocks 에서 사라지고 문단이 남음 · 실행 취소로 되돌아옴",
             H + T + menu("표 지우기") + "const gone=!tb(),paras=S.deck.blocks.filter(b=>b.type==='p').length;E.undo();await new Promise(r=>setTimeout(r,150));const back=!!tb();await idle();"
                     "return gone&&paras>=1&&back || JSON.stringify({gone,paras,back});"),
    ]


def export_steps(pid):
    W = ("if(!window.__of){window.__of=window.fetch.bind(window);window.__reqs=[];window.fetch=async(u,o={})=>{const r=await window.__of(u,o);if(String(u).includes('/api/export/')){const c=r.clone();"
         "window.__reqs.push({u:String(u),st:r.status,j:await c.json().catch(()=>null)});}return r;};}")
    return [
        step("내보내기 ▾ - 'Word 문서 (.docx)' → POST /api/export 200 · url .docx · 내려받기 링크",
             W + "window.__reqs.length=0;document.querySelector('#btnExport').click();await until(async()=>document.querySelector('.menu'),2000);[...document.querySelectorAll('.menu button')].find(b=>/docx/.test(b.textContent)).click();"
                 "await until(async()=>window.__reqs.length,15000);const r=window.__reqs[0];return r&&r.st===200&&r.j&&r.j.ok&&/\\.docx(\\?|$)/.test(r.j.url) || JSON.stringify(window.__reqs);"),
        step("내보내기 ▾ - 'PDF (Word 로 변환)' → 200(Word 있음, method word) 또는 501(needPrint)",
             W + "window.__reqs.length=0;document.querySelector('#btnExport').click();await until(async()=>document.querySelector('.menu'),2000);[...document.querySelectorAll('.menu button')].find(b=>/PDF/.test(b.textContent)).click();"
                 "await until(async()=>window.__reqs.length,120000);const r=window.__reqs[0];return r&&((r.st===200&&r.j&&r.j.ok&&/\\.pdf(\\?|$)/.test(r.j.url))||r.st===501) || JSON.stringify(window.__reqs);", timeout=150000),
    ]


IMG = ("const imgs=()=>S.deck.blocks.filter(b=>b.type==='image');"
       "const put=async(name,type,w,h)=>{let blob;if(type.startsWith('image/')){const c=document.createElement('canvas');c.width=w;c.height=h;const g=c.getContext('2d');g.fillStyle='#c8553d';g.fillRect(0,0,w,h);"
       "blob=await new Promise(r=>c.toBlob(r,type));}else blob=new Blob(['글'],{type});const dt=new DataTransfer();dt.items.add(new File([blob],name,{type}));const inp=document.querySelector('#inImage');inp.files=dt.files;"
       "inp.dispatchEvent(new Event('change',{bubbles:true}));};")


def image_steps(pid):
    """그림 - 넣기(png) · 고르기(.sel)·Delete · 오른쪽 클릭 메뉴(크게·왼쪽·설명) · png·jpg·gif 아닌 형식 거절"""
    return [
        step("그림 - 파일 넣기(png 800×400) → image 블록(src · w ≤ 본문 너비) · 서버 파일",
             H + IMG + "const n0=imgs().length;E.ed.select({id:bid(1),off:0});await put('그림.png','image/png',800,400);await until(async()=>imgs().length>n0,8000);await idle();"
                       "const b=imgs()[imgs().length-1];const f=await srv('" + pid + "');const fb=f.blocks.find(x=>x.id===(b&&b.id));"
                       "return b&&b.src&&b.w>0&&b.w<=S.box.cw+0.5&&fb&&fb.src===b.src || JSON.stringify({b,cw:S.box.cw,srv:fb});"),
        step("그림 - 누르면 .sel · Delete 로 지움",
             H + IMG + "const b=imgs()[imgs().length-1];const ie=document.querySelector('#ed > [data-id='+JSON.stringify(b.id)+']');ie.dispatchEvent(new MouseEvent('mousedown',{bubbles:true}));await new Promise(r=>setTimeout(r,80));"
                       "const sel=ie.classList.contains('sel');document.querySelector('#ed').dispatchEvent(new KeyboardEvent('keydown',{key:'Delete',bubbles:true,cancelable:true}));"
                       "document.dispatchEvent(new KeyboardEvent('keydown',{key:'Delete',bubbles:true,cancelable:true}));await new Promise(r=>setTimeout(r,150));"
                       "return sel&&!S.deck.blocks.some(x=>x.id===b.id) || JSON.stringify({sel,still:S.deck.blocks.some(x=>x.id===b.id)});"),
        step("그림 - 오른쪽 클릭 메뉴: 크게(+25%) · 왼쪽 · 설명(캡션)",
             H + IMG + "await put('둘.png','image/png',200,100);await until(async()=>imgs().length,8000);const b=imgs()[imgs().length-1];const w0=b.w;"
                       "const ctx=async(label)=>{const ie=document.querySelector('#ed > [data-id='+JSON.stringify(b.id)+']');ie.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true,clientX:300,clientY:300}));"
                       "await until(async()=>document.querySelector('.menu'),2000);const mb=[...document.querySelectorAll('.menu button')].find(x=>x.textContent.includes(label));if(!mb)return false;mb.click();await new Promise(r=>setTimeout(r,150));return true;};"
                       "window.prompt=()=>'그림 설명 시험';const a=await ctx('크게'),c=await ctx('왼쪽'),d=await ctx('설명');await idle();const x=S.deck.blocks.find(y=>y.id===b.id);"
                       "return a&&c&&d&&x.w>w0&&x.align==='left'&&x.caption==='그림 설명 시험' || JSON.stringify({a,c,d,w0,x});"),
        step("그림 - png·jpg·gif 아닌 형식(svg·글)은 거절 토스트 · 블록이 늘지 않음",
             H + IMG + "await new Promise(r=>setTimeout(r,800));const n0=imgs().length;await put('a.txt','text/plain');await new Promise(r=>setTimeout(r,600));const t1=document.querySelector('#toast').textContent;"
                       "return imgs().length===n0&&t1.length>0 || JSON.stringify({n0,n:imgs().length,toast:t1});"),
    ]


# 서식·링크·찾기 시험 문서 - f1 "첫 문단 글" · f2 "둘째 " + 굵은 "문단" + " 끝" · f3 "셋째 문단" · 표(칸에 "문단")
FMT_DOC = {"id": "pgfmt", "title": "서식 시험", "kind": "page", "slides": [], "blocks": [
    {"id": "f1", "type": "p", "runs": [{"t": "첫 문단 글"}]},
    {"id": "f2", "type": "p", "runs": [{"t": "둘째 "}, {"t": "문단", "b": True}, {"t": " 끝"}]},
    {"id": "f3", "type": "p", "runs": [{"t": "셋째 문단"}]},
    {"id": "ft", "type": "table", "cols": [40, 40], "rows": [{"id": "fr1", "cells": [{"id": "fc1", "blocks": [{"id": "fp1", "type": "p", "runs": [{"t": "칸 문단"}]}]},
                                                                                {"id": "fc2", "blocks": [{"id": "fp2", "type": "p", "runs": [{"t": "칸"}]}]}]}]},
    {"id": "f4", "type": "p", "runs": [{"t": "끝"}]}]}
MRG_DOC = {"id": "pgmrg", "title": "합치기 시험", "kind": "page", "slides": [], "blocks": [
    {"id": "m0", "type": "p", "runs": [{"t": "표"}]},
    {"id": "mt", "type": "table", "cols": [30, 30, 30], "rows": [
        {"id": f"mr{r}", "cells": [{"id": f"mc{r}{c}", "blocks": [{"id": f"mp{r}{c}", "type": "p", "runs": [{"t": f"{r}{c}"}]}]} for c in range(3)]} for r in range(3)]},
    {"id": "m9", "type": "p", "runs": [{"t": "끝"}]}]}
B_ = "const blk=(id)=>S.deck.blocks.find(b=>b.id===id);const chg=(id,v)=>{const e=document.querySelector(id);e.value=v;e.dispatchEvent(new Event('change',{bubbles:true}));};"


def fmt_steps():
    return [
        step("문단 음영 [▨] → block.fill #e6e6e6 · 화면 배경 rgb(230, 230, 230) · 다시 누르면 꺼짐 · 한 번 더 눌러 켜 둠(DOCX 확인용)",
             H + B_ + "const sh=document.querySelector('[data-act=shade]');if(!sh)return 'no shade button';E.ed.select({id:'f3',off:1});sh.click();await new Promise(r=>setTimeout(r,150));"
                      "const on=blk('f3').fill,bg=getComputedStyle(el('f3')).backgroundColor,cls=sh.classList.contains('on');E.ed.select({id:'f3',off:1});sh.click();await new Promise(r=>setTimeout(r,150));"
                      "const off=blk('f3').fill,bg2=getComputedStyle(el('f3')).backgroundColor;E.ed.select({id:'f3',off:1});sh.click();await new Promise(r=>setTimeout(r,150));await idle();"
                      "return on==='#e6e6e6'&&bg==='rgb(230, 230, 230)'&&cls&&!off&&/rgba\\(0, 0, 0, 0\\)|transparent/.test(bg2)&&blk('f3').fill==='#e6e6e6' || JSON.stringify({on,bg,cls,off,bg2,last:blk('f3').fill});"),
        step("줄 간격 2 → block.line 2 · 화면 line-height = 글자 크기의 2배",
             H + B_ + "E.ed.select({id:'f1',off:1});chg('#selLine','2');await new Promise(r=>setTimeout(r,120));const e=el('f1'),cs=getComputedStyle(e);const lh=parseFloat(cs.lineHeight),fs=parseFloat(cs.fontSize);"
                      "return blk('f1').line===2&&Math.abs(lh-2*fs)<1.5 || JSON.stringify({line:blk('f1').line,lh,fs});"),
        step("글꼴 고정폭(mono) → runs font mono · 화면 font-family 가 고정폭",
             H + B_ + "E.ed.select({id:'f1',off:0},{id:'f1',off:2});chg('#selFont','mono');await new Promise(r=>setTimeout(r,120));const r=blk('f1').runs.find(x=>x.font==='mono');"
                      "const sp=[...el('f1').querySelectorAll('span')].find(x=>x.textContent===(r&&r.t));return r&&r.t==='첫 '&&sp&&/consolas|mono/i.test(getComputedStyle(sp).fontFamily) || JSON.stringify({runs:blk('f1').runs,ff:sp&&getComputedStyle(sp).fontFamily});"),
        step("링크 - 고른 글에 https://example.com → runs link · 화면 .nt-link",
             H + B_ + "E.ed.select({id:'f3',off:0},{id:'f3',off:2});window.prompt=()=>'https://example.com';document.querySelector('[data-act=link]').click();await new Promise(r=>setTimeout(r,120));"
                      "const r=blk('f3').runs.find(x=>x.link);return r&&r.link==='https://example.com'&&r.t==='셋째'&&!!el('f3').querySelector('.nt-link') || JSON.stringify(blk('f3').runs);"),
        step("링크 - javascript: 는 거절 토스트 · 빈 값이면 링크 풀림 · 선택이 없으면 '먼저 고르세요'",
             H + B_ + "E.ed.select({id:'f3',off:0},{id:'f3',off:2});window.prompt=()=>'javascript:alert(1)';document.querySelector('[data-act=link]').click();await new Promise(r=>setTimeout(r,120));const t1=document.querySelector('#toast').textContent,still=blk('f3').runs.some(x=>x.link==='https://example.com');"
                      "window.prompt=()=>'';E.ed.select({id:'f3',off:0},{id:'f3',off:2});document.querySelector('[data-act=link]').click();await new Promise(r=>setTimeout(r,120));const gone=!blk('f3').runs.some(x=>x.link);"
                      "E.ed.select({id:'f3',off:1});document.querySelector('[data-act=link]').click();await new Promise(r=>setTimeout(r,120));const t2=document.querySelector('#toast').textContent;"
                      "return /http/.test(t1)&&still&&gone&&/먼저 고르세요/.test(t2) || JSON.stringify({t1,still,gone,t2});"),
        step("찾기 - '문단' 다음 2번 → '2 / n' · 그 자리 선택 / 바꾸기 1건 → 그 자리만 '단락'(굵은 글 안이면 굵게 유지)",
             H + B_ + "document.querySelector('[data-act=find]').click();await until(async()=>getComputedStyle(document.querySelector('#findBar')).display!=='none',2000);const f=document.querySelector('#fdFind');f.value='문단';f.dispatchEvent(new Event('input',{bubbles:true}));"
                      "document.querySelector('#fdNext').click();document.querySelector('#fdNext').click();await new Promise(r=>setTimeout(r,120));const info=document.querySelector('#fdInfo').textContent;const sel=E.ed.selection();"
                      "document.querySelector('#fdRepl').value='단락';document.querySelector('#fdOne').click();await new Promise(r=>setTimeout(r,150));const f2=blk('f2').runs;"
                      "return /^2 \\/ \\d+$/.test(info)&&sel&&sel.f.id==='f2'&&tx(blk('f2'))==='둘째 단락 끝'&&f2.some(x=>x.b&&x.t==='단락')&&tx(blk('f1'))==='첫 문단 글' || JSON.stringify({info,sel,f1:tx(blk('f1')),f2});"),
        step("찾기 - 모두 바꾸기 → 본문+표 칸 수 합계 · 실행 취소 1번에 모두 되돌아감 · Esc 로 닫힘",
             H + B_ + "const f=document.querySelector('#fdFind');f.value='문단';f.dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('#fdRepl').value='段';const u0=S.undo.length;document.querySelector('#fdAll').click();await new Promise(r=>setTimeout(r,150));"
                      "const info=document.querySelector('#fdInfo').textContent;const cell=blk('ft').rows[0].cells[0].blocks[0].runs.map(r=>r.t).join('');const after=[tx(blk('f1')),tx(blk('f3')),cell];E.undo();await new Promise(r=>setTimeout(r,150));"
                      "const back=[tx(blk('f1')),tx(blk('f3')),blk('ft').rows[0].cells[0].blocks[0].runs.map(r=>r.t).join('')];document.querySelector('#fdFind').dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));await new Promise(r=>setTimeout(r,100));"
                      "const closed=getComputedStyle(document.querySelector('#findBar')).display==='none';"
                      "return /^3곳 바꿈$/.test(info)&&after.join('|')==='첫 段 글|셋째 段|칸 段'&&back.join('|')==='첫 문단 글|셋째 문단|칸 문단'&&closed || JSON.stringify({info,after,back,closed,u0,u:S.undo.length});"),
    ]


def ruby_steps():
    return [
        step("윗주 - '글' 에 윗주 'S' → runs ruby · block.line 2 · 화면 data-ruby 와 ::before 내용",
             H + B_ + "chg('#selLine','');E.ed.select({id:'f4',off:0},{id:'f4',off:1});window.prompt=()=>'S';const rb=document.querySelector('[data-act=ruby]');if(!rb)return 'no ruby button';rb.click();await new Promise(r=>setTimeout(r,150));"
                      "const r=blk('f4').runs.find(x=>x.ruby);const sp=el('f4').querySelector('[data-ruby]');const before=sp&&getComputedStyle(sp,'::before').content;"
                      "return r&&r.ruby==='S'&&r.t==='끝'&&blk('f4').line===2&&sp&&sp.dataset.ruby==='S'&&/S/.test(before||'') || JSON.stringify({runs:blk('f4').runs,line:blk('f4').line,ruby:sp&&sp.dataset.ruby,before});"),
        step("윗주 - 있어도 선택 위치·글 길이 그대로(뒤에 친 글의 offset)",
             H + B_ + "await new Promise(r=>setTimeout(r,100));return tx(blk('f4'))==='끝!'&&(E.ed.selection()||{}).f.off===2 || JSON.stringify({t:tx(blk('f4')),sel:E.ed.selection()});",
             pre=B_ + "E.ed.select({id:'f4',off:1});", cdp=INS("!")),
        step("윗주 - 빈 값으로 떼기",
             H + B_ + "E.ed.select({id:'f4',off:0},{id:'f4',off:1});window.prompt=()=>'';document.querySelector('[data-act=ruby]').click();await new Promise(r=>setTimeout(r,150));const gone=!blk('f4').runs.some(x=>x.ruby);"
                      "E.ed.select({id:'f4',off:0},{id:'f4',off:1});window.prompt=()=>'S';document.querySelector('[data-act=ruby]').click();await new Promise(r=>setTimeout(r,150));await idle();"
                      "return gone&&blk('f4').runs.some(x=>x.ruby==='S') || JSON.stringify({gone,runs:blk('f4').runs});"),
    ]


def merge_steps():
    M = ("const t=()=>S.deck.blocks.find(b=>b.id==='mt');const td=(r,c)=>document.querySelector('#ed [data-id=mt] td[data-id=mc'+r+c+'],#ed [data-id=mt] th[data-id=mc'+r+c+']');"
         "const menu=async(r,c,label)=>{const x=td(r,c);if(!x)return 'no cell '+r+c;x.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true,clientX:200,clientY:200}));await until(async()=>document.querySelector('.menu'),2000);"
         "const mb=[...document.querySelectorAll('.menu button')].find(b=>b.textContent.includes(label));if(!mb){document.querySelectorAll('.menu').forEach(m=>m.remove());return 'no item '+label;}const dis=mb.disabled;if(!dis)mb.click();else document.querySelectorAll('.menu').forEach(m=>m.remove());await new Promise(r=>setTimeout(r,150));return dis?'disabled':'ok';};"
         "const ctext=(c)=>c.blocks.map(b=>(b.runs||[]).map(r=>r.t).join('')).join('/');")
    return [
        step("칸 합치기 - (1,1) 오른쪽과 → colspan 2 · 그 행 칸 2개 · 두 칸의 글이 이어짐",
             H + M + "const a=await menu(0,0,'오른쪽 칸과 합치기');const r0=t().rows[0];return a==='ok'&&r0.cells.length===2&&r0.cells[0].colspan===2&&/00.*01/.test(ctext(r0.cells[0])) || JSON.stringify({a,r0});"),
        step("칸 합치기 - 합친 칸에서 '아래 칸과 합치기' 는 아래 칸 너비가 달라 꺼져 있음",
             H + M + "const a=await menu(0,0,'아래 칸과 합치기');return a==='disabled' || a;"),
        step("칸 합치기 - (2,1) 아래와 → rowspan 2 · 아래 행 칸 2개 · 칸 나누기 → 원래 칸 수 · 다시 아래와 합침",
             H + M + "const a=await menu(1,0,'아래 칸과 합치기');const r1=t().rows[1],r2=t().rows[2];const ok1=a==='ok'&&r1.cells[0].rowspan===2&&r2.cells.length===2;"
                     "const b=await menu(1,0,'칸 나누기');const n=[t().rows[1].cells.length,t().rows[2].cells.length];const c=await menu(1,0,'아래 칸과 합치기');"
                     "return ok1&&b==='ok'&&n.join()==='3,3'&&c==='ok'&&t().rows[1].cells[0].rowspan===2 || JSON.stringify({a,ok1,b,n,c,rows:t().rows.map(r=>r.cells.map(x=>[x.id,x.colspan,x.rowspan]))});"),
        step("배치용 표 - 표 메뉴 '테두리 없음' → border none · 표 클래스 pg-noborder · 편집기에서는 칸 경계가 흐린 점선",
             H + M + "const a=await menu(0,0,'테두리 없음');const tb=document.querySelector('#ed [data-id=mt] table')||document.querySelector('#ed table[data-id=mt]');const cs=getComputedStyle(td(0,0));"
                     "return a==='ok'&&t().border==='none'&&tb&&tb.classList.contains('pg-noborder')&&cs.borderTopStyle==='dashed' || JSON.stringify({a,border:t().border,cls:tb&&tb.className,style:cs.borderTopStyle,color:cs.borderTopColor});"),
        step("배치용 표 - 인쇄용 규칙(page-render CSS)으로는 테두리 색이 투명",
             H + M + "const d=document.implementation.createHTMLDocument('x');window.NexaPage.injectCss(d);const tb=d.createElement('table');tb.className='pg-table pg-noborder';tb.innerHTML='<tr><td>a</td><td>b</td></tr>';d.body.appendChild(tb);"
                     "const f=document.createElement('iframe');f.style.cssText='position:fixed;left:-9999px;width:300px;height:100px';document.body.appendChild(f);f.contentDocument.open();f.contentDocument.write('<!doctype html><html><head></head><body></body></html>');f.contentDocument.close();"
                     "window.NexaPage.injectCss(f.contentDocument);f.contentDocument.body.innerHTML=tb.outerHTML;const c=f.contentWindow.getComputedStyle(f.contentDocument.querySelector('td'));const col=c.borderTopColor;f.remove();"
                     "return /rgba\\(0, 0, 0, 0\\)|transparent/.test(col) || col;"),
        step("배치용 표 - '칸 사이 세로선만' → border inner-v · 클래스 pg-innerv · 둘째 칸 왼쪽 선 실선",
             H + M + "const a=await menu(0,0,'칸 사이 세로선만');const tb=document.querySelector('#ed [data-id=mt] table')||document.querySelector('#ed table[data-id=mt]');const c2=[...tb.querySelectorAll('tr')].find(r=>r.children.length>1).children[1];const cs=getComputedStyle(c2);"
                     "return a==='ok'&&t().border==='inner-v'&&tb.classList.contains('pg-innerv')&&cs.borderLeftStyle==='solid' || JSON.stringify({a,border:t().border,cls:tb&&tb.className,left:cs.borderLeftStyle});"),
        step("합친 표 저장 - 서버 파일에 colspan·rowspan",
             H + M + "await idle();const f=await srv('pgmrg');const tt=f.blocks.find(b=>b.id==='mt');return tt.rows[0].cells[0].colspan===2&&tt.rows[1].cells[0].rowspan===2&&tt.border==='inner-v' || JSON.stringify({border:tt.border,rows:tt.rows.map(r=>r.cells.map(x=>[x.colspan,x.rowspan]))});"),
    ]


def study_steps():
    return [
        step("해설지(study-guide) - 2단: 배치용 표 1개 · 칸 2개 · 왼쪽 칸 너비 ≈ 67%(±3)",
             H + "const t=S.deck.blocks.find(b=>b.type==='table'&&b.border);const tb=t&&(document.querySelector('#ed [data-id='+t.id+'] table')||document.querySelector('#ed table[data-id='+t.id+']'));"
                 "const cells=tb?[...tb.querySelector('tr').children]:[];const r=cells.length===2?cells[0].getBoundingClientRect().width/tb.getBoundingClientRect().width:0;"
                 "return !!t&&t.rows.length===1&&t.rows[0].cells.length===2&&cells.length===2&&Math.abs(r-0.67)<=0.03 || JSON.stringify({border:t&&t.border,cells:cells.length,ratio:r});"),
        step("해설지 - 윗주 3개(S·V·접속사) · ::before 내용이 각각 그 글",
             H + "const sp=[...document.querySelectorAll('#ed [data-ruby]')];const b=sp.map(x=>getComputedStyle(x,'::before').content);"
                 "return sp.length===3&&sp.every((x,i)=>b[i].includes(x.dataset.ruby))&&sp.map(x=>x.dataset.ruby).join()==='S,V,접속사' || JSON.stringify({n:sp.length,r:sp.map(x=>x.dataset.ruby),b});"),
        step("해설지 - 머리말에 날짜와 제목 · 자리 글({title}·{date})이 남지 않음",
             H + "const h=document.querySelector('#pgHeader').textContent;const all=JSON.stringify(S.deck);"
                 "return /\\d{4}-\\d{2}-\\d{2}/.test(h)&&h.includes(S.deck.title)&&!/\\{(title|date)\\}/.test(all) || JSON.stringify({h,left:(all.match(/\\{(title|date)\\}/g)||[])});"),
    ]


POLL_DOC = {"id": "pgpoll", "title": "밖의 변경", "kind": "page", "slides": [], "blocks": [
    {"id": "q1", "type": "p", "runs": [{"t": "하나"}]},
    {"id": "q2", "type": "p", "runs": [{"t": "둘"}]},
    {"id": "qt", "type": "table", "cols": [50, 50], "rows": [{"id": "qr1", "cells": [{"id": "qc1", "blocks": [{"id": "qp1", "type": "p", "runs": [{"t": "칸"}]}]},
                                                                               {"id": "qc2", "blocks": [{"id": "qp2", "type": "p", "runs": [{"t": "칸2"}]}]}]}]},
    {"id": "q3", "type": "p", "runs": [{"t": "셋"}]}]}
FLOW_DOC = {"id": "pgflow", "title": "쪽 나눔", "kind": "page", "slides": [], "blocks": [
    {"id": "f0", "type": "p", "runs": [{"t": "머리 문단"}]},
    {"id": "fl", "type": "p", "runs": [{"t": "쪽나눔 " + "가나다라마바사아자차카타파하 " * 260}]},
    {"id": "ft", "type": "table", "cols": [30, 70], "rows": [{"id": f"fr{k}", "cells": [{"id": f"fc{k}a", "blocks": [{"id": f"fp{k}a", "type": "p", "runs": [{"t": f"행{k}"}]}]},
                                                                                     {"id": f"fc{k}b", "blocks": [{"id": f"fp{k}b", "type": "p", "runs": [{"t": "값"}]}]}]} for k in range(40)]},
    {"id": "fz", "type": "p", "runs": [{"t": "끝 문단"}]}]}
# 실제 편집기의 쪽 나눔(PG-102) - 종이 장(.pg-sheet)의 화면 좌표로 본문 범위를 잡는다(확대에도 그대로)
FL = ("const SH=()=>[...document.querySelectorAll('#sheets .pg-sheet')];"
      "const bodies=()=>{const b=S.box;return SH().map(x=>{const r=x.getBoundingClientRect();const k=r.height/b.h;return [r.top+b.t*k,r.bottom-b.b*k];});};"
      "const pageAt=(a,z)=>{z=z===undefined?a:z;return bodies().findIndex(([t,u])=>a>=t-1.5&&z<=u+1.5);};"
      "const audit=()=>{const bad=[],rg=document.createRange();for(const e of document.querySelector('#ed').children){if(e.classList.contains('pg-break'))continue;"
      "if(e.tagName==='TABLE'){for(const tr of e.rows){if(tr.classList.contains('pg-gaprow')||tr.classList.contains('pg-headrep'))continue;const r=tr.getBoundingClientRect();if(r.height&&pageAt(r.top,r.bottom)<0)bad.push(e.dataset.id+'/'+tr.rowIndex+'@'+Math.round(r.top));}continue;}"
      "const w=document.createTreeWalker(e,4);let n;while((n=w.nextNode())){rg.selectNodeContents(n);for(const r of rg.getClientRects())if(r.width>0&&r.height>0&&pageAt(r.top,r.bottom)<0)bad.push(e.dataset.id+'@'+Math.round(r.top));}}return bad;};"
      "const gaps=(id)=>[...document.querySelectorAll((id?'#ed [data-id='+id+'] ':'#ed ')+'.pg-gap')];const gapRows=()=>document.querySelectorAll('#ed tr.pg-gaprow').length;"
      "const pushed=()=>[...document.querySelector('#ed').children].filter(e=>e._pgPush).length;"
      "const cr=(id,off)=>{const w=document.createTreeWalker(el(id),4);let n,l=off;while((n=w.nextNode())){if(l<n.data.length)break;l-=n.data.length;}const r=document.createRange();r.setStart(n,l);r.setEnd(n,l+1);return r.getClientRects()[0];};"
      "const info=()=>document.querySelector('#pageInfo').textContent;const tick=(ms)=>new Promise(r=>setTimeout(r,ms||200));"
      "const FD=()=>JSON.stringify({pages:S.pages,sheets:SH().length,info:info(),gaps:gaps().length,rows:gapRows(),pushed:pushed(),bad:audit().slice(0,6)});"
      "const settle=async()=>{await tick(400);let k=-1,j=0;while(j++<20){const g=gaps().length+gapRows()+pushed()*100+S.pages*10000;if(g===k)break;k=g;await tick(250);}};"
      "const chg=(id,v)=>{const e=document.querySelector(id);e.value=v;e.dispatchEvent(new Event('change',{bubbles:true}));};")


def flow_steps():
    """실시간 쪽 나눔(PG-102 1차 · 56e5c25) - 긴 문단 · 표 40행 · 쪽 번호 · 쪽 설정 · 확대 · 편집 · 실행 취소 · 저장 · 인쇄"""
    PSD = PS + "const setup=async(f)=>{q('[data-act=setup]').click();await until(async()=>q('#psOk'),3000);f();q('#psOk').click();await idle();await settle();};"
    return [
        step("쪽 나눔 ① 긴 문단이 쪽을 넘으면 그 문단에 .pg-gap · 걸친 줄·행 없음 · 쪽 수 = 종이 장 수 = #pageInfo 'n쪽'",
             H + FL + "await until(async()=>gaps('fl').length>0,8000);await settle();window.__p0=S.pages;"
                      "return gaps('fl').length>=1&&audit().length===0&&S.pages>=3&&SH().length===S.pages&&parseInt(info())===S.pages || FD();"),
        step("쪽 나눔 ② .pg-gap 바로 뒤 글자는 다음 종이 본문 안, 바로 앞 글자는 앞 종이",
             H + FL + "const g=gaps('fl')[0];const o=g._off;const a=cr('fl',o-1),b=cr('fl',o+1);const pa=pageAt(a.top,a.bottom),pb=pageAt(b.top,b.bottom);"
                      "return pa>=0&&pb===pa+1 || JSON.stringify({o,pa,pb,a:[a.top,a.bottom],b:[b.top,b.bottom],bodies:bodies().slice(0,4)});"),
        step("쪽 나눔 ⑤ 표 40행 → 쪽 경계에 빈 행(tr.pg-gaprow) · 행이 쪽에 걸치지 않음",
             H + FL + "return document.querySelectorAll('#ed [data-id=ft] tr.pg-gaprow').length>=1&&audit().length===0 || FD();"),
        step("쪽 나눔 ③ 쪽 번호(아래 가운데)를 켜면 .pg-num 이 쪽마다 1, 2, 3 …",
             H + FL + PSD + "await setup(()=>setv('#psNum','footer-center'));const ns=[...document.querySelectorAll('#covers .pg-num')].map(x=>x.textContent);"
                            "return ns.length===S.pages&&ns.every((t,i)=>t===String(i+1)) || JSON.stringify({ns,pages:S.pages});"),
        step("쪽 나눔 ④ 방향을 가로로 → 쪽 수가 다시 잡힘(늘어남) · 종이 장 수 같음 · 걸친 줄 없음",
             H + FL + PSD + "const n0=S.pages;await setup(()=>setv('#psOrient','landscape'));"
                            "if(S.pages>n0&&SH().length===S.pages&&parseInt(info())===S.pages&&audit().length===0)return true;"
                            "const f1=JSON.parse(FD());await tick(2000);const b2=audit();const tr=[...document.querySelectorAll('#ed [data-id=ft] tr')].filter(x=>!x.classList.contains('pg-gaprow')&&!x.classList.contains('pg-headrep'));const r37=tr[37]&&tr[37].getBoundingClientRect();"
                            "window.__d4=JSON.stringify({n0,f:f1,after2s:b2.slice(0,4),row37:r37&&[Math.round(r37.top),Math.round(r37.bottom)],gapRowsAt:[...document.querySelectorAll('#ed tr.pg-gaprow')].map(x=>Math.round(x.getBoundingClientRect().top)),bodies:bodies().map(x=>x.map(Math.round)),box:S.box});return 'bad - 다음 덤프 단계';"),
        step("쪽 나눔 ④ 덤프(실패했을 때만 값 - 판정 아님)", "return window.__d4||'없음';", dump=True),
        step("쪽 나눔 ④ 세로로 되돌리면 처음 쪽 수",
             H + FL + PSD + "await setup(()=>setv('#psOrient','portrait'));return S.pages===window.__p0&&audit().length===0 || JSON.stringify({p0:window.__p0,f:JSON.parse(FD())});"),
        step("쪽 나눔 ④ 위·아래 여백 +40mm → 쪽 수 늘어남 · 걸친 줄 없음 · 되돌리면 처음 쪽 수",
             H + FL + PSD + "const m=JSON.parse(JSON.stringify(S.deck.page.margin));await setup(()=>{setv('#psMt',m.t+40);setv('#psMb',m.b+40);});const n1=S.pages,b1=audit();"
                            "await setup(()=>{setv('#psMt',m.t);setv('#psMb',m.b);});"
                            "return n1>window.__p0&&b1.length===0&&S.pages===window.__p0&&S.deck.page.margin.t===m.t || JSON.stringify({p0:window.__p0,n1,b1:b1.slice(0,4),f:JSON.parse(FD())});"),
        step("쪽 나눔 ⑥ 150% 확대 → 쪽 수 같음 · 걸친 줄·행 없음 · 다시 100%",
             H + FL + "chg('#selZoom','1.5');await settle();const n=S.pages,b=audit(),z=getComputedStyle(document.querySelector('#paper')).zoom;chg('#selZoom','1');await settle();"
                      "try{localStorage.removeItem('nexaPageZoom');}catch(e){}return z==='1.5'&&n===window.__p0&&b.length===0&&S.pages===window.__p0 || JSON.stringify({z,n,p0:window.__p0,b:b.slice(0,6)});"),
        step("쪽 나눔 ⑦ 나뉜 문단의 .pg-gap 바로 뒤에 글 치기 → 모델의 그 자리에 들어감 · 화면 글 = 모델 · 걸친 줄 없음",
             H + FL + "await idle();await settle();const t=tx(S.deck.blocks.find(b=>b.id==='fl'));const o=window.__go;"
                      "return t===window.__b.slice(0,o+2)+'쪽글'+window.__b.slice(o+2)&&el('fl').textContent===t&&audit().length===0&&gaps('fl').length>=1 || JSON.stringify({o,near:t.slice(o-3,o+8),scr:el('fl').textContent===t,f:JSON.parse(FD())});",
             pre=FL + "await settle();window.__b=tx(S.deck.blocks.find(b=>b.id==='fl'));window.__go=gaps('fl')[0]._off;E.ed.focus();E.ed.select({id:'fl',off:window.__go+2});",
             cdp=INS("쪽글"), wait=200),
        step("쪽 나눔 ⑧ 나뉜 문단에서 한글 조합(ㅎ → 하 → 한) → 글이 맞음",
             H + FL + "await idle();await settle();const t=tx(S.deck.blocks.find(b=>b.id==='fl'));const o=window.__go;"
                      "return t===window.__b.slice(0,o+2)+'쪽글한'+window.__b.slice(o+2)&&el('fl').textContent===t&&audit().length===0 || JSON.stringify({near:t.slice(o-3,o+10),f:JSON.parse(FD())});",
             pre=FL + "E.ed.focus();E.ed.select({id:'fl',off:window.__go+4});",
             cdp=[{"method": "Input.imeSetComposition", "params": {"text": x, "selectionStart": len(x), "selectionEnd": len(x)}, "wait": 30} for x in ("ㅎ", "하", "한")] + INS("한"), wait=200),
        step("쪽 나눔 ⑨ 실행 취소로 글을 되돌리면 빈 자리가 다시 잡힘(같은 쪽 수 · 걸친 줄 없음)",
             H + FL + "E.ed.focus();for(let i=0;i<8&&tx(S.deck.blocks.find(b=>b.id==='fl'))!==window.__b;i++){E.undo();await tick(120);}await idle();await settle();"
                      "const t=tx(S.deck.blocks.find(b=>b.id==='fl'));return t===window.__b&&el('fl').textContent===t&&gaps('fl').length>=1&&S.pages===window.__p0&&audit().length===0 || JSON.stringify({same:t===window.__b,f:JSON.parse(FD())});"),
        step("쪽 나눔 ⑩ 저장된 JSON 에 빈 자리 흔적 없음(pg-gap · pg-gaprow · _pgPush · 빈 행) · 표는 40행 그대로",
             H + FL + "await idle();const f=await srv('pgflow');const j=JSON.stringify(f);const t=f.blocks.find(b=>b.id==='ft');"
                      "return !/pg-gap|pg-gaprow|pg-headrep|_pg|marginTop/.test(j)&&t.rows.length===40&&tx(f.blocks.find(b=>b.id==='fl'))===window.__b || JSON.stringify({hit:(j.match(/pg-gap|pg-gaprow|pg-headrep|_pg|marginTop/)||[])[0],rows:t.rows.length});"),
        step("쪽 나눔 ⑪ 인쇄(beforeprint) → 빈 자리 0(.pg-gap · 빈 행 · 밀기) · 인쇄가 끝나면(afterprint) 다시 생김",
             H + FL + "window.dispatchEvent(new Event('beforeprint'));await tick(300);const a=[gaps().length,gapRows(),pushed()];window.dispatchEvent(new Event('afterprint'));await settle();"
                      "return a.every(x=>x===0)&&gaps('fl').length>=1&&S.pages===window.__p0 || JSON.stringify({inPrint:a,f:JSON.parse(FD())});"),
        step("쪽 나눔 ⑫ 화면 쪽 수(Chrome PDF 와 비교용)", H + FL + "await settle();return 'screenPages='+S.pages;", dump=True),
    ]


def flow_print_steps():
    return [step("쪽 나눔 ⑪ ?print=1(서버 Chrome 인쇄 화면) → .pg-gap · 빈 행 · 밀기 모두 0",
                 "await new Promise(r=>setTimeout(r,1500));const ed=document.querySelector('#ed');const g=ed.querySelectorAll('.pg-gap').length,r=ed.querySelectorAll('tr.pg-gaprow').length,u=[...ed.children].filter(e=>e._pgPush).length;"
                 "return document.body.classList.contains('printing')&&ed.children.length>=4&&g===0&&r===0&&u===0 || JSON.stringify({printing:document.body.classList.contains('printing'),n:ed.children.length,g,r,u});")]


OBJ_J = ("const tick=(ms)=>new Promise(r=>setTimeout(r,ms||200));const shape=async(label)=>{document.querySelector('[data-act=shape]').click();await tick(60);"
     "const b=[...document.querySelectorAll('.menu button')].find(x=>x.textContent.includes(label));if(!b)throw new Error('메뉴 없음 '+label);b.click();await tick(200);};"
     "const O=()=>S.deck.objects||[];const oe=(k)=>document.querySelector('.pg-obj[data-id=\"'+O()[k].id+'\"]');"
     "const geo=()=>{const sh=document.querySelector('.pg-sheet').getBoundingClientRect();return {sh,mm:sh.width/S.box.w};};"
     "const ctxm=async(el,label)=>{const r=el.getBoundingClientRect();el.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true,clientX:r.left+3,clientY:r.top+3}));await tick(60);"
     "const b=[...document.querySelectorAll('.menu button')].find(x=>x.textContent.includes(label));if(!b)throw new Error('메뉴 없음 '+label);b.click();await tick(200);};"
     "const drag=async(target,dx,dy)=>{const r=target.getBoundingClientRect(),cx=r.left+r.width/2,cy=r.top+r.height/2;target.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,cancelable:true,button:0,clientX:cx,clientY:cy}));"
     "window.dispatchEvent(new PointerEvent('pointermove',{clientX:cx+dx/2,clientY:cy+dy/2}));window.dispatchEvent(new PointerEvent('pointermove',{clientX:cx+dx,clientY:cy+dy}));window.dispatchEvent(new PointerEvent('pointerup',{}));await tick(250);};")
OBJ_PROBE = [
    ("타원 넣기 - 문서에 개체 1 · 첫 문단에 매임 · 화면 자리 = x·y(mm) · 고른 상태",
     "await tick(400); E.ed.focus(); E.ed.select({id:bid(0),off:0}); await shape('타원'); const o=O()[0], oel=oe(0), g=geo(), r=oel.getBoundingClientRect();"
     "return O().length===1&&o.shape==='ellipse'&&o.anchor===bid(0)&&oel.classList.contains('sel')&&!!oel.querySelector('ellipse')&&Math.abs((r.left-g.sh.left)/g.mm-o.x)<0.6&&Math.abs((r.top-g.sh.top)/g.mm-o.y)<0.6"
     "||JSON.stringify({o,r:[r.left,r.top],sh:[g.sh.left,g.sh.top],mm:g.mm})"),
    ("끌어 옮기기 - x +20mm · y +10mm",
     "const o=O()[0], g=geo(); await drag(oe(0), 20*g.mm, 10*g.mm); const p=O()[0]; return Math.abs(p.x-o.x-20)<0.3&&Math.abs(p.y-o.y-10)<0.3&&oe(0).classList.contains('sel')||JSON.stringify([o,p])"),
    ("크기 손잡이 - w +10mm · h +5mm",
     "const o=O()[0], g=geo(); await drag(oe(0).querySelector('.pg-obj-h'), 10*g.mm, 5*g.mm); const p=O()[0]; return Math.abs(p.w-o.w-10)<0.3&&Math.abs(p.h-o.h-5)<0.3&&Math.abs(p.x-o.x)<0.01||JSON.stringify([o,p])"),
    ("오른쪽 클릭 - 채움 회색 · 긴 점선 · 글 뒤로(#objsBack)",
     "await ctxm(oe(0),'채움 - 회색'); await ctxm(oe(0),'긴 점선'); await ctxm(oe(0),'글 뒤로'); const o=O()[0], oel=oe(0), e=oel.querySelector('ellipse');"
     "return o.fill==='#eeeeee'&&o.line.dash==='dash'&&o.z==='behind'&&oel.parentNode.id==='objsBack'&&e.getAttribute('fill')==='#eeeeee'&&!!e.getAttribute('stroke-dasharray')||JSON.stringify([o,oel.parentNode.id,e.outerHTML])"),
    ("글 상자 넣기 - 안의 글에 초점 · 글 치기 → 개체의 blocks · 초점 유지",
     "E.ed.focus(); E.ed.select({id:bid(0),off:0}); await shape('글 상자'); const b=oe(1).querySelector('.pg-obj-body'); const f0=document.activeElement===b;"
     "b.dispatchEvent(new InputEvent('beforeinput',{inputType:'insertText',data:'상자 글',bubbles:true,cancelable:true})); await tick(200); const o=O()[1];"
     "return f0&&tx(o.blocks[0])==='상자 글'&&oe(1).querySelector('.pg-obj-body').textContent==='상자 글'&&document.activeElement===oe(1).querySelector('.pg-obj-body')||JSON.stringify({f0,o,dom:oe(1).outerHTML.slice(0,300)})"),
    ("화살표·중괄호 넣기 - 선 도형은 높이 0 · 화살촉 · 중괄호 path",
     "E.ed.focus(); E.ed.select({id:bid(0),off:0}); await shape('화살표'); E.ed.focus(); E.ed.select({id:bid(0),off:0}); await shape('중괄호 {'); const a=O()[2], c=O()[3];"
     "return a.shape==='arrow'&&a.h===0&&!!oe(2).querySelector('polygon')&&c.shape==='brace-l'&&!!oe(3).querySelector('path')||JSON.stringify([a,c])"),
    ("저장 - 서버 문서에 개체 4개(형식 검사 통과)",
     "await idle(); const d=await srv(S.id); return d.objects.length===4&&d.objects[1].blocks[0].runs[0].t==='상자 글'&&document.querySelector('#status').textContent==='저장됨'||JSON.stringify([d.objects,document.querySelector('#status').textContent])"),
    ("Delete - 고른 개체를 지운다 · 실행 취소로 돌아온다",
     "const oel=oe(2); oel.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,cancelable:true,button:0,clientX:oel.getBoundingClientRect().left+2,clientY:oel.getBoundingClientRect().top})); window.dispatchEvent(new PointerEvent('pointerup',{})); await tick(100);"
     "document.dispatchEvent(new KeyboardEvent('keydown',{key:'Delete',bubbles:true,cancelable:true})); await tick(200); const n1=O().length; E.undo(); await tick(300); const n2=O().length, drawn=document.querySelectorAll('.pg-obj').length;"
     "return n1===3&&n2===4&&drawn===4||JSON.stringify([n1,n2,drawn])"),
    ("매인 문단이 다음 쪽으로 가면 개체도 따라간다(쪽 기준)",
     "const o=O()[1], y0=oe(1).getBoundingClientRect().top; const big=Array.from({length:60},(_,i)=>({id:'fill'+i,type:'p',runs:[{t:'채움 문단 '+i}]})); S.deck.blocks=[...big,...S.deck.blocks]; E.ed.refresh(); E.flow.run(); await tick(300);"
     "const shs=[...document.querySelectorAll('.pg-sheet')], r=oe(1).getBoundingClientRect(), k=shs.findIndex(s=>{const q=s.getBoundingClientRect();return r.top>=q.top-1&&r.top<=q.bottom;}), g=geo(), q=shs[k].getBoundingClientRect();"
     "return shs.length>=2&&k>=1&&Math.abs((r.top-q.top)/g.mm-o.y)<0.6||JSON.stringify({sheets:shs.length,k,y:o.y})"),
]
OBJ_DOC = {"id": "pgobj", "title": "개체 시험", "kind": "page", "slides": [], "blocks": [
    {"id": f"ob{k:02d}", "type": "p", "runs": [{"t": f"개체 문단 {k} - " + "가나다라마바사아자차카타파하 " * 3}]} for k in range(70)]}
# 개체(PG-103 1차 · 3cb9020) - 앞 9단계는 개발 세션 탐침(objs_probe.py)을 그대로 옮긴 것, 뒤는 협업 세션이 더한 것
OBJ_X = ("const shs=()=>[...document.querySelectorAll('#sheets .pg-sheet')];const sheetOf=(y)=>shs().findIndex(s=>{const q=s.getBoundingClientRect();return y>=q.top-1&&y<=q.bottom+1;});"
         "const ob=()=>O().find(o=>o.shape==='brace-l');const be=()=>[...document.querySelectorAll('.pg-obj')].find(e=>e.dataset.id===ob().id);"
         "const rects=()=>{const P=document.querySelector('#paper').getBoundingClientRect();const m={};document.querySelectorAll('.pg-obj').forEach(e=>{const r=e.getBoundingClientRect();m[e.dataset.id]=[r.left-P.left,r.top-P.top,r.width,r.height].map(Math.round);});return m;};"
         "const ext=async(id,f)=>{const r=await fetch('/api/deck/'+id,{cache:'no-store'});const v=r.headers.get('X-Deck-Version');const d=await r.json();f(d);"
         "const p=await fetch('/api/deck/'+id+'?base='+v+'&merge=1',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});return p.status;};")


def obj_steps():
    J = H + OBJ_J + OBJ_X
    out = [step(n, J + js) for n, js in OBJ_PROBE if not n.startswith("매인 문단이 다음 쪽")]
    out += [
        step("개체 ⑩ 다른 쪽으로 끌면(한 쪽 높이만큼 아래) 그 쪽의 문단에 다시 매임 · 쪽 안 높이(y) 그대로",
             J + "const o=ob(),a0=o.anchor,k0=sheetOf(be().getBoundingClientRect().top);const st=shs()[1].getBoundingClientRect().top-shs()[0].getBoundingClientRect().top;await drag(be(),0,st);await tick(300);"
                 "const p=ob(),k1=sheetOf(be().getBoundingClientRect().top),ae=el(p.anchor),ka=ae?sheetOf(ae.getBoundingClientRect().top):-9;"
                 "return k1===k0+1&&p.anchor!==a0&&ka===k1&&p.rel==='page'&&Math.abs(p.y-o.y)<0.6 || JSON.stringify({k0,k1,ka,a0,p});"),
        step("개체 ⑪ 매인 문단을 Backspace 로 앞 문단에 합치면(문단이 없어짐) 남은 문단에 다시 매임",
             J + "await tick(300);const p=ob();const ids=S.deck.blocks.map(b=>b.id);return !ids.includes(window.__ba)&&ids.includes(p.anchor)&&p.anchor!==window.__ba || JSON.stringify({gone:window.__ba,anchor:p.anchor,still:ids.includes(window.__ba)});",
             pre=OBJ_J + OBJ_X + "window.__ba=ob().anchor;E.ed.focus();E.ed.select({id:window.__ba,off:0});", cdp=KEY("Backspace", "Backspace", 8), wait=150),
        step("개체 ⑫ '문단을 따라 움직임(문단 기준)' 으로 바꾸면 rel para · 화면 자리 그대로(±1px)",
             J + "const r0=be().getBoundingClientRect();await ctxm(be(),'문단을 따라 움직임');await tick(300);const p=ob(),r1=be().getBoundingClientRect();"
                 "return p.rel==='para'&&Math.abs(r1.left-r0.left)<1&&Math.abs(r1.top-r0.top)<1 || JSON.stringify({p,r0:[r0.left,r0.top],r1:[r1.left,r1.top]});"),
        step("개체 ⑬ 저장 뒤 화면 자리를 기억(새로 고침 비교용) - 그려진 개체 수 = 문서 개체 수",
             J + "await idle();const m=rects();try{localStorage.setItem('nxObjRects',JSON.stringify(m));}catch(e){}return Object.keys(m).length===O().length&&O().length===4 || JSON.stringify({m,n:O().length});"),
        step("개체 ⑭ 인쇄 매체에서는 #objs · #objsBack 숨김(지금은 의도 - 인쇄를 화면 쪽 나눔과 같게 하는 일이 다음)",
             J + "const a=getComputedStyle(document.querySelector('#objs')).display,b=getComputedStyle(document.querySelector('#objsBack')).display;return a==='none'&&b==='none' || JSON.stringify({a,b});",
             cdp=[{"method": "Emulation.setEmulatedMedia", "params": {"media": "print"}, "wait": 200}]),
        step("개체 ⑭ 화면 매체로 돌리면 다시 보임",
             J + "return getComputedStyle(document.querySelector('#objs')).display!=='none' || 'still hidden';",
             cdp=[{"method": "Emulation.setEmulatedMedia", "params": {"media": ""}, "wait": 200}]),
    ]
    return out


def obj_reload_steps():
    J = H + OBJ_J + OBJ_X
    probe_follow = [step(n, H + OBJ_J + js) for n, js in OBJ_PROBE if n.startswith("매인 문단이 다음 쪽")]  # 탐침 단계는 shs 를 스스로 선언한다
    return [
        step("개체 ⑮ 새로 고침 뒤 그대로 그려짐 - 개수·자리(#paper 기준 ±2px)·글 상자 글",
             J + "await tick(800);let m={};try{m=JSON.parse(localStorage.getItem('nxObjRects')||'{}');localStorage.removeItem('nxObjRects');}catch(e){}const n=rects();const bad=Object.keys(m).filter(k=>!n[k]||n[k].some((v,i)=>Math.abs(v-m[k][i])>2));"
                 "const tb=O().find(o=>Array.isArray(o.blocks)&&o.blocks.length&&tx(o.blocks[0])==='상자 글');"
                 "return Object.keys(m).length===4&&Object.keys(n).length===4&&!bad.length&&!!tb || JSON.stringify({before:m,after:n,bad});"),
        step("개체 ⑯ 두 창 병합 - 이 창은 문단 끝에 글을 치고, 다른 창(밖의 저장)은 타원을 옮김 → 둘 다 남음(화면·서버)",
             J + "const st=await ext(S.id,(d)=>{const o=d.objects.find(x=>x.shape==='ellipse');window.__oid=o.id;window.__ox=Math.round((o.x+15)*10)/10;o.x=window.__ox;});"
                 "const ok=await until(async()=>{const o=S.deck.objects.find(x=>x.id===window.__oid);return o&&Math.abs(o.x-window.__ox)<0.05;},8000);await idle();"
                 "const f=await srv(S.id);const fo=f.objects.find(x=>x.id===window.__oid);const mine=tx(S.deck.blocks.find(x=>x.id===window.__mb)),fm=tx(f.blocks.find(x=>x.id===window.__mb));"
                 "return st===200&&ok&&mine.endsWith('병합글')&&fm.endsWith('병합글')&&Math.abs(fo.x-window.__ox)<0.05&&f.objects.length===4 || JSON.stringify({st,ok,mine:mine.slice(-8),fm:fm.slice(-8),fx:fo&&fo.x,want:window.__ox,n:f.objects.length});",
             pre="const b=S.deck.blocks.find(x=>x.type==='p'&&tx(x).length);window.__mb=b.id;E.ed.focus();E.ed.select({id:b.id,off:tx(b).length});", cdp=INS("병합글"), wait=100),
    ] + probe_follow


# AI 요청 패널(PG-081) - 개발 세션 탐침(req_probe.py) 도우미·단계 그대로
REQ_J = "const tick=(ms)=>new Promise(r=>setTimeout(r,ms||200));const q=(s)=>document.querySelector(s);const reqs=async()=>(await (await fetch('/api/requests/'+S.id,{cache:'no-store'})).json());"
REQ_PROBE = [
    ("처음에는 접혀 있다 · [AI 요청] 으로 연다 · 세션 칩이 있다",
     "await tick(600); const off=document.body.classList.contains('noside')&&getComputedStyle(q('#side')).display==='none'; q('#sideBtn').click(); await tick(150);"
     "return off&&!document.body.classList.contains('noside')&&q('#side').offsetWidth>300&&!!q('#sessChip')&&document.activeElement===q('#reqText')||JSON.stringify([off,q('#side').offsetWidth,q('#sessChip')&&q('#sessChip').textContent])"),
    ("대상 - 본문에서 고른 문단들(요청 칸으로 가도 남는다) · 문서 전체 체크",
     "S.deck.blocks=[{id:'a1',type:'p',runs:[{t:'첫째 문단입니다'}]},{id:'a2',type:'p',runs:[{t:'둘째 문단'}]},{id:'a3',type:'p',runs:[{t:'셋째'}]}]; E.ed.refresh(); S.dirty=true; E.ed.focus(); E.ed.select({id:'a1',off:1},{id:'a2',off:2}); await tick(150);"
     "const t1=q('#reqTarget').textContent; q('#reqText').focus(); await tick(100); const t2=q('#reqTarget').textContent, marked=[...document.querySelectorAll('#ed > .req-on')].map(e=>e.dataset.id).join();"
     "q('#reqWhole').click(); await tick(50); const t3=q('#reqTarget').textContent; q('#reqWhole').click(); await tick(50);"
     "return /첫째 문단입니다.*블록 2개/.test(t1)&&t2===t1&&marked==='a1,a2'&&t3==='문서 전체'||JSON.stringify([t1,t2,marked,t3])"),
    ("보내기 - 먼저 저장하고 요청이 생긴다(element = 첫 블록 · elements = 블록 목록) · 목록에 카드",
     "q('#reqText').value='두 문단을 한 문단으로 합쳐 주세요'; q('#reqSend').click(); await until(async()=>(await reqs()).length===1,8000); const r=(await reqs())[0]; await tick(300); const d=await srv(S.id);"
     "return r.status==='open'&&r.slide==='a1'&&r.element==='a1'&&JSON.stringify(r.elements)==='[\"a1\",\"a2\"]'&&/합쳐/.test(r.text)&&d.blocks.length===3&&d.blocks[0].id==='a1'&&!!q('#reqList .req')&&q('#reqText').value===''&&/1/.test(q('#sideBtn').textContent)"
     "||JSON.stringify({r,blocks:d.blocks.map(b=>b.id),card:!!q('#reqList .req'),btn:q('#sideBtn').textContent})"),
    ("문서 전체 요청 - 범위 없이",
     "q('#reqWhole').click(); q('#reqText').value='전체 맞춤법 검사'; q('#reqSend').click(); await until(async()=>(await reqs()).length===2,8000); const r=(await reqs()).find(x=>/맞춤법/.test(x.text)); q('#reqWhole').click();"
     "return !r.slide&&!r.element&&!r.elements||JSON.stringify(r)"),
    ("세션이 done + reply 로 바꾸면(파일) 카드에 답이 보인다 · 카드를 누르면 그 문단으로",
     "const list=await reqs(); const r=list.find(x=>x.element==='a1'); await fetch('/api/requests/'+S.id,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'update',id:r.id,status:'done',reply:'합쳤습니다'})});"
     "await until(async()=>/합쳤습니다/.test(q('#reqList').textContent),9000); E.ed.select({id:'a3',off:0}); const card=q('#reqList .req[data-rid=\"'+r.id+'\"]'); card.click(); await tick(300); const s=E.ed.selection();"
     "return !!s&&((s.a.id==='a1'&&s.f.id==='a2')||(s.a.id==='a2'&&s.f.id==='a1'))||JSON.stringify({s,txt:q('#reqList').textContent.slice(0,200)})"),
    ("닫으면 기억한다 · 폭 맞춤이 패널 너비를 뺀 자리에 맞는다",
     "q('#selZoom').value='fit'; q('#selZoom').dispatchEvent(new Event('change')); await tick(200); const w1=q('#paper').getBoundingClientRect().width; q('#sideBtn').click(); await tick(250); const w2=q('#paper').getBoundingClientRect().width;"
     "const mem=localStorage.getItem('nexaPageSide'); q('#selZoom').value='1'; q('#selZoom').dispatchEvent(new Event('change')); localStorage.removeItem('nexaPageZoom'); localStorage.removeItem('nexaPageSide');"
     "return document.body.classList.contains('noside')&&mem==='0'&&w2>w1+100||JSON.stringify([w1,w2,mem])"),
]


def req_steps():
    """AI 요청 패널(PG-081 · 2e5457d) - 앞의 6단계는 개발 세션 탐침(req_probe.py) 그대로, 사이사이 협업 세션이 더한 것"""
    J = H + REQ_J
    P = [step(n, J + js) for n, js in REQ_PROBE]
    R1 = step("요청 ⑦ 세션이 연결되지 않은 작업 공간 - 패널 안내에 '세션 연결 없음' · 세션 칩이 보임",
              J + "const h=(q('#reqHint')||{}).textContent||'';return /세션 연결 없음/.test(h)&&!!q('#sessChip')&&q('#sessChip').offsetWidth>0 || JSON.stringify({h,chip:q('#sessChip')&&q('#sessChip').textContent});")
    R2 = step("요청 ⑧ 후속 요청 - 카드의 [후속 요청] → 입력칸에 적어 보내기 → parent = 그 요청 · 목록에 '후속' 표시",
              J + "const r=(await reqs()).find(x=>x.element==='a1');const card=[...document.querySelectorAll('#reqList .req')].find(c=>c.dataset.rid===r.id);const b=card&&card.querySelector('[data-fu]');if(!b)return 'no fu button';b.click();"
                  "await until(async()=>q('#fuText'),3000);q('#fuText').value='한 문장 더 줄여 주세요';q('[data-fusend]').click();await until(async()=>(await reqs()).some(x=>x.parent===r.id),8000);"
                  "const f=(await reqs()).find(x=>x.parent===r.id);await tick(300);return !!f&&/줄여/.test(f.text)&&f.status==='open'&&!!q('#reqList .fu-tag') || JSON.stringify({f,tag:!!q('#reqList .fu-tag')});")
    R3 = step("요청 ⑨ 표 칸 안에 커서 → 대상 = 그 표('표') · 요청 칸으로 가면 표에 .req-on",
              J + "const t={id:'at',type:'table',cols:[50,50],rows:[{id:'ar',cells:[{id:'ac1',blocks:[{id:'ap1',type:'p',runs:[{t:'칸 글'}]}]},{id:'ac2',blocks:[{id:'ap2',type:'p',runs:[{t:'칸 둘'}]}]}]}]};"
                  "S.deck.blocks=[...S.deck.blocks,t];E.ed.refresh();S.dirty=true;await tick(200);const c=document.querySelector('#ed [data-id=at] .pg-cell');c.focus();const sel=getSelection();sel.selectAllChildren(c);sel.collapseToEnd();"
                  "document.dispatchEvent(new Event('selectionchange'));await tick(150);q('#reqText').focus();await tick(120);const tg=q('#reqTarget').textContent,on=[...document.querySelectorAll('#ed > .req-on')].map(e=>e.dataset.id).join();"
                  "return tg==='표'&&on==='at' || JSON.stringify({tg,on});")
    R5 = step("요청 ⑩ 패널을 편 채 폭 맞춤 → 종이 = #scroll 안쪽 - 32px(±2%) · 150% → 100% 의 1.5배(±2%)",
              J + "const chg=(v)=>{q('#selZoom').value=v;q('#selZoom').dispatchEvent(new Event('change',{bubbles:true}));};const pw=()=>q('#paper').getBoundingClientRect().width;"
                  "const open=!document.body.classList.contains('noside');chg('fit');await tick(300);const want=q('#scroll').clientWidth-32,wf=pw();chg('1');await tick(250);const w1=pw();chg('1.5');await tick(250);const w2=pw();chg('1');await tick(200);"
                  "try{localStorage.removeItem('nexaPageZoom');}catch(e){}return open&&Math.abs(wf/want-1)<=0.02&&Math.abs(w2/w1-1.5)<=0.03 || JSON.stringify({open,wf,want,w1,w2});")
    R6 = step("요청 ⑫ 떠나기 전 저장 끝(표를 넣은 변경이 서버에 - 다음 화면이 같은 문서)", H + "await E.save();await idle();const f=await srv(S.id);return !S.dirty&&f.blocks.some(b=>b.id==='at') || JSON.stringify({dirty:S.dirty,ids:f.blocks.map(b=>b.id)});")
    return [P[0], R1, P[1], P[2], P[3], R2, P[4], R3, R5, P[5], R6]


def req_reload_steps():
    J = H + REQ_J
    return [step("요청 ⑪ 새로 고침 뒤 요청 목록 유지 - 패널을 열면 카드(답 '합쳤습니다' · 후속 · 문서 전체 요청)",
                 J + "await tick(800);q('#sideBtn').click();await until(async()=>/합쳤습니다/.test(q('#reqList').textContent),6000);const t=q('#reqList').textContent;const n=(await reqs()).length;"
                     "q('#sideBtn').click();await tick(150);try{localStorage.removeItem('nexaPageSide');}catch(e){}"
                     "return /합쳤습니다/.test(t)&&/맞춤법/.test(t)&&/줄여/.test(t)&&n===3 || JSON.stringify({n,t:t.slice(0,300)});"),
            step("요청 ⑪ 새로 고침 뒤 손대지 않았으면 저장할 것 없음(떠날 때 '저장 안 된 변경' 확인창이 뜨지 않음)",
                 J + "await tick(300);const d0=S.dirty;await tick(1500);const ver=await (await fetch('/api/deck/'+S.id,{cache:'no-store'})).json();"
                     "return !S.dirty&&!d0 || JSON.stringify({d0,dirty:S.dirty,saving:S.saving,status:document.querySelector('#status').textContent,blocks:S.deck.blocks.map(b=>b.id),srv:ver.blocks.map(b=>b.id)});", dump=False)]


POLL_DEL = {"id": "pgpdel", "title": "지울 문서", "kind": "page", "slides": [], "blocks": [{"id": "d1", "type": "p", "runs": [{"t": "곧 지움"}]}]}


def poll_steps():
    """밖의 변경 따라가기(page.js poll - 3초마다 /api/version) - 다른 창·AI 저장"""
    X = ("const ext=async(id,f)=>{const r=await fetch('/api/deck/'+id,{cache:'no-store'});const v=r.headers.get('X-Deck-Version');const d=await r.json();f(d);"
         "const p=await fetch('/api/deck/'+id+'?base='+v+'&merge=1',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});return p.status;};"
         "const setT=(d,id,t)=>{const b=d.blocks.find(x=>x.id===id);b.runs=[{t}];};const toastT=()=>(document.querySelector('#toast')||{}).textContent||'';")
    return [
        step("밖의 변경 ① 깨끗한 화면 - 밖에서 q2 를 고쳐 저장 → 4초 안에 화면에 그 글 · 토스트 '밖에서 바뀐 내용을 불러왔습니다' · 선택(q1) 유지",
             H + X + "await idle();E.ed.focus();E.ed.select({id:'q1',off:1});const st=await ext('pgpoll',(d)=>setT(d,'q2','밖 고침'));let seen='';"
                     "const ok=await until(async()=>{const t=toastT();if(/밖에서 바뀐/.test(t))seen=t;return el('q2')&&el('q2').textContent==='밖 고침';},5000);await new Promise(r=>setTimeout(r,100));if(!seen)seen=toastT();"
                     "const sel=E.ed.selection();return st===200&&ok&&/밖에서 바뀐 내용을 불러왔습니다/.test(seen)&&sel&&sel.f.id==='q1' || JSON.stringify({st,ok,q2:el('q2')&&el('q2').textContent,toast:seen,sel:sel&&sel.f});"),
        step("밖의 변경 ② 고치는 중(저장 전) - 밖에서 q3 을 고친 뒤 poll → 저장하며 병합 · 내 q1 글과 밖의 q3 글이 둘 다 서버·화면에",
             H + X + "await E.poll();await idle();const f=await srv('pgpoll');const t=(id)=>tx(f.blocks.find(b=>b.id===id));"
                     "return window.__extSt===200&&t('q1').includes('내글')&&t('q3')==='밖 셋'&&el('q3').textContent==='밖 셋'&&tx(S.deck.blocks.find(b=>b.id==='q1')).includes('내글') || JSON.stringify({st:window.__extSt,q1:t('q1'),q3:t('q3'),scr:el('q3')&&el('q3').textContent,status:document.querySelector('#status').textContent});",
             pre=X + "await idle();E.ed.focus();E.ed.select({id:'q1',off:2});window.__extSt=await ext('pgpoll',(d)=>setT(d,'q3','밖 셋'));", cdp=INS("내글"), wait=50),
        step("밖의 변경 ④ 표 칸을 편집 중(초점만) - 밖에서 q2 를 고침 → 다시 그려져도 오류 없음 · 칸 글 그대로 · 초점이 그 칸(.pg-cell)으로 돌아옴",
             H + X + "await idle();const c=[...document.querySelectorAll('#ed .pg-cell')][0];c.focus();const st=await ext('pgpoll',(d)=>setT(d,'q2','밖 둘째'));window.__errs=[];window.addEventListener('error',(e)=>window.__errs.push(String(e.message)));"
                     "const ok=await until(async()=>el('q2')&&el('q2').textContent==='밖 둘째',5000);await new Promise(r=>setTimeout(r,200));const a=document.activeElement;const inCell=!!(a&&a.closest&&a.closest('.pg-cell'));"
                     "window.__pollNote='표 칸 편집 중 밖 변경: 초점 '+(inCell?'칸에 남음':'잃음('+(a&&a.tagName)+')');const cellTxt=(document.querySelector('#ed .pg-cell')||{}).textContent;"
                     "return st===200&&ok&&!window.__errs.length&&cellTxt==='칸'&&inCell&&a.classList.contains('pg-cell') || JSON.stringify({st,ok,errs:window.__errs,cellTxt,inCell,active:a&&a.className});"),
        step("밖의 변경 ④ 이어 친 글이 그 칸(첫 칸)에 들어감",
             H + "await new Promise(r=>setTimeout(r,150));await idle();const c=document.querySelector('#ed .pg-cell');const t=S.deck.blocks.find(b=>b.id==='qt');const ct=(t.rows[0].cells[0].blocks||[]).map(tx).join('');"
                 "return c.textContent==='칸이어'&&ct==='칸이어' || JSON.stringify({scr:c.textContent,doc:ct,q1:tx(S.deck.blocks.find(b=>b.id==='q1'))});", cdp=INS("이어"), wait=100),
        step("밖의 변경 ⑥ 실행 취소 - 내 글을 치고 저장 → 밖에서 q2 고침이 반영된 뒤 실행 취소 단추가 켜져 있음 · 실행 취소(E.undo) → 내 글만 사라지고 밖의 글은 남음(서버도)",
             H + X + "await idle();const st=await ext('pgpoll',(d)=>setT(d,'q2','밖 여섯'));const ok=await until(async()=>el('q2')&&el('q2').textContent==='밖 여섯',5000);"
                     "const ub=document.querySelector('[data-act=undo]');const en=ub&&!ub.disabled;const before=tx(S.deck.blocks.find(b=>b.id==='q3'));E.ed.focus();E.undo();await new Promise(r=>setTimeout(r,150));await idle();"
                     "const f=await srv('pgpoll');const t=(d,id)=>tx(d.blocks.find(b=>b.id===id));"
                     "return st===200&&ok&&en&&before.includes('끝말')&&!t(S.deck,'q3').includes('끝말')&&t(S.deck,'q2')==='밖 여섯'&&!t(f,'q3').includes('끝말')&&t(f,'q2')==='밖 여섯' || JSON.stringify({st,ok,en,before,q3:t(S.deck,'q3'),q2:t(S.deck,'q2'),srv:[t(f,'q2'),t(f,'q3')]});",
             pre="await idle();E.ed.focus();const b=S.deck.blocks.find(x=>x.id==='q3');E.ed.select({id:'q3',off:tx(b).length});", cdp=INS("끝말"), wait=100),
    ]


def poll_del_steps():
    return [
        step("밖의 변경 ③ 문서를 API 로 지움 → 상태 칩 '지워진 문서' · 그 뒤 6.5초 동안 이 문서로 나가는 요청 0(폴링 멈춤)",
             H + "await idle();let n=0,after=false;const of=window.fetch;window.fetch=function(u,o){if(after&&/pgpdel|\\/api\\/version/.test(String(u)))n++;return of.apply(this,arguments);};"
                 "const r=await of('/api/decks',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'delete',id:'pgpdel'})});"
                 "const ok=await until(async()=>document.querySelector('#status').textContent==='지워진 문서',6000);after=true;await new Promise(r=>setTimeout(r,6500));window.fetch=of;"
                 "return r.status===200&&ok&&n===0 || JSON.stringify({del:r.status,ok,status:document.querySelector('#status').textContent,after:n});"),
    ]


ZOOM = ("const chg=(id,v)=>{const e=document.querySelector(id);e.value=v;e.dispatchEvent(new Event('change',{bubbles:true}));};const pw=()=>document.querySelector('#paper').getBoundingClientRect().width;"
        "const lines=()=>(document.querySelectorAll('#sheets .pg-sheet').length-1);const info=()=>document.querySelector('#pageInfo').textContent;const pages=()=>parseInt(info());const tick=(ms)=>new Promise(r=>setTimeout(r,ms||200));")


def zoom_steps():
    """확대·축소(d17e657) - 긴 문서(pglong)"""
    return [
        step("확대 ① 150% → 종이 너비 = 100% 의 1.5배(±2%) · 쪽 경계선 수와 'n쪽' 은 100% 때와 같음",
             H + ZOOM + "chg('#selZoom','1');await tick();const w1=pw(),l1=lines(),k1=pages();chg('#selZoom','1.5');await tick();const w2=pw(),l2=lines(),k2=pages();"
                        "return Math.abs(w2/w1-1.5)<=0.03&&l1===l2&&k1===k2&&k1>=2&&getComputedStyle(document.querySelector('#paper')).zoom==='1.5' || JSON.stringify({w1,w2,r:w2/w1,l1,l2,k1,k2});"),
        step("확대 ③ 150% 에서 글자 화면 좌표로 찾은 자리(caretRangeFromPoint = 클릭이 쓰는 것)가 그 글자",
             H + ZOOM + "const w=document.createTreeWalker(document.querySelector('#ed'),NodeFilter.SHOW_TEXT,{acceptNode:(t)=>t.textContent.length>3?NodeFilter.FILTER_ACCEPT:NodeFilter.FILTER_SKIP});const n=w.nextNode();if(!n)return 'no text node';const r=document.createRange();r.setStart(n,2);r.setEnd(n,3);"
                        "const q=r.getBoundingClientRect();const c=document.caretRangeFromPoint(q.left+q.width*0.25,q.top+q.height/2);return c&&c.startContainer===n&&c.startOffset===2 || JSON.stringify({rect:[q.left,q.top,q.width,q.height],got:c&&[c.startContainer.textContent.slice(0,8),c.startOffset]});"),
        step("확대 ④ #pageInfo 글자 수 = 본문 문단 글 길이의 합(표 칸 제외)",
             H + ZOOM + "const n=S.deck.blocks.filter(b=>Array.isArray(b.runs)).reduce((a,b)=>a+[...tx(b)].length,0);const m=info().match(/([\\d,]+)자/);const got=m?Number(m[1].replace(/,/g,'')):-1;"
                        "return got===n&&n>0 || JSON.stringify({info:info(),want:n,got});"),
    ]


def zoom_reload_steps():
    return [
        step("확대 ① 새로 고침 뒤 150% 유지(#selZoom · 종이 zoom)",
             H + ZOOM + "return document.querySelector('#selZoom').value==='1.5'&&getComputedStyle(document.querySelector('#paper')).zoom==='1.5' || JSON.stringify({sel:document.querySelector('#selZoom').value,z:getComputedStyle(document.querySelector('#paper')).zoom});"),
        step("확대 ② 폭 맞춤 → 종이 너비 ≈ #scroll 안쪽 너비 - 32px(±2%)",
             H + ZOOM + "chg('#selZoom','fit');await tick(300);const want=document.querySelector('#scroll').clientWidth-32,w=pw();window.__fit1=w;return Math.abs(w/want-1)<=0.02 || JSON.stringify({w,want});"),
        step("확대 ② 창 너비를 900px 로 바꾸면 폭 맞춤이 따라감",
             H + ZOOM + "await tick(400);const want=document.querySelector('#scroll').clientWidth-32,w=pw();return Math.abs(w/want-1)<=0.02&&Math.abs(w-window.__fit1)>20 || JSON.stringify({w,want,before:window.__fit1,inner:innerWidth});",
             cdp=[{"method": "Emulation.setDeviceMetricsOverride", "params": {"width": 900, "height": 900, "deviceScaleFactor": 1, "mobile": False}, "wait": 300}]),
        step("확대 ⑤ 인쇄 매체(@media print)에서는 zoom 1 - 150% 상태에서도 종이 크기가 확대와 무관",
             H + ZOOM + "const z=getComputedStyle(document.querySelector('#paper')).zoom;window.__pz=z;return z==='1' || JSON.stringify({printZoom:z,sel:document.querySelector('#selZoom').value});",
             pre=ZOOM + "chg('#selZoom','1.5');await tick();",
             cdp=[{"method": "Emulation.clearDeviceMetricsOverride", "params": {}, "wait": 100}, {"method": "Emulation.setEmulatedMedia", "params": {"media": "print"}, "wait": 200}]),
        step("확대 ⑤ 화면 매체로 돌리면 다시 1.5",
             H + "const z=getComputedStyle(document.querySelector('#paper')).zoom;return z==='1.5' || z;",
             cdp=[{"method": "Emulation.setEmulatedMedia", "params": {"media": ""}, "wait": 200}]),
    ]


def zoom_edit_steps():
    """확대 ③ - 150% 에서 글 치기 · 글자 위치로 찾기(누른 자리 = 그 글자) · 표 칸 편집 · 칸 메뉴 자리"""
    M = ("const td=(r,c)=>document.querySelector('#ed [data-id=mt] td[data-id=mc'+r+c+'],#ed [data-id=mt] th[data-id=mc'+r+c+']');")
    return [
        step("확대 ③ 150% 에서 본문 끝에 글 치기 → 그 문단 끝에 들어가고 저장됨",
             H + ZOOM + "await idle();const b=S.deck.blocks.find(x=>Array.isArray(x.runs)&&tx(x).length);return tx(b).endsWith('줌글') || JSON.stringify({t:tx(b)});",
             pre=ZOOM + "chg('#selZoom','1.5');await tick();E.ed.focus();const b=S.deck.blocks.find(x=>Array.isArray(x.runs)&&tx(x).length);E.ed.select({id:b.id,off:tx(b).length});",
             cdp=INS("줌글"), wait=200),
        step("확대 ③ 150% 에서 칸 오른쪽 클릭 → 메뉴가 누른 자리 근처(가로: 왼쪽/오른쪽 모서리 ±40px · 세로: 누른 높이가 메뉴 안 - 화면 아래가 모자라면 위로 밀림)",
             H + ZOOM + M + "const x=td(1,1)||document.querySelector('#ed [data-id=mt] td');const q=x.getBoundingClientRect();const cx=q.left+q.width/2,cy=q.top+q.height/2;x.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true,clientX:cx,clientY:cy}));"
                             "await until(async()=>document.querySelector('.menu'),2000);const m=document.querySelector('.menu');const mr=m&&m.getBoundingClientRect();document.querySelectorAll('.menu').forEach(z=>z.remove());"
                             "return !!m&&(Math.abs(mr.left-cx)<=40||Math.abs(mr.right-cx)<=40)&&(Math.abs(mr.top-cy)<=40||(mr.top-4<=cy&&cy<=mr.bottom+4)) || JSON.stringify({click:[cx,cy],menu:mr&&[mr.left,mr.top,mr.right,mr.bottom]});"),
        step("확대 ③ 150% 에서 표 칸에 글 치기 → 그 칸의 문서에 들어감",
             H + "await idle();const t=S.deck.blocks.find(b=>b.id==='mt');const all=JSON.stringify(t);return all.includes('칸줌') || all.slice(0,300);",
             pre="const c=[...document.querySelectorAll('#ed .pg-cell')].pop();c.focus();const sel=getSelection();sel.selectAllChildren(c);sel.collapseToEnd();", cdp=INS("칸줌"), wait=200),
        step("확대 되돌림 - 100% · 기억한 값 지움(다음 시험에 남기지 않음)",
             H + ZOOM + "chg('#selZoom','1');await tick();try{localStorage.removeItem('nexaPageZoom');}catch(e){}return getComputedStyle(document.querySelector('#paper')).zoom==='1' || 'zoom not reset';"),
    ]


IMPORT_DOCX = [b""]  # 가져오기 시험용 .docx(우리 내보내기로 만든 것 - Word 가 만든 문서는 page_word_import_test)


def import_ui_steps(b64):
    return [step("새 문서 → 페이지 → [Word 문서(.docx)에서 가져오기] 에 파일 → page.html 로 이동 · 본문에 글",
                 ND + "await open();nd().querySelector('[data-kind=page]').click();await until(async()=>nd().querySelector('#ndFile'),5000);const bin=Uint8Array.from(atob('" + b64 + "'),c=>c.charCodeAt(0));"
                      "const dt=new DataTransfer();dt.items.add(new File([bin],'가져오기 화면.docx',{type:'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}));const inp=nd().querySelector('#ndFile');inp.files=dt.files;"
                      "setTimeout(()=>inp.dispatchEvent(new Event('change',{bubbles:true})),50);return true;", wait=3000),
            ]


def import_ui_check_steps():
    return [step("(앞 단계) 가져온 문서가 page.html 로 열리고 본문에 '가져온 글'",
                 "await until(async()=>location.pathname.endsWith('page.html')&&window.NexaPageEditor,8000);const S=window.NexaPageEditor&&NexaPageEditor.S;"
                 "return location.pathname.endsWith('page.html')&&S&&S.deck.blocks.some(b=>(b.runs||[]).map(r=>r.t).join('').includes('가져온 글')) || JSON.stringify({href:location.href,blocks:S&&S.deck.blocks.length});")]


ND = ("const nd=()=>document.querySelector('.nd-back');const open=async()=>{document.querySelector('#deckTabs [data-deckadd]').click();await until(async()=>nd()&&nd().querySelector('#ndTitle'),5000);};"
      "const kinds=()=>[...nd().querySelectorAll('[data-kind]')].map(b=>b.dataset.kind);")


def newdoc_off_steps():
    return [step("새 문서 대화 상자(꺼진 작업 공간) - 슬라이드 [＋] → 종류 둘(슬라이드·시트) · Esc 로 닫힘 · 바깥 누르기로 닫힘",
                 ND + "await open();const k=kinds();document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));await new Promise(r=>setTimeout(r,150));const e1=!nd();"
                      "await open();nd().dispatchEvent(new MouseEvent('mousedown',{bubbles:true}));await new Promise(r=>setTimeout(r,150));const e2=!nd();"
                      "return k.join()==='deck,sheet'&&e1&&e2 || JSON.stringify({k,e1,e2});")]


def newdoc_on_steps():
    return [
        step("새 문서 대화 상자(켠 작업 공간) - 종류 셋 · 제목이 비면 오류 글 · 페이지 → 템플릿 카드 11개(일반 문서·학습 자료)",
             ND + "await open();const k=kinds();nd().querySelector('#ndTitle').value='';nd().querySelector('#ndOk').click();await new Promise(r=>setTimeout(r,150));const err=nd().querySelector('#ndErr').textContent;"
                  "nd().querySelector('[data-kind=page]').click();await until(async()=>nd().querySelectorAll('.nd-tpl[data-tpl]').length,5000);const n=nd().querySelectorAll('.nd-tpl[data-tpl]').length,g=[...nd().querySelectorAll('.nd-group')].map(x=>x.textContent);"
                  "document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));return k.join()==='deck,sheet,page'&&/제목/.test(err)&&n===11&&g.some(x=>/일반/.test(x))&&g.some(x=>/학습/.test(x)) || JSON.stringify({k,err,n,g});"),
        step("새 문서 대화 상자 - 슬라이드로 만들면 그 덱이 열리고 덱 탭에 생김",
             ND + "await open();nd().querySelector('[data-kind=deck]').click();nd().querySelector('#ndTitle').value='대화 상자 덱';nd().querySelector('#ndOk').click();"
                  "await until(async()=>{const o=document.querySelector('#deckTabs button.on');return o&&o.textContent.trim()==='대화 상자 덱'&&!nd();},8000);const o=document.querySelector('#deckTabs button.on');"
                  "return !!o&&o.textContent.trim()==='대화 상자 덱' || JSON.stringify({on:o&&o.textContent,dlg:!!nd()});"),
        step("새 문서 대화 상자 - 시트를 고르고 [만들기] → 시트 테마 창(.nx-sn)으로 넘어감",
             ND + "await open();nd().querySelector('[data-kind=sheet]').click();await new Promise(r=>setTimeout(r,150));nd().querySelector('#ndOk').click();await until(async()=>document.querySelector('.nx-sn'),5000);"
                  "const ok=!!document.querySelector('.nx-sn')&&!nd();const sn=document.querySelector('.nx-sn');if(sn)sn.remove();return ok || JSON.stringify({sn:!!document.querySelector('.nx-sn'),dlg:!!nd()});"),
        step("새 문서 대화 상자 - 페이지 + 템플릿 '보고서'(report) 로 만들면 page.html 로 가고 문서 template = report",
             ND + "await open();nd().querySelector('[data-kind=page]').click();await until(async()=>nd().querySelector('[data-tpl=report]'),5000);nd().querySelector('[data-tpl=report]').click();"
                  "nd().querySelector('#ndTitle').value='대화 상자 보고서';setTimeout(()=>nd().querySelector('#ndOk').click(),50);return true;", wait=2500),
    ]


def newdoc_rec_steps():
    return [step("새 문서 대화 상자 - (앞 단계) 페이지 + 템플릿 '보고서' 로 만든 뒤 page.html 로 갔고 문서 template = report",
                 "const id=new URLSearchParams(location.search).get('deck');const f=await (await fetch('/api/decks',{cache:'no-store'})).json();const d=(Array.isArray(f)?f:[]).find(x=>x.title==='대화 상자 보고서');"
                 "const doc=d&&await (await fetch('/api/deck/'+d.id,{cache:'no-store'})).json();return !!d&&d.kind==='page'&&doc.template==='report' || JSON.stringify({d,tpl:doc&&doc.template});"),
            step("새 문서 대화 상자 - 같은 템플릿(report)으로 두 번 만든 뒤 다시 열면 '자주 쓰는 템플릿' 맨 앞에 '2회'",
                 ND + "await open();nd().querySelector('[data-kind=page]').click();await until(async()=>nd().querySelectorAll('.nd-tpl[data-tpl]').length,5000);const g=nd().querySelector('.nd-group').textContent,first=nd().querySelector('.nd-tpl[data-tpl]');"
                      "const r={g,tpl:first.dataset.tpl,rec:(first.querySelector('.rec')||{}).textContent};document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));"
                      "return /자주/.test(g)&&r.tpl==='report'&&/2회/.test(r.rec||'') || JSON.stringify(r);")]


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
        import base64 as _b64
        import export_docx as _xd
        import page_doc as _pd
        _doc = _pd.new_page("imp", "가져오기 원본"); _doc["blocks"] = [{"id": "i1", "type": "p", "runs": [{"t": "가져온 글"}]}]
        IMPORT_DOCX[0] = _xd.build(_doc)
        st_, r_, _ = call("POST", "/api/decks", {"action": "import", "name": "x.docx", "data": _b64.b64encode(IMPORT_DOCX[0]).decode()})
        check("가져오기 - 꺼진 작업 공간에서 .docx 가져오기 400", st_ == 400, (st_, r_))
        lines, _ = scenario([{"url": "/studio/index.html#pgslide", "wait": 2500, "steps": newdoc_off_steps()}])
        for l in lines:
            print("  ", l[:700])
            if l.startswith("FAIL"):
                FAILS.append("화면(꺼짐): " + l[5:80])
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
                step("긴 문서(문단 80개) - 쪽 경계선 수 = #pageInfo 의 n쪽 - 1 · 2쪽 이상", "const n=(document.querySelectorAll('#sheets .pg-sheet').length-1);const t=document.querySelector('#pageInfo').textContent;const k=parseInt(t);return k>=2&&n===k-1 || JSON.stringify({lines:n,info:t});")]},
            {"url": f"/studio/page.html?deck={pid}", "wait": 2500, "steps": token_steps() + setup_steps(pid) + export_steps(pid) + image_steps(pid)},
            {"url": "/studio/page.html?deck=pgtbl", "wait": 2500, "steps": table_steps("pgtbl")},
            {"url": "/studio/page.html?deck=pgfmt", "wait": 2500, "steps": fmt_steps() + ruby_steps()},
            {"url": "/studio/page.html?deck=pgmrg", "wait": 2500, "steps": merge_steps()},
            {"url": "/studio/page.html?deck=pgsgid", "wait": 2500, "steps": study_steps()},
            {"url": "/studio/page.html?deck=pgpoll", "wait": 2500, "steps": poll_steps()},
            {"url": "/studio/page.html?deck=pgpdel", "wait": 2500, "steps": poll_del_steps()},
            {"url": "/studio/page.html?deck=pglong", "wait": 3000, "steps": zoom_steps()},
            {"url": "/studio/page.html?deck=pglong", "wait": 3000, "steps": zoom_reload_steps()},
            {"url": "/studio/page.html?deck=pgmrg", "wait": 2500, "steps": zoom_edit_steps()},
            {"url": "/studio/page.html?deck=pgflow", "wait": 3000, "steps": flow_steps()},
            {"url": "/studio/page.html?deck=pgflow&print=1", "wait": 2500, "steps": flow_print_steps()},
            {"url": "/studio/page.html?deck=pgobj", "wait": 3000, "steps": obj_steps()},
            {"url": "/studio/page.html?deck=pgobj", "wait": 3000, "steps": obj_reload_steps()},
            {"url": "/studio/page.html?deck=pgreqid", "wait": 2500, "steps": req_steps()},
            {"url": "/studio/page.html?deck=pgreqid", "wait": 2500, "steps": req_reload_steps()},
            {"url": "/studio/index.html#pgslide", "wait": 2500, "steps": newdoc_on_steps()},
        ]
        import page_doc
        for doc_ in (FMT_DOC, MRG_DOC, POLL_DOC, POLL_DEL, FLOW_DOC, OBJ_DOC):  # 쪽 설정·스타일은 새 문서 기본값에 블록만 바꿔 넣는다
            full = page_doc.new_page(doc_["id"], doc_["title"]); full["blocks"] = doc_["blocks"]
            st_, r_, _ = call("PUT", f"/api/deck/{doc_['id']}", full)
            check(f"서식·합치기 시험 문서 {doc_['id']} 만들기 200", st_ == 200, (st_, r_))
        st, r, _ = call("POST", "/api/decks", {"action": "create", "kind": "page", "title": "해설지 시험", "theme": "study-guide"})
        sg_id = (r or {}).get("id") or "pgsgid"
        check("해설지 템플릿으로 만들기 200 · template = study-guide", st == 200 and deck_file(ws_on, sg_id).get("template") == "study-guide", (st, r))
        pages = [dict(x, url=x["url"].replace("pgsgid", sg_id)) for x in pages]
        st, r, _ = call("POST", "/api/decks", {"action": "create", "kind": "page", "title": "표 시험"})
        tbl_id = (r or {}).get("id") or "pgtbl"
        pages = [dict(x, url=x["url"].replace("pgtbl", tbl_id)) for x in pages]
        st, r, _ = call("POST", "/api/decks", {"action": "create", "kind": "page", "title": "요청 시험"})  # 요청 파일이 남지 않게 실행마다 새 문서
        req_id = (r or {}).get("id") or "pgreqid"
        pages = [dict(x, url=x["url"].replace("pgreqid", req_id)) for x in pages]
        pages = [dict(x, steps=[dict(y, js=y["js"].replace("'pgtbl'", f"'{tbl_id}'")) for y in x["steps"]]) for x in pages]
        lines, rc = scenario(pages)
        # 같은 템플릿으로 한 번 더 만들어(대화 상자에서 1번 + 여기서 1번 = 2회) 추천 묶음 확인
        call("POST", "/api/decks", {"action": "create", "kind": "page", "title": "보고서 둘", "theme": "report"})
        l2, _ = scenario([{"url": "/studio/index.html#pgslide", "wait": 2500, "steps": newdoc_rec_steps()}])  # 대화 상자로 1번 + API 로 1번 = report 2회
        lines += l2
        # 쪽 나눔 - 서버 Chrome PDF 쪽 수 vs 화면 쪽 수(±1 이면 통과, 다르면 수치를 남긴다)
        scr = next((int(l.rsplit("screenPages=", 1)[1].split()[0]) for l in lines if "screenPages=" in l), None)
        st_, r_, _ = call("POST", "/api/export/pgflow?pdf=1&via=chrome")
        pdfb_ = b""
        if st_ == 200 and r_.get("url"):
            with urllib.request.urlopen(B + r_["url"], timeout=60) as rr:
                pdfb_ = rr.read()
        npdf = pdfb_.count(b"/Type /Page") - pdfb_.count(b"/Type /Pages") if pdfb_ else 0
        NOTES.append(f"쪽 나눔: 화면 {scr}쪽 · Chrome PDF {npdf}쪽")
        check("쪽 나눔 ⑫ Chrome PDF 쪽 수 = 화면 쪽 수 ±1", scr is not None and npdf > 0 and abs(npdf - scr) <= 1, json.dumps({"screen": scr, "pdf": npdf, "st": st_}, ensure_ascii=False))
        for l in lines:
            print("  ", l[:700])
            if l.startswith("FAIL"):
                FAILS.append("화면: " + l[5:80])
        # 4. 내보내기 API - DOCX 내려받기 · 이름 · 가로·머리말 구조 · PDF · 슬라이드 내보내기 그대로
        import zipfile, io  # noqa: E401
        st, r, _ = call("POST", f"/api/export/{pid}")
        data = b""
        if st == 200 and r.get("url"):
            with urllib.request.urlopen(B + r["url"], timeout=30) as rr:
                data = rr.read()
        title = deck_file(ws_on, pid).get("title")
        xml = zipfile.ZipFile(io.BytesIO(data)).read("word/document.xml").decode("utf-8") if data[:2] == b"PK" else ""
        check("4 내보내기 API - POST /api/export/<페이지> 200 · /out/ 내려받기 · 이름 = 제목.docx · document.xml 에 가로(orient)·headerReference",
              st == 200 and data[:2] == b"PK" and r.get("name") == f"{title}.docx" and 'w:orient="landscape"' in xml and "headerReference" in xml,
              json.dumps({"st": st, "r": r, "bytes": len(data), "orient": 'w:orient="landscape"' in xml, "head": "headerReference" in xml}, ensure_ascii=False)[:400])
        st, r, _ = call("POST", f"/api/export/{pid}?pdf=1")
        check("4 내보내기 API ?pdf=1 - Word 있으면 200 method word · 없으면 501 needPrint", (st == 200 and r.get("method") == "word" and str(r.get("url", "")).split("?")[0].endswith(".pdf")) or (st == 501 and r.get("needPrint")), json.dumps({"st": st, "r": r}, ensure_ascii=False)[:300])
        NOTES.append(f"PDF 내보내기 응답 {st} · {json.dumps(r, ensure_ascii=False)[:160]}")
        # 토큰 글꼴이 DOCX styles.xml 에 - 제목(heading → title) 의 rFonts latin·ea
        try:
            with urllib.request.urlopen(B + "/studio/tokens.json", timeout=10) as rr:
                tok = json.loads(rr.read())
        except Exception:  # noqa: BLE001
            tok = {}
        hd = (tok.get("fonts") or {}).get("heading") or {}
        styles = zipfile.ZipFile(io.BytesIO(data)).read("word/styles.xml").decode("utf-8") if data[:2] == b"PK" else ""
        lat, ea = hd.get("latin") or hd.get("ea"), hd.get("ea") or hd.get("latin")
        check("4 DOCX styles.xml 의 글꼴 = 작업 공간 토큰 heading 의 latin·ea", bool(lat) and f'w:ascii="{lat}"' in styles and f'w:eastAsia="{ea}"' in styles,
              json.dumps({"heading": hd, "has_ascii": bool(lat) and f'w:ascii="{lat}"' in styles, "has_ea": bool(ea) and f'w:eastAsia="{ea}"' in styles}, ensure_ascii=False)[:300])
        # Chrome 인쇄 PDF(?via=chrome) - method chrome · PDF 파일 · 남는 Chrome 없음(시험 전에 있던 것은 그대로)
        def chromes():
            if os.name != "nt":
                return set()
            out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq chrome.exe", "/FO", "CSV", "/NH"], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
            return {l.split(",")[1].strip('"') for l in out.splitlines() if l.startswith('"chrome')}
        before = chromes()
        st, r, _ = call("POST", f"/api/export/{pid}?pdf=1&via=chrome")
        pdfb = b""
        if st == 200 and r.get("url"):
            with urllib.request.urlopen(B + r["url"], timeout=60) as rr:
                pdfb = rr.read()
        time.sleep(1.5)
        left = chromes() - before
        pages = pdfb.count(b"/Type /Page") - pdfb.count(b"/Type /Pages") if pdfb else 0
        check("4 내보내기 API ?pdf=1&via=chrome - 200 method chrome · PDF 파일 · 남는 Chrome 없음",
              st == 200 and r.get("method") == "chrome" and pdfb[:5] == b"%PDF-" and not left, json.dumps({"st": st, "r": r, "bytes": len(pdfb), "left": sorted(left)}, ensure_ascii=False)[:400])
        NOTES.append(f"Chrome PDF: {len(pdfb)} 바이트 · 쪽 표시 {pages}개 · 응답 pages={r.get('pages')}")
        st, r, _ = call("POST", f"/api/export/{pid}?pdf=1")
        check("4 내보내기 API ?pdf=1(via 없음) - Word 가 있으면 그대로 method word", st == 200 and r.get("method") in ("word", "chrome"), json.dumps({"st": st, "r": r}, ensure_ascii=False)[:300])
        NOTES.append(f"via 없는 PDF 방법 = {r.get('method')}")
        st, r, _ = call("POST", "/api/export/pgsheet")
        check("4 시트 내보내기는 그대로(xlsx)", st == 200 and str(r.get("url", "")).split("?")[0].endswith(".xlsx"), json.dumps({"st": st, "r": r}, ensure_ascii=False)[:300])
        # 표 문서를 Word 로 열어 표 수·행·열(Word 가 없거나 사용자가 띄워 두었으면 관찰만)
        st, r, _ = call("POST", f"/api/export/{tbl_id}")
        if st == 200 and r.get("url"):
            with tmpfiles.temp_dir("nx-pgtbl-") as d:
                f = Path(d) / "t.docx"
                with urllib.request.urlopen(B + r["url"], timeout=30) as rr:
                    f.write_bytes(rr.read())
                pw = __import__("shutil").which("pwsh") or __import__("shutil").which("powershell")
                if pw:
                    w = subprocess.run([pw, "-NoProfile", "-File", str(HERE / "docx_open_check.ps1"), "-Docx", str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
                    j = json.loads((w.stdout.strip().splitlines() or ["{}"])[-1] or "{}")
                    if w.returncode == 99:
                        NOTES.append(f"표 문서 Word 열기 - 판정 불가: {j.get('skip')}")
                    else:
                        tb = next((b for b in deck_file(ws_on, tbl_id)["blocks"] if b.get("type") == "table"), {})
                        check(f"4 표 문서 DOCX 를 Word 로 열면 표 {1 if tb else 0}개", w.returncode == 0 and j.get("tables") == (1 if tb else 0), json.dumps(j, ensure_ascii=False)[:300])
        # 서식 문서 DOCX - f1 문단의 pPr 에 spacing line=480(pStyle·numPr 뒤 · ind·jc 앞) · hyperlink 는 링크를 풀었으므로 없음 · 합친 표 gridSpan·vMerge · Word 로 열림
        import re as _re
        st, r, _ = call("POST", "/api/export/pgfmt")
        fx = b""
        if st == 200 and r.get("url"):
            with urllib.request.urlopen(B + r["url"], timeout=30) as rr:
                fx = rr.read()
        dx = zipfile.ZipFile(io.BytesIO(fx)).read("word/document.xml").decode("utf-8") if fx[:2] == b"PK" else ""
        ppr = next((m.group(1) for m in _re.finditer(r"<w:p>(?:<w:pPr>(.*?)</w:pPr>)?(?:(?!</w:p>).)*?첫 (?:(?!</w:p>).)*?</w:p>", dx)), "") or ""
        order = _re.findall(r"<w:(pStyle|numPr|spacing|ind|jc)\b", ppr)
        sp_ok = 'w:line="480"' in ppr and order.index("spacing") > max([order.index(x) for x in ("pStyle", "numPr") if x in order] or [-1]) and order.index("spacing") < min([order.index(x) for x in ("ind", "jc") if x in order] or [99])
        check("4 DOCX 줄 간격 2 - 그 문단 pPr 에 spacing line=480(pStyle·numPr 뒤, ind·jc 앞)", st == 200 and sp_ok, json.dumps({"st": st, "pPr": ppr[:300], "order": order}, ensure_ascii=False))
        shp = next((m.group(0) for m in _re.finditer(r"<w:p>(?:(?!</w:p>).)*?셋째 문단(?:(?!</w:p>).)*?</w:p>", dx)), "")
        check("4 DOCX 문단 음영 - '셋째 문단' pPr 에 w:shd fill E6E6E6", 'w:fill="E6E6E6"' in shp and "<w:shd" in shp.split("</w:pPr>")[0], shp[:300])
        check("4 DOCX 윗주 - document.xml 에 w:ruby 1개(본문 '끝' 위 'S')", dx.count("<w:ruby>") == 1, f"w:ruby {dx.count('<w:ruby>')}개")
        if pw_ := (__import__("shutil").which("pwsh") or __import__("shutil").which("powershell")):
            with tmpfiles.temp_dir("nx-pgfmt-") as d:
                f = Path(d) / "f.docx"; f.write_bytes(fx)
                w = subprocess.run([pw_, "-NoProfile", "-File", str(HERE / "docx_open_check.ps1"), "-Docx", str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
                j = json.loads((w.stdout.strip().splitlines() or ["{}"])[-1] or "{}")
                if w.returncode != 99:
                    check("4 서식 문서(줄 간격·고정폭·윗주) DOCX 를 Word 로 - 경고 없이 열림", w.returncode == 0 and j.get("ok"), json.dumps(j, ensure_ascii=False)[:300])
        st, r, _ = call("POST", "/api/export/pgmrg")
        mx = b""
        if st == 200 and r.get("url"):
            with urllib.request.urlopen(B + r["url"], timeout=30) as rr:
                mx = rr.read()
        mdx = zipfile.ZipFile(io.BytesIO(mx)).read("word/document.xml").decode("utf-8") if mx[:2] == b"PK" else ""
        check("4 합친 표 DOCX - gridSpan 2 · vMerge(restart + 이어짐)", 'w:gridSpan w:val="2"' in mdx and 'w:vMerge w:val="restart"' in mdx and "<w:vMerge/>" in mdx,
              json.dumps({"gridSpan": 'w:gridSpan w:val="2"' in mdx, "restart": 'w:vMerge w:val="restart"' in mdx, "cont": "<w:vMerge/>" in mdx}, ensure_ascii=False))
        tb_ = (_re.search(r"<w:tblBorders>(.*?)</w:tblBorders>", mdx) or [None, ""])[1] if mdx else ""
        check("4 배치용 표(inner-v) DOCX - tblBorders 에 insideV 만 single · 나머지 none(Word 가 nil 을 정의 안 됨으로 읽음) · 머리 행 회색 칠 없음",
              'w:insideV w:val="single"' in tb_ and all(f'<w:{x} w:val="none"' in tb_ for x in ("top", "left", "bottom", "right", "insideH")) and 'w:fill="F0F0F0"' not in mdx, tb_[:400])
        pw_ = __import__("shutil").which("pwsh") or __import__("shutil").which("powershell")
        if pw_ and mx[:2] == b"PK":
            with tmpfiles.temp_dir("nx-pgmrg-") as d:
                f = Path(d) / "m.docx"; f.write_bytes(mx)
                w = subprocess.run([pw_, "-NoProfile", "-File", str(HERE / "docx_open_check.ps1"), "-Docx", str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
                j = json.loads((w.stdout.strip().splitlines() or ["{}"])[-1] or "{}")
                if w.returncode == 99:
                    NOTES.append(f"합친 표 Word 열기 - 판정 불가: {j.get('skip')}")
                else:
                    check("4 합친 표 DOCX 를 Word 로 - 경고 없이 열림 · 표 1", w.returncode == 0 and j.get("ok") and j.get("tables") == 1, json.dumps(j, ensure_ascii=False)[:300])
            # 테두리 없음(none)으로 바꿔 다시 내보내 Word 에서 선이 하나도 없는지
            dm = deck_file(ws_on, "pgmrg"); vm = None
            for b_ in dm.get("blocks") or []:
                if b_.get("id") == "mt":
                    b_["border"] = "none"
            st_, r_, _ = call("PUT", "/api/deck/pgmrg", dm)
            st, r, _ = call("POST", "/api/export/pgmrg")
            nx = b""
            if st == 200 and r.get("url"):
                with urllib.request.urlopen(B + r["url"], timeout=30) as rr:
                    nx = rr.read()
            ndx = zipfile.ZipFile(io.BytesIO(nx)).read("word/document.xml").decode("utf-8") if nx[:2] == b"PK" else ""
            tn = (_re.search(r"<w:tblBorders>(.*?)</w:tblBorders>", ndx) or [None, ""])[1]
            check("4 배치용 표(none) DOCX - tblBorders 여섯 개 모두 none", st_ == 200 and tn.count('w:val="none"') == 6 and "single" not in tn, tn[:400])
            with tmpfiles.temp_dir("nx-pgnob-") as d:
                f = Path(d) / "n.docx"; f.write_bytes(nx)
                w = subprocess.run([pw_, "-NoProfile", "-File", str(HERE / "docx_open_check.ps1"), "-Docx", str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
                j = json.loads((w.stdout.strip().splitlines() or ["{}"])[-1] or "{}")
                if w.returncode == 99:
                    NOTES.append(f"배치용 표 Word 열기 - 판정 불가: {j.get('skip')}")
                else:
                    check("4 배치용 표(none)·합친 칸 DOCX 를 Word 로 - 경고 없이 열림(선 종류 판정은 합치지 않은 표로 pageword 에서)", w.returncode == 0 and j.get("ok"), json.dumps(j, ensure_ascii=False)[:300])
        # 가져오기 API(켠 작업 공간) - 그림 든 문서(앞에서 내보낸 pid)를 다시 가져와 그림이 assets/images/<id>-import-*.png 로
        st, r, _ = call("POST", f"/api/export/{pid}")
        src = b""
        if st == 200 and r.get("url"):
            with urllib.request.urlopen(B + r["url"], timeout=30) as rr:
                src = rr.read()
        import base64 as _b64
        st, r, _ = call("POST", "/api/decks", {"action": "import", "name": "그림 문서.docx", "data": _b64.b64encode(src).decode()})
        iid = (r or {}).get("id") or ""
        imgs = sorted(p_.name for p_ in (ws_on / "assets" / "images").glob(f"{iid}-import-*")) if iid else []
        f_ = deck_file(ws_on, iid) if iid and (ws_on / "decks" / f"{iid}.json").is_file() else {}
        check("가져오기 API - 켠 작업 공간 200 · kind page · blocks · warnings 키 · 그림이 assets/images/<id>-import-* 로",
              st == 200 and f_.get("kind") == "page" and f_.get("blocks") and "warnings" in (r or {}) and imgs and all(b.get("src", "").startswith("assets/images/") for b in f_["blocks"] if b.get("type") == "image"),
              json.dumps({"st": st, "r": {k: (r or {}).get(k) for k in ("id", "kind", "warnings", "error")}, "imgs": imgs}, ensure_ascii=False)[:400])
        if iid:
            l3, _ = scenario([{"url": f"/studio/page.html?deck={iid}", "wait": 3000, "steps": [step("가져온 문서 - page.html 에서 그림이 보임(naturalWidth > 0)",
                "await until(async()=>[...document.querySelectorAll('#ed img')].every(i=>i.complete),5000);const im=[...document.querySelectorAll('#ed img')];return im.length>0&&im.every(i=>i.naturalWidth>0) || JSON.stringify(im.map(i=>[i.src,i.naturalWidth]));")]}])
            for l in l3:
                print("  ", l[:600])
                if l.startswith("FAIL"):
                    FAILS.append("화면: " + l[5:80])
        st, r, _ = call("POST", "/api/export/pgsheet")
        xb = b""
        if st == 200 and r.get("url"):
            with urllib.request.urlopen(B + r["url"], timeout=30) as rr:
                xb = rr.read()
        st, r, _ = call("POST", "/api/decks", {"action": "import", "name": "시트.xlsx", "data": _b64.b64encode(xb).decode()})
        xid = (r or {}).get("id") or ""
        check("가져오기 API - .xlsx 는 그대로 시트 문서", st == 200 and xid and deck_file(ws_on, xid).get("kind") == "sheet", json.dumps({"st": st, "r": r}, ensure_ascii=False)[:300])
        import io as _io, zipfile as _zf  # noqa: E401
        fake = _io.BytesIO()
        with _zf.ZipFile(fake, "w") as z_:
            z_.writestr("hello.txt", "docx 아님")
        st, r, _ = call("POST", "/api/decks", {"action": "import", "name": "가짜.docx", "data": _b64.b64encode(fake.getvalue()).decode()})
        check("가져오기 API - docx 가 아닌 zip 을 .docx 이름으로 올리면 400", st == 400, json.dumps({"st": st, "r": r}, ensure_ascii=False)[:300])
        l4, _ = scenario([{"url": "/studio/index.html#pgslide", "wait": 2500, "steps": import_ui_steps(_b64.b64encode(IMPORT_DOCX[0]).decode())}])
        for l in l4:
            print("  ", l[:600])
            if l.startswith("FAIL"):
                FAILS.append("화면: " + l[5:80])
        _, dl, _ = call("GET", "/api/decks")
        got = [x for x in (dl if isinstance(dl, list) else []) if x.get("kind") == "page" and "가져오기" in str(x.get("title", "")) and x.get("id") != iid]
        txt_ok = any("가져온 글" in json.dumps(deck_file(ws_on, x["id"]).get("blocks"), ensure_ascii=False) for x in got)
        check("화면 가져오기 - 새 문서 대화 상자로 올린 .docx 가 페이지 문서로 만들어지고 본문에 '가져온 글'", bool(got) and txt_ok, json.dumps([(x.get("id"), x.get("title")) for x in got], ensure_ascii=False)[:300])
        # 그림이 든 문서를 Word 로 - InlineShapes
        st, r, _ = call("POST", f"/api/export/{pid}")
        if st == 200 and r.get("url"):
            with tmpfiles.temp_dir("nx-pgimg-") as d:
                f = Path(d) / "img.docx"
                with urllib.request.urlopen(B + r["url"], timeout=30) as rr:
                    f.write_bytes(rr.read())
                pw = __import__("shutil").which("pwsh") or __import__("shutil").which("powershell")
                if pw:
                    w = subprocess.run([pw, "-NoProfile", "-File", str(HERE / "docx_open_check.ps1"), "-Docx", str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
                    j = json.loads((w.stdout.strip().splitlines() or ["{}"])[-1] or "{}")
                    nimg = sum(1 for b in deck_file(ws_on, pid)["blocks"] if b.get("type") == "image")
                    if w.returncode == 99:
                        NOTES.append(f"그림 문서 Word 열기 - 판정 불가: {j.get('skip')}")
                    else:
                        check(f"4 그림 {nimg}개 든 문서 DOCX 를 Word 로 열면 InlineShapes {nimg}", w.returncode == 0 and j.get("inlineShapes") == nimg, json.dumps(j, ensure_ascii=False)[:300])
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
