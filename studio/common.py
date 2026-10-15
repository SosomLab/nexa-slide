# -*- coding: utf-8 -*-
"""스튜디오 공용 — 토큰·색 해석·인라인 강조 파서·코드 하이라이트·글자 폭 추정.

render.js 에 같은 규칙이 JS로 있다. 한쪽을 고치면 다른 쪽도 같이 고친다.
  - 인라인 강조: **굵게**, ==강조(CI 적색·굵게)==, [[토큰|색 글자]]
  - 치환: {page} = 슬라이드 순번(1부터)
  - 코드 하이라이트: 주석(-- … / /* … */ / # …), 문자열('…'), 키워드(대문자·소문자 무관)
"""
import json
import os
import math
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
    nexa-slide.json 이 있는 첫 폴더(저장소형이면 루트 표식 .nexa-slide.json 이 가리키는 폴더, 없으면 slides/). 못 찾으면 None — 현재 폴더(엔진 폴더일 수 있다)를 작업 공간으로 쓰지 않는다.
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
    from paths import repo_workspace
    cwd = Path.cwd().resolve()
    for d in (cwd, *cwd.parents):
        if (d / CONFIG_NAME).is_file():
            return d
        ws = repo_workspace(d)  # 저장소형 — 저장소 루트(또는 그 아래 폴더)에서 실행: 루트 표식 .nexa-slide.json 또는 slides/
        if ws:
            return ws
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
LOCAL_NAME = "nexa-slide.local.json"  # PC 별 설정(엔진 위치·포트 등, git 제외) - nexa-slide.json 위에 덮어쓴다


def _merge(base, over):
    out = dict(base)
    for k, v in over.items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def read_config(shared=False):
    """작업 공간 설정을 지금 다시 읽는다 = nexa-slide.json + nexa-slide.local.json(PC 별, 덮어씀).
    shared=True 면 공유 파일만 - 설정을 고쳐 쓸 때(PC 별 값이 공유 파일에 섞이지 않게)."""
    if HUB:
        return {}
    f = WORKSPACE / CONFIG_NAME
    cfg = json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {}
    loc = WORKSPACE / LOCAL_NAME
    if not shared and loc.is_file():
        try:
            over = json.loads(loc.read_text(encoding="utf-8"))
        except ValueError as e:
            sys.exit(f"{loc} 를 읽지 못했다(JSON 오류): {e}")
        if isinstance(over, dict):
            cfg = _merge(cfg, over)
    return cfg


CONFIG = read_config()


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
    try:  # 허브는 로그인 없이 닿는 /api/auth/state 로(모든 API 가 인증 뒤에 있다), 작업 공간 서버는 /api/config(로컬 직접 접속은 인증 없음)
        with urllib.request.urlopen(f"http://127.0.0.1:{int(port)}/api/{'auth/state' if HUB else 'config'}", timeout=1.5) as r:
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
    """템플릿 목록 — 숨긴 템플릿(hidden: 검토 대상으로 옮김)은 빼되, 이 작업 공간이 쓰는 것이면 남긴다."""
    out = []
    for p in sorted(TEMPLATES.iterdir()):
        if not (p / "template.json").is_file():
            continue
        t = json.loads((p / "template.json").read_text(encoding="utf-8"))
        if t.get("hidden") and p.name != TEMPLATE["name"]:
            continue
        out.append({"name": p.name, "label": t.get("label", p.name)})
    return out


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
    t["fontOverrides"] = ov.get("fonts") or {}  # 슬라이드·덱 글꼴 세트도 같은 순서로 계산하게(render.js presetFonts)
    return t


def preset_fonts(name, t=None):
    """글꼴 세트 이름 → 역할별 글꼴(resolve_tokens 와 같은 규칙: 빠진 body·mono 는 지금 값, 템플릿 글꼴 덮어쓰기는 뒤에, heading 은 body).
    없는 이름이면 None. 슬라이드·덱의 fontPreset 에 쓴다."""
    t = t or tokens()
    p = (t.get("fontPresets") or {}).get(name) if name else None
    if not p:
        return None
    f = json.loads(json.dumps(p))
    for k in ("body", "mono"):
        f.setdefault(k, t["fonts"][k])
    if t.get("fontOverrides"):
        f = _merge(f, t["fontOverrides"])
    f.setdefault("heading", f["body"])
    return f


_font_over = None  # 지금 다루는 장의 글꼴 세트(슬라이드 fontPreset > 덱 fontPreset) — 없으면 작업 공간 글꼴


def use_fonts(name):
    """내보내기·검사가 장마다 부른다 — 이름이 없거나 모르는 세트면 작업 공간 글꼴로."""
    global _font_over
    _font_over = preset_fonts(name) if name else None


def cur_fonts():
    return _font_over or tokens()["fonts"]


def font_role(k):
    """글꼴 역할 이름 정규화(render.js fontRole 와 같은 규칙): mono·code → mono, heading → heading, 그 밖(없음·body·모르는 값) → body"""
    return "mono" if k in ("mono", "code") else "heading" if k == "heading" else "body"


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


def color_alpha(value, default="#000000"):
    """토큰명 또는 #RRGGBB·#RRGGBBAA → ('#RRGGBB', 불투명도 0~1). 모르면 (default, 1). render.colorAlpha 와 같은 규칙."""
    if not value:
        return None
    cs = tokens()["colors"]
    v = value
    for _ in range(5):
        if not isinstance(v, str):
            return default, 1.0
        if v.startswith("#"):
            if len(v) == 7:
                return v.upper(), 1.0
            if len(v) == 9 and re.fullmatch(r"[0-9A-Fa-f]{2}", v[7:9]):
                return v[:7].upper(), round(int(v[7:9], 16) / 255, 3)
            return default, 1.0
        if v in cs:
            v = cs[v]
        else:
            return default, 1.0
    return default, 1.0


def _clamp01(v, dflt):
    try:
        return max(0.0, min(1.0, float(v)))
    except (TypeError, ValueError):
        return dflt


def fill_spec(value):
    """도형 채우기(fill) 값을 정규화한다(render.fillSpec 와 같은 규칙). 없으면 None.
    - 토큰·"#RRGGBB"·"#RRGGBBAA"(끝 두 자리 = 불투명도) → {"kind": "solid", "color": "#RRGGBB", "alpha": 0~1}
    - {"color": …, "alpha": 0~1} → 단색 + 투명도
    - {"gradient": {"angle": 도, "stops": [[위치 0~1, 색, (불투명도)], …] 또는 [색, 색, …](고른 간격)}, "alpha": …}
      → {"kind": "gradient", "angle": 0~360(0 = 왼→오, 90 = 위→아래, 시계 방향 - PPT a:lin 과 같음), "stops": [[위치, "#RRGGBB", 불투명도], …]}
    정지점이 하나면 단색, 없으면 None."""
    if not value:
        return None
    if isinstance(value, str):
        ca = color_alpha(value)
        return {"kind": "solid", "color": ca[0], "alpha": ca[1]} if ca else None
    if not isinstance(value, dict):
        return None
    base_a = _clamp01(value.get("alpha", 1), 1.0)
    g = value.get("gradient")
    if not isinstance(g, dict):
        ca = color_alpha(value.get("color"))
        return {"kind": "solid", "color": ca[0], "alpha": round(ca[1] * base_a, 3)} if ca else None
    raw = g.get("stops") or []
    n = len(raw)
    stops = []
    for i, st in enumerate(raw):
        if isinstance(st, str):  # 색만 → 고른 간격
            pos, col, a = (i / (n - 1) if n > 1 else 0.0), st, 1.0
        elif isinstance(st, (list, tuple)) and len(st) >= 2:
            pos, col, a = st[0], st[1], (st[2] if len(st) > 2 else 1.0)
        else:
            continue
        ca = color_alpha(col)
        if not ca:
            continue
        stops.append([round(_clamp01(pos, 0.0), 4), ca[0], round(ca[1] * _clamp01(a, 1.0) * base_a, 3)])
    stops.sort(key=lambda s: s[0])
    if not stops:
        return None
    if len(stops) == 1:
        return {"kind": "solid", "color": stops[0][1], "alpha": stops[0][2]}
    try:
        ang = float(g.get("angle", 0)) % 360
    except (TypeError, ValueError):
        ang = 0.0
    return {"kind": "gradient", "angle": round(ang, 2), "stops": stops}


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
_MARK = re.compile(r"\*\*(.+?)\*\*|==(.+?)==|\[\[([#\w-]+)\|(.+?)\]\]|__(.+?)__|(?<![\w*])\*([^*\s](?:[^*]*?[^*\s])?)\*(?![\w*])")  # **굵게** ==강조== [[색|글]] __밑줄__ *기울임* (render.js MARK 와 같다)


def runs(text, page=None):
    """'a **b** ==c== [[s1|d]] __u__ *i*' → [(글자, {'bold'|'color'|'underline'|'italic'})] (줄바꿈은 호출자가 먼저 나눈다)."""
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
        elif m.group(5) is not None:
            out.append((m.group(5), {"underline": True}))
        elif m.group(6) is not None:
            out.append((m.group(6), {"italic": True}))
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


# ---------- 여러 언어 하이라이트 - 언어 정의는 code_langs.json(render.js 와 같은 파일·같은 알고리즘) ----------
LANGS = json.loads((STUDIO / "code_langs.json").read_text(encoding="utf-8"))
_LANG_SETS = {}


def lang_of(el):
    """el["lang"] → 정의 이름(별칭 포함, 대소문자 무시). 없으면 sql(예전 기본), 모르면 plain"""
    lw = str(el.get("lang") or "sql").lower()
    if lw in LANGS and not lw.startswith("_"):
        return lw
    for k, v in LANGS.items():
        if not k.startswith("_") and lw in (v.get("alias") or []):
            return k
    return "plain"


def _isa(c):
    return ("A" <= c <= "Z") or ("a" <= c <= "z") or c == "_"


def _isd(c):
    return "0" <= c <= "9"


def hl_generic(src, name):
    sp, n, out = LANGS[name], len(src), []
    if name not in _LANG_SETS:
        low = (lambda w: w.lower()) if sp.get("ci") else (lambda w: w)
        _LANG_SETS[name] = [set(low(w) for w in (sp.get(k) or [])) for k in ("kw", "types", "lits", "fn")]
    KW, TY, LI, FN = _LANG_SETS[name]
    idx = sp.get("idx") or ""
    id0 = lambda c: _isa(c) or (c != "" and c in idx)  # noqa: E731
    id1 = lambda c: _isa(c) or _isd(c) or (c != "" and c in idx)  # noqa: E731
    at = lambda j: src[j] if 0 <= j < n else ""  # noqa: E731

    def push(v, r):
        if out and out[-1][1] is None and r is None:
            out[-1][0] += v
        else:
            out.append([v, r])

    def eol(i):
        e = src.find("\n", i)
        return n if e < 0 else e

    def skip_sp(j):
        while j < n and src[j] in (" ", "\t"):
            j += 1
        return j

    i = 0
    while i < n:
        c, prev, nx = src[i], (src[i - 1] if i else "\n"), at(i + 1)
        k = i - 1
        while k >= 0 and src[k] in (" ", "\t"):
            k -= 1
        at_line = k < 0 or src[k] == "\n"
        j, role = -1, None
        if sp.get("diff") and (i == 0 or prev == "\n"):
            j = eol(i)
            role = "st" if c == "+" else "bi" if c == "-" else "co" if c == "@" else None
        if j < 0 and sp.get("md") and at_line and c == "#":
            j, role = eol(i), "k"
        if j < 0:
            for a, b in sp.get("block") or []:
                if src.startswith(a, i):
                    e = src.find(b, i + len(a))
                    j, role = (n if e < 0 else e + len(b)), "co"
                    break
        if j < 0 and sp.get("vars") and c == "$" and nx:
            if nx in ("{", "("):
                e = src.find("}" if nx == "{" else ")", i)
                j = n if e < 0 else e + 1
            elif id0(nx) or _isd(nx):
                j = i + 2
                while j < n and id1(src[j]):
                    j += 1
            elif nx in "@#?*!$-":
                j = i + 2
            if j >= 0:
                role = "bi"
        if j < 0:
            for a in sp.get("line") or []:
                if src.startswith(a, i) and not (sp.get("hashWs") and a == "#" and not prev.isspace()):
                    j, role = eol(i), "co"
                    break
        if j < 0 and sp.get("pre") and c == "#" and at_line:
            j, role = eol(i), "bi"
        if j < 0:
            for s in sp.get("str") or []:
                a, b, raw = s[0], s[1], (len(s) > 2 and bool(s[2]))
                if not src.startswith(a, i):
                    continue
                m = i + len(a)
                while m < n:
                    if not raw and sp.get("esc") and src[m] == "\\":
                        m += 2
                        continue
                    if src.startswith(b, m):
                        if raw and len(b) == 1 and at(m + 1) == b:
                            m += 2
                            continue
                        m += len(b)
                        break
                    if len(b) == 1 and not sp.get("ml") and not raw and src[m] == "\n":
                        break
                    m += 1
                j, role = min(m, n), "st"
                if sp.get("keys") and at(skip_sp(j)) == sp["keys"]:
                    role = "tb"
                break
        if j < 0 and sp.get("tags") and c == "<" and (_isa(nx) or nx in ("/", "!", "?")):
            j = i + 1
            while j < n and (id1(src[j]) or src[j] in "/!?:-."):
                j += 1
            role = "tb"
        if j < 0 and sp.get("deco") and c == "@" and _isa(nx):
            j = i + 1
            while j < n and (id1(src[j]) or src[j] == "."):
                j += 1
            role = "bi"
        if j < 0 and (_isd(c) or (c == "." and _isd(nx))) and not (i > 0 and id1(prev)):
            j = i + 1
            while j < n and (_isa(src[j]) or _isd(src[j]) or src[j] == "."):
                j += 1
            role = "nu"
        if j < 0 and (id0(c) or ((KW or LI) and c in "@!$~" and id0(nx))):
            j = i + 1
            while j < n and id1(src[j]):
                j += 1
            w = src[i:j]
            lw = w.lower() if sp.get("ci") else w
            role = "k" if lw in KW else "tb" if lw in TY else "nu" if lw in LI else "ca" if lw in FN else None
            if role is None and sp.get("keys"):
                t = skip_sp(j)
                if at(t) == sp["keys"] and at(t + 1) != sp["keys"]:
                    role = "tb"
            if role is None and sp.get("attrs") and at(skip_sp(j)) == "=":
                role = "ca"
            if role is None and sp.get("calls", True) is not False and at(skip_sp(j)) == "(":
                role = "ca"
            if role is None and not id0(c):
                j = i + 1
        if j < 0:
            j, role = i + 1, None
        push(src[i:j], role)
        i = j
    return [tuple(t) for t in out]


def highlight(src, el):
    name = lang_of(el)
    if name == "sql":
        return hl_sql(src)
    return [(src, None)] if name == "plain" else hl_generic(src, name)


def code_lines(el):
    """code 요소 → 표시 줄 [{n: 줄 번호 글자, focus, gap(생략 줄), runs:[(글자, 역할)]}]
    start(시작 번호) · focus(강조 줄 번호) · show([[from,to],…] 구간만, 사이는 ⋮ 한 줄)"""
    src = str(el.get("text", ""))
    toks = highlight(src, el)
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
    key = (bold, mono, round(size_px * 4), id(_font_over))
    if key not in _fonts:
        try:
            from PIL import ImageFont
            ms = cur_fonts()["mono" if mono else "body"].get("measure") or {}
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


def text_pad_effective(el, default=0):
    """글 영역 여백 = max(pad, PowerPoint 도형 글 영역 들여넣기) (위, 오, 아, 왼) - render.js elBox·export_pptx.text_pad 와 같은 규칙.
    타원 = 폭·높이 × 0.14645, 둥근 사각형·칩 = 반경 × 0.29289, fill 없는 text 는 pad 그대로."""
    t, r, b, l = pad_of(el, default)
    kind = el.get("type")
    if kind == "text" and not el.get("fill"):
        return (t, r, b, l)
    w, h = float(el.get("w", 0)), float(el.get("h", 0))
    if kind == "ellipse":
        ix, iy = w * 0.14645, h * 0.14645
    else:
        rad = min(w, h) / 2 if kind == "pill" else radius(el.get("radius"), w, h)
        ix = iy = 0.29289 * rad
    return (max(t, iy), max(r, ix), max(b, iy), max(l, ix))


def pad_of(el, default=0):
    """pad(숫자 또는 [위, 오, 아, 왼]) → 네 값 튜플 (render.js padOf 와 같은 규칙)"""
    p = el.get("pad", default)
    if isinstance(p, (int, float)):
        return (p, p, p, p)
    p = list(p) + [0] * 4
    return tuple(p[:4])


# ---------- 글머리 번호 자동 감지 (render.js bulletNum 과 같은 규칙) ----------
_NUM_PATTERNS = [  # (정규식, 종류) - 글 앞의 "1. " "1) " "(1) " "a. " "A) " "①" "가. " + 공백 → 글머리 대신 번호. 두 자리까지(2024. 같은 연도는 제외), "1.5배" 처럼 공백 없는 것은 제외
    (re.compile(r"^\s*(\d{1,2})([.)])\s+(?=\S)"), "arabic"),
    (re.compile(r"^\s*\((\d{1,2})\)\s+(?=\S)"), "arabicBoth"),
    (re.compile(r"^\s*([a-z])([.)])\s+(?=\S)"), "alphaLc"),
    (re.compile(r"^\s*([A-Z])([.)])\s+(?=\S)"), "alphaUc"),
    (re.compile(r"^\s*([\u2460-\u2473])\s*(?=\S)"), "circle"),
    (re.compile(r"^\s*([\uac00-\ud7a3])([.)])\s+(?=\S)"), "korean"),
    (re.compile(r"^\s*([*+\-\u2013\u2014])\s+(?=\S)"), "symbol"),  # * + - – — + 공백 → 그 기호가 글머리
    (re.compile(r"^\s*([·‧∙ㆍ•●○◦◎■□▪▫◆◇◈▲△▼▽▶►▸▹▷→➜➤➢✓✔✗✘✦✧★☆※◉⦁])\s*(?=\S)"), "symbol"),  # 글머리 기호(공백 없어도)
]
BULLET_HEAVY = "●■◆▲▼★◉"  # 글자 크기의 60% 로 그리는 굵은 기호(● 과 같게) - 나머지 기호·번호는 100%


def bullet_num(text):
    """글 앞의 번호(1. · a) · ① …)나 글머리 기호(* - · • ■ …)를 떼어 {label, scheme, start, rest[, kind=symbol]} 로. 없으면 None.
    scheme 은 PPTX a:buAutoNum type(없으면 글자 그대로 buChar). 기호는 kind=symbol - 글머리 색으로 그린다."""
    s = str(text if text is not None else "")
    for rx, kind in _NUM_PATTERNS:
        m = rx.match(s)
        if not m:
            continue
        rest = s[m.end():]
        if kind == "arabic":
            n, sep = int(m.group(1)), m.group(2)
            return {"label": f"{n}{sep}", "scheme": "arabicPeriod" if sep == "." else "arabicParenR", "start": n, "rest": rest}
        if kind == "arabicBoth":
            n = int(m.group(1))
            return {"label": f"({n})", "scheme": "arabicParenBoth", "start": n, "rest": rest}
        if kind in ("alphaLc", "alphaUc"):
            ch, sep = m.group(1), m.group(2)
            start = ord(ch.lower()) - 96
            scheme = ("alphaLc" if kind == "alphaLc" else "alphaUc") + ("Period" if sep == "." else "ParenR")
            return {"label": f"{ch}{sep}", "scheme": scheme, "start": start, "rest": rest}
        if kind == "circle":
            ch = m.group(1)
            return {"label": ch, "scheme": "circleNumDbPlain", "start": ord(ch) - 0x2460 + 1, "rest": rest}
        if kind == "symbol":  # 글머리 기호 - 글머리 색(dot/subColor)으로, 번호가 아니라 글자 그대로(buChar)
            return {"label": m.group(1), "scheme": None, "start": 0, "kind": "symbol", "rest": rest}
        return {"label": f"{m.group(1)}{m.group(2)}", "scheme": None, "start": 1, "rest": rest}  # 가. 나. - 자동 번호 종류가 없어 글자 그대로
    return None


def num_hang(label, size, hang):
    """번호 글머리의 내어쓰기 폭 px - 번호가 ●보다 넓으면 넓힌다(글 시작 위치도 그만큼 밀린다). 기호(한 글자)는 그대로. render.js numHang 과 같은 식."""
    if len(label) <= 1:
        return hang
    w = sum(1.0 if ord(ch) > 0x2E80 else 0.55 for ch in label)  # 한글·한자 같은 전각 글자는 1em
    return max(hang, math.ceil(size * (w + 0.25)))


# ---------- 글머리 종류(marker · subMarker) - 기호 또는 번호 매기기 (render.js markerNum 과 같은 규칙) ----------
NUM_STYLES = {  # 번호 매기기 종류 → PPTX a:buAutoNum type(None 이면 글자 그대로 buChar)
    "1.": "arabicPeriod", "1)": "arabicParenR", "(1)": "arabicParenBoth", "a.": "alphaLcPeriod", "a)": "alphaLcParenR",
    "A.": "alphaUcPeriod", "A)": "alphaUcParenR", "①": "circleNumDbPlain", "가.": None,
}
KOR_NUM = "가나다라마바사아자차카타파하"


def num_label(style, n):
    """번호 매기기 종류와 순번 n(1부터) → 표시 글자. 모르는 종류면 None."""
    if style not in NUM_STYLES:
        return None
    if style == "①":
        return chr(0x2460 + n - 1) if 1 <= n <= 20 else f"({n})"
    if style == "가.":
        return (KOR_NUM[n - 1] if 1 <= n <= len(KOR_NUM) else str(n)) + "."
    a = chr(96 + n) if 1 <= n <= 26 else str(n)
    return {"1.": f"{n}.", "1)": f"{n})", "(1)": f"({n})", "a.": f"{a}.", "a)": f"{a})", "A.": f"{a.upper()}.", "A)": f"{a.upper()})"}[style]


def marker_num(style, lvl, n):
    """요소의 marker(수준 0)/subMarker(수준 1) 설정 → 그 행의 번호·기호 {label, scheme, start, kind} 또는 None(기본 ●/–).
    번호 종류(NUM_STYLES)는 순번 n 으로 번호를 매기고(kind=auto), "none" 은 글머리 없음, 그 밖의 글자는 기호(kind=symbol)."""
    if not style or style == ("●" if lvl == 0 else "–"):
        return None
    if style in NUM_STYLES:
        return {"label": num_label(style, n), "scheme": NUM_STYLES[style], "start": n, "kind": "auto"}
    if style == "none":
        return {"label": "", "scheme": None, "start": 0, "kind": "none"}
    return {"label": str(style), "scheme": None, "start": 0, "kind": "symbol"}


# ---------- 글머리(bullets) → 행 (render.js bulletRows 와 같은 규칙) ----------
def bullet_rows(el):
    """bullets → [[글자, 수준, 뒤 간격 px, 번호]]. gap(항목 사이)·subGap(하위 사이).
    번호 = 글 앞의 "1. " 같은 번호·기호를 자동 감지한 {label, scheme, start[, kind]}(글자에서는 뗀다), 없으면 요소의 marker/subMarker(글머리 종류 - 기호·번호 매기기·none)에서,
    그것도 없으면 None(기본 ●/–). autoNum: false 면 감지하지 않는다.
    spread 가 참이면 균등 간격 - 행 높이(줄 수 = 줄바꿈 수 + 1, 자동 줄바꿈은 세지 않음)를 뺀 나머지를 행 사이에 고르게 나눠
    상자 높이를 채운다(원본 PPT 의 "세로 고르게" 글상자를 옮길 때). 마지막 행 뒤는 0."""
    gap, sub_gap = el.get("gap", 14), el.get("subGap", 6)
    auto = el.get("autoNum", True) is not False
    marker, sub_marker = el.get("marker"), el.get("subMarker")
    rows = []
    cnt = [0, 0]  # 수준별 순번(번호 매기기용) - 하위는 상위 항목마다 다시 1부터

    def row(text, lvl, after):
        if lvl == 0:
            cnt[0] += 1
            cnt[1] = 0
        else:
            cnt[1] += 1
        num = bullet_num(text) if auto else None  # 글 앞에 적은 번호·기호가 먼저
        if num:
            text = num.pop("rest")
        else:
            num = marker_num(marker if lvl == 0 else sub_marker, lvl, cnt[lvl])  # 요소에 고른 글머리 종류
        return [text, lvl, after, num]

    for it in el.get("items", []):
        if isinstance(it, str):
            it = {"text": it}
        subs = it.get("sub", []) or []
        rows.append(row(it.get("text", ""), 0, sub_gap if subs else gap))
        for k, s in enumerate(subs):
            rows.append(row(s, 1, sub_gap if k < len(subs) - 1 else gap))
    if el.get("spread") and len(rows) > 1:
        size, sub, lh = float(el.get("size", 20)), float(el.get("subSize", 17)), float(el.get("lineHeight", 1.55))
        pt, _, pb, _ = pad_of(el)
        used = sum((sub if lvl else size) * lh * (str(t).count("\n") + 1) for t, lvl, _, _ in rows)
        g = max(0.0, (float(el["h"]) - pt - pb - used) / (len(rows) - 1))
        for i, r in enumerate(rows):
            r[2] = g if i < len(rows) - 1 else 0
    return rows


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


def row_heights(el, n):
    """행 높이(px) - rowH(행별 비율, colW 처럼)를 h 에 맞춰 나눈다. 없으면 고르게, 모자란 행은 준 값의 평균,
    0 이하·숫자 아님이 있으면 무시(render.js rowHeights 와 같은 규칙)."""
    N = max(1, n)
    raw = el.get("rowH")
    try:
        r = [float(v) for v in raw] if isinstance(raw, list) else []
    except (TypeError, ValueError):
        r = []
    if not r or any(not v > 0 for v in r):
        return [el["h"] / N] * n
    avg = sum(r) / len(r)
    r = (r + [avg] * n)[:n]
    tot = sum(r)
    return [el["h"] * v / tot for v in r]


def shape_text_rect(shape, w, h):
    """도형(shape 요소)의 글 영역 [l, t, r, b] - render.js SHAPES[*].rect 와 같은 식(PowerPoint 프리셋의 글 상자)."""
    ss = min(w, h)
    R = {
        "triangle": lambda: [w / 4, h / 2, 3 * w / 4, h], "rtTriangle": lambda: [w / 12, h / 2, 7 * w / 12, 11 * h / 12],
        "diamond": lambda: [w / 4, h / 4, 3 * w / 4, 3 * h / 4], "parallelogram": lambda: [ss / 8, 0, w - ss / 8, h], "trapezoid": lambda: [ss / 8, 0, w - ss / 8, h],
        "pentagon": lambda: [0.191 * w, 0.382 * h, 0.809 * w, h], "hexagon": lambda: [ss / 8, 0, w - ss / 8, h],
        "octagon": lambda: [ss * 0.29289 / 2, ss * 0.29289 / 2, w - ss * 0.29289 / 2, h - ss * 0.29289 / 2],
        "rightArrow": lambda: [0, h / 4, w - ss / 4, 3 * h / 4], "leftArrow": lambda: [ss / 4, h / 4, w, 3 * h / 4],
        "upArrow": lambda: [w / 4, ss / 4, 3 * w / 4, h], "downArrow": lambda: [w / 4, 0, 3 * w / 4, h - ss / 4],
        "leftRightArrow": lambda: [ss / 4, h / 4, w - ss / 4, 3 * h / 4],
        "chevron": lambda: [min(ss / 2, w / 2), 0, w - min(ss / 2, w / 2) / 2, h], "homePlate": lambda: [0, 0, w - min(ss / 2, w) / 2, h],
        "star5": lambda: [0.318 * w, 0.382 * h, 0.682 * w, 0.764 * h], "plus": lambda: [ss / 4, ss / 4, w - ss / 4, h - ss / 4],
        "callout": lambda: [0, 0, w, h], "roundCallout": lambda: [ss / 6 * 0.29, ss / 6 * 0.29, w - ss / 6 * 0.29, h - ss / 6 * 0.29],
        "can": lambda: [0, ss / 4, w, h - ss / 8], "cube": lambda: [0, ss / 4, w - ss / 4, h],
    }
    return R.get(shape, R["diamond"])()


def table_merges(el, nr, nc):
    """표 merge → (span{(r,c): (rows, cols)}, skip{(r,c)}) - 왼쪽 위 셀이 rows×cols 를 차지하고 나머지는 그리지 않는다. render.js tableMerges 와 같은 규칙."""
    span, skip = {}, set()
    for m in el.get("merge") or []:
        try:
            r, c, rs, cs = (int(v) for v in list(m)[:4])
        except (TypeError, ValueError):
            continue
        if r < 0 or c < 0 or r >= nr or c >= nc:
            continue
        rs, cs = max(1, min(rs, nr - r)), max(1, min(cs, nc - c))
        if rs == 1 and cs == 1:
            continue
        cells = {(r + i, c + j) for i in range(rs) for j in range(cs)}
        if any(k in skip or k in span for k in cells):
            continue  # 앞의 병합과 겹치면 무시
        span[(r, c)] = (rs, cs)
        skip |= cells - {(r, c)}
    return span, skip


def table_merges(el, nr, nc):
    """표 merge → (span{(r,c): (rows, cols)}, skip{(r,c)}) - 왼쪽 위 셀이 rows×cols 를 차지하고 나머지는 그리지 않는다. render.js tableMerges 와 같은 규칙."""
    span, skip = {}, set()
    for m in el.get("merge") or []:
        try:
            r, c, rs, cs = (int(v) for v in list(m)[:4])
        except (TypeError, ValueError):
            continue
        if r < 0 or c < 0 or r >= nr or c >= nc:
            continue
        rs, cs = max(1, min(rs, nr - r)), max(1, min(cs, nc - c))
        if rs == 1 and cs == 1:
            continue
        cells = {(r + i, c + j) for i in range(rs) for j in range(cs)}
        if any(k in skip or k in span for k in cells):
            continue  # 앞의 병합과 겹치면 무시
        span[(r, c)] = (rs, cs)
        skip |= cells - {(r, c)}
    return span, skip


def table_merges(el, nr, nc):
    """표 merge → (span{(r,c): (rows, cols)}, skip{(r,c)}) - 왼쪽 위 셀이 rows×cols 를 차지하고 나머지는 그리지 않는다. render.js tableMerges 와 같은 규칙."""
    span, skip = {}, set()
    for m in el.get("merge") or []:
        try:
            r, c, rs, cs = (int(v) for v in list(m)[:4])
        except (TypeError, ValueError):
            continue
        if r < 0 or c < 0 or r >= nr or c >= nc:
            continue
        rs, cs = max(1, min(rs, nr - r)), max(1, min(cs, nc - c))
        if rs == 1 and cs == 1:
            continue
        cells = {(r + i, c + j) for i in range(rs) for j in range(cs)}
        if any(k in skip or k in span for k in cells):
            continue  # 앞의 병합과 겹치면 무시
        span[(r, c)] = (rs, cs)
        skip |= cells - {(r, c)}
    return span, skip


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
    rowH = row_heights(el, n)
    even = all(v == rowH[0] for v in rowH)

    def row_top(k):
        return rowH[0] * k if even else sum(rowH[:k])
    header = el.get("header", True) if not is_plan else True
    head_fill, head_color = el.get("headFill", "surface-container-high"), el.get("headColor", "on-surface")
    # 본문 셀 글꼴 = colFont[열](비어 있으면 el.font, 둘 다 없으면 body) - 값은 body·heading·mono("code" 도 mono). 머리 행은 항상 본문
    fonts = el.get("colFont") or []
    def_font = font_role(el.get("font"))
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
                           "font": "body" if hd else font_role(fonts[j] if j < len(fonts) and fonts[j] else def_font)}
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
            bh = max(rowH[i + 1] - 8, lines * size * 1.5 + 12)
            cy = el["y"] + row_top(i + 1) + rowH[i + 1] / 2
            callouts.append({"row": i + 1, "text": r["note"], "fill": fill, "color": color,
                             "line": HL_ROLE[role][1] if role else "outline-variant",
                             "x": el["x"] + tw + 24, "y": cy - bh / 2, "w": cw, "h": bh, "cy": cy, "tx": el["x"] + tw})
    return {"x": el["x"], "y": el["y"], "tw": tw, "colW": colW, "rowH": rowH, "cells": cells,
            "rule": el.get("rule", "surface-container-high"), "size": el.get("size", 16), "callouts": callouts}
