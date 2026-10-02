# -*- coding: utf-8 -*-
"""시작 페이지(허브) 동작 - 새로 만들기 · 열기 · 데모 · 최근 작업 · 폴더 고르기. server.py 의 /api/home·/api/project·/api/fs 가 쓴다.

원칙: 엔진은 슬라이드 내용을 자기 폴더에 두지 않는다. 제작마다 작업 공간 폴더를 따로 두고(기본 = 문서 폴더/NexaSlide/<제목>),
그 폴더에 내용(content·decks·assets)과 서버를 실행할 정보(nexa-slide.json·nexa.py)를 넣는다. 서버도 작업 공간마다 하나씩 띄운다.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from paths import (ENGINE, default_projects_root, documents_dir, forget, inside_engine, load_settings, projects_root,
                   remember, save_settings, user_dir)

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
            if st and not st.get("hidden"):  # 숨긴 시작용 내용(검토 대상으로 옮김)은 목록에서 제외
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
    """[프로그램, 인자…] → 붙여 넣을 수 있는 한 줄. 경로·글은 따옴표로 감싼다(프로그램 이름·옵션 이름은 그대로)."""
    return " ".join(x if i == 0 or re.fullmatch(r"--[a-z-]+", x) else _quote(x, shell) for i, x in enumerate(map(str, args)))


def plan(b):
    """새로 만들기 계획 - 만들 폴더·포트와 그대로 실행할 init_workspace 명령. 시작 페이지는 이것을 보여 주고, create 는 이것을 실행한다.
    b = {title, template, starter?, deck?, folder?, sub?, port?, purpose, audience, direction, materials, askDraft}."""
    from init_workspace import free_port, hub_port, port_busy, taken_ports
    warn = []
    title = str(b.get("title") or "").strip()
    template = b.get("template") or "lecture"
    if not (TEMPLATES / template / "template.json").is_file():
        raise HubError(f"없는 템플릿: {template}")
    starter = b.get("starter") or None
    if starter and (not _supports_starter() or not (STARTERS / starter / "starter.json").is_file()):
        raise HubError(f"없는 시작용 내용: {starter}")
    name = title or "제목"
    ws = None
    custom = b.get("loc") == "custom" or bool(str(b.get("folder") or "").strip())
    folder = str(b.get("folder") or "").strip()
    if folder or not custom:  # 폴더 지정인데 아직 비어 있으면 위치 미정
        base = Path(folder).expanduser() if folder else projects_root()
        sub = str(b.get("sub") if b.get("sub") is not None else ("" if folder else slug(name))).strip().strip("/\\")
        ws = (base / sub) if sub else base
        _check_target(ws)
        if not folder and ws.exists() and any(ws.iterdir()):  # 기본 위치에서 이름이 겹치면 -2, -3 …
            k = 2
            while (base / f"{sub}-{k}").exists():
                k += 1
            warn.append(f"{ws.name} 폴더가 이미 있어 {sub}-{k} 에 만듭니다")
            ws = base / f"{sub}-{k}"
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
    args = [STUDIO / "init_workspace.py", ws or "<폴더>", "--title", name, "--template", template]
    if deck != "intro":
        args += ["--deck", deck]
    if starter:
        args += ["--starter", starter]
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
    start = [(ws or Path("<폴더>")) / "nexa.py", "start"]
    py = _py()
    cmds = {sh: {"init": _cmdline([py, *args], sh), "start": _cmdline([py, *start], sh)} for sh in ("powershell", "bash")}
    return {"ok": True, "path": str(ws) if ws else "", "title": title, "port": port, "url": f"http://127.0.0.1:{port}/",
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
    url, slog = start_server(ws)
    cfg = _read_json(ws / CONFIG_NAME) or {}
    decks = sorted(f.stem for f in (ws / cfg.get("decks", "decks")).glob("*.json") if not f.name.endswith(".requests.json"))
    return {"ok": True, "path": str(ws), "url": url, "decks": decks, "log": log + "\n" + slog}


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


# ---------- 미리보기 ----------
def _stamp(template, starter):
    """미리보기를 다시 만들지 정하는 값 - 엔진 코드·템플릿·시작용 내용 중 가장 늦게 바뀐 시각."""
    files = [*STUDIO.glob("*.py"), *TEMPLATES.rglob("*")]
    if starter:
        files += [*(STARTERS / starter).rglob("*")]
    return max((f.stat().st_mtime_ns for f in files if f.is_file()), default=0)


def preview_key(template, starter):
    return f"{template}--{starter or 'layouts'}"


def preview(template=None, starter=None):
    """템플릿 × 시작용 내용을 임시 작업 공간(PREVIEW_ROOT/<템플릿>--<내용>)에 실제로 만들어 빌드한 덱을 돌려준다.
    시작용 내용이 없으면 레이아웃 견본(전 레이아웃 한 장씩). 템플릿이 없으면 시작용 내용이 정한 템플릿.
    엔진·템플릿·내용이 바뀌지 않았으면 전에 만든 것을 그대로 쓴다. 화면은 home.html 이 render.js 로 그린다."""
    if starter and not (STARTERS / str(starter) / "starter.json").is_file():
        raise HubError(f"없는 시작용 내용: {starter}")
    if not template:
        template = ((_read_json(STARTERS / starter / "starter.json") or {}).get("template") if starter else None) or "lecture"
    if not re.fullmatch(r"[A-Za-z0-9_-]+", str(template)) or not (TEMPLATES / template / "template.json").is_file():
        raise HubError(f"없는 템플릿: {template}")
    key = preview_key(template, starter)
    ws = PREVIEW_ROOT / key
    stamp = _stamp(template, starter)
    meta = _read_json(ws / "preview.json") or {}
    if meta.get("stamp") != stamp:
        if ws.exists():
            shutil.rmtree(ws)
        label = (_read_json(TEMPLATES / template / "template.json") or {}).get("label", template)
        args = [STUDIO / "init_workspace.py", ws, "--title", f"{label} 미리보기", "--template", template, "--deck", "layouts", "--no-remember"]
        if starter:
            args += ["--starter", starter]
        code, log = _run(args, None, timeout=60)
        if code != 0:
            raise HubError("미리보기를 만들지 못했다", log=log)
        if not starter:  # 레이아웃 견본 - 레이아웃마다 필드 예시로 한 장씩
            code, out = _run([STUDIO / "layout_samples.py", "--json"], ws, timeout=60)
            if code != 0:
                raise HubError("레이아웃 견본을 읽지 못했다", log=out)
            samples = json.loads(out[out.index("{"):])
            deck = {"id": "layouts", "title": f"레이아웃 견본 {len(samples)}종", "part": "day1", "version": "0.1",
                    "slides": [{"title": v["label"], **v["sample"]} for v in samples.values()]}  # 제목 없는 예시는 레이아웃 이름으로
            (ws / "content" / "layouts.json").write_text(json.dumps(deck, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
        decks = build_all(ws)
        code, tok = _run(["-c", "import json,sys; sys.path.insert(0, sys.argv[1]); from common import resolve_tokens; "
                                "print(json.dumps(resolve_tokens(), ensure_ascii=False))", STUDIO], ws, timeout=60)
        if code != 0 or not decks:
            raise HubError("미리보기를 빌드하지 못했다", log=tok)
        meta = {"stamp": stamp, "template": template, "starter": starter, "decks": decks, "tokens": json.loads(tok[tok.index("{"):])}
        (ws / "preview.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8", newline="\n")
    cfg = _read_json(ws / CONFIG_NAME) or {}
    decks = [_read_json(ws / cfg.get("decks", "decks") / f"{d}.json") for d in meta["decks"]]
    base = "/preview/" + "/".join(Path(key, cfg.get("assetRoot", ".")).as_posix().split("/")).rstrip("/.") + "/"
    return {"ok": True, "template": template, "starter": starter, "tokens": meta["tokens"], "base": base,
            "decks": [d for d in decks if d]}


def project(b):
    act = b.get("action")
    if act == "create":
        return create(b)
    if act == "plan":
        return plan(b)
    if act == "open":
        return open_ws(b.get("path"))
    if act == "demo":
        return demo()
    if act == "forget":
        forget(b.get("path", ""))
        return {"ok": True}
    raise HubError("action = create|plan|open|demo|forget")
