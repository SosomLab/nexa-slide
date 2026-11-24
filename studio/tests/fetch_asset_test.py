# -*- coding: utf-8 -*-
"""공개 웹 파일 가져오기(studio/fetch_asset.py, 엔진 요청 #17) 시험 - 실제 인터넷에는 나가지 않는다(접속을 가짜로 바꾼다).

    python3 studio/tests/fetch_asset_test.py

주소 검사(https·443·사용자 정보) · 공인 주소 검사(사설·루프백·링크 로컬·CGNAT·IPv4-mapped) · 리다이렉트마다 다시 검사 · 크기 제한 ·
저장 자리(assets/·fonts/ 만, .. 거절) · 내용 검사(PNG·JPEG·SVG·글꼴 머리, SVG 스크립트) · 덮어쓰기 거절과 --force 백업 ·
--brand(공유 설정·옛 경로를 쓰는 덱 요소 목록) · --preset · zip 묶음 안의 글꼴(--member·굵은 파일 짝짓기·크기·머리 검사) · 웹 세션 확인(웹 검색 허용이 아닌 세션이면 종료 코드 2).
"""
import contextlib
import io
import json
import os
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tmpfiles  # noqa: E402
WS = tmpfiles.process_dir("fetch-ws")
os.environ["NEXA_SLIDE_USER_DIR"] = str(tmpfiles.process_dir("fetch-user"))  # 실제 사용자 설정을 건드리지 않게
os.environ["NEXA_SLIDE_WORKSPACE"] = str(WS)
os.environ.pop("NEXA_SLIDE_SESSION", None)
(WS / "nexa-slide.json").write_text(json.dumps({"title": "fetch", "brand": {"name": "ACME", "logo": "assets/brand/logo.png"}}), encoding="utf-8")
(WS / "decks").mkdir()
(WS / "decks" / "d1.json").write_text(json.dumps({"title": "d", "slides": [
    {"id": "s01", "elements": [{"id": "e06", "type": "image", "src": "assets/brand/logo.png"}, {"id": "e07", "type": "text", "text": "x"}]},
    {"id": "s02", "elements": [{"id": "g1", "type": "group", "elements": [{"id": "e02", "type": "image", "src": "assets/brand/logo.png"}]},
                               {"id": "e03", "type": "image", "src": "assets/img/other.png"}]}]}), encoding="utf-8")
(WS / "decks" / "d1.requests.json").write_text("[]", encoding="utf-8")
import fetch_asset as fa  # noqa: E402

FAILS = []
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", 300, 100) + b"\x08\x06\x00\x00\x00" + b"\x00" * 40
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 40
SVG = b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="10" height="10"/></svg>'
TTF = b"\x00\x01\x00\x00" + b"\x00" * 60
HTML = b"<!doctype html><html><body>404</body></html>"


def check(name, ok, got=""):
    print(("OK   " if ok else "FAIL ") + name + ("" if ok else f" → {got}"))
    if not ok:
        FAILS.append(name)


def refused(fn, *a):
    """Refuse 면 그 글, 아니면 None."""
    try:
        fn(*a)
    except fa.Refuse as e:
        return str(e)
    return None


class Resp:
    def __init__(self, status=200, body=b"", headers=None):
        self.status, self.reason, self._body, self._b, self._h = status, "", body, io.BytesIO(body), {"Content-Length": str(len(body)), **(headers or {})}

    def getheader(self, k):
        return self._h.get(k)

    def read(self, n):
        return self._b.read(n)


class Conn:
    def __init__(self, host):
        self.host = host

    def request(self, method, target, headers=None):
        SEEN.append((self.host, target, dict(headers or {})))
        r = ROUTES[(self.host, target)]
        self._r = Resp(r.status, r._body, r._h)  # 같은 주소를 여러 번 받아도 처음부터 읽게

    def getresponse(self):
        return self._r

    def close(self):
        pass


SEEN, ROUTES = [], {}


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = fa.main(list(argv))
    return rc, out.getvalue() + err.getvalue()


# ---- 1) 주소 검사
check("https 주소 → (호스트, 대상)", fa.check_url("https://Example.com/a/b.png?x=1&y=2#frag") == ("example.com", "/a/b.png?x=1&y=2"), fa.check_url("https://Example.com/a/b.png?x=1&y=2#frag"))
for bad, what in (("http://example.com/a.png", "http"), ("file:///c:/windows/win.ini", "file"), ("ftp://example.com/a.png", "ftp"), ("https://user:pw@example.com/a.png", "사용자 정보"),
                  ("https://example.com:8443/a.png", "다른 포트"), ("https:///a.png", "호스트 없음"), ("https://example.com/a b.png", "공백"), ("", "빈 값"), ("https://example.com/" + "a" * 2100, "너무 김")):
    check(f"  거절: {what}", refused(fa.check_url, bad) is not None, bad[:60])

# ---- 2) 공인 주소 검사(IP 글자는 DNS 없이 풀린다)
check("공인 IP 는 통과", fa.resolve_public("8.8.8.8") == "8.8.8.8")
for ip in ("127.0.0.1", "10.0.0.5", "192.168.0.10", "172.16.3.4", "169.254.169.254", "100.64.0.1", "0.0.0.0", "::1", "::ffff:127.0.0.1", "fe80::1", "fd00::1", "224.0.0.1"):
    check(f"  거절: {ip}", refused(fa.resolve_public, ip) is not None, ip)

# ---- 3) 저장 자리
k, p, rel = fa.dest("assets/brand/acme.png")
check("그림 → assets/ 아래", k == "image" and p == (WS / "assets" / "brand" / "acme.png").resolve() and rel == "assets/brand/acme.png", (k, p, rel))
k, p, rel = fa.dest("fonts\\Acme-Regular.ttf")
check("글꼴 → fonts/ 아래(역슬래시도)", k == "font" and p == (WS / "fonts" / "Acme-Regular.ttf").resolve() and rel == "fonts/Acme-Regular.ttf", (k, p, rel))
for bad, what in (("logo.png", "루트"), ("decks/x.png", "assets 밖"), ("assets/../nexa.py", ".."), ("assets/../../x.png", ".. 두 번"), ("/etc/x.png", "절대 경로"), ("C:/x/assets/a.png", "드라이브"),
                  ("assets/a.exe", "확장자"), ("assets/a.html", "html"), ("assets/x.ttf", "글꼴을 assets 에"), ("fonts/x.png", "그림을 fonts 에"), ("assets/.hidden.png", "점으로 시작"),
                  ("assets/con.png", "예약 이름"), ("nexa.py", "실행기"), ("assets/a.png/", "빈 조각"), ("fonts/a.woff2", "woff2"), ("assets/a;b.png", "기호")):
    check(f"  거절: {what}", refused(fa.dest, bad) is not None, bad)

# ---- 4) 내용 검사
check("PNG 크기를 읽는다", fa.sniff(PNG, ".png") == (300, 100), fa.sniff(PNG, ".png"))
check("JPEG · SVG · TTF · OTF 통과", fa.sniff(JPG, ".jpg") is None and fa.sniff(SVG, ".svg") is None and fa.sniff(TTF, ".ttf") is None and fa.sniff(b"OTTO" + b"\x00" * 20, ".otf") is None)
check("  거절: HTML 을 .png 로", refused(fa.sniff, HTML, ".png") is not None)
check("  거절: PNG 를 .jpg 로", refused(fa.sniff, PNG, ".jpg") is not None)
check("  거절: HTML 을 .svg 로", refused(fa.sniff, HTML, ".svg") is not None)
check("  거절: HTML 을 .ttf 로", refused(fa.sniff, HTML, ".ttf") is not None)
check("  거절: 빈 파일", refused(fa.sniff, b"", ".png") is not None)
for bad, what in ((b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>', "script"), (b'<svg onload="x()"></svg>', "onload"),
                  (b'<svg><a href="javascript:x()">a</a></svg>', "javascript:"), (b'<svg><foreignObject><p>x</p></foreignObject></svg>', "foreignObject"),
                  (b'<!DOCTYPE svg [<!ENTITY x SYSTEM "file:///etc/passwd">]><svg>&x;</svg>', "엔티티")):
    check(f"  거절: SVG {what}", refused(fa.sniff, bad, ".svg") is not None)

# ---- 5) 내려받기(가짜 접속) - 리다이렉트·크기·응답 코드
RESOLVED = []


def fake_resolve(host):
    RESOLVED.append(host)
    if host == "internal.example":
        raise fa.Refuse("공인 주소가 아닌 곳은 받지 않는다: internal.example → 10.0.0.5")
    return "93.184.216.34"


real_resolve, fa.resolve_public, fa._connect = fa.resolve_public, fake_resolve, lambda host, ip: Conn(host)
ROUTES.update({
    ("cdn.example", "/logo.png"): Resp(200, PNG),
    ("www.example", "/go"): Resp(302, b"", {"Location": "https://cdn.example/logo.png"}),
    ("www.example", "/rel"): Resp(301, b"", {"Location": "/go"}),
    ("www.example", "/to-http"): Resp(302, b"", {"Location": "http://cdn.example/logo.png"}),
    ("www.example", "/to-internal"): Resp(302, b"", {"Location": "https://internal.example/logo.png"}),
    ("www.example", "/loop"): Resp(302, b"", {"Location": "/loop"}),
    ("www.example", "/404.png"): Resp(404, HTML),
    ("www.example", "/big.png"): Resp(200, b"", {"Content-Length": str(50 * fa.MB)}),
    ("www.example", "/big-nolen.png"): Resp(200, PNG + b"\x00" * 4096, {"Content-Length": ""}),
    ("www.example", "/page.png"): Resp(200, HTML),
    ("www.example", "/a.svg"): Resp(200, SVG),
    ("www.example", "/f.ttf"): Resp(200, TTF),
    ("www.example", "/q.jpg?a=1&b=2"): Resp(200, JPG),
})
data, final = fa.download("https://www.example/rel", fa.LIMITS["image"])
check("리다이렉트(상대 → 다른 호스트)를 따라가 받는다", data == PNG and final == "https://cdn.example/logo.png", final)
check("  호스트마다 주소 검사", RESOLVED == ["www.example", "www.example", "cdn.example"], RESOLVED)
check("  쿠키·인증·Referer 를 보내지 않는다", all(not {"cookie", "authorization", "referer"} & {k.lower() for k in h} for _, _, h in SEEN), SEEN[-1][2])
check("  거절: https → http 리다이렉트", "https" in (refused(fa.download, "https://www.example/to-http", 10 * fa.MB) or ""))
check("  거절: 내부 주소로 리다이렉트", "공인" in (refused(fa.download, "https://www.example/to-internal", 10 * fa.MB) or ""))
check("  거절: 리다이렉트 반복", "리다이렉트" in (refused(fa.download, "https://www.example/loop", 10 * fa.MB) or ""))
check("  거절: 404", "404" in (refused(fa.download, "https://www.example/404.png", 10 * fa.MB) or ""))
check("  거절: Content-Length 가 제한보다 큼", "크다" in (refused(fa.download, "https://www.example/big.png", 10 * fa.MB) or ""))
check("  거절: 길이 없이 제한을 넘김", "크다" in (refused(fa.download, "https://www.example/big-nolen.png", 1024) or ""))

# ---- 6) 명령 전체 - 저장·덮어쓰기·백업
fa.web_block = lambda: None
rc, out = run("https://www.example/go", "--to", "assets/brand/acme.png")
check("그림 저장 → 0 · 파일 · 크기·출처 출력", rc == 0 and (WS / "assets" / "brand" / "acme.png").read_bytes() == PNG and "300×100px" in out and "출처: https://cdn.example/logo.png" in out, (rc, out))
check("  .part 가 남지 않는다", not list((WS / "assets").rglob("*.part")))
rc, out = run("https://www.example/go", "--to", "assets/brand/acme.png")
check("같은 자리 다시 → 1(이미 있음), 접속하지 않음", rc == 1 and "이미 있는" in out, (rc, out))
(WS / "assets" / "brand" / "logo.png").write_bytes(JPG)
rc, out = run("https://www.example/go", "--to", "assets/brand/logo.png", "--force")
bks = list((WS / "out" / ".history" / "fetch").glob("*/logo.png"))
check("--force → 바꾸고 기존 파일 백업", rc == 0 and (WS / "assets" / "brand" / "logo.png").read_bytes() == PNG and len(bks) == 1 and bks[0].read_bytes() == JPG and "백업" in out, (rc, out, bks))
rc, out = run("https://www.example/page.png", "--to", "assets/img/page.png")
check("HTML 쪽을 .png 로 → 1 · 파일 없음", rc == 1 and "PNG 가 아니다" in out and not (WS / "assets" / "img" / "page.png").exists(), (rc, out))
rc, out = run("https://www.example/404.png", "--to", "assets/img/x.png")
check("404 → 1 · 파일 없음", rc == 1 and not (WS / "assets" / "img" / "x.png").exists(), (rc, out))
n = len(SEEN)
rc, out = run("https://www.example/go", "--to", "decks/d1.json")
check("assets 밖 → 1 · 접속 전에 거절 · 덱 그대로", rc == 1 and len(SEEN) == n and json.loads((WS / "decks" / "d1.json").read_text(encoding="utf-8"))["title"] == "d", (rc, out))
rc, out = run("https://www.example/go", "--to", "assets/../nexa.py")
check(".. → 1 · 접속 전에 거절", rc == 1 and len(SEEN) == n and not (WS / "nexa.py").exists(), (rc, out))
rc, out = run("http://www.example/go", "--to", "assets/img/h.png")
check("http → 1 · 접속 전에 거절", rc == 1 and len(SEEN) == n, (rc, out))
rc, out = run("https://www.example/a.svg", "--to", "assets/img/a.svg")
check("SVG 저장", rc == 0 and (WS / "assets" / "img" / "a.svg").read_bytes() == SVG, (rc, out))
rc, out = run("https://www.example/f.ttf", "--to", "fonts/Acme-Regular.ttf")
check("글꼴 저장 → fonts/ · fontPresets 안내", rc == 0 and (WS / "fonts" / "Acme-Regular.ttf").read_bytes() == TTF and "fontPresets" in out and "라이선스" in out, (rc, out))
rc, out = run("https://www.example/f.ttf", "--to", "fonts/b.ttf", "--brand", "logo")
check("글꼴에 --brand → 1", rc == 1 and not (WS / "fonts" / "b.ttf").exists(), (rc, out))
(WS / "out" / ".studio").mkdir(parents=True, exist_ok=True)
(WS / "out" / ".studio" / "url.txt").write_text("https://www.example/q.jpg?a=1&b=2\n", encoding="utf-8")
rc, out = run("--url-file", str(WS / "out" / ".studio" / "url.txt"), "--to", "assets/img/q.jpg")
check("--url-file(& 가 든 주소)", rc == 0 and (WS / "assets" / "img" / "q.jpg").read_bytes() == JPG and SEEN[-1][1] == "/q.jpg?a=1&b=2", (rc, out, SEEN[-1][:2]))
rc, out = run("--url-file", str(Path(fa.__file__)), "--to", "assets/img/z.jpg")
check("--url-file 이 작업 공간 밖 → 1", rc == 1 and "작업 공간 안" in out, (rc, out))

# ---- 7) --brand
before = (WS / "decks" / "d1.json").read_bytes()
rc, out = run("https://www.example/go", "--to", "assets/brand/client.png", "--brand", "logo")
cfg = json.loads((WS / "nexa-slide.json").read_text(encoding="utf-8"))
check("--brand logo → 공유 설정 brand.logo · 다른 값 유지", rc == 0 and cfg["brand"] == {"name": "ACME", "logo": "assets/brand/client.png"} and cfg["title"] == "fetch", (rc, cfg))
check("  옛 경로를 쓰는 덱 요소 목록(묶음 안까지) · 비율", "d1: s01 e06, s02 e02" in out and "s02 e03" not in out and "300:100" in out, out)
check("  덱 파일은 고치지 않는다 · 재시작 안내", (WS / "decks" / "d1.json").read_bytes() == before and "restart" in out, out)
rc, out = run("https://www.example/a.svg", "--to", "assets/brand/mark.svg", "--brand", "wordmark")
cfg = json.loads((WS / "nexa-slide.json").read_text(encoding="utf-8"))
check("--brand wordmark(SVG)", rc == 0 and cfg["brand"].get("wordmark") == "assets/brand/mark.svg" and cfg["brand"]["logo"] == "assets/brand/client.png", (rc, cfg))

# ---- 7-2) --preset: 받은 글꼴을 글꼴 세트로(엔진 요청 #22)
def font(family, sig=b"\x00\x01\x00\x00"):
    """name 표(nameID 1 = family, Windows 영문)만 든 가장 작은 글꼴 파일."""
    s = family.encode("utf-16-be")
    name = struct.pack(">HHH", 0, 1, 18) + struct.pack(">6H", 3, 1, 0x409, 1, len(s), 0) + s
    return sig + struct.pack(">HHHH", 1, 0, 0, 0) + struct.pack(">4sIII", b"name", 0, 28, len(name)) + name


def shared():
    return json.loads((WS / "nexa-slide.json").read_text(encoding="utf-8"))


FR, FB = font("Sebang Gothic"), font("Sebang Gothic Bold", b"OTTO")
ROUTES.update({("www.example", "/sg-r.ttf"): Resp(200, FR), ("www.example", "/sg-b.otf"): Resp(200, FB)})
check("패밀리 이름을 글꼴 파일에서 읽는다", fa.family_name(FR) == "Sebang Gothic" and fa.family_name(TTF) is None and fa.family_name(b"") is None, fa.family_name(FR))
n = len(SEEN)
rc, out = run("https://www.example/sg-b.otf", "--to", "fonts/SG-Bold.otf", "--preset", "sebang", "--weight", "bold")
check("세트가 없는데 --weight bold → 1 · 접속 전에 거절", rc == 1 and len(SEEN) == n and not (WS / "fonts" / "SG-Bold.otf").exists(), (rc, out))
rc, out = run("https://www.example/sg-r.ttf", "--to", "fonts/SG-Regular.ttf", "--preset", "sebang")
cfg = shared()
pr = (cfg.get("fontPresets") or {}).get("sebang") or {}
check("--preset → 파일 저장 · fontPresets.sebang(본문·제목) · fontPreset 고름", rc == 0 and (WS / "fonts" / "SG-Regular.ttf").read_bytes() == FR and cfg.get("fontPreset") == "sebang"
      and pr.get("body", {}).get("latin") == "Sebang Gothic" and pr["body"]["ea"] == "Sebang Gothic" and '"Sebang Gothic"' in pr["body"]["css"]
      and pr["body"]["measure"] == {"regular": "SG-Regular.ttf", "bold": "SG-Regular.ttf"} and pr["heading"] == pr["body"], (rc, out, cfg))
check("  다른 설정(brand·title)은 그대로 · 굵은 파일 안내", cfg["title"] == "fetch" and cfg["brand"]["logo"] == "assets/brand/client.png" and "--weight bold" in out, (cfg, out))
import common  # noqa: E402
tk = common.resolve_tokens(common.read_config())
check("  resolve_tokens 가 그 세트를 쓴다(본문·제목 = 새 글꼴, 코드 글꼴은 템플릿 것)", tk["fonts"]["body"]["latin"] == "Sebang Gothic" and tk["fonts"]["heading"]["latin"] == "Sebang Gothic"
      and tk["fonts"]["mono"].get("latin") not in (None, "Sebang Gothic"), tk["fonts"])
rc, out = run("https://www.example/sg-b.otf", "--to", "fonts/SG-Bold.otf", "--preset", "sebang", "--weight", "bold")
pr = shared()["fontPresets"]["sebang"]
check("--weight bold → 굵은 파일만 바뀜(본문·제목)", rc == 0 and pr["body"]["measure"] == {"regular": "SG-Regular.ttf", "bold": "SG-Bold.otf"} and pr["heading"]["measure"]["bold"] == "SG-Bold.otf"
      and pr["body"]["latin"] == "Sebang Gothic", (rc, out, pr))
rc, out = run("https://www.example/sg-r.ttf", "--to", "fonts/SG-Regular.ttf", "--preset", "sebang", "--force")
check("보통 굵기를 다시 받아도 굵은 파일은 지킨다", rc == 0 and shared()["fontPresets"]["sebang"]["body"]["measure"]["bold"] == "SG-Bold.otf", (rc, out))
rc, out = run("https://www.example/f.ttf", "--to", "fonts/NoName.ttf", "--preset", "noname")
check("패밀리 이름을 못 읽음 → 1 · 파일·세트 없음", rc == 1 and "--family" in out and not (WS / "fonts" / "NoName.ttf").exists() and "noname" not in shared()["fontPresets"], (rc, out))
rc, out = run("https://www.example/f.ttf", "--to", "fonts/NoName.ttf", "--preset", "noname", "--family", "Acme Sans")
check("--family 로 직접", rc == 0 and shared()["fontPresets"]["noname"]["body"]["latin"] == "Acme Sans" and shared()["fontPreset"] == "noname" and "sebang" in shared()["fontPresets"], (rc, out))
n = len(SEEN)
for argv, what in ((("https://www.example/go", "--to", "assets/img/p.png", "--preset", "x"), "그림에 --preset"), (("https://www.example/sg-r.ttf", "--to", "fonts/sub/a.ttf", "--preset", "x"), "fonts/ 하위 폴더"),
                   (("https://www.example/sg-r.ttf", "--to", "fonts/a.ttf", "--preset", "bad name!"), "세트 이름"),
                   (("https://www.example/sg-r.ttf", "--to", "fonts/a.ttf", "--preset", next(iter(common.resolve_tokens({}).get("fontPresets") or {"default": 1}))), "템플릿 세트와 같은 이름")):
    rc, out = run(*argv)
    check(f"  거절: {what} → 1 · 접속 전에", rc == 1 and len(SEEN) == n, (rc, out))

# ---- 7-2b) zip 묶음 안의 글꼴(엔진 요청 #24 - 회사 서체는 zip 으로만 배포되는 경우가 많다)
import zipfile  # noqa: E402


def zipped(members, method=zipfile.ZIP_DEFLATED):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", method) as z:
        for name, body in members:
            z.writestr(name, body)
    return buf.getvalue()


ZR, ZB, ZX, ZO = font("Zip Gothic"), font("Zip Gothic Bold"), font("Zip Gothic ExtraBold"), font("Zip Gothic", b"OTTO")
ROUTES.update({
    ("www.example", "/one.zip"): Resp(200, zipped([("ZIP_GOTHIC_Regular/ZipGothic_Regular.ttf", ZR), ("ZIP_GOTHIC_Regular/License.txt", b"free"), ("__MACOSX/._ZipGothic_Regular.ttf", b"junk")])),
    ("www.example", "/all.zip"): Resp(200, zipped([("TTF/ZipGothic_Regular.ttf", ZR), ("TTF/ZipGothic_Bold.ttf", ZB), ("TTF/ZipGothic_ExtraBold.ttf", ZX), ("OTF/ZipGothic_Regular.otf", ZO),
                                                  ("Webfont/ZipGothic_Regular.woff", b"wOFF" + b"\x00" * 20), ("../evil.ttf", ZX)])),
    ("www.example", "/multi.zip"): Resp(200, zipped([("ZipGothic_Light.ttf", ZR), ("ZipGothic_Medium.ttf", ZB)])),
    ("www.example", "/nofont.zip"): Resp(200, zipped([("readme.txt", b"hi"), ("a.woff2", b"wOF2")])),
    ("www.example", "/fake.zip"): Resp(200, zipped([("Fake_Regular.ttf", HTML)])),
    ("www.example", "/bomb.zip"): Resp(200, zipped([("Big_Regular.ttf", b"\x00\x01\x00\x00" + b"\x00" * (fa.LIMITS["font"] + 10))])),
    ("www.example", "/broken.zip"): Resp(200, b"PK\x03\x04" + b"\x00" * 200),
})
rc, out = run("https://www.example/one.zip", "--to", "fonts/ZG-Regular.ttf", "--preset", "zipg")
pr = shared()["fontPresets"].get("zipg") or {}
check("zip(글꼴 하나) → 안의 글꼴을 --to 에 · 세트 만들고 고름", rc == 0 and (WS / "fonts" / "ZG-Regular.ttf").read_bytes() == ZR and shared()["fontPreset"] == "zipg"
      and pr.get("body", {}).get("latin") == "Zip Gothic" and pr["body"]["measure"] == {"regular": "ZG-Regular.ttf", "bold": "ZG-Regular.ttf"} and "zip 묶음에서 꺼냄: ZIP_GOTHIC_Regular/ZipGothic_Regular.ttf" in out, (rc, out, pr))
check("  묶음을 풀어 놓지 않는다(글꼴 말고는 남지 않음)", not list(WS.rglob("License.txt")) and not list(WS.rglob("*.zip")) and not list(WS.rglob("__MACOSX")))
rc, out = run("https://www.example/all.zip", "--to", "fonts/ZA-Regular.ttf", "--preset", "zipall")
pr = shared()["fontPresets"].get("zipall") or {}
check("zip(여러 개) + --preset → Regular 를 고르고 Bold 를 같이 꺼내 짝짓는다(ExtraBold 아님)", rc == 0 and (WS / "fonts" / "ZA-Regular.ttf").read_bytes() == ZR and (WS / "fonts" / "ZipGothic_Bold.ttf").read_bytes() == ZB
      and pr.get("body", {}).get("measure") == {"regular": "ZA-Regular.ttf", "bold": "ZipGothic_Bold.ttf"} and pr["heading"]["measure"]["bold"] == "ZipGothic_Bold.ttf"
      and "굵은 파일 ZipGothic_Bold.ttf" in out and "안의 글꼴" in out and "--weight bold 로 더한다" not in out, (rc, out, pr))
check("  안의 경로(../)는 저장 자리에 쓰이지 않는다", not (WS / "evil.ttf").exists() and not (WS.parent / "evil.ttf").exists() and not (WS / "fonts" / "TTF").exists())
rc, out = run("https://www.example/all.zip", "--to", "fonts/ZA-Regular.otf")
check("  --to 가 .otf 면 OTF 쪽을 꺼낸다", rc == 0 and (WS / "fonts" / "ZA-Regular.otf").read_bytes() == ZO, (rc, out))
rc, out = run("https://www.example/all.zip", "--to", "fonts/ZA-Bold.ttf")
check("  --to 이름의 Bold → Bold 를 꺼낸다", rc == 0 and (WS / "fonts" / "ZA-Bold.ttf").read_bytes() == ZB, (rc, out))
rc, out = run("https://www.example/all.zip", "--to", "fonts/ZA-B2.ttf", "--preset", "zipall", "--weight", "bold")
check("  --weight bold → Bold 를 꺼내 세트의 굵은 파일로", rc == 0 and (WS / "fonts" / "ZA-B2.ttf").read_bytes() == ZB and shared()["fontPresets"]["zipall"]["body"]["measure"] == {"regular": "ZA-Regular.ttf", "bold": "ZA-B2.ttf"}, (rc, out))
rc, out = run("https://www.example/all.zip", "--to", "fonts/ZA-XB.ttf", "--member", "ExtraBold")
check("  --member 낱말(ExtraBold)", rc == 0 and (WS / "fonts" / "ZA-XB.ttf").read_bytes() == ZX, (rc, out))
rc, out = run("https://www.example/all.zip", "--to", "fonts/ZA-M1.ttf", "--member", "Bold")
check("  --member Bold 는 ExtraBold 에 맞지 않는다", rc == 0 and (WS / "fonts" / "ZA-M1.ttf").read_bytes() == ZB, (rc, out))
rc, out = run("https://www.example/all.zip", "--to", "fonts/ZA-M3.ttf", "--member", "ZipGothic")
check("  --member 가 여러 개에 맞으면 굵기 낱말(Regular)로 마저 고른다", rc == 0 and (WS / "fonts" / "ZA-M3.ttf").read_bytes() == ZR, (rc, out))
rc, out = run("https://www.example/all.zip", "--to", "fonts/ZA-M2.ttf", "--member", "TTF/ZipGothic_ExtraBold.ttf")
check("  --member 안의 경로 그대로", rc == 0 and (WS / "fonts" / "ZA-M2.ttf").read_bytes() == ZX, (rc, out))
for argv, want, what in ((("https://www.example/all.zip", "--to", "fonts/n1.ttf", "--member", "Light"), "안의 글꼴:", "--member 에 맞는 것이 없음(목록을 보여 준다)"),
                         (("https://www.example/multi.zip", "--to", "fonts/n1.ttf"), "여러 개", "굵기 낱말로도 못 고름(목록을 보여 준다)"),
                         (("https://www.example/multi.zip", "--to", "fonts/n1.ttf", "--member", "ZipGothic"), "여러 개", "--member 가 여러 개에 맞음"),
                         (("https://www.example/one.zip", "--to", "fonts/n1.otf"), ".otf 글꼴이 없다", "묶음에 그 확장자가 없음"),
                         (("https://www.example/nofont.zip", "--to", "fonts/n1.ttf"), "글꼴 파일(.ttf·.otf)이 없다", "글꼴이 없는 묶음"),
                         (("https://www.example/fake.zip", "--to", "fonts/n1.ttf"), "글꼴 파일(TTF·OTF)이 아니다", "안의 파일이 글꼴이 아님(머리 검사)"),
                         (("https://www.example/bomb.zip", "--to", "fonts/n1.ttf"), "너무 크다", "풀린 크기가 한도를 넘음"),
                         (("https://www.example/broken.zip", "--to", "fonts/n1.ttf"), "zip 묶음을 읽지 못했다", "깨진 묶음"),
                         (("https://www.example/sg-r.ttf", "--to", "fonts/n1.ttf", "--member", "Regular"), "zip 이 아니다", "zip 이 아닌데 --member"),
                         (("https://www.example/go", "--to", "assets/img/n1.png", "--member", "Regular"), "--member", "그림에 --member")):
    rc, out = run(*argv)
    check(f"  거절: {what} → 1 · 파일 없음", rc == 1 and want in out and not (WS / "fonts" / "n1.ttf").exists() and not (WS / "fonts" / "n1.otf").exists(), (rc, out))
rc, out = run("https://www.example/one.zip", "--to", "assets/img/z.png")
check("  거절: zip 을 그림으로 → 1", rc == 1 and "PNG 가 아니다" in out and not (WS / "assets" / "img" / "z.png").exists(), (rc, out))
(WS / "fonts" / "ZipGothic_Bold.ttf").write_bytes(ZX)  # 굵은 파일 자리에 다른 내용이 이미 있다
rc, out = run("https://www.example/all.zip", "--to", "fonts/ZC-Regular.ttf", "--preset", "zipc")
pr = shared()["fontPresets"].get("zipc") or {}
check("  굵은 파일 자리가 이미 있으면 덮어쓰지 않고 알림 · 보통 굵기는 적용", rc == 0 and (WS / "fonts" / "ZipGothic_Bold.ttf").read_bytes() == ZX and pr.get("body", {}).get("measure") == {"regular": "ZC-Regular.ttf", "bold": "ZC-Regular.ttf"}
      and "굵은 파일을 꺼내지 못했다" in out and "--weight bold" in out, (rc, out, pr))
check("  .part 가 남지 않는다", not list((WS / "fonts").rglob("*.part")))

# ---- 7-3) set_fonts <세트> --from: fonts/ 에 손으로 넣어 둔 파일로 세트 만들기(엔진 요청 #23 - 내려받을 주소가 없는 글꼴)
import subprocess  # noqa: E402
SET_FONTS = str(Path(fa.__file__).with_name("set_fonts.py"))


def set_fonts(*args):
    r = subprocess.run([sys.executable, SET_FONTS, *args], env={**os.environ, "PYTHONIOENCODING": "utf-8"}, cwd=str(WS), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout + r.stderr


(WS / "fonts" / "Hand-Regular.ttf").write_bytes(font("Hand Gothic"))
(WS / "fonts" / "Hand-Bold.ttf").write_bytes(font("Hand Gothic Bold"))
(WS / "fonts" / "page.ttf").write_bytes(HTML)
rc, out = set_fonts("hand", "--from", "Hand-Regular.ttf", "--bold", "Hand-Bold.ttf")
pr = shared()["fontPresets"].get("hand") or {}
check("set_fonts <세트> --from --bold → 세트 만들고 고름(패밀리 이름은 파일에서)", rc == 0 and shared()["fontPreset"] == "hand" and pr.get("body", {}).get("latin") == "Hand Gothic"
      and pr["body"]["measure"] == {"regular": "Hand-Regular.ttf", "bold": "Hand-Bold.ttf"} and pr["heading"]["measure"]["bold"] == "Hand-Bold.ttf" and "sebang" in shared()["fontPresets"], (rc, out, pr))
rc, out = set_fonts()
check("  목록에 새 세트가 보인다", rc == 0 and "hand" in out and "Hand Gothic" in out, (rc, out))
rc, out = set_fonts("sebang")
check("  이름만 주면 예전처럼 고르기", rc == 0 and shared()["fontPreset"] == "sebang", (rc, out))
before = (WS / "nexa-slide.json").read_bytes()
for args, what in ((("x1", "--from", "Missing.ttf"), "없는 파일"), (("x1", "--from", "../nexa-slide.json"), "fonts/ 밖"), (("x1", "--from", "page.ttf"), "글꼴이 아닌 내용"),
                   (("x1", "--from", "NoName.ttf"), "패밀리 이름 없음"), (("bad name!", "--from", "Hand-Regular.ttf"), "세트 이름"), (("x1", "--from", "Hand-Regular.ttf", "--bold", "Missing.ttf"), "없는 굵은 파일")):
    rc, out = set_fonts(*args)
    check(f"  거절: {what} → 설정 그대로", rc != 0 and (WS / "nexa-slide.json").read_bytes() == before, (rc, out))
rc, out = set_fonts("x1", "--from", "NoName.ttf", "--family", "Named Sans")
check("  --family 로 직접", rc == 0 and shared()["fontPresets"]["x1"]["body"]["latin"] == "Named Sans", (rc, out))

# ---- 8) 웹 세션 확인
fa.web_block = lambda: "이 웹 세션에는 웹 접근이 허용되지 않았다"
n = len(SEEN)
rc, out = run("https://www.example/go", "--to", "assets/img/blocked.png")
check("웹 검색 허용이 아닌 세션 → 2 · 접속하지 않음 · 파일 없음", rc == 2 and len(SEEN) == n and not (WS / "assets" / "img" / "blocked.png").exists(), (rc, out))
import importlib  # noqa: E402
real = importlib.reload(fa)  # 바꿔 둔 web_block·resolve_public·_connect 를 실제 함수로 되돌린다
real.running_server = lambda: None
check("서버·세션 없음(터미널 직접 실행) → 허용", real.web_block() is None)
os.environ["NEXA_SLIDE_SESSION"] = "web:claude"
check("웹 세션 환경인데 서버에 확인 못 함 → 거절", real.web_block() is not None)
os.environ.pop("NEXA_SLIDE_SESSION")


class _Open:
    def __init__(self, body):
        self._b = body

    def __enter__(self):
        return io.BytesIO(json.dumps(self._b).encode("utf-8"))

    def __exit__(self, *a):
        return False


real.running_server = lambda: {"url": "http://127.0.0.1:1/"}
for body, want, what in (({"state": "off"}, True, "세션 없음 → 허용"), ({"state": "running", "allowWeb": False}, False, "턴 실행 중 · 웹 허용 아님 → 거절"),
                         ({"state": "ready", "allowWeb": False}, False, "대기 중 · 웹 허용 아님 → 거절"), ({"state": "running", "allowWeb": True}, True, "웹 검색 허용 세션 → 허용")):
    real.urllib.request.urlopen = lambda url, timeout=0, _b=body: _Open(_b)
    check(f"  서버 답 {what}", (real.web_block() is None) == want, real.web_block())
os.environ["NEXA_SLIDE_SESSION"] = "manual"  # 환경 변수를 바꿔도 서버의 답이 정한다
real.urllib.request.urlopen = lambda url, timeout=0: _Open({"state": "running", "allowWeb": False})
check("  환경 변수를 바꿔도 서버의 답(웹 허용 아님)이 이긴다", real.web_block() is not None)
os.environ.pop("NEXA_SLIDE_SESSION")
check("공인 주소 검사 함수는 그대로(되돌림 확인)", refused(real.resolve_public, "127.0.0.1") is not None and real_resolve is not None)

print("\n실패:", FAILS or "없음")
print("전부 통과" if not FAILS else "")
sys.exit(1 if FAILS else 0)
