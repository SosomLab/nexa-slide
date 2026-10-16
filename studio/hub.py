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

from paths import (ENGINE, default_projects_root, documents_dir, forget, inside_engine, load_settings, load_ws_config, projects_root,
                   remember, repo_workspace, save_settings, user_dir)

STUDIO = ENGINE / "studio"
EXAMPLE = ENGINE / "example"
STARTERS = ENGINE / "starters"
TEMPLATES = STUDIO / "templates"
CONFIG_NAME = "nexa-slide.json"
DEMO_DIR = "nexa-slide-demo"
PREVIEW_ROOT = user_dir() / "hub" / "preview"  # 미리보기용 임시 작업 공간(엔진·기준 폴더 밖, 사용자 설정 폴더)


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
def templates():
    out = []
    for d in sorted(TEMPLATES.iterdir()):
        t = _read_json(d / "template.json")
        if not t or t.get("hidden"):  # 숨긴 템플릿(검토 대상으로 옮김) — 목록에서 제외, 이미 쓰는 작업 공간은 그대로 동작
            continue
        tok = _read_json(d / t["tokens"]) if t.get("tokens") else None
        if tok is None and t.get("extends"):
            base = _read_json(TEMPLATES / t["extends"] / "template.json") or {}
            tok = _read_json(TEMPLATES / t["extends"] / base.get("tokens", "tokens.json")) or {}
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
        out.append({"name": d.name, "label": t.get("label", d.name), "description": t.get("description", ""), "i18n": t.get("i18n") or {},
                    "extends": t.get("extends"), "swatches": sw,
                    "concept": f"/studio/templates/{d.name}/design/concept.html" if (d / "design" / "concept.html").is_file() else None})
    return out


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


def workspace_info(path, state=False):
    """작업 공간 요약 - 제목·템플릿·덱 수·세션. state 면 실행 상태(running·url)까지 확인한다(응답을 두드려 본다)."""
    p = Path(path)
    if not (p / CONFIG_NAME).is_file():
        return {"path": str(p), "exists": p.is_dir(), "workspace": False}
    cfg = load_ws_config(p)  # PC 별 nexa-slide.local.json(포트 등)까지
    decks_dir = p / cfg.get("decks", "decks")
    decks = sorted(f.stem for f in decks_dir.glob("*.json") if not f.name.endswith(".requests.json")) if decks_dir.is_dir() else []
    info = server_state(p, cfg) if state else {"running": None, "url": (_read_json(p / cfg.get("out", "out") / ".studio" / "server.json") or {}).get("url")}
    return {"path": str(p), "exists": True, "workspace": True, "title": cfg.get("title", p.name), "template": cfg.get("template", "lecture"),
            "port": cfg.get("port"), "decks": decks, "url": info.get("url"), "running": info.get("running"), "git": _git_root(p) is not None,
            "brief": (p / "BRIEF.md").is_file(), "root": str((p / cfg["repo"]["root"]).resolve()) if isinstance(cfg.get("repo"), dict) else "",
            "session": session_summary(p, cfg)}


SESSION_KEYS = ("sessionAgent", "sessionModel", "sessionModels", "sessionIdleMinutes", "sessionTurnMinutes", "sessionMax", "sessionMaxTurns", "sessionBudgetUsd", "agentPaths",
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
            "recent": recent, "templates": templates(), "starters": starters() if _supports_starter() else [],
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
    for k in ("sessionIdleMinutes", "sessionTurnMinutes", "sessionMax", "sessionMaxTurns"):
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
    b = {title, template, starter?, deck?, folder?, sub?, slidesDir?, port?, purpose, audience, direction, materials, askDraft}.
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
    deck = re.sub(r"[^A-Za-z0-9_-]", "", str(b.get("deck") or "")) or "intro"
    args = [STUDIO / "init_workspace.py", target or "<폴더>", "--title", name, "--template", template]
    if deck != "intro":
        args += ["--deck", deck]
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
def _stamp(template, starter):
    """미리보기를 다시 만들지 정하는 값 - 엔진 코드·템플릿·시작용 내용 중 가장 늦게 바뀐 시각."""
    files = [*STUDIO.glob("*.py"), *TEMPLATES.rglob("*")]
    if starter:
        files += [*(STARTERS / starter).rglob("*")]
    return max((f.stat().st_mtime_ns for f in files if f.is_file()), default=0)


def preview_key(template, starter, lang="ko"):
    return f"{template}--{starter or 'layouts'}" + ("" if (lang or "ko") == "ko" else f"--{lang}")


def preview(template=None, starter=None, lang="ko"):
    """템플릿 × 시작용 내용을 임시 작업 공간(PREVIEW_ROOT/<템플릿>--<내용>)에 실제로 만들어 빌드한 덱을 돌려준다.
    시작용 내용이 없으면 레이아웃 견본(전 레이아웃 한 장씩). 템플릿이 없으면 시작용 내용이 정한 템플릿.
    엔진·템플릿·내용이 바뀌지 않았으면 전에 만든 것을 그대로 쓴다. 화면은 home.html 이 render.js 로 그린다."""
    if starter and not (STARTERS / str(starter) / "starter.json").is_file():
        raise HubError(f"없는 시작용 내용: {starter}")
    if not template:
        template = ((_read_json(STARTERS / starter / "starter.json") or {}).get("template") if starter else None) or "lecture"
    if not re.fullmatch(r"[A-Za-z0-9_-]+", str(template)) or not (TEMPLATES / template / "template.json").is_file():
        raise HubError(f"없는 템플릿: {template}")
    lang = re.sub(r"[^a-z-]", "", str(lang or "ko").lower()) or "ko"  # 견본 글 언어 - studio/i18n/content.<lang>.json · starters/<이름>/content.<lang>/ (없으면 한국어)
    key = preview_key(template, starter, lang)
    ws = PREVIEW_ROOT / key
    stamp = _stamp(template, starter) + (f"|{lang}|{(STUDIO / 'i18n' / f'content.{lang}.json').stat().st_mtime_ns if (STUDIO / 'i18n' / f'content.{lang}.json').is_file() else 0}" if lang != "ko" else "")
    meta = _read_json(ws / "preview.json") or {}
    if meta.get("stamp") != stamp:
        if ws.exists():
            shutil.rmtree(ws)
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
    raise HubError("action = create|plan|open|start|stop|demo|forget")
