# -*- coding: utf-8 -*-
"""스튜디오 공용 — 토큰·색 해석·인라인 강조 파서·코드 하이라이트·글자 폭 추정.

render.js 에 같은 규칙이 JS로 있다. 한쪽을 고치면 다른 쪽도 같이 고친다.
  - 인라인 강조: **굵게**, ==강조(CI 적색·굵게)==, [[토큰|색 글자]]
  - 치환: {page} = 슬라이드 순번(1부터)
  - 코드 하이라이트: 주석(-- … / /* … */ / # …), 문자열('…'), 키워드(대문자·소문자 무관)
"""
import json
import os
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):  # Windows 콘솔(cp949)에서도 한글·기호 출력
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

STUDIO = Path(__file__).resolve().parent  # 엔진 폴더 (이 파일이 있는 곳)
CONFIG_NAME = "nexa-slide.json"


def _workspace():
    """작업 공간(덱·내용·산출물이 있는 폴더)을 정한다.

    우선순위: 명령행 --workspace <경로> > 환경변수 NEXA_SLIDE_WORKSPACE > 현재 폴더부터 위로 올라가며
    nexa-slide.json 이 있는 첫 폴더. 못 찾으면 None — 현재 폴더(엔진 폴더일 수 있다)를 작업 공간으로 쓰지 않는다.
    --workspace 는 여기서 꺼내 지우므로 각 도구의 인자 해석과 겹치지 않는다.
    """
    argv = sys.argv
    for k, a in enumerate(argv[1:], 1):
        if a in ("--workspace", "-W") and k + 1 < len(argv):
            os.environ["NEXA_SLIDE_WORKSPACE"] = argv[k + 1]
            del argv[k:k + 2]
            break
        if a.startswith("--workspace="):
            os.environ["NEXA_SLIDE_WORKSPACE"] = a.split("=", 1)[1]
            del argv[k]
            break
    env = os.environ.get("NEXA_SLIDE_WORKSPACE")
    if env:
        return Path(env).resolve()
    cwd = Path.cwd().resolve()
    for d in (cwd, *cwd.parents):
        if (d / CONFIG_NAME).is_file():
            return d
    return None


# 작업 공간 없이 도는 도구 — 서버는 이때 허브(시작 페이지)로 뜬다. 나머지 도구는 작업 공간이 있어야 한다.
HUB_TOOLS = {"server.py", "service.py", "status.py"}
_TOOL = Path(sys.argv[0]).name if sys.argv and sys.argv[0] else ""
WORKSPACE = _workspace()
REFUSED = None  # 엔진 폴더 안이라 서버가 열지 않은 작업 공간
if WORKSPACE is not None and _TOOL in HUB_TOOLS:
    from paths import inside_engine
    if inside_engine(WORKSPACE):  # 엔진은 슬라이드 내용을 자기 폴더에 두지 않는다(예제는 데모로 복사해 연다)
        REFUSED, WORKSPACE = WORKSPACE, None
if WORKSPACE is None and _TOOL not in HUB_TOOLS and __name__ != "__main__":
    sys.exit("nexa-slide 작업 공간을 찾지 못했다 — --workspace <폴더> 를 주거나 작업 공간(nexa-slide.json 이 있는 폴더) 안에서 실행한다. "
             "새로 만들려면 서버(python3 studio/server.py)를 띄워 시작 페이지에서 만든다")
HUB = WORKSPACE is None  # 허브 모드: 시작 페이지만(덱 API 는 빈 결과)
if HUB:
    os.environ.pop("NEXA_SLIDE_WORKSPACE", None)
else:
    os.environ["NEXA_SLIDE_WORKSPACE"] = str(WORKSPACE)  # 하위 프로세스(export·set_fonts 등)도 같은 작업 공간
CONFIG = {}
if not HUB and (WORKSPACE / CONFIG_NAME).is_file():
    CONFIG = json.loads((WORKSPACE / CONFIG_NAME).read_text(encoding="utf-8"))


def _ws_path(key, default):
    return (WORKSPACE / CONFIG.get(key, default)).resolve()


if HUB:  # 허브 상태(서버 정보·로그)는 사용자 설정 폴더에 — 엔진·현재 폴더에 아무것도 쓰지 않는다
    from paths import hub_port, user_dir
    OUT = user_dir() / "hub"
    REPO = ASSET_ROOT = CONTENT = DECKS = OUT / "_no-workspace"  # 만들지 않는 자리(덱·그림 없음)
    DEFAULT_PORT = hub_port()
else:
    # 덱 JSON 의 그림 경로(src·img)는 assetRoot 기준 상대 경로다. 서버는 이 폴더를 / 로 내준다.
    REPO = ASSET_ROOT = _ws_path("assetRoot", ".")
    CONTENT = _ws_path("content", "content")
    DECKS = _ws_path("decks", "decks")
    OUT = _ws_path("out", "out")
    DEFAULT_PORT = int(CONFIG.get("port", 5600))  # 작업 공간마다 다른 포트를 주면 여러 서버를 함께 띄울 수 있다
STATE = OUT / ".studio"  # 세션 연결 상태·즉시 전송 신호·실행 중 서버 정보 (git 제외 영역)
SERVER_INFO = STATE / "server.json"  # 실행 중인 서버 {port, url, pid, workspace, started}


def _serves_here(port):
    """그 포트의 nexa-slide 서버가 이 작업 공간을 내주고 있는지 (/api/config 의 path 로 확인)."""
    import socket
    import urllib.request
    try:  # 닫힌 포트는 Windows 에서 연결 거부까지 1.5초 이상 걸린다 → 짧게 먼저 두드린다
        socket.create_connection(("127.0.0.1", int(port)), timeout=0.3).close()
    except OSError:
        return False
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{int(port)}/api/config", timeout=1.5) as r:
            cfg = json.loads(r.read().decode("utf-8"))
        if HUB:
            return cfg.get("mode") == "hub"
        return bool(cfg.get("path")) and Path(cfg["path"]).resolve() == WORKSPACE
    except Exception:  # noqa: BLE001 — 응답 없음·다른 서비스
        return False


def running_server():
    """이 작업 공간에서 실제로 살아 있는 서버 {port, url, pid, started, …} 또는 None.
    server.json 의 포트를 먼저, 그다음 설정 포트를 물어본다(비정상 종료로 server.json 이 낡았을 수 있다)."""
    try:
        info = json.loads(SERVER_INFO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        info = {}
    if info.get("port") and _serves_here(info["port"]):
        return info
    if _serves_here(DEFAULT_PORT):
        return {"port": DEFAULT_PORT, "url": f"http://127.0.0.1:{DEFAULT_PORT}/", "pid": "?", "started": "?"}
    return None


def server_port(default=None):
    """이 작업 공간에서 실행 중인 서버 포트, 없으면 설정 포트."""
    run = running_server()
    return int(run["port"]) if run else (default or DEFAULT_PORT)
# ---------- 템플릿 — 디자인(색·글꼴·크기·검사 기준·디자인 기준 문서)은 엔진의 templates/<이름>/ 에 있고,
#            작업 공간은 nexa-slide.json 의 "template"(·"fontPreset")으로 고르기만 한다 ----------
TEMPLATES = STUDIO / "templates"
DEFAULT_TEMPLATE = "lecture"


def _merge(base, over):
    out = dict(base)
    for k, v in over.items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def load_template(name, _seen=()):
    """templates/<이름>/template.json — "extends" 를 따라 합친다. 경로 항목(tokens·design)은 정의한 템플릿 폴더 기준."""
    d = TEMPLATES / name
    f = d / "template.json"
    if not f.is_file():
        have = ", ".join(sorted(p.name for p in TEMPLATES.iterdir() if (p / "template.json").is_file()))
        raise SystemExit(f"없는 템플릿: {name} — 있는 것: {have}")
    raw = json.loads(f.read_text(encoding="utf-8"))
    for k in ("tokens",):
        if k in raw:
            raw[k] = str((d / raw[k]).resolve())
    if isinstance(raw.get("design"), dict):
        raw["design"] = {k: str((d / v).resolve()) for k, v in raw["design"].items()}
    base = load_template(raw["extends"], _seen + (name,)) if raw.get("extends") and raw["extends"] not in _seen else {}
    out = _merge(base, {k: v for k, v in raw.items() if k != "extends"})
    out["name"] = name
    return out


def list_templates():
    return [{"name": p.name, "label": json.loads((p / "template.json").read_text(encoding="utf-8")).get("label", p.name)}
            for p in sorted(TEMPLATES.iterdir()) if (p / "template.json").is_file()]


# NEXA_SLIDE_TEMPLATE 은 미리보기·비교용 임시 덮어쓰기(설정 파일은 그대로)
TEMPLATE = load_template(os.environ.get("NEXA_SLIDE_TEMPLATE") or CONFIG.get("template", DEFAULT_TEMPLATE))
TOKENS = Path(TEMPLATE["tokens"])
SIZES = TEMPLATE.get("sizes", {})
MIN_PX = {k: v for k, v in SIZES.get("minPx", {}).items() if not k.startswith("_")}


def fit_size(px, role=None):
    """템플릿 최소 크기 적용 — 역할(role) 값이 있으면 그것, 없으면 default. 이미 크면 그대로(여러 번 적용해도 같음)."""
    if px is None:
        return px
    lim = MIN_PX.get(role or "default", MIN_PX.get("default", 0)) or 0
    return max(px, lim) if lim else px


def resolve_tokens(config=None):
    """템플릿 토큰 + 작업 공간이 고른 글꼴 프리셋(fontPreset). config 를 주면 그 설정으로(서버가 매번 새로 읽을 때)."""
    t = json.loads(TOKENS.read_text(encoding="utf-8"))
    # 템플릿의 tokenOverrides(색·반경 등)를 토큰 파일 위에 덮는다 — 목적별 템플릿은 lecture 토큰을 바탕으로 값만 바꾼다
    ov = TEMPLATE.get("tokenOverrides") or {}
    t = _merge(t, {k: v for k, v in ov.items() if k != "fonts"})
    cfg = config if config is not None else CONFIG
    if isinstance(cfg.get("fontPresets"), dict):  # 작업 공간 전용 글꼴 세트(회사 서체 등) — 파일은 작업 공간 fonts/ 에 둔다
        t["fontPresets"] = {**t.get("fontPresets", {}), **cfg["fontPresets"]}
    preset = cfg.get("fontPreset")
    if preset and preset in t.get("fontPresets", {}):
        f = json.loads(json.dumps(t["fontPresets"][preset]))
        for k in ("body", "mono"):  # 세트에 없는 역할은 기본값(heading 은 아래에서 세트의 body 를 따른다)
            f.setdefault(k, t["fonts"][k])
        t["fonts"] = f
        t["fontPreset"] = preset
    if ov.get("fonts"):  # 글꼴 덮어쓰기는 프리셋 뒤에(예: heading 만 명조)
        t["fonts"] = _merge(t["fonts"], ov["fonts"])
    t["fonts"].setdefault("heading", t["fonts"]["body"])
    return t


def read_config():
    """nexa-slide.json 을 지금 다시 읽는다(서버처럼 오래 도는 프로세스용)."""
    if HUB:
        return {}
    f = WORKSPACE / CONFIG_NAME
    return json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {}
BRAND = {"name": "", "logo": "", "wordmark": "", "favicon": "", **CONFIG.get("brand", {})}

_tokens = None


def tokens():
    global _tokens
    if _tokens is None:
        _tokens = resolve_tokens()
    return _tokens


def color(value, default="#000000"):
    """토큰명 또는 #hex → '#RRGGBB'. 토큰이 다른 토큰을 가리키면 따라간다. 모르면 default."""
    if not value:
        return None
    cs = tokens()["colors"]
    v = value
    for _ in range(5):
        if isinstance(v, str) and v.startswith("#"):
            return v.upper() if len(v) == 7 else default
        if v in cs:
            v = cs[v]
        else:
            return default
    return default


def radius(value, w, h):
    """radius(px 숫자 또는 토큰 r-s/r-m/r-l/r-full) → px (짧은 변의 절반을 넘지 않음)."""
    if value in (None, 0, "0", ""):
        return 0
    r = tokens()["radius"].get(value, value) if isinstance(value, str) else value
    try:
        r = float(r)
    except (TypeError, ValueError):
        r = 0
    return max(0.0, min(r, min(w, h) / 2))


# ---------- 인라인 강조 ----------
_MARK = re.compile(r"\*\*(.+?)\*\*|==(.+?)==|\[\[([#\w-]+)\|(.+?)\]\]")


def runs(text, page=None):
    """'a **b** ==c== [[s1|d]]' → [(글자, {'bold':bool,'color':토큰|None})] (줄바꿈은 호출자가 먼저 나눈다)."""
    if page is not None:
        text = text.replace("{page}", str(page))
    out, pos = [], 0
    for m in _MARK.finditer(text):
        if m.start() > pos:
            out.append((text[pos:m.start()], {}))
        if m.group(1) is not None:
            out.append((m.group(1), {"bold": True}))
        elif m.group(2) is not None:
            out.append((m.group(2), {"bold": True, "color": "primary"}))
        else:
            out.append((m.group(4), {"color": m.group(3)}))
        pos = m.end()
    if pos < len(text):
        out.append((text[pos:], {}))
    return out or [("", {})]


def plain(text):
    return "".join(t for t, _ in runs(text))


# ---------- 코드 하이라이트 (ppt/design/concept.html hlSQL() 이식 — render.js hlSQL 과 같은 결과) ----------
# 역할: k 예약어·타입·함수(굵게) · tb 테이블·CTE · al 테이블 별칭(기울임) · ca 결과 컬럼 별칭(기울임)
#       st 문자열 · nu 숫자 · co 주석 · bi 바인드 · None 일반(컬럼 등)
SQL_KW = set(("select from where and or not in exists join left right full outer inner cross on as group by order having union all with recursive "
              "case when then else end between like is null distinct insert into values update set delete merge using matched connect prior start table desc asc over "
              "partition fetch first rows only create index primary key foreign references constraint default level nocycle siblings search depth breadth cycle to").split(" "))
SQL_TYPE = set("varchar varchar2 number date text char integer int timestamp clob blob boolean".split(" "))
_SQL_RX = re.compile(r"""(--[^\n]*|/\*[\s\S]*?\*/)|('(?:[^']|'')*')|(:[A-Za-z_]\w*)|(\b\d+(?:\.\d+)?\b)|("[^"]+"|[A-Za-z_][\w$#]*)|(\s+|[^\s])""", re.A)
_WS = re.compile(r"^\s+$")


def hl_sql(src):
    """SQL → [(글자, 역할)] (줄바꿈 포함). 2패스: 1차로 테이블·별칭 수집, 2차로 칠하기."""
    toks = []
    for m in _SQL_RX.finditer(src):
        kind = "co" if m.group(1) else "st" if m.group(2) else "bi" if m.group(3) else "nu" if m.group(4) else "id" if m.group(5) else "p"
        toks.append((kind, m.group(0)))
    tables, aliases = set(), set()

    def nxt(i):
        for j in range(i + 1, len(toks)):
            if not _WS.match(toks[j][1]):
                return toks[j]
        return None

    def run_pass():
        prev, expect, out = "", False, []
        for i, (t, v) in enumerate(toks):
            if t != "id":
                if not (t == "p" and (_WS.match(v) or v == ".")):
                    expect = False
                if t == "p" and v == ",":
                    prev = "from" if prev == "_t" else prev
                out.append((v, None if t == "p" else t))
                continue
            low, nx = v.lower(), nxt(i)
            if low in SQL_TYPE:
                prev = low
                out.append((v, "k"))
            elif low in SQL_KW:
                if low != "recursive":
                    prev = low
                expect = False
                out.append((v, "k"))
            elif nx and nx[1] == "(" and prev not in ("with", "_t"):
                prev = ""
                out.append((v, "k"))
            elif nx and nx[1] == ".":
                out.append((v, "al" if low in aliases else "tb"))
            elif prev in ("from", "join", "into", "update", "with", "table", "using", "merge"):
                tables.add(low)
                prev, expect = "_t", True
                out.append((v, "tb"))
            elif expect and prev == "_t":
                aliases.add(low)
                expect, prev = False, ""
                out.append((v, "al"))
            elif prev == "as":
                prev = ""
                out.append((v, "tb" if low in tables else "ca"))
            elif low in tables:
                out.append((v, "tb"))
            elif low in aliases:
                out.append((v, "al"))
            else:
                prev = ""
                out.append((v, None))
        return out

    run_pass()          # 1차: 테이블·별칭 수집
    return run_pass()   # 2차: 색 입히기


PY_KW = set("def return import from as for in if elif else while with try except finally class lambda and or not is None True False yield pass break continue raise async await".split())
_PY_RX = re.compile(r"""(#[^\n]*)|('[^'\n]*'|"[^"\n]*")|(\b\d+(?:\.\d+)?\b)|([A-Za-z_]\w*)|(\s+|[^\s])""", re.A)


def hl_python(src):
    out = []
    for m in _PY_RX.finditer(src):
        v = m.group(0)
        out.append((v, "co" if m.group(1) else "st" if m.group(2) else "nu" if m.group(3)
                    else ("k" if v in PY_KW else None) if m.group(4) else None))
    return out


def code_lines(el):
    """code 요소 → 표시 줄 [{n: 줄 번호 글자, focus, gap(생략 줄), runs:[(글자, 역할)]}]
    start(시작 번호) · focus(강조 줄 번호) · show([[from,to],…] 구간만, 사이는 ⋮ 한 줄)"""
    src = str(el.get("text", ""))
    toks = hl_python(src) if el.get("lang") == "python" else hl_sql(src)
    lines = [[]]
    for v, role in toks:
        for i, part in enumerate(v.split("\n")):
            if i:
                lines.append([])
            if part:
                lines[-1].append((part, role))
    start = int(el.get("start", 1) or 1)
    focus = set(int(x) for x in (el.get("focus") or []))
    show = el.get("show") or None
    out, gap = [], False
    for i, ln in enumerate(lines):
        n = start + i
        if show and not any(a <= n <= b for a, b in show):
            if not gap:
                out.append({"n": "⋮", "focus": False, "gap": True, "runs": []})
                gap = True
            continue
        gap = False
        out.append({"n": str(n), "focus": n in focus, "gap": False, "runs": ln})
    return out


CODE_GUTTER_W = 48   # 줄 번호 열 폭(px) — 오른쪽 여백 12, 코드 왼쪽 여백 14
CODE_PAD_Y = 12


def code_style(role):
    """역할 → (색 토큰, 굵게, 기울임)"""
    return tuple(tokens()["codeStyle"].get(role or "ink", tokens()["codeStyle"]["ink"]))


# ---------- 글자 폭(레이아웃 빌더용) ----------
_fonts = {}


def fonts_dir():
    """작업 공간의 글꼴 파일 폴더(nexa-slide.json "fontsDir", 기본 fonts/). 글꼴 파일은 엔진에 두지 않는다."""
    return (WORKSPACE / CONFIG.get("fontsDir", "fonts")) if WORKSPACE else None


def _font_file(name):
    import os
    wd = fonts_dir()
    for d in ((wd,) if wd else ()) + (Path("C:/Windows/Fonts"), Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Windows/Fonts",
                                     Path.home() / "Library/Fonts", Path("/Library/Fonts"), Path.home() / ".local/share/fonts"):
        if (d / name).exists():
            return d / name
    return None


def text_width(s, size_px, bold=False, mono=False):
    """문자열 폭(px) 추정. Pillow + 설치된 글꼴이 있으면 현재 글꼴 프리셋(tokens.json fonts.*.measure)으로 잰다.
    고정폭: 라틴은 글꼴로 재고, 한글·한자 등 넓은 글자는 라틴 2칸으로 센다(코드의 한글은 D2Coding 등 2칸 글꼴)."""
    s = plain(s)
    key = (bold, mono, round(size_px * 4))
    if key not in _fonts:
        try:
            from PIL import ImageFont
            ms = tokens()["fonts"]["mono" if mono else "body"].get("measure") or {}
            name = ms.get("bold" if bold else "regular") or (
                ("consolab.ttf" if bold else "consola.ttf") if mono else ("malgunbd.ttf" if bold else "malgun.ttf"))
            path = _font_file(name) or _font_file(("consolab.ttf" if bold else "consola.ttf") if mono else ("malgunbd.ttf" if bold else "malgun.ttf"))
            _fonts[key] = ImageFont.truetype(str(path), size=max(1, round(size_px * 4)))
        except Exception:
            _fonts[key] = None
    f = _fonts[key]
    if f is not None:
        if mono:
            cw = f.getlength("M") / 4
            return max(sum(cw * (2 if ord(ch) > 0x2E80 else 1) for ch in line) for line in s.split("\n"))
        return max(f.getlength(line) for line in s.split("\n")) / 4
    w = 0
    for ch in max(s.split("\n"), key=len):
        w += size_px * (0.55 if mono else (1.0 if ord(ch) > 0x2E80 else (0.3 if ch == " " else 0.56)))
    return w


def load_deck(deck_id):
    return json.loads((DECKS / f"{deck_id}.json").read_text(encoding="utf-8"))


def safe_id(deck_id):
    return bool(re.fullmatch(r"[A-Za-z0-9_-]{1,64}", deck_id or ""))


# ---------- 실행계획(plan) 강조: [[글자]] = warn, [[ok:글자]] = ok ----------
# 표시는 글자 폭을 바꾸지 않는다(배경색·글자색·굵게만). 표시 기호 자체는 폭을 차지하지 않으므로
# 원문 정렬을 유지하려면 [[ ]] 를 뺀 글자가 원문과 같게 쓴다.
_PLAN = re.compile(r"\[\[(?:(warn|ok):)?(.+?)\]\]")
HL_ROLE = {"warn": ("primary-container", "primary"), "ok": ("lab-container", "lab")}


def plan_runs(line):
    out, pos = [], 0
    for m in _PLAN.finditer(line):
        if m.start() > pos:
            out.append((line[pos:m.start()], None))
        out.append((m.group(2), m.group(1) or "warn"))
        pos = m.end()
    if pos < len(line):
        out.append((line[pos:], None))
    return out


# ---------- 표(table · plan-table) → 셀 격자 (render.js 의 tableGrid 와 같은 규칙) ----------
CELL_PADX = 14
_NUM = re.compile(r"^[\s*+\-]?[\d,.\s%:]*\d[\d,.\s%KMG]*$")


def table_grid(el):
    """반환: {x, y, tw, colW(px), rowH(px), cells[r][c]{text,fill,color,bold,align,font}, rule, callouts[]}"""
    is_plan = el.get("type") == "plan-table"
    if is_plan:
        cols = el.get("columns", [])
        body = el.get("rows", [])
        n = len(body) + 1
        has_note = any(r.get("note") for r in body)
        cw = el.get("calloutW", 0) if has_note else 0
        tw = el["w"] - (cw + 24 if cw else 0)
    else:
        rows = el.get("rows", [])
        cols = rows[0] if rows else []
        n = len(rows)
        tw, cw = el["w"], 0
    nc = max(1, len(cols))
    ratios = el.get("colW") or [1] * nc
    ratios = (list(ratios) + [1] * nc)[:nc]
    tot = sum(ratios) or 1
    colW = [tw * r / tot for r in ratios]
    rowH = [el["h"] / max(1, n)] * n
    header = el.get("header", True) if not is_plan else True
    head_fill, head_color = el.get("headFill", "surface-container-high"), el.get("headColor", "on-surface")
    fonts = el.get("colFont") or []
    aligns = el.get("align") or []
    cells = []
    if is_plan:
        op = el.get("opCol", 1)
        auto = []
        for j in range(nc):
            vals = [str((r.get("cells") or [])[j]) if j < len(r.get("cells") or []) else "" for r in body]
            auto.append("right" if j != op and any(v.strip() for v in vals) and all((not v.strip()) or _NUM.match(v) for v in vals) else "left")
        cells.append([{"text": str(c), "fill": head_fill, "color": head_color, "bold": True, "font": "body",
                       "align": aligns[j] if j < len(aligns) and aligns[j] else auto[j]} for j, c in enumerate(cols)])
        for r in body:
            rc = list(r.get("cells") or []) + [""] * nc
            hl = {int(k): v for k, v in (r.get("hl") or {}).items()}
            row = []
            for j in range(nc):
                t = str(rc[j])
                if j == op:
                    t = "  " * int(r.get("depth", 0)) + t
                role = hl.get(j)
                fill, color = HL_ROLE.get(role, (None, el.get("color", "on-surface")))
                row.append({"text": t, "fill": fill, "color": color, "bold": bool(role), "font": "mono",
                            "align": aligns[j] if j < len(aligns) and aligns[j] else auto[j]})
            cells.append(row)
    else:
        for i, r in enumerate(el.get("rows", [])):
            rc = list(r) + [""] * nc
            hd = header and i == 0
            cells.append([{"text": str(rc[j]), "fill": head_fill if hd else None,
                           "color": head_color if hd else el.get("color", "on-surface"), "bold": hd,
                           "align": (aligns[j] if j < len(aligns) and aligns[j] else "left"),
                           "font": "body" if hd else (fonts[j] if j < len(fonts) and fonts[j] else "body")}
                          for j in range(nc)])
    callouts = []
    if is_plan and cw:
        size = el.get("size", 15)
        for i, r in enumerate(el.get("rows", [])):
            if not r.get("note"):
                continue
            roles = set((r.get("hl") or {}).values())
            role = "warn" if "warn" in roles else ("ok" if "ok" in roles else None)
            fill, color = HL_ROLE.get(role, ("surface-container", "on-surface-variant"))
            if role:
                color = f"on-{fill}" if f"on-{fill}" in tokens()["colors"] else color
            lines = str(r["note"]).count("\n") + 1
            bh = max(rowH[0] - 8, lines * size * 1.5 + 12)
            cy = el["y"] + rowH[0] * (i + 1) + rowH[0] / 2
            callouts.append({"row": i + 1, "text": r["note"], "fill": fill, "color": color,
                             "line": HL_ROLE[role][1] if role else "outline-variant",
                             "x": el["x"] + tw + 24, "y": cy - bh / 2, "w": cw, "h": bh, "cy": cy, "tx": el["x"] + tw})
    return {"x": el["x"], "y": el["y"], "tw": tw, "colW": colW, "rowH": rowH, "cells": cells,
            "rule": el.get("rule", "surface-container-high"), "size": el.get("size", 16), "callouts": callouts}
