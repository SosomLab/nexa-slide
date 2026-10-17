# -*- coding: utf-8 -*-
"""0.22.25 검증 - 보기 전용 공유 링크(/s/<토큰>/, engine-request #2): 관리자 만들기 → 로그인 없이 200 · 덱 응답에 notes·hidden 없음 → 허용 밖 경로·POST 403
→ 비밀번호 오답 5회 잠금 → 회수 뒤 거부 → 만료(expires 과거) 거부 → 접근 로그에 토큰 원문 없음. 격리 허브(5799) + example 사본(저장소 밖)."""
import http.cookiejar
import json
import os
import shutil
import tempfile
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    _s.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
STUDIO = Path(__file__).resolve().parents[1]  # studio/ (이 파일은 studio/tests/)
ENGINE = STUDIO.parent
WORK = Path(os.environ.get("NEXA_TEST_DIR") or Path(tempfile.gettempdir()) / "nexa-slide-tests")  # 시험 산출물(사용자 설정·작업 공간) - 저장소 밖(허브는 엔진 안의 작업 공간을 거절한다)
for _d in (WORK / "user", WORK / "projects"):
    _d.mkdir(parents=True, exist_ok=True)
USER, PROJ, HUB_PORT = WORK / "user", WORK / "projects", 5799
BASE = f"http://127.0.0.1:{HUB_PORT}"
ENV = {**os.environ, "NEXA_SLIDE_USER_DIR": str(USER), "NEXA_SLIDE_PROJECTS": str(PROJ), "PYTHONIOENCODING": "utf-8"}
ENV.pop("NEXA_SLIDE_WORKSPACE", None)
FAILS = []
WS = PROJ / "share-example"
SHARE_FILE = USER / "hub" / "share.json"
SETTINGS = {"hubPort": HUB_PORT, "hubProxy": True, "engine": str(ENGINE)}
CHROME = Path("C:/Program Files/Google/Chrome/Application/chrome.exe")


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else extra)
    if not cond:
        FAILS.append(name)


def svc(cmd):
    return subprocess.run([sys.executable, str(STUDIO / "service.py"), cmd], env=ENV, cwd=str(USER), capture_output=True, text=True, encoding="utf-8")


def client():
    """쿠키 단지 하나 = 브라우저 하나. req → (status, json) · raw → (status, headers, bytes)."""
    jar = http.cookiejar.CookieJar()

    class NoRedirect(urllib.request.HTTPRedirectHandler):  # 302 를 따라가지 않고 그대로 본다(/s/<토큰> → /s/<토큰>/ 확인)
        def redirect_request(self, *a, **k):
            return None
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar), NoRedirect)

    def raw(method, url, body=None, headers=None):
        h = {"Accept": "application/json", "Origin": BASE, **(headers or {})}
        data = json.dumps(body).encode() if body is not None else None
        if data:
            h["Content-Type"] = "application/json"
        try:
            with op.open(urllib.request.Request(url, data=data, method=method, headers=h), timeout=120) as r:
                return r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read()

    def req(method, url, body=None, headers=None):
        st, _, b = raw(method, url, body, headers)
        try:
            return st, json.loads(b or b"{}")
        except ValueError:
            return st, {"_raw": b[:200]}
    req.raw = raw
    req.jar = jar
    return req


def fixture():
    """example 사본(저장소 밖) - 둘째 장에 notes, 셋째 장을 숨김으로, fonts/ 에 가짜 글꼴 파일(fontcss 접두 확인용)."""
    if WS.exists():
        shutil.rmtree(WS, ignore_errors=True)
    shutil.copytree(ENGINE / "example", WS, ignore=shutil.ignore_patterns("*.requests.json", ".history", "out"))
    dp = WS / "decks" / "demo.json"
    d = json.loads(dp.read_text(encoding="utf-8"))
    d["slides"][0]["notes"] = "첫 장 노트 - 공유 응답에 보이면 안 된다"
    d["slides"][1]["notes"] = d["slides"][1].get("notes") or "둘째 장 노트"
    d["slides"][2]["hidden"] = True
    dp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    (WS / "fonts").mkdir(exist_ok=True)
    (WS / "fonts" / "Dummy-Bold.ttf").write_bytes(b"not really a font")
    (WS / "nexa-slide.local.json").unlink(missing_ok=True)
    return len(d["slides"]), [s["id"] for s in d["slides"] if not s.get("hidden")]


(USER / "settings.json").write_text(json.dumps(SETTINGS), encoding="utf-8")
SHARE_FILE.unlink(missing_ok=True)
for _f in (USER / "hub" / "logs").glob("access-*.log"):
    _f.unlink(missing_ok=True)
total, visible = fixture()
ws_path = None
try:
    print(svc("start").stdout.strip())
    (USER / "users.json").unlink(missing_ok=True)
    admin = client()
    st, r = admin("POST", BASE + "/api/auth/setup", {"id": "admin", "password": "share-test-pass-1"})
    check("관리자 설정", st == 200, (st, r))
    st, r = admin("POST", BASE + "/api/project", {"action": "open", "path": str(WS)})
    check("example 사본 열기(작업 공간 서버 기동)", st == 200 and r.get("id"), (st, r))
    wid, ws_path = r.get("id"), r.get("path")
    st, r = admin("POST", BASE + "/api/auth/users", {"action": "add", "id": "bob", "password": "bob-pass-1234", "role": "user"})
    bob = client()
    st, r = bob("POST", BASE + "/api/auth/login", {"id": "bob", "password": "bob-pass-1234"})
    check("일반 사용자 bob 로그인", st == 200, (st, r))

    # ---------- 만들기(관리자) ----------
    st, r = admin("POST", BASE + "/api/share", {"action": "create", "ws": wid, "deck": "demo", "days": 7})
    check("관리자 공유 링크 만들기 → token·url·link", st == 200 and r.get("token") and r.get("url", "").startswith("/s/") and r["link"]["status"] == "ok", (st, r))
    tok, lid = r.get("token"), r.get("link", {}).get("id")
    url = BASE + r["url"]
    st, r = admin("POST", BASE + "/api/share", {"action": "create", "ws": wid, "deck": "demo", "days": 0})
    check("만료 0일 → 400", st == 400, (st, r))
    st, r = admin("POST", BASE + "/api/share", {"action": "create", "ws": wid, "deck": "demo", "days": 365})
    check("만료 365일(최대 90 초과) → 400", st == 400, (st, r))
    st, r = admin("POST", BASE + "/api/share", {"action": "create", "ws": wid, "deck": "nope", "days": 1})
    check("없는 덱 → 404", st == 404, (st, r))
    st, r = admin("POST", BASE + "/api/share", {"action": "create", "ws": "no-such-ws-000000", "deck": "demo"})
    check("모르는 작업 공간 → 404", st == 404, (st, r))
    st, r = admin("POST", BASE + "/api/share", {"action": "create", "ws": wid, "deck": "demo", "password": "abc"})
    check("비밀번호 3자 → 400", st == 400, (st, r))
    st, r = admin("GET", BASE + "/api/share")
    check("관리자 목록 1건·maxDays 90·canCreate", st == 200 and len(r.get("links", [])) == 1 and r.get("maxDays") == 90 and r.get("canCreate") is True and r.get("admin") is True, (st, r))
    check("  목록에 토큰 해시·비밀번호 없음", st == 200 and all("tokenHash" not in l and "pw" not in l for l in r.get("links", [])), r)

    # ---------- 로그인 없이 열람 ----------
    anon = client()
    st, h, b = anon.raw("GET", url, headers={"Accept": "text/html"})
    check("로그인 없이 /s/<토큰>/ → 200 view.html", st == 200 and "보기 전용 공유 링크 페이지".encode("utf-8") in b and "text/html" in h.get("Content-Type", ""), (st, h.get("Content-Type"), b[:120]))
    st, h, b = anon.raw("GET", BASE + f"/s/{tok}", headers={"Accept": "text/html"})
    check("/s/<토큰>(빗금 없음) → 302 /s/<토큰>/", st == 302 and h.get("Location", "").endswith(f"/s/{tok}/"), (st, h.get("Location")))
    st, r = anon("GET", url + "api/share/state")
    check("state: deck=demo · needPassword false", st == 200 and r.get("deck") == "demo" and r.get("needPassword") is False, (st, r))
    st, r = anon("GET", url + "api/deck/demo")
    check("/api/deck/demo → 200", st == 200 and isinstance(r.get("slides"), list), (st, str(r)[:200]))
    slides = r.get("slides", []) if st == 200 else []
    check("  응답에 notes 없음", slides and not any("notes" in s for s in slides) and "notes" not in r and "노트" not in json.dumps(r, ensure_ascii=False), [s.get("id") for s in slides if "notes" in s])
    check(f"  숨김 장 없음({total}장 중 {len(visible)}장) · 원래 번호 page", [s["id"] for s in slides] == visible and all(isinstance(s.get("page"), int) for s in slides) and slides[2]["page"] == 4, [(s.get("id"), s.get("page")) for s in slides])
    st, h, b = anon.raw("GET", url + "studio/tokens.json")
    check("tokens.json → 200 json", st == 200 and b.startswith(b"{"), (st, b[:60]))
    st, h, b = anon.raw("GET", url + "studio/render.js")
    check("render.js → 200", st == 200 and b"renderSlide" in b, st)
    st, h, b = anon.raw("GET", url + "studio/i18n/en.js")
    check("i18n/en.js → 200", st == 200, st)
    st, h, b = anon.raw("GET", url + "studio/fonts.css")
    check("fonts.css → 200", st == 200, st)
    st, h, b = anon.raw("GET", url + "api/fontcss")
    css = b.decode("utf-8", "replace")
    check("api/fontcss → 200, /wsfonts/ 앞에 /s/<토큰> 접두", st == 200 and f'url("/s/{tok}/wsfonts/Dummy-Bold.ttf")' in css, (st, css[:200]))
    st, h, b = anon.raw("GET", url + "wsfonts/Dummy-Bold.ttf")
    check("wsfonts/Dummy-Bold.ttf → 200", st == 200 and b == b"not really a font", (st, b[:40]))
    st, h, b = anon.raw("GET", url + "assets/brand/logo.png")
    check("덱이 참조하는 그림 assets/brand/logo.png → 200", st == 200 and h.get("Content-Type", "").startswith("image/"), (st, h.get("Content-Type")))
    st, h, b = anon.raw("HEAD", url + "assets/brand/logo.png")
    check("  HEAD 도 200", st == 200, st)

    # ---------- 허용 밖 ----------
    for p in ("api/decks", "api/deck/other", "api/config", "api/version/demo", "nexa-slide.json", "decks/demo.json", "studio/index.html", "studio/", "studio/view.html", "out/demo.pptx", "assets/", "api/share"):
        st, r = anon("GET", url + p)
        check(f"허용 밖 GET {p} → 403", st == 403, (st, r))
    st, r = anon("POST", url + "api/deck/demo", {"x": 1})
    check("POST /api/deck/demo → 403", st == 403, (st, r))
    st, r = anon("PUT", url + "api/deck/demo", {"title": "hack"})
    check("PUT /api/deck/demo → 403", st == 403, (st, r))
    st, r = anon("POST", url + "api/requests/demo", {"action": "add"})
    check("POST /api/requests → 403", st == 403, (st, r))
    st, r = anon("DELETE", url + "api/deck/demo")
    check("DELETE → 403", st == 403, (st, r))
    st, r = anon("GET", BASE + "/api/share")
    check("토큰 없이 허브 /api/share → 401(로그인)", st == 401, (st, r))
    st, r = anon("GET", BASE + f"/w/{wid}/api/deck/demo")
    check("토큰 쿠키로 /w/ 중계는 못 연다 → 401", st == 401, (st, r))
    d2 = json.loads((WS / "decks" / "demo.json").read_text(encoding="utf-8"))
    check("원본 덱 파일 불변(노트·숨김 그대로)", d2["slides"][0].get("notes") and d2["slides"][2].get("hidden") is True)

    # ---------- 잘못된 토큰 ----------
    st_bad, h_bad, b_bad = anon.raw("GET", BASE + "/s/" + "x" * 43 + "/", headers={"Accept": "text/html"})
    check("잘못된 토큰 → 404 안내 페이지", st_bad == 404 and "열 수 없습니다".encode("utf-8") in b_bad, (st_bad, b_bad[:100]))
    st, h, b = anon.raw("GET", BASE + "/s/short/", headers={"Accept": "text/html"})
    check("형식 안 맞는 토큰 → 404 같은 본문", st == 404 and b == b_bad, (st, b[:80]))
    st, h, b = anon.raw("GET", BASE + "/s/" + "x" * 43 + "/api/deck/demo")
    check("잘못된 토큰의 API 경로도 404 같은 본문", st == 404 and b == b_bad, st)

    # ---------- 비밀번호 링크 ----------
    st, r = admin("POST", BASE + "/api/share", {"action": "create", "ws": wid, "deck": "demo", "days": 1, "password": "view-pass-9"})
    check("비밀번호 링크 만들기", st == 200 and r["link"]["hasPassword"] is True, (st, r))
    tok2, lid2, url2 = r["token"], r["link"]["id"], BASE + r["url"]
    pwc = client()
    st, h, b = pwc.raw("GET", url2, headers={"Accept": "text/html"})
    check("비밀번호 링크 페이지는 200(입력 화면)", st == 200 and b"gateForm" in b, st)
    st, r = pwc("GET", url2 + "api/share/state")
    check("  state needPassword true", st == 200 and r.get("needPassword") is True, (st, r))
    st, r = pwc("GET", url2 + "api/deck/demo")
    check("  비밀번호 전 덱 → 401 password", st == 401 and r.get("error") == "password", (st, r))
    st, r = pwc("GET", url2 + "studio/tokens.json")
    check("  비밀번호 전 tokens.json → 401", st == 401, (st, r))
    st, r = pwc("POST", url2 + "api/share/auth", {"password": "wrong"}, headers={"Origin": "http://evil.example"})
    check("  다른 출처 POST → 403", st == 403, (st, r))
    codes = [pwc("POST", url2 + "api/share/auth", {"password": f"wrong-{i}"})[0] for i in range(5)]
    check("  오답 5회 → 401 ×5", codes == [401] * 5, codes)
    st, r = pwc("POST", url2 + "api/share/auth", {"password": "wrong-6"})
    check("  6회째 → 429 잠금", st == 429, (st, r))
    st, r = pwc("POST", url2 + "api/share/auth", {"password": "view-pass-9"})
    check("  잠긴 동안 정답도 429", st == 429, (st, r))
    st, r = pwc("GET", url2 + "api/share/state")
    check("  state locked > 0", st == 200 and r.get("locked", 0) > 0, r)
    st, r = admin("POST", BASE + "/api/share", {"action": "create", "ws": wid, "deck": "demo", "days": 1, "password": "view-pass-9"})
    tok3, lid3, url3 = r["token"], r["link"]["id"], BASE + r["url"]
    pw3 = client()
    st, r = pw3("POST", url3 + "api/share/auth", {"password": "nope-1234"})
    check("다른 비밀번호 링크(잠금은 링크별): 오답 1회 401", st == 401, (st, r))
    st, h, b = pw3.raw("POST", url3 + "api/share/auth", {"password": "view-pass-9"})
    ck = h.get("Set-Cookie", "")
    check("  정답 → 200 + Set-Cookie nexa_share(Path=/s/<토큰>/, HttpOnly, SameSite=Lax)", st == 200 and ck.startswith("nexa_share=") and f"Path=/s/{tok3}/" in ck and "HttpOnly" in ck and "SameSite=Lax" in ck, (st, ck[:160]))
    check("  쿠키 값(id.만료.서명)에 토큰 원문 없음", tok3 not in ck.split(";")[0], ck.split(";")[0])
    st, r = pw3("GET", url3 + "api/share/state")
    check("  이제 needPassword false", st == 200 and r.get("needPassword") is False, r)
    st, r = pw3("GET", url3 + "api/deck/demo")
    check("  덱 200 · notes 없음", st == 200 and not any("notes" in s for s in r.get("slides", [])), (st, str(r)[:100]))
    st, r = pwc("GET", url2 + "api/deck/demo")
    check("  그 쿠키는 다른 링크(url2)에는 안 붙는다(Path) → 401", st == 401, (st, r))
    pw4 = client()
    pw4.jar.set_cookie(http.cookiejar.Cookie(0, "nexa_share", ck.split(";")[0].split("=", 1)[1], None, False, "127.0.0.1", False, False, f"/s/{tok2}/", True, False, None, False, None, None, {}))
    st, r = pw4("GET", url2 + "api/deck/demo")
    check("  url3 의 쿠키 값을 url2 에 옮겨 붙여도 401(id·서명 불일치)", st == 401, (st, r))

    # ---------- 회수 ----------
    st, r = bob("POST", BASE + f"/api/share/{lid}", {"action": "revoke"})
    check("bob 이 관리자 링크 회수 → 403", st == 403, (st, r))
    st, r = bob("GET", BASE + "/api/share")
    check("bob 목록은 비어 있음(내 것만)·admin false", st == 200 and r.get("links") == [] and r.get("admin") is False, (st, r))
    st, r = bob("POST", BASE + "/api/share", {"action": "create", "ws": wid, "deck": "demo", "days": 2})
    check("bob 만들기(shareCreate any) → 200", st == 200, (st, r))
    lid_b, tok_b = r["link"]["id"], r["token"]
    st, r = bob("GET", BASE + f"/api/share?ws={wid}&deck=demo")
    check("  bob 목록 1건(자기 것)", st == 200 and [l["id"] for l in r.get("links", [])] == [lid_b], (st, r))
    st, r = admin("GET", BASE + "/api/share")
    check("  관리자 목록 4건(전체)", st == 200 and len(r.get("links", [])) == 4 and any(l["by"] == "bob" for l in r["links"]), (st, len(r.get("links", []))))
    st, r = bob("POST", BASE + f"/api/share/{lid_b}", {"action": "revoke"})
    check("bob 자기 링크 회수 → 200 revoked", st == 200 and r["link"]["status"] == "revoked", (st, r))
    st, h, b = client().raw("GET", BASE + f"/s/{tok_b}/", headers={"Accept": "text/html"})
    check("  회수된 링크 → 410, 잘못된 토큰과 같은 본문", st == 410 and b == b_bad, (st, b[:80]))
    st, r = admin("POST", BASE + f"/api/share/{lid}", {"action": "revoke"})
    check("관리자 회수 → 200", st == 200 and r["link"]["status"] == "revoked", (st, r))
    st, r = anon("GET", url + "api/deck/demo")
    check("  회수 뒤 덱 → 410", st == 410, (st, str(r)[:80]))
    st, h, b = anon.raw("GET", url, headers={"Accept": "text/html"})
    check("  회수 뒤 페이지 → 410 같은 본문", st == 410 and b == b_bad, st)
    st, r = admin("POST", BASE + f"/api/share/{lid}", {"action": "revoke"})
    check("  다시 회수해도 200(멱등)", st == 200 and r["link"]["status"] == "revoked", (st, r))
    st, r = admin("POST", BASE + "/api/share/zzzzzzzz", {"action": "revoke"})
    check("없는 링크 회수 → 404", st == 404, (st, r))

    # ---------- 만료 - share.json 의 expires 를 과거로 ----------
    data = json.loads(SHARE_FILE.read_text(encoding="utf-8"))
    data["links"][lid3]["expires"] = time.time() - 60
    SHARE_FILE.write_text(json.dumps(data), encoding="utf-8")
    st, h, b = pw3.raw("GET", url3, headers={"Accept": "text/html"})
    check("만료된 링크 → 410 같은 본문", st == 410 and b == b_bad, (st, b[:80]))
    st, r = pw3("GET", url3 + "api/deck/demo")
    check("  만료 뒤 덱(쿠키 있어도) → 410", st == 410, st)
    st, r = admin("GET", BASE + "/api/share")
    check("  목록 status expired", any(l["id"] == lid3 and l["status"] == "expired" for l in r.get("links", [])), r.get("links"))
    check("  share.json 에 토큰 원문 없음", not any(t in SHARE_FILE.read_text(encoding="utf-8") for t in (tok, tok2, tok3, tok_b)))

    # ---------- 정책 shareCreate: admin ----------
    (USER / "settings.json").write_text(json.dumps({**json.loads((USER / "settings.json").read_text(encoding="utf-8")), "shareCreate": "admin", "shareMaxDays": 10}), encoding="utf-8")
    st, r = bob("POST", BASE + "/api/share", {"action": "create", "ws": wid, "deck": "demo", "days": 1})
    check("shareCreate admin: bob 만들기 → 403", st == 403, (st, r))
    st, r = bob("GET", BASE + "/api/share")
    check("  bob canCreate false", st == 200 and r.get("canCreate") is False, r)
    st, r = admin("POST", BASE + "/api/share", {"action": "create", "ws": wid, "deck": "demo", "days": 30})
    check("  shareMaxDays 10: 관리자 30일 → 400", st == 400, (st, r))
    st, r = admin("POST", BASE + "/api/share", {"action": "create", "ws": wid, "deck": "demo"})
    check("  관리자 기본 7일 → 200", st == 200, (st, r))
    tok5 = r["token"]
    for l in admin("GET", BASE + "/api/share")[1].get("links", []):
        if l["status"] == "ok":
            admin("POST", BASE + f"/api/share/{l['id']}", {"action": "revoke"})

    # ---------- Chrome: view.html 콘솔 오류 0 (있을 때만) ----------
    if CHROME.is_file() and shutil.which("node"):
        s = (USER / "settings.json"); s.write_text(json.dumps({**json.loads(s.read_text(encoding="utf-8")), "shareCreate": "any"}), encoding="utf-8")
        st, r = admin("POST", BASE + "/api/share", {"action": "create", "ws": wid, "deck": "demo", "days": 1})
        tok6, lid6 = r["token"], r["link"]["id"]
        sc = {"base": BASE, "ignoreErrors": "fontfile|wsfonts|Dummy|OTS", "pages": [{"url": f"/s/{tok6}/", "wait": 2500, "steps": [
            {"name": "슬라이드 한 장 렌더", "js": "document.querySelectorAll('#st .rs-slide').length === 1 && document.body.dataset.ready === '1'"},
            {"name": f"쪽 번호 1 / {len(visible)}", "js": f"document.querySelector('#pos').textContent.trim() === '1 / {len(visible)}'"},
            {"name": "→ 키로 다음 장", "js": "document.dispatchEvent(new KeyboardEvent('keydown', {key: 'ArrowRight'})); await new Promise(r => setTimeout(r, 300)); return document.querySelector('#pos').textContent.trim().startsWith('2 /') && location.hash === '#2'"},
            {"name": "End 키로 마지막 장", "js": f"document.dispatchEvent(new KeyboardEvent('keydown', {{key: 'End'}})); await new Promise(r => setTimeout(r, 300)); return document.querySelector('#pos').textContent.trim() === '{len(visible)} / {len(visible)}'"},
            {"name": "노트·편집 UI 없음", "js": "!document.querySelector('#presentNotes, #notes, textarea, [contenteditable]')"},
            {"name": "그림이 공유 접두로 읽힘", "js": "[...document.querySelectorAll('#st img')].every(i => i.getAttribute('src').startsWith(location.pathname))"},
        ]}]}
        scf = WORK / "share_smoke.json"
        scf.write_text(json.dumps(sc, ensure_ascii=False), encoding="utf-8")
        pr = subprocess.run(["node", str(HERE / "smoke.js"), str(scf)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
        out = (pr.stdout or "") + (pr.stderr or "")
        print("\n".join("   " + l for l in out.splitlines() if l.strip()))
        check("Chrome view.html 콘솔 오류 0·단계 통과", pr.returncode == 0, out[-400:])
        admin("POST", BASE + f"/api/share/{lid6}", {"action": "revoke"})
        toks = (tok, tok2, tok3, tok_b, tok5, tok6)
    else:
        print("SKIP Chrome 또는 node 없음 - view.html 화면 확인 생략")
        toks = (tok, tok2, tok3, tok_b, tok5)

    # ---------- 접근 로그 ----------
    time.sleep(0.5)
    logs = "".join(p.read_text(encoding="utf-8", errors="replace") for p in sorted((USER / "hub" / "logs").glob("access-*.log")))
    check("접근 로그에 토큰 원문 없음", logs and not any(t in logs for t in toks))
    for ev in (f"share.create:{lid}", f"share.view:{lid}", f"share.denied:{lid}:path", f"share.denied:{lid}:method", f"share.revoke:{lid}", f"share.denied:{lid}:revoked",
               f"share.auth.fail:{lid2}", f"share.auth.locked:{lid2}", f"share.auth:{lid3}", f"share.denied:{lid3}:expired", "share.denied:-:unknown", f"share.denied:{lid}:owner", "share.denied:-:policy"):
        check(f"  로그 이벤트 {ev}", f'"event":"{ev}"' in logs)
    check("  공유 요청 줄의 user=share:<id>·path=/s/<id>/…", f'"path":"/s/{lid}/api/decks"' in logs and f'"user":"share:{lid}"' in logs)
    check("  share.json 경로 밖 토큰 없음(settings·users)", not any(t in (USER / "settings.json").read_text(encoding="utf-8") for t in toks))
finally:
    try:
        if ws_path:
            admin("POST", BASE + "/api/project", {"action": "stop", "path": ws_path})
    except Exception:  # noqa: BLE001
        pass
    print("  ", svc("stop").stdout.strip())
    (USER / "settings.json").write_text(json.dumps(SETTINGS), encoding="utf-8")
print("\n실패:", FAILS or "없음")
sys.exit(1 if FAILS else 0)
