# -*- coding: utf-8 -*-
"""다국어 런타임 스캔 - 편집기(작업 공간 서버 5667)와 시작 페이지(격리 허브 5798)를 영어(?lang=en)로 띄워 여러 화면 상태에서
아직 한글로 남은 텍스트 노드·title·placeholder·option 을 모아 보고한다(슬라이드 안 글·덱 이름 같은 데이터는 뺀다).
    python3 studio/tests/i18n_scan.py            편집기 + 시작 페이지
    python3 studio/tests/i18n_scan.py editor     편집기만 · home = 시작 페이지만
보고: 남은 문구를 화면 상태와 함께 찍고 studio/tests/out/i18n_scan.json 에 둔다. 사전은 studio/i18n/en.js 에 더한다(docs/dev/i18n.md)."""
import http.cookiejar, json, os, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path
for _s in (sys.stdout, sys.stderr): _s.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
STUDIO = HERE.parent
sys.path.insert(0, str(HERE))
import editor_ui_test as E  # noqa: E402

COLLECT = r"""
const out=new Set(); const SKIP=new Set(['SCRIPT','STYLE','TEXTAREA','CODE','PRE','KBD']);
const data=(el)=>el.closest && el.closest('#host, .thumb, .rs-slide, .ad-vp, .pv-vp, #pngWrap');
const vis=(el)=>{ if(!el||!el.getBoundingClientRect) return false; const r=el.getBoundingClientRect(); if(r.width===0&&r.height===0) return false; let p=el; while(p&&p!==document.body){ const cs=getComputedStyle(p); if(cs.display==='none'||cs.visibility==='hidden') return false; p=p.parentElement;} return true; };
const w=document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT|NodeFilter.SHOW_ELEMENT);
let n; while((n=w.nextNode())){ if(n.nodeType===1){ if(data(n)||!vis(n)) continue; for(const a of ['title','placeholder','aria-label']){ const v=n.getAttribute&&n.getAttribute(a); if(v&&/[가-힣]/.test(v)) out.add('@'+a+' '+v.trim()); } if(n.tagName==='OPTION'&&/[가-힣]/.test(n.textContent)) out.add('<option> '+n.textContent.trim()); }
 else { const p=n.parentNode; if(!p||SKIP.has(p.tagName)||data(p)||!vis(p)) continue; const v=n.nodeValue; if(/[가-힣]/.test(v)) out.add(v.trim()); } }
return JSON.stringify([...out]);
"""
W = "await new Promise(r=>setTimeout(r,400));"


def step(name, js):
    return {"name": name, "dump": True, "js": js + "\nawait new Promise(r=>setTimeout(r,300));" + COLLECT}


def run_smoke(sc, name):
    scp = HERE / "out" / f"i18n_{name}.json"; scp.parent.mkdir(exist_ok=True)
    scp.write_text(json.dumps(sc, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run(["node", str(HERE / "smoke.js"), str(scp)], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(HERE))
    found = {}
    for line in (r.stdout or "").splitlines():
        if line.startswith(("OK", "FAIL")) and "→" in line:
            nm, _, rest = line.partition(" → ")
            try:
                arr = json.loads(rest[rest.index("["):])
            except Exception:  # noqa: BLE001
                print("??", line[:200]); continue
            for s in arr:
                found.setdefault(s, []).append(nm.replace("OK   ", "").replace("FAIL ", "").strip())
        elif line.startswith("FAIL"):
            print(line[:300])
    return found


def scan_editor():
    close = "document.body.click();"
    steps = [
        step("편집기 기본(선택 없음)", ""),
        step("표 선택", f"document.querySelector('[data-sel=\"e01\"]').click();{W}"),
        step("글머리 선택", f"document.querySelector('[data-sel=\"e02\"]').click();{W}"),
        step("요청 탭", f"document.querySelector('[data-tab=\"reqs\"]').click();{W}"),
        step("요청 기록 창", f"document.querySelector('#reqMore').click();{W}"),
        step("기록 탭", f"document.querySelector('#reqHist input').dispatchEvent(new KeyboardEvent('keydown',{{key:'Escape',bubbles:true}}));{W}document.querySelector('[data-tab=\"hist\"]').click();{W}"),
        step("변경 탭", f"document.querySelector('[data-tab=\"chg\"]').click();{W}"),
        step("속성 탭", f"document.querySelector('[data-tab=\"props\"]').click();{W}"),
        step("더보기 메뉴", f"document.querySelector('#moreBtn').click();{W}"),
        step("내보내기 메뉴", f"{close}{W}document.querySelector('#exportBtn').click();{W}"),
        step("세션 칩 메뉴", f"{close}{W}document.querySelector('#sessChip').click();{W}"),
        step("삽입 패널", f"{close}{W}document.querySelector('#addBtn').click();{W}"),
        step("명령 팔레트", f"{close}{W}document.dispatchEvent(new KeyboardEvent('keydown',{{key:'k',ctrlKey:true,bubbles:true}}));{W}"),
        step("단축키 도움말", f"document.querySelector('#cmdpal input').dispatchEvent(new KeyboardEvent('keydown',{{key:'Escape',bubbles:true}}));{W}document.dispatchEvent(new KeyboardEvent('keydown',{{key:'?',bubbles:true}}));{W}"),
        step("슬라이드 추가 창", f"document.querySelector('#help') && document.querySelector('#help').classList.remove('show');{W}const b=[...document.querySelectorAll('button')].find(x=>/새 슬라이드|New slide/.test(x.textContent)); if(b) b.click();{W}"),
        step("오른쪽 클릭 메뉴", f"document.querySelector('#addDlg') && document.querySelector('#addDlg').classList.remove('show');{W}const el=document.querySelector('#host .rs-el'); el.dispatchEvent(new MouseEvent('contextmenu',{{bubbles:true,clientX:300,clientY:300}}));{W}"),
        step("글꼴 창", f"{close}{W}const c=document.querySelector('#fontChip, [data-f=\"fonts\"]'); const b=[...document.querySelectorAll('#moreBtn')]; if(b[0]) {{ b[0].click(); {W} const it=[...document.querySelectorAll('.menu button')].find(x=>/글꼴|font/i.test(x.textContent)); if(it) it.click(); }}{W}"),
    ]
    steps_fx = [
        step("그림 선택", f"document.querySelector('[data-sel=\"e05\"]').click();{W}"),
        step("상자 선택", f"document.querySelector('[data-sel=\"e02\"]').click();{W}"),
        step("링크 메뉴", f"document.querySelector('#ftb [data-f=\"link\"]').click();{W}"),
        step("회전 메뉴", f"{close}{W}document.querySelector('#ftb [data-f=\"rot\"]').click();{W}"),
        step("위치 조정 메뉴", f"{close}{W}document.querySelector('#ftb [data-f=\"pos\"]').click();{W}"),
        step("자르기 메뉴", f"{close}{W}document.querySelector('[data-sel=\"e05\"]').click();{W}document.querySelector('#ftb [data-f=\"crop\"]').click();{W}"),
    ]
    sc = {"base": f"http://127.0.0.1:{E.PORT}", "pages": [
        {"url": "/studio/?lang=en#tbltest/1", "wait": 2500, "steps": steps},
        {"url": "/studio/?lang=en#fxtest/1", "wait": 2500, "steps": steps_fx},
        {"url": "/studio/?lang=en#shapetest/1", "wait": 2500, "steps": [step("도형 선택", f"document.querySelector('[data-sel=\"e01\"]').click();{W}")]},
        {"url": "/studio/presenter.html?lang=en&deck=fxtest", "wait": 2000, "steps": [step("발표자 보기", "")]},
        {"url": "/studio/fonts.html?lang=en", "wait": 2000, "steps": [step("글꼴 페이지", "")]},
    ]}
    E.fixture()
    srv = subprocess.Popen([sys.executable, str(STUDIO / "server.py"), "--workspace", str(E.WS), "--port", str(E.PORT)], env=E.ENV, cwd=str(E.WS), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{E.PORT}/api/decks", timeout=2).read(); break
            except Exception:  # noqa: BLE001
                time.sleep(0.5)
        return run_smoke(sc, "editor")
    finally:
        srv.terminate()


def scan_home():
    WORK = Path(os.environ.get("NEXA_TEST_DIR") or Path(tempfile.gettempdir()) / "nexa-slide-tests") / "i18n"
    USER, PROJ, PORT = WORK / "user", WORK / "projects", 5798
    for d in (USER, PROJ):
        d.mkdir(parents=True, exist_ok=True)
    BASE = f"http://127.0.0.1:{PORT}"
    ENV = {**os.environ, "NEXA_SLIDE_USER_DIR": str(USER), "NEXA_SLIDE_PROJECTS": str(PROJ), "PYTHONIOENCODING": "utf-8"}; ENV.pop("NEXA_SLIDE_WORKSPACE", None)
    svc = lambda cmd: subprocess.run([sys.executable, str(STUDIO / "service.py"), cmd], env=ENV, cwd=str(USER), capture_output=True, text=True, encoding="utf-8")  # noqa: E731
    (USER / "settings.json").write_text(json.dumps({"hubPort": PORT, "hubProxy": True, "engine": str(STUDIO.parent), "sessionAllowGit": True}), encoding="utf-8")
    (USER / "users.json").unlink(missing_ok=True)
    print(svc("start").stdout.strip()[:120])
    close = "document.querySelectorAll('.modal-back.on').forEach(m=>m.classList.remove('on'));"
    steps = [
        step("시작 페이지", f"{W}{W}"),
        step("새로 만들기 - 제목·폴더 지정", f"const t=document.querySelector('#fTitle'); if(t){{t.value='My talk'; t.dispatchEvent(new Event('input',{{bubbles:true}}));}}{W}const c=document.querySelector('[data-loc=\"custom\"], input[name=loc][value=custom]'); if(c) c.click();{W}"),
        step("설정 창", f"location.hash='#settings'; window.dispatchEvent(new HashChangeEvent('hashchange'));{W}{W}{W}"),
        step("설치 안내 창", f"{close}{W}const i=document.querySelector('[data-info]'); if(i) i.click();{W}{W}"),
        step("세션 시작 창", f"{close}{W}const s=document.querySelector('[data-sess=\"start\"]'); if(s) s.click();{W}{W}"),
        step("엔진 세션 시작 창", f"{close}{W}const s=document.querySelector('[data-eng=\"start\"]'); if(s) s.click();{W}{W}"),
        step("서버 작업 카드 ⋯ 메뉴", f"{close}{W}const s=document.querySelector('[data-eng=\"manualhow\"]'); if(s) s.click();{W}{W}"),
        step("폴더 고르기 창", f"{close}{W}document.body.click();{W}const b=document.querySelector('#fBrowse'); if(b) b.click();{W}{W}"),
        step("미리 보기 창", f"{close}{W}const b=document.querySelector('#fPreview'); if(b) b.click();{W}{W}{W}{W}"),
        step("기본 메뉴", f"{close}{W}document.querySelector('#menuBtn').click();{W}"),
    ]
    sc = {"base": BASE, "login": {"id": "admin", "password": "i18n-pass-123"}, "pages": [
        {"url": "/studio/home.html?lang=en#start", "wait": 2500, "steps": steps},
        {"url": "/studio/home.html?lang=en#tutorial", "wait": 2000, "steps": [step("튜토리얼", "")]},
        {"url": "/studio/home.html?lang=en#demo", "wait": 2000, "steps": [step("데모", "")]},
        {"url": "/studio/home.html?lang=en#templates", "wait": 2000, "steps": [step("템플릿", "")]},
        {"url": "/studio/home.html?lang=en#samples", "wait": 2000, "steps": [step("샘플", "")]},
        {"url": "/account?lang=en", "wait": 2000, "steps": [step("계정", "")]},  # 허브의 계정 페이지 경로(/studio/account.html 은 다른 화면으로 넘어간다)
        {"url": "/engine?lang=en", "wait": 2000, "steps": [step("서버 작업 목록", "")]},
        {"url": "/review?lang=en", "wait": 2500, "steps": [step("템플릿 검토", "")]},
        {"url": "/review/slides?lang=en", "wait": 2500, "steps": [step("슬라이드 유형 검토", "")]},
    ]}
    try:
        jar = http.cookiejar.CookieJar(); op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

        def req(method, url, body=None):
            h = {"Accept": "application/json", "Origin": BASE, "Content-Type": "application/json"}
            with op.open(urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, method=method, headers=h), timeout=120) as r:
                return json.loads(r.read())
        for _ in range(40):
            try:
                req("GET", BASE + "/api/home"); break
            except Exception:  # noqa: BLE001
                time.sleep(0.5)
        try:
            req("POST", BASE + "/api/auth/setup", {"id": "admin", "password": "i18n-pass-123"})
        except Exception as e:  # noqa: BLE001
            print("setup:", e)
        req("POST", BASE + "/api/project", {"action": "demo"})
        req("POST", BASE + "/api/engine/requests", {"action": "add", "title": "i18n 대기 요청", "body": "b"})
        return run_smoke(sc, "home")
    finally:
        print(svc("stop").stdout.strip()[:120])


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    found = {}
    if what in ("all", "editor"):
        found.update({k: ["편집기 · " + v[0]] for k, v in scan_editor().items()})
    if what in ("all", "home"):
        found.update({k: ["시작 페이지 · " + v[0]] for k, v in scan_home().items()})
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "i18n_scan.json").write_text(json.dumps(found, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"남은 한글 글: {len(found)}")
    for s in found:
        print(" ", repr(s)[:180], " <-", found[s][0])


if __name__ == "__main__":
    main()
