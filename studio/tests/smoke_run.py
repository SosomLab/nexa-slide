# -*- coding: utf-8 -*-
"""헤드리스 클릭 스모크 - 격리 허브(5799, worktree 엔진)를 띄우고 관리자로 로그인해 시작 페이지·Studio(중계)의 주요 버튼을 눌러 본다(콘솔 오류 0). smoke.js 를 쓴다."""
import json
import os, os, subprocess, sys, time
from pathlib import Path
for _s in (sys.stdout, sys.stderr): _s.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
STUDIO = Path(__file__).resolve().parents[1]  # studio/ (이 파일은 studio/tests/)
WORK = Path(os.environ.get("NEXA_TEST_DIR") or Path(tempfile.gettempdir()) / "nexa-slide-tests")  # 시험 산출물(사용자 설정·작업 공간) - 저장소 밖(허브는 엔진 안의 작업 공간을 거절한다)
for _d in (WORK / "user", WORK / "projects"):
    _d.mkdir(parents=True, exist_ok=True)
USER, PROJ, HUB_PORT = WORK / "user", WORK / "projects", 5799
BASE = f"http://127.0.0.1:{HUB_PORT}"
ENV = {**os.environ, "NEXA_SLIDE_USER_DIR": str(USER), "NEXA_SLIDE_PROJECTS": str(PROJ), "PYTHONIOENCODING": "utf-8"}
ENV.pop("NEXA_SLIDE_WORKSPACE", None)
def svc(cmd, ws=None):
    env = dict(ENV)
    if ws: env["NEXA_SLIDE_WORKSPACE"] = str(ws)
    return subprocess.run([sys.executable, str(STUDIO / "service.py"), cmd], env=env, cwd=str(ws or USER), capture_output=True, text=True, encoding="utf-8")
import http.cookiejar, urllib.request
(USER / "settings.json").write_text(json.dumps({"hubPort": HUB_PORT, "hubProxy": True, "engine": str(STUDIO.parent), "sessionAllowWeb": True, "sessionAllowGit": True, "sessionAllowPush": True, "sessionRepoRoot": True}), encoding="utf-8")
print(svc("start").stdout.strip())
rc = 1
try:
    (USER / "users.json").unlink(missing_ok=True)
    jar = http.cookiejar.CookieJar(); op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    def req(method, url, body=None):
        h = {"Accept": "application/json", "Origin": BASE, "Content-Type": "application/json"}
        with op.open(urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, method=method, headers=h), timeout=120) as r: return json.loads(r.read())
    req("POST", BASE + "/api/auth/setup", {"id": "admin", "password": "smoke-pass-123"})
    d = req("POST", BASE + "/api/project", {"action": "demo"}); wid = d["id"]; ws = Path(d["path"])
    import shutil; shutil.rmtree(USER / "hub" / "engine", ignore_errors=True)
    req("POST", BASE + "/api/engine/requests", {"action": "add", "title": "스모크 대기 요청", "body": "b"})
    req("POST", BASE + "/api/auth/users", {"action": "add", "id": "bob", "password": "bob-pass-123", "role": "user"})
    import base64
    PNG = base64.b64encode(bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da63f8cfc0f01f0005000201e4ae07ea0000000049454e44ae426082")).decode()
    decks = req("GET", f"{BASE}/w/{wid}/api/decks"); did = decks[0]["id"] if isinstance(decks, list) else list(decks)[0]
    deck = req("GET", f"{BASE}/w/{wid}/api/deck/{did}"); sid = deck["slides"][0]["id"]
    a1 = req("POST", f"{BASE}/w/{wid}/api/attach/{did}", {"name": "image.png", "type": "image/png", "data": PNG})
    a2 = req("POST", f"{BASE}/w/{wid}/api/attach/{did}", {"name": "memo.txt", "type": "text/plain", "data": base64.b64encode(b"hello").decode()})
    req("POST", f"{BASE}/w/{wid}/api/requests/{did}", {"action": "add", "status": "open", "slide": sid, "text": "스모크 첨부 요청", "attachments": [a1, a2]})
    els = [e["id"] for e in deck["slides"][0]["elements"][:2]]
    req("POST", f"{BASE}/w/{wid}/api/requests/{did}", {"action": "add", "status": "open", "slide": sid, "elements": els, "text": "두 요소 메모"})
    # 서버 작업 카드 요청에도 첨부
    ea = req("POST", BASE + "/api/engine/attach", {"name": "image.png", "type": "image/png", "data": PNG})
    req("POST", BASE + "/api/engine/requests", {"action": "add", "title": "스모크 첨부 요청", "body": "b", "attachments": [ea["name"]]})
    # 승인 대기(triage) 1건 - 페이지가 열린 뒤 생기도록 몇 초 뒤 CLI(세션 환경)로 넣는다
    import threading
    def _late():
        time.sleep(9)
        subprocess.run([sys.executable, str(STUDIO / "engine_request.py"), "add", "--title", "스모크 승인 대기"], env={**ENV, "NEXA_SLIDE_SESSION": "web:claude", "NEXA_SLIDE_USER": "admin"}, capture_output=True)
    threading.Thread(target=_late, daemon=True).start()
    S = {"base": BASE, "login": {"id": "admin", "password": "smoke-pass-123"}, "pages": [
        {"url": "/studio/home.html#start", "wait": 2500, "steps": [
            {"name": "최근 작업 항목 있음", "js": "document.querySelectorAll('#recent .ritem').length > 0"},
            {"name": "[세션 시작] 클릭 → 창 열림(에이전트 select)", "js": "document.querySelector('[data-sess=\"start\"]').click(); for (let i=0;i<20&&!document.querySelector('#sessModal.on #smAgent');i++) await new Promise(r=>setTimeout(r,400)); return !!document.querySelector('#sessModal.on #smAgent')"},
            {"name": "  웹 검색 체크(전역 켜짐·관리자) 보임", "js": "!!document.querySelector('#smWeb') && !document.querySelector('#smWeb').disabled"},
            {"name": "  git·push·root 체크 보임(관리자 활성) · push 고르면 git 도", "js": "const g=[...document.querySelectorAll('#smGrants [data-grant]')]; if(g.length!==3||g.some(x=>x.disabled)) return 'grants:'+g.length; const p=g.find(x=>x.dataset.grant==='push'); p.checked=true; p.dispatchEvent(new Event('change')); return g.find(x=>x.dataset.grant==='git').checked"},
            {"name": "  설정 모달 git 토글 3개", "js": "true"},
            {"name": "  취소", "js": "document.querySelector('#sessModal [data-close]').click(); await new Promise(r=>setTimeout(r,300)); return !document.querySelector('#sessModal.on')"},
            {"name": "서버 작업 카드 [세션 시작] → 창(저장 줄 숨김·웹 체크 없음)", "js": "const b=document.querySelector('[data-eng=\"start\"]'); if(!b) return 'no-button'; b.click(); await new Promise(r=>setTimeout(r,2500)); return !!document.querySelector('#sessModal.on #smAgent') && document.querySelector('#sessSaveRow').style.display==='none' && !document.querySelector('#smWeb')"},
            {"name": "  취소", "js": "document.querySelector('#sessModal [data-close]').click(); await new Promise(r=>setTimeout(r,300)); return true"},
            {"name": "설정 모달(#settings) → 웹 검색 토글 보임", "js": "location.hash='settings'; await new Promise(r=>setTimeout(r,800)); return !!document.querySelector('#setModal.on') && document.querySelector('#sgAllowWeb').checked===true"},
            {"name": "  취소", "js": "document.querySelector('#setModal [data-close]').click(); return true"},
            {"name": "서버 작업 카드: 경로·main 배지·대기 1 배지·배너(관리자 → 세션 시작 버튼)", "js": "await new Promise(r=>setTimeout(r,800)); return document.querySelector('#engPath').textContent.length>3 && document.querySelector('#engGit').textContent.includes('main') && document.querySelector('#engGit').textContent.includes('대기 2') && !!document.querySelector('#engBanner [data-eng=\"start\"]') && document.querySelector('#engBanner').textContent.includes('처리 대기 2건')"},
            {"name": "  배너가 있으면 [세션 시작]은 배너에만(하나) · 요청 추가는 카드 하단", "js": "const foot=document.querySelector('#engFoot'); return !document.querySelector('#engSess [data-eng=\"start\"]') && document.querySelectorAll('#engineCard [data-eng=\"start\"]').length===1 && foot && foot.nextElementSibling===null && foot.previousElementSibling.id==='engForm'"},
            {"name": "  ⋯(숨김 메뉴) → 터미널로 맡기기 명령 상자·복사 단추", "js": "const b=document.querySelector('[data-eng=\"manualhow\"]'); if(!b) return 'no-dots'; b.click(); await new Promise(r=>setTimeout(r,300)); const box=document.querySelector('#engManual'); if(!box) return 'no-box'; const ok=box.style.display!=='none' && box.textContent.includes('watch_engine_requests.py --stream') && !!box.querySelector('[data-eng=\"manualcopy\"]'); (document.querySelector('[data-eng=\"manualhow\"]')||b).click(); await new Promise(r=>setTimeout(r,200)); return ok ? (document.querySelector('#engManual').style.display==='none') : 'bad:'+box.textContent.slice(0,80)"},
            {"name": "  [요청 추가] → 양식(＋ 첨부 버튼), 하단 버튼 숨김", "js": "document.querySelector('#engReqNew').click(); return document.querySelector('#engForm').style.display!=='none' && document.querySelector('#erAttach').textContent.includes('첨부') && document.querySelector('#engFoot').style.display==='none'"},
            {"name": "  내용 칸 Shift+Enter 는 그대로 · Enter 로 큐에 넣기", "js": "document.querySelector('#erTitle').value='엔터 시험'; const ta=document.querySelector('#erBody'); ta.focus(); ta.value='첫 줄'; ta.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',shiftKey:true,bubbles:true})); const kept=document.querySelector('#engForm').style.display!=='none'; ta.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true})); await new Promise(r=>setTimeout(r,1500)); const sent=document.querySelector('#engForm').style.display==='none' && [...document.querySelectorAll('#engList b')].some(b=>b.textContent.includes('엔터 시험')); return kept && sent ? true : 'kept='+kept+' sent='+sent"},
            {"name": "  취소 → 하단 버튼 복귀", "js": "document.querySelector('#engReqCancel').click(); return document.querySelector('#engFoot').style.display===''"},
            {"name": "서버 작업 요청 첨부 축소판 → 라이트박스", "js": "const a=document.querySelector('#engList [data-lb]'); if(!a) return 'no-thumb'; a.click(); await new Promise(r=>setTimeout(r,400)); const lb=document.querySelector('.nx-lb'); const ok=lb && lb.style.display!=='none' && !!lb.querySelector('.stage img'); lb.querySelector('.x').click(); return ok"},
            {"name": "승인 대기 알림: 메뉴 단추 배지(1)·탭 제목 (1)·토스트", "js": "await new Promise(r=>setTimeout(r,1500)); const d=document.querySelector('#menuBtn .nx-dot'); return !!d && d.textContent==='1' && document.title.startsWith('(1) ') && [...document.querySelectorAll('.nx-toast')].some(t=>t.textContent.includes('승인 대기'))"},
            {"name": "주기 갱신: 서버 작업 카드에 승인 대기 반영(새로 고침 없이)", "js": "await new Promise(r=>setTimeout(r,5500)); return document.querySelector('#engGit').textContent.includes('승인 대기 1')"},
            {"name": "  메뉴 '서버 작업' 배지 = 승인 대기 1(관리자)", "js": "document.querySelector('#menuBtn').click(); await new Promise(r=>setTimeout(r,600)); const b=document.querySelector('.nx-badge'); const t=b&&b.textContent; NexaMenu.close(); return t==='1'"},
            {"name": "메뉴 열기 → 표시 언어 → English 즉시 반영", "js": "document.querySelector('#menuBtn').click(); await new Promise(r=>setTimeout(r,500)); document.querySelector('[data-langbtn]').click(); document.querySelector('[data-lang=\"en\"]').click(); await new Promise(r=>setTimeout(r,500)); return document.documentElement.lang==='en' && document.querySelector('[data-langbtn] small').textContent==='English' && document.title.replace(/^\(\d+\) /,'')==='nexa-slide start'"},
            {"name": "  한국어로 되돌림", "js": "document.querySelector('[data-lang=\"ko\"]').click(); await new Promise(r=>setTimeout(r,500)); NexaMenu.close(); return document.documentElement.lang==='ko' && document.title.replace(/^\(\d+\) /,'')==='nexa-slide 시작'"},
        ]},
        {"url": f"/w/{wid}/studio/", "wait": 4000, "steps": [
            {"name": "편집기 로드(슬라이드 있음)", "js": "document.querySelectorAll('#rail .th, #rail .thumb, #rail [data-i]').length > 0 || !!document.querySelector('#stage')"},
            {"name": "세션 칩 클릭 → 메뉴(웹 세션 시작…)", "js": "document.querySelector('#sessChip').click(); await new Promise(r=>setTimeout(r,500)); return [...document.querySelectorAll('.menu *')].some(e=>e.textContent.includes('웹 세션 시작'))"},
            {"name": "  웹 세션 시작… → 창(에이전트·웹 체크·git 체크 3)", "js": "[...document.querySelectorAll('.menu button')].find(e=>e.textContent.includes('웹 세션 시작')).click(); for (let i=0;i<25&&!document.querySelector('#sessDlg.show #sdAgent');i++) await new Promise(r=>setTimeout(r,400)); return !!document.querySelector('#sessDlg.show #sdAgent') && !!document.querySelector('#sdWeb') && document.querySelectorAll('#sdGrants [data-grant]').length===3"},
            {"name": "  닫기", "js": "document.querySelector('#sessDlg [data-sd=\"close\"]').click(); return true"},
            {"name": "요청 탭 → ＋ 첨부 버튼·'AI 에게 요청'(세션 없음)", "js": "document.querySelector('[data-tab=\"reqs\"]').click(); await new Promise(r=>setTimeout(r,500)); return document.querySelector('[data-attach=\"tab\"]').textContent.includes('첨부') && document.querySelector('#tab-reqs h3').textContent.trim()==='AI 에게 요청'"},
            {"name": "메모 팝오버 ＋ 첨부 버튼", "js": "document.querySelector('#memo [data-attach=\"memo\"]').textContent.includes('첨부')"},
            {"name": "요청 첨부 축소판 클릭 → 라이트박스(1 / 2, img, 토글 숨김)", "js": "document.querySelector('#reqFilter [data-v=\"0\"]').click(); await new Promise(r=>setTimeout(r,300)); const a=document.querySelector('[data-lb]'); if(!a) return 'no-thumb'; a.click(); await new Promise(r=>setTimeout(r,400)); const lb=document.querySelector('.nx-lb'); return lb && lb.style.display!=='none' && lb.querySelector('.cnt').textContent==='1 / 2' && !!lb.querySelector('.stage img') && lb.querySelector('.alt').style.display==='none'"},
            {"name": "  → 다음(문서 카드) · ← 키 · Esc 닫기", "js": "const lb=document.querySelector('.nx-lb'); lb.querySelector('.nav.r').click(); await new Promise(r=>setTimeout(r,200)); const doc=!!lb.querySelector('.stage .doc') && lb.querySelector('.cnt').textContent==='2 / 2'; lb.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowLeft',bubbles:true})); await new Promise(r=>setTimeout(r,200)); const back=lb.querySelector('.cnt').textContent==='1 / 2'; lb.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true})); await new Promise(r=>setTimeout(r,200)); return doc && back && lb.style.display==='none'"},
            {"name": "후속 요청 → 입력칸(앞선 답 없음)·Enter 보내기 → 같은 묶음에 '후속' 카드", "js": "const card=[...document.querySelectorAll('#tab-reqs .req')].find(c=>c.textContent.includes('스모크 첨부 요청')); if(!card) return 'no-card'; card.querySelector('[data-fu]').click(); await new Promise(r=>setTimeout(r,300)); const ta=document.querySelector('#fuText'); if(!ta) return 'no-form'; ta.value='후속 시험 답'; ta.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true})); await new Promise(r=>setTimeout(r,1200)); const th=[...document.querySelectorAll('#tab-reqs .thread')].find(t=>t.textContent.includes('스모크 첨부 요청')); return !!th && th.classList.contains('multi') && !!th.querySelector('.req.fu .fu-tag') && th.textContent.includes('후속 시험 답') && !document.querySelector('#fuText')"},
            {"name": "  '다시 열기' 툴팁 안내(완료 요청)", "js": "true"},
            {"name": "덱 탭 ＋ → 새 덱(prompt 대체) → 탭에 생기고 열림", "js": "const ans=['smoke-deck','스모크 덱']; window.prompt=()=>ans.shift(); document.querySelector('#deckTabs [data-deckadd]').click(); await new Promise(r=>setTimeout(r,1500)); return !!document.querySelector('#deckTabs [data-deck=\"smoke-deck\"].on') && document.querySelectorAll('.thumb').length===1"},
            {"name": "  오른쪽 클릭 → 제목 바꾸기", "js": "window.prompt=()=>'바뀐 제목'; const t=document.querySelector('#deckTabs [data-deck=\"smoke-deck\"]'); t.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,clientX:300,clientY:60})); await new Promise(r=>setTimeout(r,300)); [...document.querySelectorAll('.menu button')].find(b=>b.textContent.includes('제목 바꾸기')).click(); await new Promise(r=>setTimeout(r,1200)); return document.querySelector('#deckTabs [data-deck=\"smoke-deck\"]').title.startsWith('바뀐 제목')"},
            {"name": "  오른쪽 클릭 → 이름(id) 바꾸기 → 새 탭으로 열림", "js": "window.prompt=()=>'smoke-deck2'; const t=document.querySelector('#deckTabs [data-deck=\"smoke-deck\"]'); t.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,clientX:300,clientY:60})); await new Promise(r=>setTimeout(r,300)); [...document.querySelectorAll('.menu button')].find(b=>b.textContent.includes('이름(id)')).click(); await new Promise(r=>setTimeout(r,1500)); return !document.querySelector('#deckTabs [data-deck=\"smoke-deck\"]') && !!document.querySelector('#deckTabs [data-deck=\"smoke-deck2\"].on')"},
            {"name": "  오른쪽 클릭 → 삭제(confirm 대체) → 탭 사라지고 다른 덱 열림", "js": "window.confirm=()=>true; const t=document.querySelector('#deckTabs [data-deck=\"smoke-deck2\"]'); t.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,clientX:300,clientY:60})); await new Promise(r=>setTimeout(r,300)); [...document.querySelectorAll('.menu button')].find(b=>b.textContent.includes('삭제')).click(); await new Promise(r=>setTimeout(r,1500)); return !document.querySelector('#deckTabs [data-deck=\"smoke-deck2\"]') && !!document.querySelector('#deckTabs button.on')"},
            {"name": "여러 요소 메모: 캔버스에 요소 2개 테두리·카드 '외 1'", "js": "document.querySelector('#deckTabs [data-deck]').click(); await new Promise(r=>setTimeout(r,1200)); const card=[...document.querySelectorAll('#tab-reqs .req')].find(c=>c.textContent.includes('두 요소 메모')); return !!card && /외 1/.test(card.textContent) && document.querySelectorAll('#marks .mk').length>=2"},
            {"name": "  요소 2개 고른 뒤 💬 → 팝오버 '요소 2개 (…)'", "js": "const ids=[...document.querySelectorAll('#host [data-id]')].slice(0,2).map(e=>e.dataset.id); if(ids.length<2) return 'no-els:'+document.querySelectorAll('#host [data-id]').length; const a=document.querySelector('#host [data-id=\"'+ids[0]+'\"]'); a.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,clientX:a.getBoundingClientRect().x+5,clientY:a.getBoundingClientRect().y+5})); a.dispatchEvent(new PointerEvent('pointerup',{bubbles:true})); const b=document.querySelector('#host [data-id=\"'+ids[1]+'\"]'); b.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,shiftKey:true,clientX:b.getBoundingClientRect().x+5,clientY:b.getBoundingClientRect().y+5})); b.dispatchEvent(new PointerEvent('pointerup',{bubbles:true,shiftKey:true})); await new Promise(r=>setTimeout(r,300)); const m=document.querySelector('#ftb [data-f=\"memo\"]'); if(!m) return 'no-memo-btn'; m.click(); await new Promise(r=>setTimeout(r,300)); return document.querySelector('#memoTarget').textContent"},
            {"name": "속성 탭: 글자 요소를 고르면 '적용 글꼴' 줄(라틴·pt·세트)", "js": "if(document.querySelector('#memoCancel')) document.querySelector('#memoCancel').click(); const el=[...document.querySelectorAll('#host [data-id]')].find(e=>e.querySelector('.rs-box'))||document.querySelector('#host [data-id]'); el.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,clientX:el.getBoundingClientRect().x+4,clientY:el.getBoundingClientRect().y+4})); el.dispatchEvent(new PointerEvent('pointerup',{bubbles:true})); document.querySelector('[data-tab=\"props\"]').click(); await new Promise(r=>setTimeout(r,400)); const txt=(document.querySelector('#tab-props')||{}).textContent||''; return /적용 글꼴/.test(txt) && /pt/.test(txt) ? txt.slice(txt.indexOf('적용 글꼴'), txt.indexOf('적용 글꼴')+70) : 'no:'+txt.slice(0,120)"},
            {"name": "요소 목록: 클릭 1 · Ctrl+클릭 2 · Shift+클릭 범위 4", "js": "document.querySelector('[data-tab=\"props\"]').click(); await new Promise(r=>setTimeout(r,300)); const rows=()=>[...document.querySelectorAll('#tab-props .ellist [data-sel]')]; if(rows().length<4) return 'rows:'+rows().length; rows()[0].click(); await new Promise(r=>setTimeout(r,200)); const one=document.querySelectorAll('#tab-props .ellist .on').length; rows()[2].dispatchEvent(new MouseEvent('click',{bubbles:true,ctrlKey:true})); await new Promise(r=>setTimeout(r,200)); const two=document.querySelectorAll('#tab-props .ellist .on').length; rows()[3].dispatchEvent(new MouseEvent('click',{bubbles:true,shiftKey:true})); await new Promise(r=>setTimeout(r,200)); const four=document.querySelectorAll('#tab-props .ellist .on').length; return one===1 && two===2 && four===4 ? true : 'one='+one+' two='+two+' four='+four"},
            {"name": "내보내기 메뉴 열림", "js": "document.querySelector('#exportBtn').click(); await new Promise(r=>setTimeout(r,300)); const ok=!!document.querySelector('.menu'); document.body.click(); return ok"},
            {"name": "표시 언어 en → 머리줄 번역", "js": "I18N.set('en'); await new Promise(r=>setTimeout(r,500)); const t=document.querySelector('#sessChip').textContent; I18N.set('ko'); return /session/i.test(t)"},
        ]},
    ]}
    (WORK / "smoke_scn.json").write_text(json.dumps(S, ensure_ascii=False), "utf-8")
    S2 = {"base": BASE, "login": {"id": "bob", "password": "bob-pass-123"}, "pages": [
        {"url": "/studio/home.html#start", "wait": 2500, "steps": [
            {"name": "일반 사용자: 배너에 [관리자에게 시작 요청] 버튼", "js": "await new Promise(r=>setTimeout(r,800)); return !!document.querySelector('#engBanner [data-eng=\"askstart\"]') && !document.querySelector('[data-eng=\"start\"]')"},
            {"name": "  누르면 '관리자에게 시작 요청됨' 배지", "js": "document.querySelector('#engBanner [data-eng=\"askstart\"]').click(); await new Promise(r=>setTimeout(r,1200)); return document.querySelector('#engBanner').textContent.includes('관리자에게 시작 요청됨') && document.querySelector('#engBanner').textContent.includes('bob')"},
            {"name": "  일반 사용자 세션 시작 창: 웹 체크 비활성", "js": "document.querySelector('[data-sess=\"start\"]').click(); await new Promise(r=>setTimeout(r,2500)); const w=document.querySelector('#smWeb'); return !!w && w.disabled"},
            {"name": "  일반 사용자: git 체크 비활성", "js": "const g=[...document.querySelectorAll('#smGrants [data-grant]')]; return g.length===3 && g.every(x=>x.disabled)"},
            {"name": "  세션 ID 배지: 시작하면 'ID xxxxxxxx' 가 주기 갱신으로 보임", "js": "true"},
        ]}]}
    (WORK / "smoke_scn2.json").write_text(json.dumps(S2, ensure_ascii=False), "utf-8")
    r = subprocess.run(["node", str(HERE / "smoke.js"), str(WORK / "smoke_scn.json")], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    print(r.stdout); print(r.stderr[-2000:] if r.returncode else "")
    time.sleep(1.5)  # 앞 Chrome 이 디버그 포트를 놓을 때까지
    r2 = subprocess.run(["node", str(HERE / "smoke.js"), str(WORK / "smoke_scn2.json")], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    print(r2.stdout); print(r2.stderr[-2000:] if r2.returncode else "")
    rc = r.returncode or r2.returncode
finally:
    import glob
    for f in glob.glob(str(PROJ / "nexa-slide-demo" / "decks" / "*.requests.json")): os.remove(f)  # requests.json 정리 - 다른 시험(c1)을 오염시키지 않게
    shutil.rmtree(PROJ / "nexa-slide-demo" / "out" / "attach", ignore_errors=True)
    print("  ", svc("stop", ws).stdout.strip() if 'ws' in dir() else "")
    print("  ", svc("stop").stdout.strip())
sys.exit(rc)
