# -*- coding: utf-8 -*-
"""검토 등록부 — 템플릿·레이아웃·참고 덱·사이트·파일 같은 "검토 대상"을 등록하고 미리 보며 검토·승인한다(표준 라이브러리만).

시작 페이지(허브) 서버가 이 모듈을 불러 /review 에 붙인다(기본 메뉴 "템플릿 검토"):
    python3 studio/service.py start   → http://127.0.0.1:5599/review
따로 띄울 수도 있다(같은 경로):
    python docs/research/review/review_server.py [--port 5590] [--genspark <조사 폴더>]   → http://127.0.0.1:5590/review

등록부는 이 폴더의 registry.json(저장소에 둔다 — 우리가 쓴 제목·메모·날짜·상태만). 미리보기용 원본(Genspark 썸네일·장 HTML 등)은
저장소 밖 조사 폴더에서 읽기만 한다(기본 <저장소>/../_research/genspark-slides, NEXA_RESEARCH_GENSPARK 또는 --genspark 로 바꿈).

경로
  GET  /review                                 검토 화면(review.html)
  GET  /api/review/items                       대상 목록(최근 등록 순) + 집계
  POST /api/review/items                       {kind, title, source:{type:"site"|"file"|…, url?, path?}, note?, tags?} → 새 대상
  POST /api/review/items/<id>                  {action: "review"|"approve"|"hold"|"reject"|"reopen"|"note", note?}
  GET  /api/review/preview/<id>                미리보기 자료(장 썸네일·장 HTML 주소·근거 덱 등)
  GET  /review/gs/<경로>                       Genspark 조사 폴더의 정적 파일(썸네일·장 HTML·그림)
"""
import argparse
import datetime as dt
import json
import os
import re
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
REGISTRY = HERE / "registry.json"
GS_DATA = REPO / "docs/research/genspark-skills/data"
LOCK = threading.Lock()
STATUS = ("registered", "reviewing", "approved", "held", "rejected")
GS = None  # Genspark 조사 폴더(없으면 미리보기 없음)
_gs = {}


def configure(genspark=None):
    global GS
    p = Path(genspark or os.environ.get("NEXA_RESEARCH_GENSPARK") or REPO.parent / "_research" / "genspark-slides")
    GS = p if p.is_dir() else None
    _gs.clear()


def now():
    return dt.datetime.now().isoformat(timespec="seconds")


def load():
    try:
        return json.loads(REGISTRY.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"items": []}


def save(reg):
    fd, tmp = tempfile.mkstemp(dir=str(HERE), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(reg, ensure_ascii=False, indent=1) + "\n")
    os.replace(tmp, REGISTRY)


def gs_skill_dir(no):
    if not _gs and GS and (GS / "skills").is_dir():
        for d in (GS / "skills").iterdir():
            _gs[d.name[:3]] = d
    return _gs.get(no)


def gs_url(p):
    return "/review/gs/" + quote(p.relative_to(GS).as_posix())


def gs_slides(no):
    """스킬의 장 목록 — 썸네일·장 HTML 주소(manifest 순서)."""
    d = gs_skill_dir(no)
    man = next(d.glob("deck/*/manifest.json"), None) if d else None
    if not man:
        return []
    order = json.loads(man.read_text(encoding="utf-8"))["playlist"]
    thumbs = {p.name[:2]: p for p in (d / "thumbnails").glob("*.png")} if (d / "thumbnails").is_dir() else {}
    return [{"id": f"{no}-{i:02d}", "n": i, "kind": re.sub(r"^\d+[-_]?", "", Path(name).stem),
             "thumb": gs_url(thumbs[f"{i:02d}"]) if f"{i:02d}" in thumbs else None, "html": gs_url(man.parent / "slides" / name)}
            for i, name in enumerate(order, 1)]


def gs_json(name):
    try:
        return json.loads((GS_DATA / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def preview(item):
    src = item.get("source", {})
    t = src.get("type")
    if t == "genspark-skill":
        return {"decks": [{"no": src["ref"], "title": item["title"], "slides": gs_slides(src["ref"])}]}
    if t == "genspark-template":
        cen = {c["no"]: c for c in (gs_json("census.json") or [])}
        return {"decks": [{"no": n, "title": cen.get(n, {}).get("name", n), "slides": gs_slides(n)} for n in src.get("sources", [])]}
    if t == "genspark-layout":
        slides = []
        for sid in src.get("examples", []):
            no, n = sid.split("-")
            s = next((x for x in gs_slides(no) if x["n"] == int(n)), None)
            if s:
                slides.append(s)
        return {"slides": slides}
    if t == "site":
        return {"site": src.get("url")}
    if t == "file":
        p = Path(src.get("path") or "")
        return {"file": {"path": str(p), "exists": p.exists(), "size": p.stat().st_size if p.is_file() else None}}
    return {}


CTYPE = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".svg": "image/svg+xml", ".gif": "image/gif",
         ".html": "text/html; charset=utf-8", ".json": "application/json; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "application/javascript"}


def js(code, obj):
    return code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8"


def handle_get(path):
    """(상태 코드, 본문 바이트, Content-Type) 또는 이 모듈의 경로가 아니면 None."""
    p = unquote(urlparse(path).path)
    if p in ("/review", "/review/"):
        return 200, (HERE / "review.html").read_bytes(), "text/html; charset=utf-8"
    if p == "/api/review/items":
        if GS is None:
            configure()
        items = sorted(load()["items"], key=lambda x: (x.get("registeredAt", ""), x["id"]), reverse=True)
        return js(200, {"items": items, "counts": {s: sum(1 for x in items if x.get("status") == s) for s in STATUS}, "genspark": str(GS) if GS else None})
    m = re.fullmatch(r"/api/review/preview/([\w.:-]+)", p)
    if m:
        if GS is None:
            configure()
        it = next((x for x in load()["items"] if x["id"] == m.group(1)), None)
        return js(200, preview(it)) if it else js(404, {"error": "없는 대상"})
    if p.startswith("/review/gs/"):
        if GS is None:
            configure()
        if not GS:
            return js(404, {"error": "조사 폴더 없음"})
        f = (GS / p[len("/review/gs/"):]).resolve()
        if GS.resolve() not in f.parents or not f.is_file():
            return js(404, {"error": "없음"})
        return 200, f.read_bytes(), CTYPE.get(f.suffix.lower(), "application/octet-stream")
    return None


def handle_post(path, raw):
    """(상태 코드, 본문, Content-Type) 또는 None."""
    p = unquote(urlparse(path).path)
    if not p.startswith("/api/review/items"):
        return None
    try:
        b = json.loads((raw or b"{}").decode("utf-8") or "{}")
    except ValueError as e:
        return js(400, {"error": f"JSON 오류: {e}"})
    with LOCK:
        reg = load()
        if p == "/api/review/items":
            title = str(b.get("title") or "").strip()
            if not title:
                return js(400, {"error": "제목이 필요하다"})
            base = re.sub(r"[^a-z0-9]+", "-", str(b.get("kind") or "item").lower()).strip("-") or "item"
            k, ids = 1, {x["id"] for x in reg["items"]}
            while f"{base}-{dt.date.today():%Y%m%d}-{k}" in ids:
                k += 1
            it = {"id": f"{base}-{dt.date.today():%Y%m%d}-{k}", "kind": b.get("kind") or "reference", "title": title,
                  "source": b.get("source") or {}, "tags": b.get("tags") or [], "note": b.get("note") or "",
                  "status": "registered", "registeredAt": now(), "reviewedAt": None, "approvedAt": None,
                  "history": [{"at": now(), "action": "register", "note": b.get("note") or ""}]}
            reg["items"].append(it)
            save(reg)
            return js(200, it)
        m = re.fullmatch(r"/api/review/items/([\w.:-]+)", p)
        if not m:
            return js(404, {"error": "없음"})
        it = next((x for x in reg["items"] if x["id"] == m.group(1)), None)
        if not it:
            return js(404, {"error": "없는 대상"})
        act, note = b.get("action"), str(b.get("note") or "")
        to = {"review": "reviewing", "approve": "approved", "hold": "held", "reject": "rejected", "reopen": "registered"}.get(act)
        if act != "note" and not to:
            return js(400, {"error": "action = review|approve|hold|reject|reopen|note"})
        if to:
            it["status"] = to
            if to != "registered" and not it.get("reviewedAt"):
                it["reviewedAt"] = now()  # 처음 검토한 날
            if to == "approved":
                it["approvedAt"] = now()
            if to == "registered":
                it["approvedAt"] = None
        if act == "note":
            it["note"] = note
        it.setdefault("history", []).append({"at": now(), "action": act, "note": note})
        save(reg)
        return js(200, it)


class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def reply(self, r):
        code, body, ctype = r or js(404, {"error": "없음"})
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if urlparse(self.path).path == "/":
            self.send_response(302)
            self.send_header("Location", "/review")
            self.end_headers()
            return
        self.reply(handle_get(self.path))

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        self.reply(handle_post(self.path, self.rfile.read(n) if n else b""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=5590)
    ap.add_argument("--genspark")
    a = ap.parse_args()
    configure(a.genspark)
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), H)
    print(f"검토 등록부: http://127.0.0.1:{a.port}/review  (등록부 {REGISTRY} · Genspark 원본 {GS or '없음'})", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
