# -*- coding: utf-8 -*-
"""검토 등록부 서버 — 템플릿·레이아웃·참고 덱·사이트·파일 같은 "검토 대상"을 등록하고 미리 보며 검토·승인한다(표준 라이브러리만).

    python docs/research/review/review_server.py [--port 5590] [--genspark <조사 폴더>]
    → http://127.0.0.1:5590/

등록부는 이 폴더의 registry.json(저장소에 둔다 — 우리가 쓴 제목·메모·날짜·상태만). 미리보기용 원본(Genspark 썸네일·장 HTML 등)은
저장소 밖 조사 폴더에서 읽기만 한다(기본 <저장소>/../_research/genspark-slides, --genspark 또는 NEXA_RESEARCH_GENSPARK 로 바꿈).

API
  GET  /api/items                         대상 목록(최근 등록 순) + 집계
  POST /api/items                         {kind, title, source:{type:"site"|"file"|…, url?, path?}, note?, tags?} → 새 대상(status registered)
  POST /api/items/<id>                    {action: "review"|"approve"|"hold"|"reject"|"reopen"|"note", note?} → 상태·날짜·이력 갱신
  GET  /api/preview/<id>                  미리보기 자료(장 썸네일·장 HTML 주소·근거 덱 등)
  GET  /gs/<경로>                         Genspark 조사 폴더의 정적 파일(썸네일·장 HTML·그림)
"""
import argparse
import datetime as dt
import json
import os
import re
import tempfile
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
REGISTRY = HERE / "registry.json"
GS_DATA = REPO / "docs/research/genspark-skills/data"
LOCK = threading.Lock()
GS = None  # Genspark 조사 폴더
STATUS = ("registered", "reviewing", "approved", "held", "rejected")


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


_gs = {}


def gs_skill_dir(no):
    """스킬 번호(3자리) → 조사 폴더의 스킬 폴더."""
    if no not in _gs and GS and (GS / "skills").is_dir():
        for d in (GS / "skills").iterdir():
            _gs[d.name[:3]] = d
    return _gs.get(no)


def gs_slides(no):
    """스킬의 장 목록 — 썸네일·장 HTML 주소(manifest 순서)."""
    d = gs_skill_dir(no)
    if not d:
        return []
    man = next(d.glob("deck/*/manifest.json"), None)
    if not man:
        return []
    order = json.loads(man.read_text(encoding="utf-8"))["playlist"]
    thumbs = {p.name[:2]: p for p in (d / "thumbnails").glob("*.png")} if (d / "thumbnails").is_dir() else {}
    out = []
    for i, name in enumerate(order, 1):
        t = thumbs.get(f"{i:02d}")
        rel = lambda p: "/gs/" + quote(p.relative_to(GS).as_posix())  # noqa: E731
        out.append({"id": f"{no}-{i:02d}", "n": i, "kind": re.sub(r"^\d+[-_]?", "", Path(name).stem),
                    "thumb": rel(t) if t else None, "html": rel(man.parent / "slides" / name)})
    return out


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
        return {"decks": [{"no": n, "title": cen.get(n, {}).get("name", n), "slides": gs_slides(n)} for n in src.get("sources", [])],
                "detail": src.get("detail")}
    if t == "genspark-layout":
        ids = src.get("examples", [])
        slides = []
        for sid in ids:
            no, n = sid.split("-")
            s = next((x for x in gs_slides(no) if x["n"] == int(n)), None)
            if s:
                slides.append(s)
        return {"slides": slides, "detail": src.get("detail")}
    if t == "site":
        return {"site": src.get("url")}
    if t == "file":
        p = Path(src.get("path") or "")
        return {"file": {"path": str(p), "exists": p.exists(), "size": p.stat().st_size if p.is_file() else None}}
    return {}


class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def send(self, code, body, ctype="application/json; charset=utf-8"):
        b = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n).decode("utf-8") or "{}") if n else {}

    def do_GET(self):
        u = urlparse(self.path)
        p = unquote(u.path)
        if p in ("/", "/index.html"):
            return self.send(200, (HERE / "review.html").read_bytes(), "text/html; charset=utf-8")
        if p == "/api/items":
            reg = load()
            items = sorted(reg["items"], key=lambda x: (x.get("registeredAt", ""), x["id"]), reverse=True)
            cnt = {s: sum(1 for x in items if x.get("status") == s) for s in STATUS}
            return self.send(200, {"items": items, "counts": cnt, "genspark": str(GS) if GS else None})
        m = re.fullmatch(r"/api/preview/([\w.:-]+)", p)
        if m:
            it = next((x for x in load()["items"] if x["id"] == m.group(1)), None)
            return self.send(200, preview(it)) if it else self.send(404, {"error": "없는 대상"})
        if p.startswith("/gs/") and GS:
            f = (GS / p[4:]).resolve()
            if GS.resolve() not in f.parents or not f.is_file():
                return self.send(404, {"error": "없음"})
            ext = f.suffix.lower()
            ctype = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".svg": "image/svg+xml",
                     ".html": "text/html; charset=utf-8", ".json": "application/json; charset=utf-8", ".css": "text/css"}.get(ext, "application/octet-stream")
            return self.send(200, f.read_bytes(), ctype)
        self.send(404, {"error": "없음"})

    def do_POST(self):
        try:
            self.post()
        except Exception as e:  # noqa: BLE001 — 잘못된 본문 등은 400 으로 알린다
            self.send(400, {"error": f"{type(e).__name__}: {e}"})

    def post(self):
        p = unquote(urlparse(self.path).path)
        b = self.body()
        with LOCK:
            reg = load()
            if p == "/api/items":
                title = str(b.get("title") or "").strip()
                if not title:
                    return self.send(400, {"error": "제목이 필요하다"})
                base = re.sub(r"[^a-z0-9]+", "-", str(b.get("kind") or "item").lower()).strip("-")
                k, ids = 1, {x["id"] for x in reg["items"]}
                while f"{base}-{dt.date.today():%Y%m%d}-{k}" in ids:
                    k += 1
                it = {"id": f"{base}-{dt.date.today():%Y%m%d}-{k}", "kind": b.get("kind") or "reference", "title": title,
                      "source": b.get("source") or {}, "tags": b.get("tags") or [], "note": b.get("note") or "",
                      "status": "registered", "registeredAt": now(), "reviewedAt": None, "approvedAt": None,
                      "history": [{"at": now(), "action": "register", "note": b.get("note") or ""}]}
                reg["items"].append(it)
                save(reg)
                return self.send(200, it)
            m = re.fullmatch(r"/api/items/([\w.:-]+)", p)
            if m:
                it = next((x for x in reg["items"] if x["id"] == m.group(1)), None)
                if not it:
                    return self.send(404, {"error": "없는 대상"})
                act, note = b.get("action"), str(b.get("note") or "")
                to = {"review": "reviewing", "approve": "approved", "hold": "held", "reject": "rejected", "reopen": "registered"}.get(act)
                if act not in ("note",) and not to:
                    return self.send(400, {"error": "action = review|approve|hold|reject|reopen|note"})
                if to:
                    it["status"] = to
                    if to in ("reviewing", "approved", "held", "rejected") and not it.get("reviewedAt"):
                        it["reviewedAt"] = now()  # 처음 검토한 날
                    if to == "approved":
                        it["approvedAt"] = now()
                    if to == "registered":
                        it["approvedAt"] = None
                if act == "note" or note:
                    it["note"] = note if act == "note" else it.get("note", "")
                it.setdefault("history", []).append({"at": now(), "action": act, "note": note})
                save(reg)
                return self.send(200, it)
        self.send(404, {"error": "없음"})


def main():
    global GS
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=5590)
    ap.add_argument("--genspark", default=os.environ.get("NEXA_RESEARCH_GENSPARK") or str(REPO.parent / "_research" / "genspark-slides"))
    a = ap.parse_args()
    GS = Path(a.genspark) if Path(a.genspark).is_dir() else None
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), H)
    print(f"검토 등록부: http://127.0.0.1:{a.port}/  (등록부 {REGISTRY} · Genspark 원본 {GS or '없음'})", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
