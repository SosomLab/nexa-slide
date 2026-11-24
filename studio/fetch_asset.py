# -*- coding: utf-8 -*-
"""공개 웹의 그림·글꼴 파일을 작업 공간으로 가져오기 - 로고·CI 그림은 assets/ 아래, 글꼴은 fonts/ 아래로만.

    python3 nexa.py fetch_asset <https 주소> --to assets/brand/acme-logo.png
    python3 nexa.py fetch_asset <https 주소> --to assets/brand/acme-logo.png --brand logo   # 받은 그림을 nexa-slide.json 의 brand.logo 로
    python3 nexa.py fetch_asset <https 주소> --to fonts/Acme-Regular.ttf
    python3 nexa.py fetch_asset <https 주소> --to fonts/Acme-Regular.ttf --preset acme                # 받은 글꼴로 글꼴 세트 acme 를 만들고 고른다
    python3 nexa.py fetch_asset <https 주소> --to fonts/Acme-Bold.ttf --preset acme --weight bold    # 그 세트의 굵은 글꼴 파일
    python3 nexa.py fetch_asset --url-file out/.studio/url.txt --to assets/img/photo.jpg    # 주소에 & 가 있으면(Windows python 래퍼가 인자를 자른다)

덱의 image 요소 src 에 https 주소를 그대로 넣으면 PPTX 에서 "이미지 없음" 이 된다 - 이 명령으로 받아 둔 뒤 그 경로(--to 값)를 src 에 쓴다.

지키는 것
  - 주소: https(443)만, 사용자 정보(user:pw@) 없음. 호스트가 가리키는 IP 가 모두 공인 주소여야 한다(사설·루프백·링크 로컬·내부망은 거절).
    리다이렉트(5번까지)도 매번 같은 검사를 하고, 확인한 그 IP 로 접속한다. 쿠키·인증 머리는 보내지 않는다.
  - 종류: 그림 .png .jpg .jpeg .svg → assets/ 아래 · 글꼴 .ttf .otf → fonts/ 아래(nexa-slide.json fontsDir). 그 밖의 확장자·폴더는 거절.
    내용이 확장자와 맞아야 한다(파일 머리 확인 - 오류 쪽 HTML 이 logo.png 로 저장되지 않게). SVG 는 스크립트·이벤트 속성·외부 엔티티가 있으면 거절.
  - 크기: 그림 10 MB · SVG 2 MB · 글꼴 30 MB 까지. 전체 60초.
  - 이미 있는 파일은 덮어쓰지 않는다. --force 면 기존 파일을 out/.history/fetch/<시각>/ 에 백업하고 바꾼다.
  - 웹 세션 안에서는 그 세션에 **웹 검색 허용**(관리자가 켬)이 있을 때만 동작한다 - 작업 공간 서버에 물어 확인한다.
  - 주소(쿼리 포함)에 덱 내용·사내 이름·개인 정보를 넣지 않는다. 로고·글꼴은 상표·라이선스가 있다 - 쓸 권리가 있는 것만 받는다.

--brand logo|wordmark|favicon: 받은 그림을 공유 설정 nexa-slide.json 의 brand.<키> 로 적는다(그림만). 새로 빌드하는 장과 편집기 머리 로고가 따라 바뀐다
(서버 재시작 뒤). **이미 만든 덱의 로고 요소는 src 가 덱에 적혀 있어** 자동으로 바뀌지 않는다 - 옛 경로를 쓰는 요소 목록을 출력하니
draft_deck → src 수정 → save_deck 으로 바꾼다(또는 같은 경로에 --force 로 덮어쓰면 덱을 고치지 않아도 된다).
--preset <세트>: 받은 글꼴을 작업 공간에 적용한다 - 공유 설정의 fontPresets.<세트>(본문·제목 = 이 글꼴, 코드 글꼴은 템플릿 것)를 만들고 fontPreset 으로 고른다.
패밀리 이름은 글꼴 파일(name 표)에서 읽는다(--family 로 직접 줄 수 있다). 파일은 fonts/ 바로 아래에 받는다. --weight bold 는 이미 만든 세트의 굵은 파일만 바꾼다.
종료 코드: 0 저장됨 · 1 거절·실패 · 2 이 세션에 웹이 허용되지 않음
"""
import argparse
import datetime as dt
import hashlib
import http.client
import ipaddress
import json
import os
import re
import socket
import ssl
import struct
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ASSET_ROOT, CONFIG_NAME, DECKS, LOCAL_NAME, OUT, WORKSPACE, fonts_dir, read_config, resolve_tokens, running_server  # noqa: E402

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".svg")
FONT_EXTS = (".ttf", ".otf")
MB = 1024 * 1024
LIMITS = {"image": 10 * MB, "svg": 2 * MB, "font": 30 * MB}
MAX_REDIRECTS = 5
TOTAL_SEC = 60  # 전체 시간(리다이렉트 포함)
SOCK_SEC = 15   # 접속·읽기 한 번
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; nexa-slide fetch_asset)", "Accept": "*/*", "Accept-Encoding": "identity"}  # 쿠키·Referer·인증 없음
NAME_RX = re.compile(r"[A-Za-z0-9가-힣_-][A-Za-z0-9가-힣._-]{0,79}")  # 경로 조각 - 점으로 시작하지 않는다
WINDOWS_RESERVED = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}
BRAND_KEYS = {"logo": "assets/brand/logo.png", "wordmark": "assets/brand/wordmark.png", "favicon": ""}  # 키 → 설정에 없을 때 덱이 쓰는 기본 경로(layouts.py)
SVG_BAD = (("<script", "스크립트"), ("<foreignobject", "foreignObject"), ("javascript:", "javascript: 주소"), ("<!entity", "엔티티 선언"))


class Refuse(Exception):
    """가져오지 않는 이유(사용자에게 그대로 보인다)."""


# ---------- 주소 ----------
def check_url(url):
    """https 주소 검사 → (호스트(ASCII), 요청 대상 path?query). 아니면 Refuse."""
    url = str(url or "").strip()
    if not url or len(url) > 2000 or re.search(r"[\s\x00-\x1f\x7f]", url):
        raise Refuse("주소가 비었거나 너무 길거나 공백·제어 문자가 있다")
    try:
        u = urllib.parse.urlsplit(url)
        port = u.port
    except ValueError as e:
        raise Refuse(f"주소를 읽지 못했다: {e}")
    if u.scheme.lower() != "https":
        raise Refuse("https 주소만 받는다")
    if u.username is not None or u.password is not None:
        raise Refuse("주소에 사용자 정보(user:pw@)를 둘 수 없다")
    if not u.hostname:
        raise Refuse("주소에 호스트가 없다")
    if port not in (None, 443):
        raise Refuse("https 기본 포트(443)만 받는다")
    try:
        host = u.hostname.encode("idna").decode("ascii").lower()
    except UnicodeError:
        raise Refuse(f"호스트 이름을 읽지 못했다: {u.hostname}")
    target = urllib.parse.quote(u.path or "/", safe="/%:@!$&'()*+,;=~-._")
    if u.query:
        target += "?" + urllib.parse.quote(u.query, safe="/%:@!$&'()*+,;=~-._?")
    return host, target


def resolve_public(host):
    """호스트 → 접속할 IP(문자열). 이름이 가리키는 주소가 **하나라도** 공인 주소가 아니면 Refuse(내부망·루프백·메타데이터 주소로 새지 않게)."""
    try:
        infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError as e:
        raise Refuse(f"주소를 찾지 못했다: {host} ({e})")
    ips = []
    for info in infos:
        ip = ipaddress.ip_address(str(info[4][0]).split("%")[0])
        if ip.version == 6 and ip.ipv4_mapped is not None:
            ip = ip.ipv4_mapped
        if not ip.is_global or ip.is_multicast:
            raise Refuse(f"공인 주소가 아닌 곳은 받지 않는다: {host} → {ip}")
        if str(ip) not in ips:
            ips.append(str(ip))
    if not ips:
        raise Refuse(f"주소를 찾지 못했다: {host}")
    return sorted(ips, key=lambda s: ":" in s)[0]  # IPv4 먼저


class _Pinned(http.client.HTTPSConnection):
    """검사한 IP 로 접속하되 인증서·SNI 는 호스트 이름으로 - 검사와 접속 사이에 DNS 답이 바뀌어도 다른 곳으로 가지 않는다."""

    def __init__(self, host, ip):
        self._ctx = ssl.create_default_context()
        super().__init__(host, 443, timeout=SOCK_SEC, context=self._ctx)
        self._ip = ip

    def connect(self):
        sock = socket.create_connection((self._ip, 443), SOCK_SEC)
        self.sock = self._ctx.wrap_socket(sock, server_hostname=self.host)


def _connect(host, ip):
    return _Pinned(host, ip)


def download(url, limit):
    """url → (bytes, 마지막 주소). 환경 변수의 프록시는 쓰지 않는다(검사한 IP 로 직접 접속)."""
    deadline = time.monotonic() + TOTAL_SEC
    for _hop in range(MAX_REDIRECTS + 1):
        host, target = check_url(url)
        conn = _connect(host, resolve_public(host))
        try:
            conn.request("GET", target, headers=HEADERS)
            r = conn.getresponse()
            if r.status in (301, 302, 303, 307, 308):
                loc = r.getheader("Location")
                if not loc:
                    raise Refuse(f"리다이렉트({r.status})에 Location 이 없다")
                url = urllib.parse.urljoin(url, loc)
                continue
            if r.status != 200:
                raise Refuse(f"서버 응답 {r.status} {r.reason or ''}".rstrip())
            n = r.getheader("Content-Length") or ""
            if n.isdigit() and int(n) > limit:
                raise Refuse(f"파일이 너무 크다({int(n) // 1024} KB) - {limit // MB} MB 까지")
            buf = bytearray()
            while True:
                chunk = r.read(65536)
                if not chunk:
                    break
                buf += chunk
                if len(buf) > limit:
                    raise Refuse(f"파일이 너무 크다 - {limit // MB} MB 까지")
                if time.monotonic() > deadline:
                    raise Refuse(f"시간 초과({TOTAL_SEC}초)")
            return bytes(buf), url
        except (OSError, http.client.HTTPException) as e:
            raise Refuse(f"내려받지 못했다({host}): {type(e).__name__}: {e}")
        finally:
            conn.close()
    raise Refuse(f"리다이렉트가 너무 많다({MAX_REDIRECTS}번 넘음)")


# ---------- 저장 자리 · 내용 ----------
def dest(to):
    """--to(작업 공간 기준 상대 경로) → (종류 image|font, 디스크 경로, 표시·src 용 상대 경로). assets/ · fonts/ 아래가 아니면 Refuse."""
    s = str(to or "").strip().replace("\\", "/")
    parts = s.split("/")
    if not s or s.startswith("/") or re.match(r"[A-Za-z]:", s) or len(parts) > 8:
        raise Refuse("--to 는 작업 공간 기준 상대 경로(예 assets/brand/logo.png · fonts/Acme-Regular.ttf)")
    for p in parts:
        if not NAME_RX.fullmatch(p) or p.endswith(".") or p.split(".")[0].lower() in WINDOWS_RESERVED:
            raise Refuse(f"--to 에 쓸 수 없는 이름: {p or '(빈 조각)'} - 영문·숫자·한글·-·_·. 만, .. 없이")
    ext = Path(parts[-1]).suffix.lower()
    if ext in IMAGE_EXTS:
        kind, base, path = "image", ASSET_ROOT / "assets", ASSET_ROOT.joinpath(*parts)
        if parts[0] != "assets" or len(parts) < 2:
            raise Refuse("그림(" + " ".join(IMAGE_EXTS) + ")은 assets/ 아래로만 저장한다")
    elif ext in FONT_EXTS:
        kind, base, path = "font", fonts_dir(), fonts_dir().joinpath(*parts[1:])
        if parts[0] != "fonts" or len(parts) < 2:
            raise Refuse("글꼴(" + " ".join(FONT_EXTS) + ")은 fonts/ 아래로만 저장한다")
    else:
        raise Refuse(f"받지 않는 확장자: {ext or '(없음)'} - 그림 {' '.join(IMAGE_EXTS)} · 글꼴 {' '.join(FONT_EXTS)}")
    base, real = base.resolve(), path.resolve()
    if base not in real.parents:  # 폴더 링크로 밖을 가리키는 경우까지
        raise Refuse("저장 자리가 assets/ · fonts/ 밖을 가리킨다")
    if real.is_dir():
        raise Refuse(f"그 이름의 폴더가 있다: {s}")
    return kind, real, s


def sniff(data, ext):
    """내용이 확장자와 맞는지 - 안 맞으면 Refuse. 그림이면 (가로, 세로) 또는 None 을 돌려준다(PNG 만 읽는다)."""
    if not data:
        raise Refuse("빈 파일이다")
    if ext == ".png":
        if not data.startswith(b"\x89PNG\r\n\x1a\n") or len(data) < 24:
            raise Refuse("PNG 가 아니다(파일 머리가 다르다 - 오류 쪽이나 다른 형식일 수 있다)")
        return struct.unpack(">II", data[16:24])
    if ext in (".jpg", ".jpeg"):
        if not data.startswith(b"\xff\xd8\xff"):
            raise Refuse("JPEG 가 아니다(파일 머리가 다르다)")
        return None
    if ext == ".svg":
        if len(data) > LIMITS["svg"]:
            raise Refuse(f"SVG 가 너무 크다 - {LIMITS['svg'] // MB} MB 까지")
        try:
            low = data.decode("utf-8-sig").lower()
        except UnicodeDecodeError:
            raise Refuse("SVG 가 아니다(UTF-8 글이 아니다)")
        if "<svg" not in low[:8192]:
            raise Refuse("SVG 가 아니다(<svg 가 없다)")
        for needle, what in SVG_BAD:
            if needle in low:
                raise Refuse(f"SVG 에 {what} 가 있어 받지 않는다")
        if re.search(r"[\s\"'/]on[a-z]+\s*=", low):
            raise Refuse("SVG 에 이벤트 속성(on…=)이 있어 받지 않는다")
        return None
    if data[:4] not in (b"\x00\x01\x00\x00", b"OTTO", b"true"):  # TrueType · OpenType(CFF) · 옛 Mac TrueType
        raise Refuse("글꼴 파일(TTF·OTF)이 아니다(파일 머리가 다르다 - 묶음 .ttc·.woff·압축 파일은 받지 않는다)")
    return None


def save(path, data, force):
    """원자적으로 쓴다. 이미 있으면 force 일 때만 - 기존 파일은 out/.history/fetch/<시각>/ 에 백업. 백업 경로(없으면 None)를 돌려준다."""
    backup = None
    if path.is_file():
        if path.read_bytes() == data:
            return None
        if not force:
            raise Refuse(f"이미 있는 파일이다: {path.name} - 다른 이름으로 받거나, 바꾸려면 --force(기존 파일은 백업한다)")
        hist = OUT / ".history" / "fetch" / dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:22]
        backup = hist / path.name
        hist.mkdir(parents=True, exist_ok=True)
        backup.write_bytes(path.read_bytes())
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    part.write_bytes(data)
    os.replace(part, path)
    return backup


# ---------- brand ----------
def set_brand(key, rel):
    """공유 설정 nexa-slide.json 의 brand.<key> = rel. 바꾸기 전 값(없으면 기본 경로)을 돌려준다."""
    shared = read_config(shared=True)  # 공유 파일에만 쓴다(PC 별 nexa-slide.local.json 값은 섞지 않는다)
    brand = shared.get("brand") if isinstance(shared.get("brand"), dict) else {}
    old = brand.get(key) or BRAND_KEYS[key]
    shared["brand"] = {**brand, key: rel}
    (WORKSPACE / CONFIG_NAME).write_text(json.dumps(shared, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return old


# ---------- 글꼴 세트 ----------
PRESET_RX = re.compile(r"[A-Za-z0-9_-]{1,64}")


def family_name(data):
    """글꼴 파일의 패밀리 이름(name 표의 nameID 1) - 영문(Windows 0x409) 먼저, 없으면 다른 언어, 못 읽으면 None."""
    try:
        num = struct.unpack(">H", data[4:6])[0]
        tab = next(o for tag, _cs, o, _ln in (struct.unpack(">4sIII", data[12 + i * 16:28 + i * 16]) for i in range(num)) if tag == b"name")
        count, strings = struct.unpack(">HH", data[tab + 2:tab + 6])
        found = {}
        for i in range(count):
            plat, _enc, lang, nid, ln, off = struct.unpack(">6H", data[tab + 6 + i * 12:tab + 18 + i * 12])
            if nid != 1 or plat not in (1, 3):
                continue
            raw = data[tab + strings + off:tab + strings + off + ln]
            s = " ".join(raw.decode("utf-16-be" if plat == 3 else "mac_roman", "replace").split())
            if s:
                found.setdefault(0 if (plat, lang) == (3, 0x409) else 1 if plat == 3 else 2, s)
        return found[min(found)] if found else None
    except (StopIteration, struct.error, ValueError):
        return None


def preset_check(name, weight):
    """내려받기 전 검사 - 세트 이름, 템플릿(엔진)의 세트와 같은 이름은 쓰지 않는다(작업 공간 것이 가려 버린다), bold 는 있는 세트에만."""
    if not PRESET_RX.fullmatch(name):
        raise Refuse("글꼴 세트 이름은 영문·숫자·-·_ 로 1~64자")
    shared = read_config(shared=True)
    mine = shared.get("fontPresets") if isinstance(shared.get("fontPresets"), dict) else {}
    if name not in mine and name in (resolve_tokens({**shared, "fontPresets": None}).get("fontPresets") or {}):
        raise Refuse(f"템플릿의 글꼴 세트와 같은 이름은 쓸 수 없다: {name} - 다른 이름을 고른다")
    cur = mine.get(name) if isinstance(mine.get(name), dict) else {}
    if weight == "bold" and not isinstance((cur.get("body") or {}).get("measure"), dict):
        raise Refuse(f"글꼴 세트 {name} 가 아직 없다 - 보통 굵기 파일을 먼저 --preset {name} 로 받는다")


def set_preset(name, weight, fname, family):
    """공유 설정 nexa-slide.json 의 fontPresets.<name> 을 만들거나 고치고 fontPreset 으로 고른다(마법사 hub.create_template 와 같은 모양).
    regular = 세트를 이 글꼴로(굵은 파일이 아직 없으면 같은 파일) · bold = 있는 세트의 굵은 파일만 바꾼다. 세트(dict)를 돌려준다."""
    shared = read_config(shared=True)  # 공유 파일에만 쓴다(PC 별 nexa-slide.local.json 값은 섞지 않는다)
    presets = shared.get("fontPresets") if isinstance(shared.get("fontPresets"), dict) else {}
    cur = presets.get(name) if isinstance(presets.get(name), dict) else None
    if weight == "bold":  # 세트가 있는지는 preset_check 가 내려받기 전에 봤다
        for role in ("body", "heading"):
            if isinstance((cur.get(role) or {}).get("measure"), dict):
                cur[role]["measure"]["bold"] = fname
    else:
        body = (cur or {}).get("body") if isinstance((cur or {}).get("body"), dict) else {}
        old = body.get("measure") if isinstance(body.get("measure"), dict) else {}
        bold = old.get("bold") if body.get("latin") == family and old.get("bold") != old.get("regular") else None  # 같은 글꼴의 굵은 파일은 지킨다
        face = {"css": f'"{family}", "Malgun Gothic", "맑은 고딕", "Apple SD Gothic Neo", sans-serif', "latin": family, "ea": family,
                "measure": {"regular": fname, "bold": bold or fname}}
        cur = {**(cur or {}), "body": dict(face, measure=dict(face["measure"])), "heading": dict(face, measure=dict(face["measure"]))}
        cur.pop("pptTextShift", None)  # 글꼴이 바뀌었으니 줄 배치 보정은 새 파일의 메트릭으로 다시 계산되게
    shared["fontPresets"] = {**presets, name: cur}
    shared["fontPreset"] = name
    (WORKSPACE / CONFIG_NAME).write_text(json.dumps(shared, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return cur


def _image_ids(els, src):
    for e in els if isinstance(els, list) else []:
        if isinstance(e, dict):
            if e.get("type") == "image" and e.get("src") == src:
                yield str(e.get("id"))
            yield from _image_ids(e.get("elements"), src)  # 묶음 안


def deck_uses(src):
    """src 를 쓰는 image 요소 - [(덱, [(장, 요소)…])]. 덱은 읽기만 한다(고치는 것은 save_deck)."""
    out = []
    for f in sorted(DECKS.glob("*.json")) if DECKS.is_dir() else []:
        try:
            deck = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(deck, dict) or not isinstance(deck.get("slides"), list):
            continue
        hits = [(str(s.get("id")), i) for s in deck["slides"] if isinstance(s, dict) for i in _image_ids(s.get("elements"), src)]
        if hits:
            out.append((f.stem, hits))
    return out


# ---------- 웹 세션 확인 ----------
def web_block():
    """이 작업 공간에 웹 세션이 살아 있는데 웹 검색 허용이 아니면 거절 이유, 아니면 None.
    세션이 준 환경 변수가 아니라 **작업 공간 서버에 물어** 정한다(.env·환경 변수로 바꿀 수 없게). 서버·세션이 없으면 터미널 사용자의 직접 실행이다."""
    in_web = (os.environ.get("NEXA_SLIDE_SESSION") or "").startswith("web:")
    why = "이 웹 세션에는 웹 접근이 허용되지 않았다 - 관리자가 전역 설정의 '웹 검색 허용'을 켜고 세션을 '웹 검색 허용'으로 다시 시작해야 한다"
    run = running_server()
    if not run:
        return why + "(작업 공간 서버에 확인하지 못함)" if in_web else None
    try:
        with urllib.request.urlopen(f"{run['url']}api/wsession", timeout=5) as r:
            info = json.loads(r.read().decode("utf-8"))
    except Exception:  # noqa: BLE001 - 응답 없음·형식 오류
        return why + "(작업 공간 서버에 확인하지 못함)" if in_web else None
    if (info.get("state") or "off") == "off":
        return None
    return None if info.get("allowWeb") else why


def main(argv=None):
    ap = argparse.ArgumentParser(description="공개 웹의 그림·글꼴 파일을 작업 공간 assets/ · fonts/ 로 가져오기")
    ap.add_argument("url", nargs="?", help="https 주소")
    ap.add_argument("--url-file", help="주소를 적은 글 파일(첫 줄) - 주소에 & 등이 있어 인자로 못 넘길 때")
    ap.add_argument("--to", required=True, help="저장할 자리(작업 공간 기준) - 그림 assets/… · 글꼴 fonts/…")
    ap.add_argument("--force", action="store_true", help="이미 있는 파일을 바꾼다(기존 파일은 out/.history/fetch/ 에 백업)")
    ap.add_argument("--brand", choices=sorted(BRAND_KEYS), help="받은 그림을 nexa-slide.json 의 brand.<키> 로 적는다")
    ap.add_argument("--preset", help="받은 글꼴로 글꼴 세트(nexa-slide.json fontPresets.<이름>)를 만들고 그 세트를 고른다")
    ap.add_argument("--weight", choices=("regular", "bold"), default="regular", help="--preset 과 함께 - bold 면 있는 세트의 굵은 글꼴 파일만 바꾼다")
    ap.add_argument("--family", help="--preset 과 함께 - 글꼴 패밀리 이름(비우면 글꼴 파일에서 읽는다)")
    a = ap.parse_args(argv)
    try:
        why = web_block()
        if why:
            print(f"가져오지 않음: {why}", file=sys.stderr)
            return 2
        url = a.url
        if a.url_file:
            uf = Path(a.url_file).resolve()
            if WORKSPACE.resolve() not in uf.parents or not uf.is_file():
                raise Refuse(f"--url-file 은 작업 공간 안의 글 파일: {a.url_file}")
            lines = uf.read_text(encoding="utf-8-sig", errors="replace").split()
            url = lines[0] if lines else ""
        if not url:
            raise Refuse("주소를 준다(인자 또는 --url-file)")
        check_url(url)
        kind, path, rel = dest(a.to)
        ext = path.suffix.lower()
        if a.brand and kind != "image":
            raise Refuse("--brand 는 그림에만 쓴다")
        if a.preset:
            if kind != "font" or path.parent != fonts_dir().resolve():
                raise Refuse("--preset 은 글꼴에만 쓴다 - fonts/ 바로 아래(--to fonts/<파일 이름>)로 받는다")
            preset_check(a.preset, a.weight)
        if path.is_file() and not a.force:
            raise Refuse(f"이미 있는 파일이다: {rel} - 다른 이름으로 받거나, 바꾸려면 --force(기존 파일은 백업한다)")
        data, final = download(url, LIMITS[kind])
        size = sniff(data, ext)
        family = " ".join((a.family or family_name(data) or "").split()) if a.preset else ""
        if a.preset and a.weight == "regular" and (not family or '"' in family or len(family) > 60):  # 파일을 쓰기 전에
            raise Refuse("글꼴 파일에서 패밀리 이름을 읽지 못했다 - --family \"<글꼴 이름>\" 으로 준다")
        backup = save(path, data, a.force)
        preset = set_preset(a.preset, a.weight, path.name, family) if a.preset else None
    except Refuse as e:
        print(f"가져오지 않음: {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"가져오지 않음: 파일을 쓰지 못했다 - {e}", file=sys.stderr)
        return 1
    print(f"저장됨: {rel} · {len(data):,} 바이트" + (f" · {size[0]}×{size[1]}px" if size else "") + f" · sha256 {hashlib.sha256(data).hexdigest()[:12]}")
    print(f"출처: {final}")
    if backup:
        print(f"기존 파일 백업: {backup.relative_to(WORKSPACE) if WORKSPACE in backup.parents else backup}")
    if preset:
        ms = preset["body"]["measure"]
        print(f"글꼴 세트 {a.preset}: {preset['body']['latin']} · 보통 {ms['regular']} · 굵게 {ms['bold']} → fontPreset = {a.preset} ({CONFIG_NAME})")
        if read_config().get("fontPreset") != a.preset:
            print(f"알림: 이 PC 의 {LOCAL_NAME} 에 fontPreset 이 있어 이 PC 에서는 그 값이 쓰인다")
        if ms["regular"] == ms["bold"]:
            print(f"다음: 굵은 글꼴 파일이 따로 있으면 fetch_asset <주소> --to fonts/<파일> --preset {a.preset} --weight bold 로 더한다.")
        print("다음: 편집기는 새로 고치면 이 글꼴로 보인다. PowerPoint 에 쓰려면 install_fonts, PPTX 는 다시 내보낸다. 글꼴은 라이선스를 확인한다(배포·임베드 허용 범위).")
        return 0
    if kind == "font":
        print("다음: 글꼴 세트는 nexa-slide.json 의 fontPresets 에 정의하고(measure 에 이 파일 이름) set_fonts <세트> 로 고른다. PowerPoint 에 쓰려면 install_fonts. "
              "글꼴은 라이선스를 확인한다(배포·임베드 허용 범위).")
        return 0
    if not a.brand:
        print(f'다음: image 요소의 src 에 "{rel}" 를 쓴다(draft_deck → 사본 수정 → save_deck).')
        return 0
    old = set_brand(a.brand, rel)
    print(f"brand.{a.brand}: {old or '(없음)'} → {rel} ({CONFIG_NAME})")
    if ((read_config().get("brand") or {}).get(a.brand)) != rel:
        print(f"알림: 이 PC 의 {LOCAL_NAME} 에 brand.{a.brand} 가 있어 이 PC 에서는 그 값이 쓰인다")
    if a.brand == "logo" and ext != ".png":
        print("알림: 로고의 가로세로 비율은 PNG 머리에서 읽는다 - PNG 가 아니면 기본 비율로 배치되니 로고 요소의 크기를 직접 맞춘다")
    uses = deck_uses(old) if old and old != rel else []
    if uses:
        print(f"이미 만든 덱에서 옛 경로({old})를 쓰는 요소 - src 를 \"{rel}\" 로 바꾼다(draft_deck → 사본 수정 → save_deck)"
              + (f", 상자 비율은 {size[0]}:{size[1]}" if size else "") + ":")
        for deck, hits in uses:
            print(f"  {deck}: " + ", ".join(f"{s} {e}" for s, e in hits[:30]) + (f" … 외 {len(hits) - 30}곳" if len(hits) > 30 else ""))
    print("다음: 서버를 다시 시작해야 새 장·편집기 머리 로고에 반영된다(python3 nexa.py restart - 웹 세션 안이면 사용자에게 재시작을 안내).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
