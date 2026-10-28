# -*- coding: utf-8 -*-
"""시작 페이지(허브) 동작 - 새로 만들기 · 열기 · 데모 · 최근 작업 · 폴더 고르기. server.py 의 /api/home·/api/project·/api/fs 가 쓴다.

원칙: 엔진은 슬라이드 내용을 자기 폴더에 두지 않는다. 제작마다 작업 공간 폴더를 따로 두고(기본 = 문서 폴더/NexaSlide/<제목>),
그 폴더에 내용(content·decks·assets)과 서버를 실행할 정보(nexa-slide.json·nexa.py)를 넣는다. 서버도 작업 공간마다 하나씩 띄운다.
새로 만들 때 고른 폴더는 저장소 관리 기준 폴더(루트 - 자료·소스는 사용자 구조)이고 작업 공간은 그 아래 slides/ 다(init_workspace.py).

중계(허브 한 포트) - 허브는 /w/<id>/… 를 그 작업 공간 서버로 넘긴다(server.py H.proxy). id = ws_id(경로), 대상은 proxy_target 이 정한다
(떠 있으면 그 서버, 꺼져 있으면 --port auto 로 띄움). 사용자 설정 hubProxy(기본 켬)가 켜져 있으면 열기·만들기가 중계 주소로 간다.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from paths import (ENGINE, LOCAL_CONFIG, default_projects_root, documents_dir, forget, inside_engine, load_settings, load_ws_config, projects_root,
                   remember, repo_workspace, save_settings, user_dir)

STUDIO = ENGINE / "studio"
EXAMPLE = ENGINE / "example"
STARTERS = ENGINE / "starters"
TEMPLATES = STUDIO / "templates"
CONFIG_NAME = "nexa-slide.json"
DEMO_DIR = "nexa-slide-demo"
PREVIEW_ROOT = user_dir() / "hub" / "preview"  # 미리보기용 임시 작업 공간(엔진·기준 폴더 밖, 사용자 설정 폴더)
NEW_ATTACH = user_dir() / "hub" / "new-attach"  # 새로 만들기 "참고 자료" 첨부 - 만들 때 작업 공간 materials/ 로 옮긴다


class HubError(Exception):
    def __init__(self, msg, **extra):
        super().__init__(msg)
        self.extra = extra


def _run(args, ws=None, timeout=120):
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    env.pop("NEXA_SLIDE_WORKSPACE", None)
    if ws:
        env["NEXA_SLIDE_WORKSPACE"] = str(ws)
    r = subprocess.run([sys.executable, *map(str, args)], cwd=str(ws or ENGINE), env=env, capture_output=True, timeout=timeout)
    out = ((r.stdout or b"") + (r.stderr or b"")).decode("utf-8", "replace").strip()
    return r.returncode, out


def _read_json(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def slug(title):
    """폴더 이름 - 한글은 그대로, 파일 이름에 못 쓰는 글자·공백은 '-'."""
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "-", title.strip())
    s = re.sub(r"\s+", "-", s).strip(".- ")
    return s[:60] or "slides"


# ---------- 중계(허브 한 포트로 여러 작업 공간) ----------
def ws_id(path):
    """작업 공간 → 중계 주소의 이름 /w/<id>/ - 폴더 이름(읽기용) + 경로 해시 6자(같은 이름 구분). 경로가 같으면 늘 같은 값."""
    p = Path(path).resolve()
    key = str(p).lower() if os.name == "nt" else str(p)
    h = hashlib.sha1(key.encode("utf-8")).hexdigest()[:6]
    name = p.name if p.name not in ("slides", "ppt", "") or p.parent == p else f"{p.parent.name}-{p.name}"  # slides/ 는 저장소 이름을 붙여 알아보기 쉽게
    name = re.sub(r"[#%?&+;=\s]+", "-", slug(name))  # 주소에 그대로 쓰는 글자만(한글은 그대로 - 브라우저가 알아서 부호화)
    return f"{name[:24].strip('-') or 'ws'}-{h}"


def ws_by_id(wid):
    """중계 이름 → 작업 공간 폴더(최근 작업 목록에서 찾는다 - 열기·만들기를 거친 작업 공간만). 없으면 None."""
    for r in load_settings().get("recent", []):
        try:
            if ws_id(r["path"]) == wid and (Path(r["path"]) / CONFIG_NAME).is_file():
                return Path(r["path"]).resolve()
        except (KeyError, OSError):
            continue
    return None


def proxy_on():
    """허브에서 열기·만들기가 중계 주소(/w/<id>/)로 가는가 - 사용자 설정 hubProxy(기본 켬). 끄면 그 작업 공간 서버의 포트로 바로 간다."""
    return bool(load_settings().get("hubProxy", True))


def nav(ws, direct):
    """열기·만들기 응답의 이동 주소 - url(이동할 곳) · direct(그 작업 공간 서버 주소) · id(중계 이름) · hubUrl(중계 주소)."""
    wid = ws_id(ws)
    hub_url = f"/w/{wid}/"
    return {"url": hub_url if proxy_on() else direct, "direct": direct, "id": wid, "hubUrl": hub_url}


# ---------- 목록 ----------
def _template_card(d, t, workspace=False):
    """템플릿 카드 항목 - 색 견본은 토큰 파일(+extends 바탕) 위에 tokenOverrides 를 덮어 계산한다."""
    tok = _read_json(d / t["tokens"]) if t.get("tokens") else None
    if tok is None and t.get("extends"):
        base = _read_json(TEMPLATES / t["extends"] / "template.json") or {}
        tok = _read_json(TEMPLATES / t["extends"] / base.get("tokens", "tokens.json")) or {}
        if base.get("tokenOverrides"):  # 바탕이 목적별 템플릿(lecture 토큰 + 덮어쓰기)이면 그 값 위에
            tok = {**tok, "colors": {**tok.get("colors", {}), **((base["tokenOverrides"].get("colors")) or {})}}
    cs = dict((tok or {}).get("colors", {}))
    cs.update(((t.get("tokenOverrides") or {}).get("colors")) or {})

    def c(k):
        v = cs.get(k)
        for _ in range(5):
            if isinstance(v, str) and v.startswith("#"):
                return v
            v = cs.get(v)
        return None
    sw = [x for x in (c("primary"), c("primary-container"), c("day1"), c("day2"), c("day3"), c("on-surface")) if x]
    item = {"name": d.name, "label": t.get("label", d.name), "description": t.get("description", ""), "i18n": t.get("i18n") or {},
            "extends": t.get("extends"), "swatches": sw,
            "concept": f"/studio/templates/{d.name}/design/concept.html" if not workspace and (d / "design" / "concept.html").is_file() else None}
    if workspace:
        item["workspace"] = True
    return item


def ws_templates(ws):
    """작업 공간 templates/<이름>/template.json 목록(회사 템플릿 - extends+tokenOverrides 만, docs/templates.md). 엔진과 겹치는 이름은 뺀다(엔진 것이 쓰인다)."""
    out = []
    root = Path(ws) / "templates" if ws else None
    if not root or not root.is_dir():
        return out
    for d in sorted(root.iterdir()):
        t = _read_json(d / "template.json")
        if not t or not re.fullmatch(r"[A-Za-z0-9_-]+", d.name) or (TEMPLATES / d.name / "template.json").is_file():
            continue
        if not isinstance(t.get("extends"), str) or not (TEMPLATES / t["extends"] / "template.json").is_file():
            t = {**t, "extends": "lecture"}  # 로더(common.load_template)와 같은 처리
        t.pop("tokens", None)
        out.append(_template_card(d, t, workspace=True))
    return out


def templates(ws=None):
    """엔진 템플릿 목록(+ ws 를 주면 그 작업 공간의 회사 템플릿을 뒤에 - 작업 공간 서버의 시작 페이지에서만 보인다)."""
    out = []
    for d in sorted(TEMPLATES.iterdir()):
        t = _read_json(d / "template.json")
        if not t or t.get("hidden"):  # 숨긴 템플릿(검토 대상으로 옮김) — 목록에서 제외, 이미 쓰는 작업 공간은 그대로 동작
            continue
        out.append(_template_card(d, t))
    return out + ws_templates(ws)


def starters():
    """엔진 starters/<이름>/starter.json - 시작용 내용(있을 때만). init_workspace.py --starter 로 쓴다."""
    out = []
    if STARTERS.is_dir():
        for d in sorted(STARTERS.iterdir()):
            st = _read_json(d / "starter.json")
            if st and not st.get("hidden"):  # 숨긴 시작용 내용(검토 대상으로 옮김)은 목록에서 제외
                out.append({"name": d.name, "label": st.get("label", d.name), "description": st.get("description", ""),
                            "template": st.get("template"), "i18n": st.get("i18n") or {}})
    return out


def _supports_starter():
    try:
        return "--starter" in (STUDIO / "init_workspace.py").read_text(encoding="utf-8")
    except OSError:
        return False


def find_workspace(p, deep=False):
    """폴더 → 작업 공간 폴더(없으면 None). 그 폴더가 작업 공간이면 그것, 저장소 루트면 루트 표식 .nexa-slide.json 이 가리키는 폴더(없으면 slides/).
    deep 이면 표식이 없는 예전 저장소를 위해 바로 아래 폴더도 본다(예: <폴더>/ppt)."""
    p = Path(p)
    if (p / CONFIG_NAME).is_file():
        return p
    ws = repo_workspace(p)
    if ws:
        return ws
    if deep:
        try:
            subs = sorted(d for d in p.iterdir() if d.is_dir() and not d.name.startswith((".", "$")) and (d / CONFIG_NAME).is_file())
        except OSError:
            subs = []
        if subs:
            return subs[0]
    return None


def _serving(ws, url):
    """url 의 nexa-slide 서버가 ws 작업 공간을 내주고 있는가(/api/config 의 path). 닫힌 포트는 짧게 먼저 두드린다."""
    import socket
    import urllib.parse
    import urllib.request
    try:
        u = urllib.parse.urlparse(str(url or ""))
        socket.create_connection((u.hostname or "127.0.0.1", u.port or 80), timeout=0.3).close()
        with urllib.request.urlopen(url.rstrip("/") + "/api/config", timeout=1.5) as r:
            cfg = json.loads(r.read().decode("utf-8"))
        return bool(cfg.get("path")) and Path(cfg["path"]).resolve() == Path(ws).resolve()
    except Exception:  # noqa: BLE001 - 응답 없음·다른 서비스
        return False


def server_state(ws, cfg=None):
    """작업 공간 서버 상태 {running, url, pid} - server.json 의 주소가 실제로 이 작업 공간을 내주는지 확인한다."""
    cfg = cfg if cfg is not None else load_ws_config(ws)
    info = _read_json(Path(ws) / cfg.get("out", "out") / ".studio" / "server.json") or {}
    if info.get("url") and _serving(ws, info["url"]):
        return {"running": True, "url": info["url"], "pid": info.get("pid")}
    return {"running": False, "url": None, "pid": None}


def session_summary(ws, cfg=None):
    """작업 공간의 AI 세션 요약 - 파일만 읽는다(서버에 묻지 않음). {kind: web|manual|none, connected, label, agent, model, user, started, lastSeen, open, working, last, defaults}"""
    import time
    ws = Path(ws)
    cfg = cfg if cfg is not None else load_ws_config(ws)
    st_dir = ws / cfg.get("out", "out") / ".studio"
    hb = _read_json(st_dir / "session.json") or {}
    age = (time.time() - float(hb.get("ts", 0))) if hb else None
    connected = bool(hb) and not hb.get("stopped") and age <= float(hb.get("interval", 1)) * 4 + 2
    out = {"kind": (hb.get("kind") or "manual") if connected else "none", "connected": connected, "label": hb.get("label", ""),
           "agent": hb.get("agent"), "model": hb.get("model"), "user": hb.get("user"), "started": hb.get("started", ""), "lastSeen": hb.get("last_seen", ""),
           "state": hb.get("state"), "turn": hb.get("turn"), "allowWeb": bool(hb.get("allowWeb")), "grants": hb.get("grants") or [], "sessionId": hb.get("sessionId"), "cwd": hb.get("cwd"), "entry": hb.get("entry"),  # 웹 세션의 하트비트가 적는 상태(running = 턴 실행 중)
           "open": 0, "working": 0, "defaults": {"agent": cfg.get("sessionAgent"), "model": cfg.get("sessionModel")}}
    decks_dir = ws / cfg.get("decks", "decks")
    for f in (decks_dir.glob("*.requests.json") if decks_dir.is_dir() else []):
        try:
            rs = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        out["open"] += sum(1 for r in rs if r.get("status") == "open")
        out["working"] += sum(1 for r in rs if r.get("status") == "working")
    last = _read_json(st_dir / "wsession.json")
    if last:
        out["last"] = {k: last.get(k) for k in ("agent", "model", "startedBy", "startedAt", "stoppedAt", "reason", "turns", "lastError", "allowWeb", "sessionId")}
    return out


def _is_sheet(p):
    """덱 파일이 시트 문서(kind sheet)인가 - 큰 덱을 다 읽지 않게 앞부분만 본다(kind 는 id·title 다음에 쓴다)."""
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            head = f.read(4096)
    except OSError:
        return False
    return re.search(r'"kind"\s*:\s*"sheet"', head) is not None


def sheet_themes(rows=None):
    """새 시트에 고를 테마 - 엔진 테마 + 최근 작업 공간의 회사 테마(assets/sheet-themes/<이름>/). 고르면 새 작업 공간으로 복사한다."""
    out = []

    def add(d, src, ws=None, title=None):
        try:
            t = json.loads((d / "theme.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        pal = t.get("palette") or {}
        out.append({"key": f"{src}:{d.name}", "name": d.name, "label": t.get("label") or d.name, "source": src, "from": str(ws) if ws else "",
                    "wsTitle": title or "", "font": t.get("font") or "", "swatches": [pal.get(k) for k in ("primary", "secondary", "line", "band", "input") if pal.get(k)],
                    "pages": [p.get("name") for p in t.get("pages", [])], "logo": (d / "logo.png").is_file()})
    for d in sorted((STUDIO / "sheet_themes").glob("*")) if (STUDIO / "sheet_themes").is_dir() else []:
        if (d / "theme.json").is_file():
            add(d, "engine")
    for r in rows if rows is not None else load_settings().get("recent", []):
        p = Path(r["path"])
        cfg = load_ws_config(p) if (p / CONFIG_NAME).is_file() else None
        if cfg is None:
            continue
        base = p / cfg.get("assetRoot", ".") / "assets" / "sheet-themes"
        for d in sorted(base.glob("*")) if base.is_dir() else []:
            if (d / "theme.json").is_file() and not any(x["source"] == "ws" and x["name"] == d.name for x in out):  # 같은 이름은 먼저 본(최근) 작업 공간 것
                add(d, "ws", p, cfg.get("title") or p.name)
    return out


def save_attach(b):
    """새로 만들기 참고 자료 첨부 {name, type, data(base64)} → hub/new-attach/<id><확장자>. 만들 때 attachments=[{name, orig}] 로 넘긴다."""
    import base64
    import datetime as dt
    types = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif", "image/webp": ".webp", "application/pdf": ".pdf", "text/plain": ".txt",
             "text/markdown": ".md", "text/csv": ".csv", "application/json": ".json",
             "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
             "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx"}
    name = str(b.get("name") or "")[:120]
    ctype = str(b.get("type") or "").split(";")[0].strip().lower()
    ext = types.get(ctype) or (Path(name).suffix.lower() if Path(name).suffix.lower() in types.values() else None)
    if not ext:
        raise HubError(f"지원하지 않는 형식: {ctype or name or '?'} (그림·PDF·글·pptx/docx/xlsx)")
    try:
        data = base64.b64decode(str(b.get("data") or ""), validate=True)
    except (ValueError, TypeError):
        raise HubError("data 는 base64")
    if not data or len(data) > 20 * 1024 * 1024:
        raise HubError("내용 없음" if not data else "20MB 보다 크다")
    NEW_ATTACH.mkdir(parents=True, exist_ok=True)
    fid = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ext
    (NEW_ATTACH / fid).write_bytes(data)
    return {"ok": True, "name": fid, "orig": name or fid, "size": len(data), "type": ctype}


def claim_attachments(ws, items):
    """첨부를 작업 공간 materials/ 로 옮기고 BRIEF.md 참고 자료에 적는다 - 옮긴 경로(작업 공간 기준) 목록."""
    if not isinstance(items, list) or not items:
        return []
    dest = ws / "materials"
    moved = []
    for a in items[:30]:
        fid = str((a or {}).get("name") or "")
        src = NEW_ATTACH / fid
        if not re.fullmatch(r"[\w.-]+", fid) or not src.is_file():
            continue
        orig = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', " ", str(a.get("orig") or fid)).strip()[:100] or fid
        if not Path(orig).suffix:
            orig += src.suffix
        dest.mkdir(parents=True, exist_ok=True)
        p, k = dest / orig, 2
        while p.exists():
            p, k = dest / f"{Path(orig).stem}-{k}{Path(orig).suffix}", k + 1
        shutil.move(str(src), str(p))
        moved.append(p.relative_to(ws).as_posix())
    if moved:
        brief = ws / "BRIEF.md"
        lines = "\n".join(f"- {m} (첨부 - 세션이 Read 로 연다. pptx·docx·xlsx·pdf 는 `python3 nexa.py import_doc {m}` / import_pptx)" for m in moved)
        text = brief.read_text(encoding="utf-8") if brief.is_file() else f"# 작성 브리프\n"
        text = text.rstrip() + f"\n\n## 첨부한 참고 자료\n\n{lines}\n"
        brief.write_text(text, encoding="utf-8", newline="\n")
    return moved


def workspace_info(path, state=False):
    """작업 공간 요약 - 제목·템플릿·덱 수·세션. state 면 실행 상태(running·url)까지 확인한다(응답을 두드려 본다)."""
    p = Path(path)
    if not (p / CONFIG_NAME).is_file():
        return {"path": str(p), "exists": p.is_dir(), "workspace": False}
    cfg = load_ws_config(p)  # PC 별 nexa-slide.local.json(포트 등)까지
    decks_dir = p / cfg.get("decks", "decks")
    decks = sorted(f.stem for f in decks_dir.glob("*.json") if not f.name.endswith(".requests.json")) if decks_dir.is_dir() else []
    sheets = [d for d in decks if _is_sheet(decks_dir / f"{d}.json")]
    info = server_state(p, cfg) if state else {"running": None, "url": (_read_json(p / cfg.get("out", "out") / ".studio" / "server.json") or {}).get("url")}
    return {"path": str(p), "exists": True, "workspace": True, "title": cfg.get("title", p.name), "template": cfg.get("template", "lecture"),
            "port": cfg.get("port"), "decks": decks, "sheets": sheets, "url": info.get("url"), "running": info.get("running"), "git": _git_root(p) is not None,
            "brief": (p / "BRIEF.md").is_file(), "root": str((p / cfg["repo"]["root"]).resolve()) if isinstance(cfg.get("repo"), dict) else "",
            "session": session_summary(p, cfg)}


SESSION_KEYS = ("sessionAgent", "sessionModel", "sessionModels", "sessionIdleMinutes", "sessionTurnMinutes", "sessionMax", "sessionMaxTurns", "sessionBudgetUsd", "engineMaxTurns", "engineTurnMinutes", "engineContinue", "agentPaths",
                "sessionAllowWeb", "sessionAllowGit", "sessionAllowPush", "sessionRepoRoot")  # 세션 단위로 열 수 있는 권한의 전역 스위치(기본 끔) - 웹 검색 · git 기록 · push · 저장소 루트 접근


def session_ws(path, op, agent=None, model=None, user=None, role=None, save_as=None, allow_web=False, grants=None):
    """허브에서 작업 공간의 웹 세션을 켜고 끈다 - 서버가 꺼져 있으면 먼저 띄우고(--port auto) 그 서버의 /api/wsession 을 공유 비밀·사용자 머리로 부른다(결정 5)."""
    import urllib.error
    import urllib.request
    import auth
    if op not in ("start", "stop", "model", "status"):
        raise HubError("op = start|stop|model|status")
    ws = _ws_of(path)
    st = server_state(ws)
    if not st["running"]:
        if op == "stop":  # 서버가 꺼져 있어도 터미널 세션(watch_requests)은 살아 있을 수 있다 - 하트비트의 수동 감시를 끝낸다
            import procutil
            cfg = load_ws_config(ws)
            manual = procutil.stop_manual(ws / cfg.get("out", "out") / ".studio" / "session.json")
            return {"ok": True, "path": str(ws), "running": False, "state": "off", "stopped": bool(manual.get("stopped")), "manual": manual, "session": session_summary(ws)}
        if op == "status":
            return {"ok": True, "path": str(ws), "running": False, "state": "off", "session": session_summary(ws)}
        url, _ = start_server(ws, auto=True)
    else:
        url = st["url"]
    headers = {"Content-Type": "application/json", "X-Nexa-Hub-Key": auth.hub_key(), "X-Nexa-User": user or "", "X-Nexa-Role": role or "user"}
    if op == "status":
        req = urllib.request.Request(url + "api/wsession", headers=headers)
    else:
        body = {"action": op}
        if agent:
            body["agent"] = agent
        if model:
            body["model"] = model
        if save_as in ("local", "shared"):
            body["saveAs"] = save_as
        if allow_web:  # 세션 단위 웹 검색 허용 - 작업 공간 서버가 역할(X-Nexa-Role)과 전역 설정을 확인한다
            body["allowWeb"] = True
        if grants:  # git·push·root - 같은 확인
            body["grants"] = [g for g in grants if g in ("git", "push", "root")]
        req = urllib.request.Request(url + "api/wsession", data=json.dumps(body).encode("utf-8"), method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return {"ok": True, "path": str(ws), "url": url, **json.loads(r.read().decode("utf-8"))}
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read().decode("utf-8")).get("error") or str(e)
        except ValueError:
            msg = str(e)
        raise HubError(msg)
    except Exception as e:  # noqa: BLE001
        raise HubError(f"작업 공간 서버에 닿지 못했다: {e}")


def _git_root(p):
    p = Path(p).resolve()
    for d in (p, *p.parents):
        if (d / ".git").exists():
            return d
    return None


def home(current=None, refused=None):
    from concurrent.futures import ThreadPoolExecutor
    s = load_settings()
    rows = s.get("recent", [])
    with ThreadPoolExecutor(max_workers=8) as ex:  # 꺼진 작업 공간마다 연결 시도가 있어 동시에 확인한다
        infos = list(ex.map(lambda r: workspace_info(r["path"], state=True), rows))
    recent = []
    for r, i in zip(rows, infos):
        i["opened"] = r.get("opened", "")
        i.setdefault("title", r.get("title") or Path(r["path"]).name)
        if i.get("workspace"):
            i["id"] = ws_id(r["path"])
            i["hubUrl"] = f"/w/{i['id']}/"
        recent.append(i)
    cur = workspace_info(current) if current else None
    if cur and cur.get("workspace"):
        cur["id"] = ws_id(current)
        cur["hubUrl"] = f"/w/{cur['id']}/"
    return {"documents": str(documents_dir()), "projectsRoot": str(projects_root()), "projectsRootDefault": str(default_projects_root()),
            "projectsRootFromEnv": bool(os.environ.get("NEXA_SLIDE_PROJECTS")), "engine": str(ENGINE),
            "current": cur, "refused": str(refused) if refused else None, "proxy": proxy_on(),
            "sessionGlobal": {k: s.get(k) for k in SESSION_KEYS if s.get(k) is not None},
            "recent": recent, "templates": templates(current), "starters": starters() if _supports_starter() else [], "sheetThemes": sheet_themes(rows),
            "samples": s.get("samples", []), "demo": str(projects_root() / DEMO_DIR)}


# ---------- 설정 ----------
def update_settings(b):
    s = load_settings()
    if "projectsRoot" in b:
        v = str(b["projectsRoot"] or "").strip()
        if v:
            p = Path(v).expanduser()
            if not p.is_absolute():
                raise HubError("기준 폴더는 절대 경로로 준다")
            if inside_engine(p):
                raise HubError("엔진 폴더 안은 기준 폴더로 쓸 수 없다")
            s["projectsRoot"] = str(p)
        else:
            s.pop("projectsRoot", None)  # 기본(문서 폴더/NexaSlide)으로
    if "samples" in b:
        out = []
        for x in b["samples"] or []:
            url = str(x.get("url", "")).strip()
            if not re.match(r"^https?://", url):
                raise HubError(f"샘플 주소는 http(s):// 로 시작해야 한다: {url}")
            out.append({"name": str(x.get("name") or url)[:80], "url": url[:500], "note": str(x.get("note", ""))[:200]})
        s["samples"] = out
    if "hubProxy" in b:  # 허브 한 포트로 중계(/w/<id>/) - 끄면 작업 공간 서버 포트로 바로 이동
        s["hubProxy"] = bool(b["hubProxy"])
    # AI 세션 전역 기본(관리자만 - server.py 가 역할을 확인한다). 빈 값은 지운다(기본으로)
    for k in ("sessionAgent", "sessionModel"):
        if k in b:
            v = str(b[k] or "").strip()
            if k == "sessionAgent" and v and v not in ("claude", "codex"):
                raise HubError("에이전트는 claude 또는 codex")
            if v:
                s[k] = v
            else:
                s.pop(k, None)
    if "sessionModels" in b:
        m = b["sessionModels"] or {}
        if not isinstance(m, dict):
            raise HubError("sessionModels 는 {에이전트: [모델…]}")
        s["sessionModels"] = {str(k): [str(x).strip() for x in (v or []) if str(x).strip()] for k, v in m.items() if str(k) in ("claude", "codex")}
    for k in ("sessionIdleMinutes", "sessionTurnMinutes", "sessionMax", "sessionMaxTurns", "engineMaxTurns", "engineTurnMinutes", "engineContinue"):
        if k in b:
            v = str(b[k] if b[k] is not None else "").strip()
            if v:
                try:
                    n = int(v)
                except ValueError:
                    raise HubError(f"{k} 는 정수")
                if n < 0 or n > 100000:
                    raise HubError(f"{k} 범위 밖")
                s[k] = n
            else:
                s.pop(k, None)
    for k in ("sessionAllowWeb", "sessionAllowGit", "sessionAllowPush", "sessionRepoRoot"):
        if k in b:
            if b[k]:
                s[k] = True
            else:
                s.pop(k, None)
    if "sessionBudgetUsd" in b:
        v = str(b["sessionBudgetUsd"] if b["sessionBudgetUsd"] is not None else "").strip()
        if v:
            try:
                s["sessionBudgetUsd"] = float(v)
            except ValueError:
                raise HubError("sessionBudgetUsd 는 숫자")
        else:
            s.pop("sessionBudgetUsd", None)
    if "agentPaths" in b:
        ap = b["agentPaths"] or {}
        s["agentPaths"] = {str(k): str(v).strip() for k, v in ap.items() if str(k) in ("claude", "codex") and str(v).strip()} if isinstance(ap, dict) else {}
    save_settings(s)
    return s


# ---------- 폴더 고르기 ----------
def list_dir(path=None):
    """폴더 고르기 창 - 하위 폴더(숨김 제외)와 표시(git 저장소·작업 공간)."""
    if not path:
        p = projects_root() if projects_root().is_dir() else documents_dir()
    else:
        p = Path(path).expanduser()
    p = p.resolve()
    if not p.is_dir():
        raise HubError(f"폴더가 없다: {p}")
    dirs = []
    try:
        for d in sorted(p.iterdir(), key=lambda x: x.name.lower()):
            try:
                if not d.is_dir() or d.name.startswith((".", "$")) or d.name in ("node_modules", "__pycache__"):
                    continue
                dirs.append({"name": d.name, "path": str(d), "git": (d / ".git").exists(), "workspace": find_workspace(d) is not None})
            except OSError:
                continue
    except PermissionError:
        raise HubError(f"읽을 권한이 없다: {p}")
    roots = []
    if os.name == "nt":
        import string
        roots = [f"{c}:\\" for c in string.ascii_uppercase if os.path.exists(f"{c}:\\")]
    else:
        roots = ["/"]
    return {"path": str(p), "parent": str(p.parent) if p.parent != p else None, "dirs": dirs, "roots": roots,
            "git": (p / ".git").exists(), "gitRoot": str(_git_root(p) or ""), "workspace": find_workspace(p) is not None,
            "insideEngine": inside_engine(p), "places": {"문서": str(documents_dir()), "제작 기준": str(projects_root()), "홈": str(Path.home())}}


# ---------- 서버 ----------
def start_server(ws, auto=False):
    """작업 공간 서버를 띄우고(이미 떠 있으면 그대로) 주소를 돌려준다.
    auto 면 설정 포트가 쓰는 중일 때 다음 빈 포트로 띄운다(--port auto) - 허브 중계로 여러 작업 공간을 함께 띄울 때(실제 포트는 server.json 에)."""
    code, log = _run([STUDIO / "service.py", "start"] + (["--port", "auto"] if auto else []), ws, timeout=30)
    code2, st = _run([STUDIO / "status.py", "--json"], ws, timeout=15)
    try:
        sv = json.loads(st)["server"]
    except (ValueError, KeyError):
        sv = {}
    if not sv.get("running"):
        raise HubError("작업 공간 서버를 띄우지 못했다", log=log + "\n" + st)
    return sv["url"], log


def _check_target(p):
    if not p.is_absolute():
        raise HubError("폴더는 절대 경로로 준다")
    if inside_engine(p):
        raise HubError("엔진 폴더 안에는 만들 수 없다 - 슬라이드 내용은 엔진과 다른 폴더·저장소에 둔다")


def _py():
    """명령 안내에 쓸 파이썬 이름 - PATH 에 python3 이 있으면 그것, 없으면 python."""
    return "python3" if shutil.which("python3") else "python"


def _quote(x, shell):
    x = str(x)
    if re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_./:=+-]*", x):  # 따옴표가 필요 없는 값(이름·숫자·주소)
        return x
    if shell == "powershell":
        return "'" + x.replace("'", "''") + "'"
    return "'" + x.replace("'", "'\\''") + "'"


def _cmdline(args, shell):
    """[프로그램, 인자…] → 붙여 넣을 수 있는 한 줄. 경로·글은 따옴표로 감싼다(프로그램 이름·옵션 이름은 그대로).
    bash 는 경로(Path 인자·프로그램)의 구분자를 / 로 쓴다 - Windows 경로도 D:/… (Git Bash 에서 그대로 동작, bash 형식과 일치).
    사용자가 적은 글(브리프)은 바꾸지 않는다."""
    def s(i, x):
        t = str(x)
        return t.replace("\\", "/") if shell == "bash" and (isinstance(x, Path) or i == 0) else t
    return " ".join(x if i == 0 or re.fullmatch(r"--[a-z-]+", x) else _quote(x, shell) for i, x in enumerate(s(i, a) for i, a in enumerate(args)))


def plan(b):
    """새로 만들기 계획 - 만들 폴더·포트와 그대로 실행할 init_workspace 명령. 시작 페이지는 이것을 보여 주고, create 는 이것을 실행한다.
    b = {title, template, starter?, deck?, kind?(sheet), folder?, sub?, slidesDir?, port?, purpose, audience, direction, materials, askDraft}.
    folder(+sub) 는 저장소 루트, 작업 공간은 그 아래 slidesDir(기본 slides)."""
    from init_workspace import free_port, hub_port, port_busy, resolve_target, taken_ports
    warn = []
    title = str(b.get("title") or "").strip()
    template = b.get("template") or "lecture"
    if not (TEMPLATES / template / "template.json").is_file():
        raise HubError(f"없는 템플릿: {template}")
    starter = b.get("starter") or None
    if starter and (not _supports_starter() or not (STARTERS / starter / "starter.json").is_file()):
        raise HubError(f"없는 시작용 내용: {starter}")
    name = title or re.sub(r"[^\w가-힣 .-]", "", str(b.get("defaultTitle") or ""))[:40].strip() or "제목"  # 비었을 때 자리 글 - 화면 언어대로(영어면 Title)
    slides_dir = str(b.get("slidesDir") or "").strip().strip("/\\") or "slides"
    if not re.fullmatch(r"[^\\/:*?\"<>|]+", slides_dir) or slides_dir.startswith("."):
        raise HubError(f"작업 공간 폴더는 폴더 이름 하나로 적는다(/ \\ : * ? \" < > | 없이, . 으로 시작하지 않게): {slides_dir}")
    ws = target = root = None  # target = init_workspace 에 주는 폴더(저장소 루트), ws = 그 아래 작업 공간
    custom = b.get("loc") == "custom" or bool(str(b.get("folder") or "").strip())
    folder = str(b.get("folder") or "").strip()
    if folder or not custom:  # 폴더 지정인데 아직 비어 있으면 위치 미정
        base = Path(folder).expanduser() if folder else projects_root()
        sub = str(b.get("sub") if b.get("sub") is not None else ("" if folder else slug(name))).strip().strip("/\\")
        target = (base / sub) if sub else base
        _check_target(target)
        if not folder and target.exists() and any(target.iterdir()):  # 기본 위치에서 이름이 겹치면 -2, -3 …
            k = 2
            while (base / f"{sub}-{k}").exists():
                k += 1
            warn.append(f"{target.name} 폴더가 이미 있어 {sub}-{k} 에 만듭니다")
            target = base / f"{sub}-{k}"
        ws, root = resolve_target(target.resolve(), slides_dir=slides_dir)
        if (ws / CONFIG_NAME).is_file():
            warn.append("이 폴더에는 이미 작업 공간이 있습니다 - 만들지 않고 열기를 권합니다")
    raw = str(b.get("port") or "").strip()
    if raw:
        try:
            port = int(raw)
        except ValueError:
            raise HubError("포트는 숫자로 적는다")
        if not 1024 <= port <= 65535:
            raise HubError("포트는 1024~65535")
        if port == hub_port():
            warn.append(f"포트 {port} 는 시작 페이지(허브) 포트입니다 - 다른 포트를 고르세요")
        elif port_busy(port):
            warn.append(f"포트 {port} 는 지금 다른 프로그램이 쓰고 있습니다 - 이대로는 만들 수 없습니다")
        elif taken_ports(skip=ws).get(port):
            warn.append(f"포트 {port} 는 작업 공간 {taken_ports(skip=ws)[port]} 설정과 같습니다 - 두 서버를 함께 띄우면 뒤에 띄운 쪽이 실패합니다")
    else:
        port = free_port(skip=ws)
    sheet = b.get("kind") == "sheet"  # 첫 문서를 시트로(docs/sheets.md) - 시작용 내용은 쓰지 않는다
    deck = re.sub(r"[^A-Za-z0-9_-]", "", str(b.get("deck") or "")) or "intro"
    args = [STUDIO / "init_workspace.py", target or "<폴더>", "--title", name, "--template", template]
    if deck != "intro":
        args += ["--deck", deck]
    if sheet:
        args += ["--kind", "sheet"]
        starter = None
        st = b.get("sheetTheme") if isinstance(b.get("sheetTheme"), dict) else {}
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,39}", str(st.get("name") or "")):
            args += ["--sheet-theme", st["name"]]
            if st.get("from"):
                args += ["--sheet-theme-from", str(st["from"])]
    if starter:
        args += ["--starter", starter]
        lang = re.sub(r"[^a-z]", "", str(b.get("lang") or "ko").lower())[:5]
        if lang and lang != "ko":  # 화면 언어가 영어면 시작용 내용도 영어로(번역본 폴더 또는 사전) - 0.22.10
            args += ["--lang", lang]
    if slides_dir != "slides":
        args += ["--slides-dir", slides_dir]
    args += ["--port", port, "--build"]
    for key in ("purpose", "audience"):
        v = " ".join(str(b.get(key) or "").split())
        if v:
            args += [f"--{key}", v]
    for key, opt in (("direction", "--direction"), ("materials", "--material")):  # 여러 줄은 줄마다 옵션 하나
        for line in str(b.get(key) or "").splitlines():
            if line.strip():
                args += [opt, line.strip()]
    if b.get("askDraft"):
        args += ["--ask-draft"]
    if isinstance(b.get("wizard"), dict):  # 회사 템플릿 마법사 - 만든 뒤 그 작업 공간에 templates/<이름>/ 을 두고 template 을 바꾼다(기반 템플릿으로 먼저 만든다)
        wn = str(b["wizard"].get("name") or "")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,39}", wn):
            raise HubError("회사 템플릿 이름은 영문·숫자·-·_ 로 1~40자")
        if (TEMPLATES / wn / "template.json").is_file():
            raise HubError(f"엔진 템플릿과 같은 이름은 쓸 수 없다: {wn}")
        warn.append(f"만든 뒤 회사 템플릿 {wn}({template} 바탕)을 작업 공간 templates/{wn}/ 에 두고 적용합니다")
    start = [(ws or Path("<폴더>") / slides_dir) / "nexa.py", "start"]
    py = _py()
    if ws and "&" in str(ws) and os.name == "nt":
        # pyenv-win 등의 python3 은 배치(.bat) 대리 실행기라 인자 경로의 & 에서 명령이 잘린다 → 실제 실행 파일로 안내
        shim = shutil.which("python3") or ""
        if shim.lower().endswith((".bat", ".cmd")) and " " not in sys.executable:
            py = sys.executable
        warn.append("경로에 & 가 있습니다 - Windows 의 python3(배치 실행기)는 & 에서 명령이 잘려 실제 파이썬 실행 파일 경로로 안내합니다. "
                    "가능하면 폴더 이름에서 & 를 빼세요(예: S&OP → S-OP).")
    cmds = {sh: {"init": _cmdline([py, *args], sh), "start": _cmdline([py, *start], sh)} for sh in ("powershell", "bash")}
    return {"ok": True, "path": str(ws) if ws else "", "root": str(root) if root else "", "title": title, "port": port, "url": f"http://127.0.0.1:{port}/",
            "args": [str(x) for x in args], "commands": cmds, "warnings": warn, "ready": bool(title and ws)}


def create(b):
    """새 작업 공간 - plan 의 init_workspace 명령을 그대로 실행하고(브리프·빌드·초안 요청·최근 작업 포함) 서버를 띄운다."""
    p = plan(b)
    if not p["title"]:
        raise HubError("제목을 적는다")
    if not p["path"]:
        raise HubError("저장할 폴더를 고른다")
    ws = Path(p["path"])
    if (ws / CONFIG_NAME).is_file():  # 지정한 폴더에 이미 있으면 만들지 않고 열기를 권한다
        raise HubError("이 폴더에는 이미 작업 공간이 있다 - 열기로 연다", existing=str(ws))
    code, log = _run(p["args"], None, timeout=300)
    if code != 0 or not (ws / CONFIG_NAME).is_file():
        raise HubError("작업 공간을 만들지 못했다", log=log)
    if isinstance(b.get("wizard"), dict):  # 회사 템플릿 - 서버를 띄우기 전에 두므로 재시작이 필요 없다(덱은 기반 템플릿으로 빌드됨 - sizes 는 같다)
        try:
            tr = create_template({**b["wizard"], "ws": str(ws), "base": b["wizard"].get("base") or p["args"][p["args"].index("--template") + 1]})
        except HubError as e:
            raise HubError(f"작업 공간은 만들었지만 회사 템플릿을 만들지 못했다: {e}", path=str(ws), log=log, **e.extra)
        log += "\n" + "\n".join(f"템플릿 {tr['name']}: {f}" for f in tr["files"])
    moved = claim_attachments(ws, b.get("attachments"))  # 참고 자료 첨부 → materials/ · BRIEF.md
    if moved:
        log += "\n첨부: " + ", ".join(moved)
    url, slog = start_server(ws, auto=proxy_on())
    cfg = _read_json(ws / CONFIG_NAME) or {}
    decks = sorted(f.stem for f in (ws / cfg.get("decks", "decks")).glob("*.json") if not f.name.endswith(".requests.json"))
    return {"ok": True, "path": str(ws), **nav(ws, url), "decks": decks, "log": log + "\n" + slog}


def build_all(ws):
    """content/*.json(밑줄로 시작하는 공통 파일 제외)을 모두 빌드한다."""
    cfg = _read_json(ws / CONFIG_NAME) or {}
    content = ws / cfg.get("content", "content")
    built = []
    for f in sorted(content.glob("*.json")) if content.is_dir() else []:
        if f.name.startswith("_"):
            continue
        code, _ = _run([STUDIO / "build_deck.py", f.stem], ws, timeout=120)
        if code == 0:
            built.append(f.stem)
    return built


def open_ws(path):
    p = Path(str(path or "").strip()).expanduser()
    if not p.is_absolute():
        raise HubError("폴더는 절대 경로로 준다")
    if not p.is_dir():
        raise HubError(f"폴더가 없다: {p}")
    if inside_engine(p):
        raise HubError("엔진 폴더 안의 작업 공간은 열지 않는다 - 예제는 '데모'로 연다")
    ws = find_workspace(p, deep=True)
    if ws is None:
        raise HubError("이 폴더에는 작업 공간(nexa-slide.json)이 없다 - 이 폴더를 저장소 루트로 새로 만들 수 있다(작업 공간은 slides/)",
                       needInit=True, path=str(p), git=(p / ".git").exists())
    cfg = load_ws_config(ws)
    remember(ws, cfg.get("title", ws.name))
    st = server_state(ws, cfg)
    if st["running"]:  # 이미 떠 있으면 띄우지 않고 그 주소로
        return {"ok": True, "path": str(ws), **nav(ws, st["url"]), "log": ""}
    url, log = start_server(ws, auto=proxy_on())
    return {"ok": True, "path": str(ws), **nav(ws, url), "log": log}


def _ws_of(path):
    p = Path(str(path or "").strip()).expanduser()
    if not p.is_absolute() or not p.is_dir():
        raise HubError(f"폴더가 없다: {p}")
    ws = find_workspace(p, deep=True)
    if ws is None:
        raise HubError(f"작업 공간(nexa-slide.json)이 없다: {p}")
    return ws


def start_ws(path):
    """작업 공간 서버만 띄운다(페이지는 이동하지 않는다) - 이미 떠 있으면 그대로."""
    ws = _ws_of(path)
    st = server_state(ws)
    if st["running"]:
        return {"ok": True, "path": str(ws), **st, "id": ws_id(ws), "hubUrl": f"/w/{ws_id(ws)}/"}
    url, log = start_server(ws, auto=proxy_on())
    return {"ok": True, "path": str(ws), "running": True, "url": url, "log": log, "id": ws_id(ws), "hubUrl": f"/w/{ws_id(ws)}/"}


def proxy_target(wid):
    """중계 대상 - 중계 이름의 작업 공간 서버가 듣는 포트. 꺼져 있으면 띄운다(설정 포트가 쓰는 중이면 빈 포트로).
    nexa.py 로 이미 띄운 서버가 있으면 그 서버로 - 작업 공간당 서버는 하나다."""
    ws = ws_by_id(wid)
    if ws is None:
        raise HubError(f"모르는 작업 공간이다: {wid} - 시작 페이지에서 열거나 만든 작업 공간만 중계한다")
    st = server_state(ws)
    url = st["url"]
    if not st["running"]:
        url, _ = start_server(ws, auto=True)
    import urllib.parse
    port = urllib.parse.urlparse(url).port
    if not port:
        raise HubError(f"작업 공간 서버 주소를 알 수 없다: {url}")
    return ws, int(port)


def stop_ws(path):
    """작업 공간 서버를 끈다(service.py stop). 지금 이 페이지를 내주는 서버 자신은 끄지 않는다."""
    ws = _ws_of(path)
    me = os.environ.get("NEXA_SLIDE_WORKSPACE")
    if me and Path(me).resolve() == ws.resolve():
        raise HubError("지금 이 페이지를 내주는 작업 공간 서버다 - 여기서는 끄지 않는다(터미널에서 nexa.py stop)")
    code, log = _run([STUDIO / "service.py", "stop"], ws, timeout=30)
    st = server_state(ws)
    if st["running"]:
        raise HubError("서버를 끄지 못했다", log=log)
    return {"ok": True, "path": str(ws), "running": False, "log": log}


def demo():
    """엔진 예제를 제작 기준 폴더의 nexa-slide-demo 로 복사해(처음 한 번) 연다 - 엔진 폴더에서 직접 열지 않는다."""
    ws = projects_root() / DEMO_DIR
    if not (ws / CONFIG_NAME).is_file():
        for sub in ("content", "decks", "assets"):
            src = EXAMPLE / sub
            if src.is_dir():
                shutil.copytree(src, ws / sub, dirs_exist_ok=True, ignore=shutil.ignore_patterns("*.requests.json", ".history"))
        ex = _read_json(EXAMPLE / CONFIG_NAME) or {}
        code, log = _run([STUDIO / "init_workspace.py", ws, "--title", ex.get("title") or "nexa-slide 데모",
                          "--template", ex.get("template", "lecture"), "--deck", "demo", "--flat"], None, timeout=60)
        if code != 0:
            raise HubError("데모를 만들지 못했다", log=log)
        cfg = _read_json(ws / CONFIG_NAME) or {}
        keep = {k: cfg[k] for k in ("port", "engine") if k in cfg}
        cfg = {**cfg, **{k: v for k, v in ex.items() if k not in ("port", "engine")}, **keep}
        (ws / CONFIG_NAME).write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    remember(ws, (_read_json(ws / CONFIG_NAME) or {}).get("title", "데모"))
    url, log = start_server(ws, auto=proxy_on())
    return {"ok": True, "path": str(ws), **nav(ws, url)}


# ---------- 미리보기 ----------
def _stamp(template, starter, ws_tpl=None):
    """미리보기를 다시 만들지 정하는 값 - 엔진 코드·템플릿·시작용 내용(·작업 공간 템플릿 폴더·그 로고) 중 가장 늦게 바뀐 시각."""
    files = [*STUDIO.glob("*.py"), *TEMPLATES.rglob("*")]
    if starter:
        files += [*(STARTERS / starter).rglob("*")]
    if ws_tpl:
        files += [*ws_tpl[0].rglob("*"), *ws_tpl[1].glob("*.png")]
    return max((f.stat().st_mtime_ns for f in files if f.is_file()), default=0)


def preview_key(template, starter, lang="ko", ws=None):
    return (f"ws-{ws_id(ws)}--" if ws else "") + f"{template}--{starter or 'layouts'}" + ("" if (lang or "ko") == "ko" else f"--{lang}")


def preview(template=None, starter=None, lang="ko", ws=None):
    """템플릿 × 시작용 내용을 임시 작업 공간(PREVIEW_ROOT/<템플릿>--<내용>)에 실제로 만들어 빌드한 덱을 돌려준다.
    시작용 내용이 없으면 레이아웃 견본(전 레이아웃 한 장씩). 템플릿이 없으면 시작용 내용이 정한 템플릿.
    엔진·템플릿·내용이 바뀌지 않았으면 전에 만든 것을 그대로 쓴다. 화면은 home.html 이 render.js 로 그린다.
    ws(작업 공간 서버의 시작 페이지)를 주면 그 작업 공간의 회사 템플릿(templates/<이름>/)도 된다 - template.json 과 로고를 임시 작업 공간에 복사해 빌드한다."""
    if starter and not (STARTERS / str(starter) / "starter.json").is_file():
        raise HubError(f"없는 시작용 내용: {starter}")
    if not template:
        template = ((_read_json(STARTERS / starter / "starter.json") or {}).get("template") if starter else None) or "lecture"
    ws_tpl = None  # (작업 공간 템플릿 폴더, 그 작업 공간의 assets/brand 폴더)
    if not re.fullmatch(r"[A-Za-z0-9_-]+", str(template)):
        raise HubError(f"없는 템플릿: {template}")
    if not (TEMPLATES / template / "template.json").is_file():
        src = Path(ws) / "templates" / template if ws else None
        if not src or not (src / "template.json").is_file():
            raise HubError(f"없는 템플릿: {template}")
        wcfg = load_ws_config(ws)
        ws_tpl = (src, (Path(ws) / wcfg.get("assetRoot", ".") / "assets" / "brand").resolve())
    lang = re.sub(r"[^a-z-]", "", str(lang or "ko").lower()) or "ko"  # 견본 글 언어 - studio/i18n/content.<lang>.json · starters/<이름>/content.<lang>/ (없으면 한국어)
    key = preview_key(template, starter, lang, ws if ws_tpl else None)
    ws = PREVIEW_ROOT / key
    stamp = str(_stamp(template, starter, ws_tpl)) + (f"|{lang}|{(STUDIO / 'i18n' / f'content.{lang}.json').stat().st_mtime_ns if (STUDIO / 'i18n' / f'content.{lang}.json').is_file() else 0}" if lang != "ko" else "")
    meta = _read_json(ws / "preview.json") or {}
    if meta.get("stamp") != stamp:
        if ws.exists():
            shutil.rmtree(ws)
        if ws_tpl:  # 회사 템플릿 - init 전에 임시 작업 공간에 template.json·로고를 두면 init·빌드가 그것을 읽는다
            (ws / "templates" / template).mkdir(parents=True, exist_ok=True)
            shutil.copy2(ws_tpl[0] / "template.json", ws / "templates" / template / "template.json")
            for f in ws_tpl[1].glob("*.png") if ws_tpl[1].is_dir() else []:
                (ws / "assets" / "brand").mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, ws / "assets" / "brand" / f.name)
            label = (_read_json(ws_tpl[0] / "template.json") or {}).get("label", template)
        else:
            label = (_read_json(TEMPLATES / template / "template.json") or {}).get("label", template)
        args = [STUDIO / "init_workspace.py", ws, "--title", f"{label} 미리보기", "--template", template, "--deck", "layouts", "--no-remember", "--flat"]
        if starter:
            args += ["--starter", starter]
        if lang != "ko":
            args += ["--lang", lang]
        code, log = _run(args, None, timeout=60)
        if code != 0:
            raise HubError("미리보기를 만들지 못했다", log=log)
        if not starter:  # 레이아웃 견본 - 레이아웃마다 필드 예시로 한 장씩
            code, out = _run([STUDIO / "layout_samples.py", "--json", "--lang", lang], ws, timeout=60)
            if code != 0:
                raise HubError("레이아웃 견본을 읽지 못했다", log=out)
            samples = json.loads(out[out.index("{"):])
            deck = {"id": "layouts", "title": f"레이아웃 견본 {len(samples)}종", "part": "day1", "version": "0.1",
                    "slides": [{"title": v["label"], **v["sample"]} for v in samples.values()]}  # 제목 없는 예시는 레이아웃 이름으로
            (ws / "content" / "layouts.json").write_text(json.dumps(deck, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
        decks = build_all(ws)
        if lang != "ko":  # 빌드된 덱의 글(레이아웃이 넣는 목차·N부·자리 글 포함)을 번역 - 사용자 덱이 아닌 미리 보기용 임시 작업 공간이라 괜찮다
            from content_i18n import tr as _tr
            dcfg = _read_json(ws / CONFIG_NAME) or {}
            for d in decks:
                dp = ws / dcfg.get("decks", "decks") / f"{d}.json"
                dj = _read_json(dp)
                if dj:
                    dp.write_text(json.dumps(_tr(dj, lang), ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
        code, tok = _run(["-c", "import json,sys; sys.path.insert(0, sys.argv[1]); from common import resolve_tokens; "
                                "print(json.dumps(resolve_tokens(), ensure_ascii=False))", STUDIO], ws, timeout=60)
        if code != 0 or not decks:
            raise HubError("미리보기를 빌드하지 못했다", log=tok)
        meta = {"stamp": stamp, "template": template, "starter": starter, "decks": decks, "tokens": json.loads(tok[tok.index("{"):])}
        (ws / "preview.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8", newline="\n")
    cfg = _read_json(ws / CONFIG_NAME) or {}
    decks = [_read_json(ws / cfg.get("decks", "decks") / f"{d}.json") for d in meta["decks"]]
    base = "/preview/" + "/".join(Path(key, cfg.get("assetRoot", ".")).as_posix().split("/")).rstrip("/.") + "/"
    return {"ok": True, "template": template, "starter": starter, "lang": lang, "tokens": meta["tokens"], "base": base,
            "decks": [d for d in decks if d]}


def project(b):
    act = b.get("action")
    if act == "create":
        return create(b)
    if act == "plan":
        return plan(b)
    if act == "open":
        return open_ws(b.get("path"))
    if act == "start":
        return start_ws(b.get("path"))
    if act == "stop":
        return stop_ws(b.get("path"))
    if act == "demo":
        return demo()
    if act == "forget":
        forget(b.get("path", ""))
        return {"ok": True}
    if act == "palette":
        return palette_preview(b)
    if act == "attach":
        return save_attach(b)
    if act == "template":
        return create_template(b)
    raise HubError("action = create|plan|open|start|stop|demo|forget|palette|attach|template")


# ---------- 회사 템플릿 만들기(마법사) - 작업 공간에만 쓴다(docs/dev/template-wizard-design.md, 안 A) ----------
PNG_SIG = b"\x89PNG\r\n\x1a\n"
FONT_EXTS = (".ttf", ".otf", ".woff", ".woff2")
TEMPLATE_NAME_RX = r"[A-Za-z0-9][A-Za-z0-9_-]{0,39}"
WINDOWS_RESERVED = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}  # 폴더 이름으로 쓸 수 없다(#7)


def palette_preview(b):
    """마법사 미리 보기용 - 색 5개(+고급에서 고친 파생값) → 파생 색 전부와 대비 경고. 아무것도 쓰지 않는다."""
    import palette
    try:
        return {"ok": True, **palette.build(b.get("colors") or {})}
    except ValueError as e:
        raise HubError(str(e))


def _b64_file(item, what, max_mb, exts=None):
    """{name, data(base64)} → (안전한 파일 이름, bytes). 크기·확장자 확인."""
    import base64
    if not isinstance(item, dict) or not item.get("data"):
        raise HubError(f"{what} 파일이 비었다")
    name = re.sub(r"[^A-Za-z0-9가-힣._ -]+", "-", str(item.get("name") or what)).strip(" .-") or what
    ext = Path(name).suffix.lower()
    if exts and ext not in exts:
        raise HubError(f"{what} 파일은 {' · '.join(exts)} 만: {name}")
    try:
        data = base64.b64decode(str(item["data"]).split(",")[-1], validate=False)
    except (ValueError, TypeError):
        raise HubError(f"{what} 파일을 읽지 못했다(base64)")
    if len(data) > max_mb * 1024 * 1024:
        raise HubError(f"{what} 파일이 너무 크다({len(data) // 1024} KB) - {max_mb} MB 까지")
    return name, data


def create_template(b):
    """b = {ws, name, base, colors{primary, surface, on-surface, accent1, accent2, …파생값}, label?, description?, brand?{name, logo{name,data}, wordmark{…}},
            font?{preset} | font?{name, family, files{regular{name,data}, bold?{…}}}, overwrite?}
    → 작업 공간에 templates/<이름>/template.json(extends+tokenOverrides) · assets/brand/logo.png · fonts/<파일> 을 쓰고 nexa-slide.json 의
      template(·brand·fontPresets·fontPreset)을 바꾼다(set_template 과 같은 처리 - 공유 파일에만). 엔진 저장소에는 아무것도 쓰지 않는다.
    서버가 떠 있으면 재시작이 필요하다(응답 restart). 기존 덱의 글자 크기 하한은 build_deck --force 때 적용된다."""
    import datetime as _dt
    import palette
    ws = _ws_of(b.get("ws") or b.get("path"))
    name = str(b.get("name") or "").strip()
    if not re.fullmatch(TEMPLATE_NAME_RX, name):
        raise HubError("템플릿 이름은 영문·숫자·-·_ 로 1~40자(영문·숫자로 시작)")
    if name.lower() in WINDOWS_RESERVED:  # con·aux·com1… - Windows 에서 폴더를 만들 수 없다(엔진 이름 검사보다 먼저 - TEMPLATES/con.exists() 가 True 라 안내가 틀렸었다, #7)
        raise HubError(f"Windows 예약 이름은 쓸 수 없다: {name} - 다른 이름을 고른다")
    if (TEMPLATES / name).exists():
        raise HubError(f"엔진 템플릿과 같은 이름은 쓸 수 없다: {name} - 다른 이름을 고른다")
    base = str(b.get("base") or "lecture")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", base) or not (TEMPLATES / base / "template.json").is_file():
        raise HubError(f"없는 기반 템플릿: {base}(엔진 템플릿 중 하나)")
    tdir = ws / "templates" / name
    if (tdir / "template.json").is_file() and not b.get("overwrite"):
        raise HubError(f"이미 있는 템플릿: {name} - 다른 이름을 쓰거나 덮어쓰기를 고른다", exists=True)
    try:
        colors = palette.derive(b.get("colors") or {})
    except ValueError as e:
        raise HubError(f"색: {e}")
    warns = palette.warnings(colors)
    label = " ".join(str(b.get("label") or "").split())[:80] or name
    desc = " ".join(str(b.get("description") or "").split())[:300] or f"회사 템플릿 - {base} 바탕, 시작 페이지의 마법사로 만듦"
    tj = {"_comment": "작업 공간 템플릿(회사 템플릿) - 엔진 템플릿을 extends 하고 tokenOverrides·label·description·parts 만 바꾼다. tokens·design·sizes·check 는 둘 수 없다(docs/templates.md)",
          "extends": base, "label": label, "description": desc, "tokenOverrides": {"colors": colors}}
    i18n = b.get("i18n")
    if isinstance(i18n, dict) and isinstance(i18n.get("en"), dict):
        tj["i18n"] = {"en": {k: " ".join(str(i18n["en"].get(k) or "").split())[:300] for k in ("label", "description") if i18n["en"].get(k)}}
    cfg = load_ws_config(ws, local=False)  # 공유 파일에만 쓴다(PC 별 nexa-slide.local.json 값은 섞지 않는다)
    asset_root = (ws / cfg.get("assetRoot", ".")).resolve()
    writes = []  # (경로, bytes) - 검사가 다 끝난 뒤 한꺼번에 쓴다
    brand = b.get("brand") if isinstance(b.get("brand"), dict) else {}
    bcfg = dict(cfg.get("brand") or {})
    for key, default in (("logo", "assets/brand/logo.png"), ("wordmark", "assets/brand/wordmark.png")):
        if brand.get(key):
            _n, data = _b64_file(brand[key], "로고" if key == "logo" else "워드마크", 4)
            if not data.startswith(PNG_SIG):
                raise HubError(("로고" if key == "logo" else "워드마크") + " 는 PNG 파일만(가로세로 비율을 PNG 머리에서 읽는다)")
            writes.append((asset_root / default, data))
            bcfg[key] = default
    if brand.get("name") is not None:
        bcfg["name"] = " ".join(str(brand.get("name") or "").split())[:80]
    if brand:
        cfg["brand"] = bcfg
    font = b.get("font") if isinstance(b.get("font"), dict) else {}
    if font.get("files"):  # 전용 글꼴 - 파일은 fonts/, 세트는 nexa-slide.json fontPresets(엔진에 글꼴 파일을 넣지 않는다 - docs/fonts.md)
        fname = str(font.get("name") or name)
        family = " ".join(str(font.get("family") or "").split())[:60]
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", fname):
            raise HubError("글꼴 세트 이름은 영문·숫자·-·_")
        if not family or '"' in family:
            raise HubError("글꼴 이름(family)을 적는다 - 글꼴 파일의 패밀리 이름")
        files = font["files"] if isinstance(font["files"], dict) else {}
        if not files.get("regular"):
            raise HubError("글꼴 파일(regular)을 올린다")
        fdir = ws / cfg.get("fontsDir", "fonts")
        measure = {}
        for role in ("regular", "bold"):
            if files.get(role):
                fn, data = _b64_file(files[role], f"글꼴({role})", 30, FONT_EXTS)
                writes.append((fdir / fn, data))
                measure[role] = fn
        measure.setdefault("bold", measure["regular"])
        face = {"css": f'"{family}", "Malgun Gothic", "맑은 고딕", "Apple SD Gothic Neo", sans-serif', "latin": family, "ea": family, "measure": measure}
        cfg.setdefault("fontPresets", {})[fname] = {"body": dict(face), "heading": dict(face)}
        cfg["fontPreset"] = fname
    elif font.get("preset"):
        preset = str(font["preset"])
        btpl = _read_json(TEMPLATES / base / "template.json") or {}
        bname = base if btpl.get("tokens") else (btpl.get("extends") or "lecture")
        btok = _read_json(TEMPLATES / bname / ((_read_json(TEMPLATES / bname / "template.json") or {}).get("tokens") or "tokens.json")) or {}
        if preset not in (btok.get("fontPresets") or {}) and preset not in (cfg.get("fontPresets") or {}):
            raise HubError(f"없는 글꼴 세트: {preset}")
        cfg["fontPreset"] = preset
    cfg["template"] = name
    made, backups = [], []
    try:  # 템플릿 폴더부터 - 여기서 실패하면(예약 이름·권한) 로고·글꼴을 건드리기 전에 끝난다(#7: 로고만 바뀐 반쪽 상태 방지)
        tdir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise HubError(f"템플릿 폴더를 만들지 못했다: templates/{name} - {e}")
    hist_root = ws / cfg.get("out", "out") / ".history" / "wizard"
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:22]  # 밀리초까지 - 같은 초에 두 번 만들어도 앞 백업을 덮지 않는다(#8)
    hist, n = hist_root / stamp, 2
    while hist.exists():  # 그래도 겹치면 _2, _3 …
        hist = hist_root / f"{stamp}_{n}"
        n += 1
    for p, data in writes:
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.is_file() and p.read_bytes() != data:  # 기존 로고·글꼴 파일은 out/.history/wizard/<시각>/ 에 백업하고 덮어쓴다(#7)
            rel = p.relative_to(asset_root) if asset_root in p.parents else Path(p.name)
            bk = hist / rel
            bk.parent.mkdir(parents=True, exist_ok=True)
            bk.write_bytes(p.read_bytes())
            backups.append(str(bk.relative_to(ws)) if ws in bk.parents else str(bk))
        p.write_bytes(data)
        made.append(str(p.relative_to(ws)) if ws in p.parents else str(p))
    (tdir / "template.json").write_text(json.dumps(tj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    made.insert(0, f"templates/{name}/template.json")
    (ws / CONFIG_NAME).write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    made.append(CONFIG_NAME)
    st = server_state(ws)
    local_tpl = load_ws_config(ws).get("template")
    note = ("작업 공간 서버를 다시 시작해야 새 템플릿이 반영됩니다. " if st["running"] else "") + "기존 덱의 글자 크기 하한은 build_deck --force 로 다시 빌드할 때 적용되고, PPTX 는 다시 내보냅니다."
    if local_tpl != name:
        note += f" 알림: 이 PC 의 {LOCAL_CONFIG} 에 template 이 있어 이 PC 에서는 그 값({local_tpl})이 쓰입니다."
    if backups:
        note += f" 바뀐 기존 파일 {len(backups)}개는 {hist.relative_to(ws) if ws in hist.parents else hist} 에 백업했습니다."
    return {"ok": True, "path": str(ws), "name": name, "base": base, "label": label, "dir": str(tdir), "files": made, "backups": backups, "colors": colors, "warnings": warns,
            "config": {"template": name, "fontPreset": cfg.get("fontPreset"), "brand": cfg.get("brand")},
            "restart": {"needed": bool(st["running"]), "running": bool(st["running"]), "url": st.get("url"), "id": ws_id(ws), "hubUrl": f"/w/{ws_id(ws)}/"},
            "template": next((t for t in ws_templates(ws) if t["name"] == name), None), "note": note}
