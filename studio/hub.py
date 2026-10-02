# -*- coding: utf-8 -*-
"""시작 페이지(허브) 동작 - 새로 만들기 · 열기 · 데모 · 최근 작업 · 폴더 고르기. server.py 의 /api/home·/api/project·/api/fs 가 쓴다.

원칙: 엔진은 슬라이드 내용을 자기 폴더에 두지 않는다. 제작마다 작업 공간 폴더를 따로 두고(기본 = 문서 폴더/NexaSlide/<제목>),
그 폴더에 내용(content·decks·assets)과 서버를 실행할 정보(nexa-slide.json·nexa.py)를 넣는다. 서버도 작업 공간마다 하나씩 띄운다.
"""
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from paths import (ENGINE, default_projects_root, documents_dir, forget, inside_engine, load_settings, projects_root,
                   remember, save_settings)

STUDIO = ENGINE / "studio"
EXAMPLE = ENGINE / "example"
STARTERS = ENGINE / "starters"
TEMPLATES = STUDIO / "templates"
CONFIG_NAME = "nexa-slide.json"
DEMO_DIR = "nexa-slide-demo"


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


# ---------- 목록 ----------
def templates():
    out = []
    for d in sorted(TEMPLATES.iterdir()):
        t = _read_json(d / "template.json")
        if not t:
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
        out.append({"name": d.name, "label": t.get("label", d.name), "description": t.get("description", ""),
                    "extends": t.get("extends"), "swatches": sw,
                    "concept": f"/studio/templates/{d.name}/design/concept.html" if (d / "design" / "concept.html").is_file() else None})
    return out


def starters():
    """엔진 starters/<이름>/starter.json - 시작용 내용(있을 때만). init_workspace.py --starter 로 쓴다."""
    out = []
    if STARTERS.is_dir():
        for d in sorted(STARTERS.iterdir()):
            st = _read_json(d / "starter.json")
            if st:
                out.append({"name": d.name, "label": st.get("label", d.name), "description": st.get("description", ""),
                            "template": st.get("template")})
    return out


def _supports_starter():
    try:
        return "--starter" in (STUDIO / "init_workspace.py").read_text(encoding="utf-8")
    except OSError:
        return False


def workspace_info(path):
    """작업 공간 요약 - 제목·템플릿·덱 수·실행 중 서버(server.json 기준, 응답은 확인하지 않음)."""
    p = Path(path)
    cfg = _read_json(p / CONFIG_NAME)
    if cfg is None:
        return {"path": str(p), "exists": p.is_dir(), "workspace": False}
    decks_dir = p / cfg.get("decks", "decks")
    decks = sorted(f.stem for f in decks_dir.glob("*.json") if not f.name.endswith(".requests.json")) if decks_dir.is_dir() else []
    info = _read_json(p / cfg.get("out", "out") / ".studio" / "server.json") or {}
    return {"path": str(p), "exists": True, "workspace": True, "title": cfg.get("title", p.name), "template": cfg.get("template", "lecture"),
            "port": cfg.get("port"), "decks": decks, "url": info.get("url"), "git": _git_root(p) is not None,
            "brief": (p / "BRIEF.md").is_file()}


def _git_root(p):
    p = Path(p).resolve()
    for d in (p, *p.parents):
        if (d / ".git").exists():
            return d
    return None


def home(current=None, refused=None):
    s = load_settings()
    recent = []
    for r in s.get("recent", []):
        i = workspace_info(r["path"])
        i["opened"] = r.get("opened", "")
        i.setdefault("title", r.get("title") or Path(r["path"]).name)
        recent.append(i)
    return {"documents": str(documents_dir()), "projectsRoot": str(projects_root()), "projectsRootDefault": str(default_projects_root()),
            "projectsRootFromEnv": bool(os.environ.get("NEXA_SLIDE_PROJECTS")), "engine": str(ENGINE),
            "current": workspace_info(current) if current else None, "refused": str(refused) if refused else None,
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
                dirs.append({"name": d.name, "path": str(d), "git": (d / ".git").exists(), "workspace": (d / CONFIG_NAME).is_file()})
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
            "git": (p / ".git").exists(), "gitRoot": str(_git_root(p) or ""), "workspace": (p / CONFIG_NAME).is_file(),
            "insideEngine": inside_engine(p), "places": {"문서": str(documents_dir()), "제작 기준": str(projects_root()), "홈": str(Path.home())}}


# ---------- 서버 ----------
def start_server(ws):
    """작업 공간 서버를 띄우고(이미 떠 있으면 그대로) 주소를 돌려준다."""
    code, log = _run([STUDIO / "service.py", "start"], ws, timeout=30)
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


def _brief_md(b, deck):
    lines = [f"# {b['title']} - 작성 브리프", "",
             f"- 만든 날짜: {dt.date.today().isoformat()}",
             f"- 템플릿: {b.get('template') or 'lecture'}" + (f" · 시작용 내용: {b['starter']}" if b.get("starter") else ""),
             f"- 첫 덱: `{deck}`", ""]
    for key, head in (("purpose", "목적"), ("audience", "대상(청중)"), ("direction", "작성 방향"), ("materials", "참고 자료")):
        v = str(b.get(key) or "").strip()
        lines += [f"## {head}", "", v or "(비어 있음)", ""]
    lines += ["---", "", "> 이 파일은 시작 페이지에서 만들 때 받은 내용이다. Claude 세션은 초안을 쓰기 전에 먼저 읽는다.", ""]
    return "\n".join(lines)


def create(b):
    """새 작업 공간: {title, template, starter?, deck?, folder?, sub?, purpose, audience, direction, materials, askDraft}."""
    title = str(b.get("title") or "").strip()
    if not title:
        raise HubError("제목을 적는다")
    template = b.get("template") or "lecture"
    if not (TEMPLATES / template / "template.json").is_file():
        raise HubError(f"없는 템플릿: {template}")
    base = Path(str(b.get("folder") or "").strip()).expanduser() if b.get("folder") else projects_root()
    sub = str(b.get("sub") if b.get("sub") is not None else ("" if b.get("folder") else slug(title))).strip().strip("/\\")
    ws = (base / sub) if sub else base
    _check_target(ws)
    if not b.get("folder") and ws.exists() and any(ws.iterdir()):  # 기본 위치에서 이름이 겹치면 -2, -3 …
        k = 2
        while (base / f"{sub}-{k}").exists():
            k += 1
        ws = base / f"{sub}-{k}"
    if (ws / CONFIG_NAME).is_file():  # 지정한 폴더에 이미 있으면 만들지 않고 열기를 권한다
        raise HubError("이 폴더에는 이미 작업 공간이 있다 - 열기로 연다", existing=str(ws))
    deck = re.sub(r"[^A-Za-z0-9_-]", "", str(b.get("deck") or "")) or "intro"
    args = [STUDIO / "init_workspace.py", ws, "--title", title, "--template", template, "--deck", deck]
    starter = b.get("starter") or None
    if starter:
        if not _supports_starter() or not (STARTERS / starter / "starter.json").is_file():
            raise HubError(f"없는 시작용 내용: {starter}")
        args += ["--starter", starter]
    code, log = _run(args, None, timeout=60)
    if code != 0 or not (ws / CONFIG_NAME).is_file():
        raise HubError("작업 공간을 만들지 못했다", log=log)
    (ws / "BRIEF.md").write_text(_brief_md({**b, "title": title, "template": template, "starter": starter}, deck), encoding="utf-8", newline="\n")
    cm = ws / "CLAUDE.md"
    if cm.is_file() and "BRIEF.md" not in cm.read_text(encoding="utf-8"):
        with cm.open("a", encoding="utf-8", newline="\n") as f:
            f.write("\n## 작성 브리프\n\n- 시작 페이지에서 받은 목적·대상·작성 방향·참고 자료는 `BRIEF.md` 에 있다. 초안을 쓰기 전에 먼저 읽고, 자료에 없는 내용은 지어내지 않는다.\n")
    built = build_all(ws)
    if b.get("askDraft"):
        _ask_draft(ws, built[0] if built else deck)
    remember(ws, title)
    url, slog = start_server(ws)
    return {"ok": True, "path": str(ws), "url": url, "decks": built, "log": log + "\n" + slog}


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


def _ask_draft(ws, deck):
    """세션에 보낼 첫 요청 - 브리프로 초안 쓰기(대기 상태라 세션이 연결되면 전달된다)."""
    cfg = _read_json(ws / CONFIG_NAME) or {}
    p = ws / cfg.get("decks", "decks") / f"{deck}.requests.json"
    items = _read_json(p, []) or []
    d = _read_json(ws / cfg.get("decks", "decks") / f"{deck}.json") or {}
    first = (d.get("slides") or [{}])[0].get("id")
    items.append({"id": "r" + dt.datetime.now().strftime("%Y%m%d%H%M%S%f")[:17], "slide": first, "element": None,
                  "text": "BRIEF.md 의 목적·대상·작성 방향·참고 자료로 이 덱의 초안을 써 주세요. 템플릿 디자인은 그대로 두고, 자료에 없는 내용은 지어내지 말고 확인 질문으로 남겨 주세요.",
                  "status": "open", "reply": "", "created": dt.datetime.now().isoformat(timespec="seconds")})
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")


def open_ws(path):
    p = Path(str(path or "").strip()).expanduser()
    if not p.is_absolute():
        raise HubError("폴더는 절대 경로로 준다")
    if not p.is_dir():
        raise HubError(f"폴더가 없다: {p}")
    if inside_engine(p):
        raise HubError("엔진 폴더 안의 작업 공간은 열지 않는다 - 예제는 '데모'로 연다")
    if not (p / CONFIG_NAME).is_file():
        raise HubError("이 폴더에는 작업 공간(nexa-slide.json)이 없다 - 여기에 새로 만들 수 있다", needInit=True, path=str(p),
                       git=(p / ".git").exists())
    cfg = _read_json(p / CONFIG_NAME) or {}
    remember(p, cfg.get("title", p.name))
    url, log = start_server(p)
    return {"ok": True, "path": str(p), "url": url, "log": log}


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
                          "--template", ex.get("template", "lecture"), "--deck", "demo"], None, timeout=60)
        if code != 0:
            raise HubError("데모를 만들지 못했다", log=log)
        cfg = _read_json(ws / CONFIG_NAME) or {}
        keep = {k: cfg[k] for k in ("port", "engine") if k in cfg}
        cfg = {**cfg, **{k: v for k, v in ex.items() if k not in ("port", "engine")}, **keep}
        (ws / CONFIG_NAME).write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    remember(ws, (_read_json(ws / CONFIG_NAME) or {}).get("title", "데모"))
    url, log = start_server(ws)
    return {"ok": True, "path": str(ws), "url": url}


def project(b):
    act = b.get("action")
    if act == "create":
        return create(b)
    if act == "open":
        return open_ws(b.get("path"))
    if act == "demo":
        return demo()
    if act == "forget":
        forget(b.get("path", ""))
        return {"ok": True}
    raise HubError("action = create|open|demo|forget")
