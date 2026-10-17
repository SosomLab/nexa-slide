# -*- coding: utf-8 -*-
"""0.22.26 검증 - 회사 템플릿 만들기 마법사(엔진 요청 #3): palette 파생 · POST /api/project {action: template} → 작업 공간 파일 3종 ·
resolve_tokens 색 일치 · export_pptx 의 srgbClr 에 primary · 엔진 이름 충돌 거부 · 금지 키 무시·경고 · 권한(비관리자) ·
작업 공간 서버의 /api/templates·/api/home·/api/preview 에 회사 템플릿 · 엔진 저장소 git status 불변.

격리: NEXA_SLIDE_USER_DIR(허브 5799) · 엔진 example 을 저장소 밖(NEXA_TEST_DIR/projects/wizard-example)으로 복사해 쓴다. 엔진에는 아무것도 쓰지 않는다."""
import http.cookiejar
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
import zlib
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    _s.reconfigure(encoding="utf-8", errors="replace")
STUDIO = Path(__file__).resolve().parents[1]
ENGINE = STUDIO.parent
sys.path.insert(0, str(STUDIO))
import palette  # noqa: E402

WORK = Path(os.environ.get("NEXA_TEST_DIR") or Path(tempfile.gettempdir()) / "nexa-slide-tests")  # 저장소 밖(허브는 엔진 안의 작업 공간을 거절한다)
USER, PROJ, HUB_PORT = WORK / "user-wizard", WORK / "projects", 5799
WS = PROJ / "wizard-example"
BASE = f"http://127.0.0.1:{HUB_PORT}"
ENV = {**os.environ, "NEXA_SLIDE_USER_DIR": str(USER), "NEXA_SLIDE_PROJECTS": str(PROJ), "PYTHONIOENCODING": "utf-8"}
ENV.pop("NEXA_SLIDE_WORKSPACE", None)
FAILS = []
PRIMARY, SURFACE, ON_SURFACE, ACC1, ACC2 = "#1A6B3C", "#FFFFFF", "#1C2324", "#263238", "#8A5A00"


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else extra)
    if not cond:
        FAILS.append(name)


def svc(cmd):
    return subprocess.run([sys.executable, str(STUDIO / "service.py"), cmd], env=ENV, cwd=str(USER), capture_output=True, text=True, encoding="utf-8")


def client():
    jar = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def req(method, url, body=None, timeout=120):
        h = {"Accept": "application/json", "Origin": BASE}
        data = json.dumps(body).encode() if body is not None else None
        if data:
            h["Content-Type"] = "application/json"
        try:
            with op.open(urllib.request.Request(url, data=data, method=method, headers=h), timeout=timeout) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")
    return req


def png(w, h, rgb=(26, 107, 60)):
    """작은 단색 PNG(가로세로 비율 확인용)."""
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def b64(data):
    import base64
    return base64.b64encode(data).decode("ascii")


def ws_py(args, timeout=180):
    """작업 공간 사본에서 엔진 도구 실행 → (code, stdout, stderr)."""
    r = subprocess.run([sys.executable, *map(str, args)], env={**ENV, "NEXA_SLIDE_WORKSPACE": str(WS)}, cwd=str(WS), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    return r.returncode, r.stdout or "", r.stderr or ""


def resolve_tokens():
    code, out, err = ws_py(["-c", f"import json,sys; sys.path.insert(0, {str(STUDIO)!r}); from common import resolve_tokens; print(json.dumps(resolve_tokens()))"])
    return (json.loads(out[out.index("{"):]) if code == 0 and "{" in out else {}), err


def git_status():
    r = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=str(ENGINE), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout


# ---------- 1) palette 단위 시험(순수 함수) ----------
check("palette.norm_hex", palette.norm_hex(" #abc ") == "#AABBCC" and palette.norm_hex("0F5257") == "#0F5257" and palette.norm_hex("#GG0000") is None and palette.norm_hex(None) is None)
check("palette.lum 흰 1 · 검정 0", abs(palette.lum("#FFFFFF") - 1) < 1e-9 and palette.lum("#000000") == 0 and palette.lum("nope") is None)
check("palette.contrast 흑백 21 · 같은 색 1 · 색 아님 None", abs(palette.contrast("#000000", "#FFFFFF") - 21) < 1e-9 and palette.contrast("#777777", "#777777") == 1 and palette.contrast(None, "#fff") is None)
check("palette.mix 중간·끝", palette.mix("#000000", "#FFFFFF", 0.5) == "#808080" and palette.mix("#102030", "#FFFFFF", 0) == "#102030" and palette.mix("#102030", "#FFFFFF", 1) == "#FFFFFF")
d = palette.derive({"primary": PRIMARY, "surface": SURFACE, "on-surface": ON_SURFACE, "accent1": ACC1, "accent2": ACC2})
check("derive 역할 전부(23)·입력 그대로", set(d) == set(palette.DERIVED_KEYS) and d["primary"] == PRIMARY and d["day1"] == ACC1 and d["day2"] == ACC2 and d["surface"] == SURFACE, d)
check("derive on-primary 흰(진한 주색) · container 는 surface 쪽", d["on-primary"] == "#FFFFFF" and palette.contrast(d["primary-container"], SURFACE) < 1.6 and palette.lum(d["primary-container"]) > palette.lum(PRIMARY), d)
check("derive on-*-container 대비 4.5 이상", all(palette.contrast(d[f"on-{k}-container"], d[f"{k}-container"]) >= 4.5 for k in ("primary", "day1", "day2", "day3")), d)
check("derive day3 = primary·accent2 중간", d["day3"] == palette.mix(PRIMARY, ACC2, 0.5))
check("derive panel 밝은 바탕 = on-surface/surface", d["panel"] == ON_SURFACE and d["on-panel"] == SURFACE)
check("derive 경고 없음(기본 입력)", palette.warnings(d) == [], palette.warnings(d))
dk = palette.derive({"primary": "#E0A64A", "surface": "#141414", "on-surface": "#F3F0EA", "accent1": "#7FB3A6", "accent2": "#C48FB0"})
check("derive 어두운 바탕 - on-primary 검정 · container 어둡게 · panel 은 surface-container-high", dk["on-primary"] == "#000000" and palette.lum(dk["primary-container"]) < palette.lum("#E0A64A") and dk["panel"] == dk["surface-container-high"], dk)
adv = palette.derive({"primary": PRIMARY, "surface": SURFACE, "on-surface": ON_SURFACE, "accent1": ACC1, "accent2": ACC2, "primary-container": "#abcdef"})
check("derive 고급 파생값은 그대로(정규화)", adv["primary-container"] == "#ABCDEF")
bad = palette.derive({"primary": "#FFFF00", "surface": "#777777", "on-surface": "#888888", "accent1": ACC1, "accent2": ACC2})
wl = palette.warnings(bad)
check("warnings 낮은 대비 짝 보고(on-surface/surface)", any(w["fg"] == "on-surface" and w["bg"] == "surface" and w["ratio"] < 4.5 for w in wl), wl)
try:
    palette.derive({"primary": "red"})
    check("derive 잘못된 색 → ValueError", False)
except ValueError as e:
    check("derive 잘못된 색 → ValueError", "surface" in str(e), e)

# ---------- 2) 격리 허브 + example 사본 ----------
for _d in (USER, PROJ):
    _d.mkdir(parents=True, exist_ok=True)
if WS.exists():
    shutil.rmtree(WS)
shutil.copytree(ENGINE / "example", WS, ignore=shutil.ignore_patterns("out", ".studio", "__pycache__"))
(USER / "settings.json").write_text(json.dumps({"hubPort": HUB_PORT, "hubProxy": True, "engine": str(ENGINE), "recent": [{"path": str(WS), "title": "wizard-example", "opened": "2026-10-17T00:00:00"}]}), encoding="utf-8")
(USER / "users.json").unlink(missing_ok=True)
status0 = git_status()
logo = png(40, 20)
started = False
try:
    print(svc("start").stdout.strip())
    started = True
    admin = client()
    st, r = admin("POST", BASE + "/api/auth/setup", {"id": "admin", "password": "wizard-test-pass-1"})
    check("관리자 설정", st == 200, (st, r))

    # 2a) palette 미리 보기 API(쓰기 없음)
    st, r = admin("POST", BASE + "/api/project", {"action": "palette", "colors": {"primary": PRIMARY, "surface": SURFACE, "on-surface": ON_SURFACE, "accent1": ACC1, "accent2": ACC2}})
    check("palette API - 파생 색 전부·경고 목록", st == 200 and r.get("ok") and set(r["colors"]) == set(palette.DERIVED_KEYS) and r["warnings"] == [], (st, r))
    st, r = admin("POST", BASE + "/api/project", {"action": "palette", "colors": {"primary": "zzz"}})
    check("palette API - 잘못된 색 400", st == 400 and "색" in r.get("error", ""), (st, r))

    # 2b) 만들기 - 거부 사례 먼저(파일이 생기지 않아야 한다)
    body = {"action": "template", "ws": str(WS), "name": "acme", "base": "brief", "label": "ACME 회사 템플릿", "description": "시험",
            "colors": {"primary": PRIMARY, "surface": SURFACE, "on-surface": ON_SURFACE, "accent1": ACC1, "accent2": ACC2},
            "brand": {"name": "ACME", "logo": {"name": "acme-logo.png", "data": b64(logo)}}, "font": {"preset": "modern"}}
    st, r = admin("POST", BASE + "/api/project", {**body, "name": "lecture"})
    check("엔진 템플릿 이름(lecture) 거부 400", st == 400 and "엔진 템플릿" in r.get("error", ""), (st, r))
    st, r = admin("POST", BASE + "/api/project", {**body, "name": "../x"})
    check("이상한 이름 거부 400", st == 400, (st, r))
    st, r = admin("POST", BASE + "/api/project", {**body, "base": "no-such"})
    check("없는 기반 템플릿 거부 400", st == 400 and "기반" in r.get("error", ""), (st, r))
    st, r = admin("POST", BASE + "/api/project", {**body, "brand": {"logo": {"name": "x.jpg", "data": b64(b"\xff\xd8\xff\xe0JFIF")}}})
    check("PNG 아닌 로고 거부 400", st == 400 and "PNG" in r.get("error", ""), (st, r))
    st, r = admin("POST", BASE + "/api/project", {**body, "font": {"preset": "no-such-preset"}})
    check("없는 글꼴 세트 거부 400", st == 400 and "글꼴 세트" in r.get("error", ""), (st, r))
    check("거부 뒤 파일 없음", not (WS / "templates").exists() and json.loads((WS / "nexa-slide.json").read_text(encoding="utf-8")).get("template") == "lecture")

    # 2c) 만들기 성공 → 파일 3종
    st, r = admin("POST", BASE + "/api/project", body)
    check("회사 템플릿 만들기 200", st == 200 and r.get("ok") and r.get("name") == "acme", (st, r))
    tj = json.loads((WS / "templates" / "acme" / "template.json").read_text(encoding="utf-8")) if (WS / "templates" / "acme" / "template.json").is_file() else {}
    check("  templates/acme/template.json = extends brief + tokenOverrides.colors(파생 전부) · 금지 키 없음", tj.get("extends") == "brief" and tj.get("label") == "ACME 회사 템플릿"
          and set((tj.get("tokenOverrides") or {}).get("colors") or {}) == set(palette.DERIVED_KEYS) and tj["tokenOverrides"]["colors"]["primary"] == PRIMARY
          and not any(k in tj for k in ("tokens", "design", "sizes", "check")), tj)
    lp = WS / "assets" / "brand" / "logo.png"
    check("  assets/brand/logo.png 가 올린 PNG 그대로", lp.is_file() and lp.read_bytes() == logo)
    cfg = json.loads((WS / "nexa-slide.json").read_text(encoding="utf-8"))
    check("  nexa-slide.json template=acme · fontPreset=modern · brand.name=ACME · brand.logo", cfg.get("template") == "acme" and cfg.get("fontPreset") == "modern" and cfg.get("brand", {}).get("name") == "ACME" and cfg["brand"].get("logo") == "assets/brand/logo.png", cfg)
    check("  응답 files·restart(서버 꺼짐 → needed False)·note", set(r.get("files") or []) >= {"templates/acme/template.json", "nexa-slide.json"} and r.get("restart", {}).get("needed") is False and "build_deck --force" in r.get("note", ""), r)
    check("  응답 template 카드(workspace·swatches 첫 색 = primary)", (r.get("template") or {}).get("workspace") is True and (r.get("template") or {}).get("swatches", [""])[0] == PRIMARY, r.get("template"))
    st, r2 = admin("POST", BASE + "/api/project", body)
    check("같은 이름 다시 → 400 exists", st == 400 and r2.get("exists") is True, (st, r2))
    st, r2 = admin("POST", BASE + "/api/project", {**body, "overwrite": True, "label": "ACME v2"})
    check("overwrite 로 덮어쓰기 200", st == 200 and r2.get("label") == "ACME v2", (st, r2))
    # #7: Windows 예약 이름은 아무것도 쓰기 전에 거부(로고만 바뀐 반쪽 상태 금지) · 기존 로고·글꼴을 덮어쓸 때 백업
    logo_before = lp.read_bytes()
    for bad in ("aux", "COM1", "lpt1", "con", "NUL"):
        st, r3 = admin("POST", BASE + "/api/project", {**body, "name": bad, "brand": {"logo": {"name": "l.png", "data": b64(png(10, 10, (1, 2, 3)))}}})
        names = [p.name.lower() for p in (WS / "templates").iterdir()]  # (Windows 에서는 Path("con").exists() 가 늘 True 라 목록으로 본다)
        check(f"예약 이름 {bad} → 400 안내·파일 불변", st == 400 and "예약" in str(r3.get("error", "")) and bad.lower() not in names and lp.read_bytes() == logo_before, (st, r3))
    logo2 = png(40, 20, (200, 10, 10))
    st, r3 = admin("POST", BASE + "/api/project", {**body, "overwrite": True, "brand": {"logo": {"name": "acme2.png", "data": b64(logo2)}}})
    hist = WS / "out" / ".history" / "wizard"
    bks = sorted(hist.glob("*/assets/brand/logo.png")) if hist.exists() else []
    check("다른 로고로 덮어쓰면 이전 로고가 out/.history/wizard/<시각>/ 에 백업", st == 200 and r3.get("backups") and bks and bks[-1].read_bytes() == logo_before and lp.read_bytes() == logo2, (st, r3.get("backups"), [str(b) for b in bks]))
    st, r3 = admin("POST", BASE + "/api/project", {**body, "overwrite": True, "brand": {"logo": {"name": "acme2.png", "data": b64(logo2)}}})
    check("같은 바이트면 백업 없음", st == 200 and not r3.get("backups"), r3.get("backups"))
    # #8: 같은 초에 연달아 두 번(B → C → D) - 백업 폴더가 밀리초(+순번)라 B·C 가 모두 남아야 한다
    logo3, logo4 = png(40, 20, (10, 200, 10)), png(40, 20, (10, 10, 200))
    n0 = len(list(hist.glob("*/assets/brand/logo.png")))
    bk_paths = []
    for lg in (logo3, logo4):
        st, r3 = admin("POST", BASE + "/api/project", {**body, "overwrite": True, "brand": {"logo": {"name": "acme3.png", "data": b64(lg)}}})
        bk_paths += r3.get("backups") or []
    kept = [p.read_bytes() for p in hist.glob("*/assets/brand/logo.png")]
    check("연달아 덮어써도 백업 폴더가 겹치지 않아 이전 로고 둘 다 남음", len(kept) == n0 + 2 and logo2 in kept and logo3 in kept and len(set(bk_paths)) == 2, (n0, len(kept), bk_paths))
    st, r3 = admin("POST", BASE + "/api/project", {**body, "overwrite": True})  # 원래 로고로 되돌림(아래 검사들이 logo 바이트를 본다)
    check("원래 로고로 복구", st == 200 and lp.read_bytes() == logo)

    # 2d) resolve_tokens 색 일치(작업 공간 사본에서 엔진 common 이 읽는 값)
    tok, err = resolve_tokens()
    cs = tok.get("colors", {})
    check("resolve_tokens: primary·day1·day2·on-surface = 입력, primary-container = 파생값, 경고 없음", cs.get("primary") == PRIMARY and cs.get("day1") == ACC1 and cs.get("day2") == ACC2 and cs.get("on-surface") == ON_SURFACE
          and cs.get("primary-container") == d["primary-container"] and "알림" not in err and tok.get("fontPreset") == "modern", (cs.get("primary"), err[-300:]))
    check("resolve_tokens: 바탕(brief)의 s3 등 다른 토큰은 그대로", cs.get("s3") == "#A91F24" and cs.get("white") == "#FFFFFF")
    code, out, err = ws_py([STUDIO / "set_template.py", "--json"])
    lst = json.loads(out[out.index("{"):]) if code == 0 else {}
    check("set_template --json: current acme · 목록에 acme(workspace) 가 엔진 뒤에", lst.get("current") == "acme" and any(t["name"] == "acme" and t.get("workspace") for t in lst.get("templates", [])) and lst.get("templates", [{}])[-1].get("name") == "acme", (code, out[-200:], err[-200:]))
    code, out, err = ws_py([STUDIO / "set_template.py", "acme"])
    check("set_template acme (CLI 로 고르기) 성공", code == 0 and "acme" in out, (code, out, err))

    # 2e) export_pptx --out → srgbClr 에 primary
    outp = WS / "out" / "wizard-demo.pptx"
    code, out, err = ws_py([STUDIO / "export_pptx.py", "demo", "--out", outp])
    check("export_pptx demo --out", code == 0 and outp.is_file(), (code, out[-300:], err[-300:]))
    if outp.is_file():
        with zipfile.ZipFile(outp) as z:
            xml = "".join(z.read(n).decode("utf-8", "replace") for n in z.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml"))
        check("  slide XML 의 srgbClr 에 primary 값", f'val="{PRIMARY[1:]}"' in xml, "없음")
        check("  slide XML 에 brief 의 primary(0F5257)는 없음", 'val="0F5257"' not in xml)

    # 2f) 금지 키 무시·경고
    tj2 = {**tj, "tokens": "tokens.json", "sizes": {"minPx": {"default": 40}}, "check": {"minFontPt": {"default": 30}}, "design": {"concept": "x.html"}}
    (WS / "templates" / "acme" / "template.json").write_text(json.dumps(tj2, ensure_ascii=False, indent=2), encoding="utf-8")
    tok, err = resolve_tokens()
    check("금지 키(tokens·sizes·check·design) → 무시하고 경고, 색은 그대로", tok.get("colors", {}).get("primary") == PRIMARY and "무시" in err and "tokens" in err and "sizes" in err, err[-400:])
    code, out, err = ws_py(["-c", f"import json,sys; sys.path.insert(0, {str(STUDIO)!r}); from common import TEMPLATE, SIZES, TOKENS; print(json.dumps({{'sizes': SIZES, 'tokens': str(TOKENS), 'ws': TEMPLATE.get('workspace')}}))"])
    info = json.loads(out[out.index("{"):]) if code == 0 else {}
    check("  sizes 는 바탕(brief 15px) · tokens 는 엔진 lecture 파일 · workspace 표시", (info.get("sizes") or {}).get("minPx", {}).get("default") == 15 and info.get("tokens", "").replace("\\", "/").endswith("studio/templates/lecture/tokens.json") and info.get("ws") is True, info)
    (WS / "templates" / "acme" / "template.json").write_text(json.dumps(tj, ensure_ascii=False, indent=2), encoding="utf-8")
    # extends 가 엔진 템플릿이 아니면 lecture 바탕 + 경고
    (WS / "templates" / "acme2").mkdir(exist_ok=True)
    (WS / "templates" / "acme2" / "template.json").write_text(json.dumps({"extends": "acme", "label": "x", "tokenOverrides": {"colors": {"primary": "#123456"}}}), encoding="utf-8")
    code, out, err = ws_py([STUDIO / "set_template.py", "--json"])
    check("extends 가 작업 공간 템플릿이면 lecture 바탕 + 경고", code == 0 and "lecture 를 바탕" in err and "acme2" in out, (code, err[-300:]))
    shutil.rmtree(WS / "templates" / "acme2")
    # 엔진과 같은 이름의 폴더는 무시 + 경고
    (WS / "templates" / "lecture").mkdir(exist_ok=True)
    (WS / "templates" / "lecture" / "template.json").write_text(json.dumps({"extends": "brief", "tokenOverrides": {"colors": {"primary": "#123456"}}}), encoding="utf-8")
    code, out, err = ws_py([STUDIO / "set_template.py", "--json"])
    names = [t["name"] for t in (json.loads(out[out.index("{"):]) if code == 0 else {}).get("templates", [])]
    check("엔진과 같은 이름의 작업 공간 템플릿은 무시(목록에 lecture 하나) + 경고", names.count("lecture") == 1 and "이름이 같아" in err, (names, err[-300:]))
    shutil.rmtree(WS / "templates" / "lecture")

    # 2g) 전용 글꼴 파일 올리기 → fonts/ + fontPresets
    fake = b"\x00\x01\x00\x00" + b"\x00" * 64  # 진짜 글꼴은 아니지만 파일로 두는 것까지만 확인(메트릭을 못 읽으면 기본 C 로 계산한다)
    st, r = admin("POST", BASE + "/api/project", {**body, "name": "acme-font", "font": {"name": "corp", "family": "Corp Sans", "files": {"regular": {"name": "CorpSans.ttf", "data": b64(fake)}, "bold": {"name": "CorpSans-Bold.ttf", "data": b64(fake)}}}, "brand": {}})
    cfg = json.loads((WS / "nexa-slide.json").read_text(encoding="utf-8"))
    check("전용 글꼴: fonts/ 파일 2개 · fontPresets.corp(body·heading measure) · fontPreset=corp", st == 200 and (WS / "fonts" / "CorpSans.ttf").is_file() and (WS / "fonts" / "CorpSans-Bold.ttf").is_file()
          and cfg.get("fontPreset") == "corp" and cfg.get("fontPresets", {}).get("corp", {}).get("body", {}).get("measure", {}).get("bold") == "CorpSans-Bold.ttf" and cfg["fontPresets"]["corp"]["heading"]["latin"] == "Corp Sans", (st, r, cfg.get("fontPresets")))
    st, r = admin("POST", BASE + "/api/project", {**body, "name": "acme-font2", "font": {"name": "corp2", "family": "X", "files": {"regular": {"name": "x.exe", "data": b64(fake)}}}, "brand": {}})
    check("글꼴 확장자 아닌 파일 거부 400", st == 400 and ".ttf" in r.get("error", ""), (st, r))
    # 다시 acme 로(글꼴 세트는 modern)
    st, r = admin("POST", BASE + "/api/project", {**body, "overwrite": True})
    check("acme 다시 적용", st == 200 and json.loads((WS / "nexa-slide.json").read_text(encoding="utf-8")).get("template") == "acme")

    # 2h) 권한 - 비관리자: 최근 작업(허브에서 연 작업 공간)에는 허용, 모르는 작업 공간은 403
    st, r = admin("POST", BASE + "/api/auth/users", {"action": "add", "id": "u1", "password": "wizard-user-pass-1", "role": "user"})
    user = client()
    st, r = user("POST", BASE + "/api/auth/login", {"id": "u1", "password": "wizard-user-pass-1"})
    check("일반 사용자 로그인", st == 200, (st, r))
    other = PROJ / "wizard-other"
    if other.exists():
        shutil.rmtree(other)
    shutil.copytree(ENGINE / "example", other, ignore=shutil.ignore_patterns("out", ".studio", "__pycache__"))
    st, r = user("POST", BASE + "/api/project", {**body, "ws": str(other), "name": "acme-u"})
    check("비관리자 - 허브가 모르는 작업 공간 403", st == 403, (st, r))
    st, r = user("POST", BASE + "/api/project", {**body, "name": "acme-u", "brand": {}, "font": {}})
    check("비관리자 - 최근 작업의 작업 공간은 허용", st == 200 and (WS / "templates" / "acme-u" / "template.json").is_file(), (st, r))
    shutil.rmtree(other, ignore_errors=True)
    st, r = admin("POST", BASE + "/api/project", {**body, "overwrite": True})  # 다시 acme

    # 2i) 허브의 /api/preview 는 엔진 템플릿만, 작업 공간 서버는 회사 템플릿도
    st, r = admin("GET", BASE + "/api/preview?template=acme")
    check("허브 /api/preview?template=acme → 400(엔진 템플릿만)", st == 400, (st, r))
    st, r = admin("POST", BASE + "/api/project", {"action": "start", "path": str(WS)})
    check("작업 공간 서버 시작(재시작 단추와 같은 경로)", st == 200 and r.get("running") and r.get("url"), (st, r))
    if st == 200:
        url = r["url"].rstrip("/")
        direct = client()
        st, t = direct("GET", url + "/api/templates")
        check("  작업 공간 서버 /api/templates: current acme · acme(workspace) 포함", t.get("current") == "acme" and any(x["name"] == "acme" and x.get("workspace") for x in t.get("templates", [])), t)
        st, h = direct("GET", url + "/api/home")
        check("  /api/home templates 에 acme 카드(workspace·extends brief)", any(x["name"] == "acme" and x.get("workspace") and x.get("extends") == "brief" for x in h.get("templates", [])), [x["name"] for x in h.get("templates", [])])
        st, c = direct("GET", url + "/api/config")
        tcs = ((c.get("tokens") or {}).get("colors") or {}) if isinstance(c, dict) else {}
        check("  /api/config tokens.colors.primary = 입력", (tcs.get("primary") == PRIMARY) if tcs else True, "config 에 tokens 없음(건너뜀)" if not tcs else tcs.get("primary"))
        t0 = time.time()
        st, pv = direct("GET", url + "/api/preview?template=acme", timeout=180)
        check(f"  /api/preview?template=acme (회사 템플릿 미리 보기 빌드, {time.time() - t0:.0f}s) tokens.colors.primary", st == 200 and pv.get("ok") and pv["tokens"]["colors"].get("primary") == PRIMARY and len(pv.get("decks") or []) >= 1, (st, str(pv)[:300]))
        st, r = admin("POST", BASE + "/api/project", {"action": "stop", "path": str(WS)})
        check("  작업 공간 서버 중지", st == 200, (st, r))

    # 2j) 엔진 저장소에는 아무것도 쓰지 않았다
    status1 = git_status()
    check("엔진 저장소 git status 불변", status0 == status1, "\n".join(sorted(set(status1.splitlines()) ^ set(status0.splitlines()))))
    check("엔진 studio/templates 에 acme 없음", not (STUDIO / "templates" / "acme").exists())
finally:
    if started:
        print("  ", svc("stop").stdout.strip())
print("\n실패:", FAILS or "없음")
sys.exit(1 if FAILS else 0)
