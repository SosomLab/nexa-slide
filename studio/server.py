# -*- coding: utf-8 -*-
"""nexa-slide 로컬 서버 (표준 라이브러리만).

    python3 studio/server.py --workspace <작업 공간> [--port N | --port auto]

포트: --port > nexa-slide.json "port" > 5600. 이미 쓰는 포트면 알리고 끝낸다(--port auto 는 그 포트부터 빈 포트를 찾는다).
작업 공간마다 포트를 다르게 주면 여러 작업 공간의 서버를 함께 띄울 수 있다. 실행 중 정보는 <out>/.studio/server.json.

정적 경로
  /studio/…   엔진 폴더(편집기 index.html·render.js·studio.js). /studio/tokens.json 은 작업 공간 토큰(없으면 엔진 기본값)
  /out/…      작업 공간 산출물(PPTX·렌더 PNG). 점(.)으로 시작하는 경로는 막는다(.studio 상태·.history 백업)
  그 밖       assetRoot(덱 그림 경로 src·img 의 기준 폴더)
API
  GET  /api/decks                    덱 목록
  GET  /api/deck/<id>                덱 JSON (헤더 X-Deck-Version = 파일 mtime_ns)
  PUT  /api/deck/<id>?base=<ver>     덱 저장(원자적 쓰기, .history 백업 50개). base 가 현재와 다르면 409 (force=1 이면 무시)
  GET  /api/version/<id>             {"deck": ver, "requests": ver}
  GET  /api/requests/<id>            요청 메모 목록
  POST /api/requests/<id>            {"action": "add"|"update"|"delete", ...}
  POST /api/export/<id>              PPTX 생성 → {"url": "/out/<id>.pptx"}
  GET  /api/render/<id>              마지막 PowerPoint 렌더 PNG 목록
  POST /api/render/<id>              PPTX 생성 + PowerPoint COM 으로 PNG 렌더
  GET  /api/layouts                  레이아웃 목록
  POST /api/newslide                 {"layout", "part"} → 자리 표시 내용으로 만든 슬라이드
  GET  /api/fonts                    글꼴 프리셋 목록·현재 값
  GET  /api/fontfile/<이름>          설치된 글꼴 파일(편집기 @font-face 용 — fonts.css)
  POST /api/fonts                    {"preset": 이름} → tokens.json 의 fonts 를 그 프리셋으로(set_fonts.py)
  GET  /api/config                   작업 공간 이름·브랜드(로고·워드마크·파비콘·로고 비율)
  GET  /api/session                  Claude 세션 연결 상태(watch_requests.py 하트비트) + 처리 중 요청 수
  POST /api/flush/<id>               "지금 보내기" — 대기 시간 없이 열린 요청을 세션에 바로 전달하라는 신호
"""
import argparse
import datetime as dt
import json
import mimetypes
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

STUDIO = Path(__file__).resolve().parent
sys.path.insert(0, str(STUDIO))
from common import ASSET_ROOT, BRAND, CONFIG, DECKS, DEFAULT_PORT, OUT, SERVER_INFO, STATE, TOKENS, WORKSPACE, running_server, safe_id  # noqa: E402
from watch_requests import session_status  # noqa: E402

HISTORY_KEEP = 50
RENDER_LOCK = threading.Lock()
WRITE_LOCK = threading.Lock()
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/vnd.openxmlformats-officedocument.presentationml.presentation", ".pptx")


def ver(p: Path):
    try:
        return str(p.stat().st_mtime_ns)
    except FileNotFoundError:
        return "0"


def deck_path(i):
    return DECKS / f"{i}.json"


def req_path(i):
    return DECKS / f"{i}.requests.json"


def atomic_write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        for k in range(5):  # Windows: 다른 프로세스가 잠깐 열고 있으면 재시도
            try:
                os.replace(tmp, path)
                return
            except PermissionError:
                time.sleep(0.1 * (k + 1))
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def backup(i):
    src = deck_path(i)
    if not src.exists():
        return
    h = DECKS / ".history" / i
    h.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, h / (dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".json"))
    files = sorted(h.glob("*.json"))
    for old in files[:-HISTORY_KEEP]:
        old.unlink(missing_ok=True)


def dumps(o):
    return json.dumps(o, ensure_ascii=False, indent=1)


def run(cmd, timeout):
    r = subprocess.run(cmd, cwd=str(WORKSPACE), capture_output=True, timeout=timeout,
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    out = (r.stdout or b"").decode("utf-8", "replace") + (r.stderr or b"").decode("utf-8", "replace")
    return r.returncode, out.strip()


def export(i):
    return run([sys.executable, str(STUDIO / "export_pptx.py"), i], 120)


def render_list(i):
    d = OUT / i
    files = sorted(d.glob("slide-*.png")) if d.exists() else []
    return [f"/out/{i}/{f.name}?v={f.stat().st_mtime_ns}" for f in files]


class H(BaseHTTPRequestHandler):
    server_version = "nexa-slide/0.2"

    def log_message(self, fmt, *args):
        if any(k in (self.path or "") for k in ("/api/version/", "/api/session")):
            return  # 2초 폴링은 기록하지 않는다
        sys.stderr.write("%s %s\n" % (self.log_date_time_string(), fmt % args))

    # ---------- 응답 도우미 ----------
    def send_json(self, obj, status=200, headers=None):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(b)

    def err(self, status, msg):
        self.send_json({"ok": False, "error": msg}, status)

    def body_json(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b""
        return json.loads(raw.decode("utf-8") or "null")

    # ---------- 라우팅 ----------
    def route(self, method):
        u = urlparse(self.path)
        parts = [unquote(p) for p in u.path.split("/") if p]
        q = parse_qs(u.query)
        if not parts or parts[0] != "api":
            if method == "GET" or method == "HEAD":
                return self.static(u.path, head=method == "HEAD")
            return self.err(405, "method")
        name = parts[1] if len(parts) > 1 else ""
        arg = parts[2] if len(parts) > 2 else None
        if arg is not None and not safe_id(arg):
            return self.err(400, "잘못된 id")
        try:
            fn = getattr(self, f"api_{method.lower()}_{name}", None)
            if fn is None:
                return self.err(404, "없는 API")
            return fn(arg, q)
        except json.JSONDecodeError as e:
            return self.err(400, f"JSON 오류: {e}")
        except Exception as e:  # noqa: BLE001
            return self.err(500, f"{type(e).__name__}: {e}")

    def do_GET(self):
        self.route("GET")

    def do_HEAD(self):
        self.route("HEAD")

    def do_PUT(self):
        self.route("PUT")

    def do_POST(self):
        self.route("POST")

    # ---------- 정적 ----------
    def static(self, path, head=False):
        if path in ("", "/", "/studio"):
            self.send_response(302)
            self.send_header("Location", "/studio/")
            self.end_headers()
            return
        rel = unquote(path).lstrip("/")
        parts = Path(rel).parts
        if any(p.startswith(".") for p in parts):
            return self.err(403, "숨김 경로")
        if parts and parts[0] == "studio":  # 엔진 파일
            root, rel = STUDIO, "/".join(parts[1:])
            if rel == "tokens.json":
                root, rel = TOKENS.parent, TOKENS.name
        elif parts and parts[0] == "out":  # 작업 공간 산출물
            root, rel = OUT, "/".join(parts[1:])
        else:  # 덱 그림 경로 기준 폴더
            root = ASSET_ROOT
        root = root.resolve()
        p = (root / rel).resolve()
        if root not in p.parents and p != root:
            return self.err(403, "허용 폴더 밖")
        if p.is_dir():
            p = p / "index.html"
        if not p.is_file():
            return self.err(404, "없음")
        ctype = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
            ctype += "; charset=utf-8"
        data = p.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if not head:
            self.wfile.write(data)

    # ---------- 덱 ----------
    def api_get_decks(self, _, q):
        out = []
        for f in sorted(DECKS.glob("*.json")):
            if f.name.endswith(".requests.json"):
                continue
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
                out.append({"id": f.stem, "title": d.get("title", f.stem), "slides": len(d.get("slides", [])),
                            "updated": d.get("updated", ""), "version": ver(f)})
            except Exception as e:  # noqa: BLE001
                out.append({"id": f.stem, "title": f"(읽기 오류: {e})", "slides": 0, "version": ver(f)})
        self.send_json(out)

    def api_get_deck(self, i, q):
        p = deck_path(i)
        if not p.exists():
            return self.err(404, "덱 없음")
        v = ver(p)
        data = p.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Deck-Version", v)
        self.end_headers()
        self.wfile.write(data)

    def api_put_deck(self, i, q):
        deck = self.body_json()
        if not isinstance(deck, dict) or not isinstance(deck.get("slides"), list):
            return self.err(400, "덱 형식 아님(slides 목록 필요)")
        if deck.get("id", i) != i:
            return self.err(400, "id 불일치")
        for s in deck["slides"]:
            if not isinstance(s, dict) or not isinstance(s.get("elements", []), list):
                return self.err(400, "슬라이드 형식 아님")
        base = (q.get("base") or [self.headers.get("X-Base-Version") or ""])[0]
        force = (q.get("force") or ["0"])[0] == "1"
        with WRITE_LOCK:
            p = deck_path(i)
            cur = ver(p)
            if p.exists() and base and base != cur and not force:
                return self.send_json({"ok": False, "error": "conflict", "version": cur}, 409)
            deck["id"] = i
            deck["updated"] = dt.datetime.now().isoformat(timespec="seconds")
            backup(i)
            atomic_write(p, dumps(deck))
            self.send_json({"ok": True, "version": ver(p), "updated": deck["updated"]})

    def api_get_version(self, i, q):
        self.send_json({"deck": ver(deck_path(i)), "requests": ver(req_path(i)), "session": session_status()})

    # ---------- 작업 공간·세션 ----------
    def api_get_config(self, _, q):
        from layouts import LOGO, LOGO_RATIO, WORDMARK
        self.send_json({"workspace": WORKSPACE.name, "path": str(WORKSPACE), "port": self.server.server_port,
                        "title": CONFIG.get("title", WORKSPACE.name),
                        "brand": {**BRAND, "logo": LOGO, "wordmark": WORDMARK, "logoRatio": LOGO_RATIO}})

    def api_get_session(self, _, q):
        self.send_json(session_status())

    def api_post_flush(self, i, q):
        """편집기 "지금 보내기" — 감시 스크립트가 다음 확인(1초 이내)에 조용한 대기 없이 바로 내보낸다."""
        STATE.mkdir(parents=True, exist_ok=True)
        atomic_write(STATE / "flush.json", dumps({"deck": i, "at": dt.datetime.now().isoformat(timespec="seconds")}))
        self.send_json({"ok": True, "session": session_status()})

    # ---------- 요청 메모 ----------
    def _reqs(self, i):
        p = req_path(i)
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []

    def api_get_requests(self, i, q):
        self.send_json(self._reqs(i))

    def api_post_requests(self, i, q):
        b = self.body_json() or {}
        act = b.get("action", "add")
        with WRITE_LOCK:
            items = self._reqs(i)
            if act == "add":
                text = str(b.get("text", "")).strip()
                if not text:
                    return self.err(400, "내용 없음")
                items.append({"id": "r" + dt.datetime.now().strftime("%Y%m%d%H%M%S%f")[:17], "slide": b.get("slide"),
                              "element": b.get("element"), "text": text, "status": "open", "reply": "",
                              "created": dt.datetime.now().isoformat(timespec="seconds")})
            elif act == "delete":
                items = [r for r in items if r.get("id") != b.get("id")]
            elif act == "update":
                for r in items:
                    if r.get("id") == b.get("id"):
                        for k in ("status", "reply", "text"):
                            if k in b:
                                r[k] = b[k]
            else:
                return self.err(400, "action = add|update|delete")
            atomic_write(req_path(i), dumps(items))
        self.send_json(items)

    # ---------- 내보내기·렌더 ----------
    def api_post_export(self, i, q):
        if not deck_path(i).exists():
            return self.err(404, "덱 없음")
        code, log = export(i)
        f = OUT / f"{i}.pptx"
        if code != 0 or not f.exists():
            return self.send_json({"ok": False, "error": "export 실패", "log": log}, 500)
        self.send_json({"ok": True, "path": str(f), "url": f"/out/{i}.pptx?v={ver(f)}", "log": log})

    # ---------- 글꼴 프리셋 ----------
    def fonts_info(self):
        t = json.loads(TOKENS.read_text(encoding="utf-8"))
        ps = [{"name": k, "label": f"{v['body']['latin']} · {v['mono']['latin']}" + (f" + {v['mono']['ea']}" if v['mono'].get('ea') not in (None, v['body']['ea']) else "")}
              for k, v in t.get("fontPresets", {}).items()]
        return {"ok": True, "current": t.get("fontPreset", ""), "presets": ps}

    FONT_FILES = {
        "Pretendard-Regular": "Pretendard-Regular.otf", "Pretendard-Medium": "Pretendard-Medium.otf",
        "Pretendard-SemiBold": "Pretendard-SemiBold.otf", "Pretendard-Bold": "Pretendard-Bold.otf",
        "Pretendard-ExtraBold": "Pretendard-ExtraBold.otf",
        "JetBrainsMono-Regular": "JetBrainsMono-Regular.ttf", "JetBrainsMono-Italic": "JetBrainsMono-Italic.ttf",
        "JetBrainsMono-Bold": "JetBrainsMono-Bold.ttf", "JetBrainsMono-BoldItalic": "JetBrainsMono-BoldItalic.ttf",
        "D2Coding": "D2Coding-Ver1.3.2-20180524.ttf", "D2Coding-Bold": "D2CodingBold-Ver1.3.2-20180524.ttf",
    }

    def api_get_fontfile(self, name, q):
        fn = self.FONT_FILES.get(name or "")
        if not fn:
            return self.err(404, "모르는 글꼴")
        for d in (Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Windows/Fonts", Path("C:/Windows/Fonts"),
                  Path.home() / "Library/Fonts", Path.home() / ".local/share/fonts"):
            p = d / fn
            if p.is_file():
                data = p.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "font/otf" if fn.endswith(".otf") else "font/ttf")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "max-age=86400")
                self.end_headers()
                self.wfile.write(data)
                return
        return self.err(404, "글꼴 파일 없음 — ppt/studio/install_fonts.ps1 로 설치")

    def api_get_fonts(self, _, q):
        self.send_json(self.fonts_info())

    def api_post_fonts(self, _, q):
        body = self.body_json() or {}
        name = str(body.get("preset", ""))
        if name not in {p["name"] for p in self.fonts_info()["presets"]}:
            return self.err(400, "없는 프리셋")
        code, log = run([sys.executable, str(STUDIO / "set_fonts.py"), name], 30)
        if code != 0:
            return self.send_json({"ok": False, "error": "프리셋 전환 실패", "log": log}, 500)
        self.send_json(self.fonts_info())

    def api_get_render(self, i, q):
        self.send_json({"ok": True, "slides": render_list(i)})

    def api_post_render(self, i, q):
        if not RENDER_LOCK.acquire(blocking=False):
            return self.err(429, "렌더 중")
        try:
            code, log = export(i)
            if code != 0:
                return self.send_json({"ok": False, "error": "export 실패", "log": log}, 500)
            ps = shutil.which("pwsh") or shutil.which("powershell")
            if not ps:
                return self.send_json({"ok": False, "error": "PowerShell 없음"}, 500)
            code, log2 = run([ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(STUDIO / "render_pptx.ps1"),
                              "-Pptx", str(OUT / f"{i}.pptx"), "-OutDir", str(OUT / i)], 300)
            if code != 0:
                return self.send_json({"ok": False, "error": "PowerPoint 렌더 실패", "log": log2}, 500)
            self.send_json({"ok": True, "slides": render_list(i), "log": log + "\n" + log2})
        finally:
            RENDER_LOCK.release()

    # ---------- 레이아웃 ----------
    def api_get_layouts(self, _, q):
        from layouts import LAYOUTS
        self.send_json([{"name": k, "label": v[0]} for k, v in LAYOUTS.items()])

    def api_post_newslide(self, _, q):
        from layouts import SAMPLES, build_slide
        b = self.body_json() or {}
        name = b.get("layout", "bullets")
        if name not in SAMPLES:
            return self.err(400, "알 수 없는 레이아웃")
        self.send_json(build_slide(name, SAMPLES[name], b.get("part", "day1"), b.get("id", "new")))


class Server(ThreadingHTTPServer):
    """포트를 혼자 쓰는 서버. 표준 HTTPServer 는 SO_REUSEADDR 를 켜는데, Windows 에서는 이것 때문에
    두 프로세스가 같은 포트를 열 수 있다(뒤에 뜬 서버가 요청을 가로챔) → 끄고 Windows 는 배타 사용을 켠다."""
    allow_reuse_address = False
    daemon_threads = True

    def server_bind(self):
        import socket
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def _bind(port, auto):
    """포트를 연다. 쓰는 중이면 auto 일 때 다음 포트(최대 50개)를 시도한다."""
    for p in range(port, port + (50 if auto else 1)):
        try:
            return Server(("127.0.0.1", p), H)
        except OSError:
            continue
    other = ""
    try:
        info = json.loads(SERVER_INFO.read_text(encoding="utf-8"))
        if int(info.get("port", 0)) == port:
            other = f" — 이 작업 공간의 서버가 이미 실행 중일 수 있다(pid {info.get('pid')}, {info.get('started')})"
    except (OSError, ValueError):
        pass
    sys.exit(f"포트 {port} 를 쓸 수 없다{other}. 다른 포트: --port <N>, 빈 포트 자동: --port auto, "
             f"또는 nexa-slide.json 의 \"port\" 를 바꾼다")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default=None, help="포트 번호 또는 auto (기본: nexa-slide.json port → 5600)")
    ap.add_argument("--force", action="store_true", help="이 작업 공간의 서버가 이미 떠 있어도 하나 더 띄운다")
    a = ap.parse_args()
    run = running_server()
    if run and not a.force:
        sys.exit(f"이 작업 공간의 서버가 이미 실행 중이다: {run['url']} (pid {run['pid']}, {run['started']}) — 그대로 쓰면 된다")
    auto = str(a.port).lower() == "auto"
    port = DEFAULT_PORT if a.port is None or auto else int(a.port)
    DECKS.mkdir(parents=True, exist_ok=True)
    srv = _bind(port, auto)
    port = srv.server_port
    url = f"http://127.0.0.1:{port}/"
    STATE.mkdir(parents=True, exist_ok=True)
    atomic_write(SERVER_INFO, dumps({"port": port, "url": url, "pid": os.getpid(), "workspace": str(WORKSPACE),
                                     "title": CONFIG.get("title", WORKSPACE.name),
                                     "started": dt.datetime.now().isoformat(timespec="seconds")}))
    print(f"nexa-slide: {url}  작업 공간 {WORKSPACE}  (Ctrl+C 로 종료)", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
        try:  # 내가 쓴 정보일 때만 지운다(같은 작업 공간에 다른 서버가 뒤에 떴을 수 있다)
            if json.loads(SERVER_INFO.read_text(encoding="utf-8")).get("pid") == os.getpid():
                SERVER_INFO.unlink()
        except (OSError, ValueError):
            pass


if __name__ == "__main__":
    main()
