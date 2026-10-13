# -*- coding: utf-8 -*-
"""작업 공간 기준 폴더·사용자 설정 - 엔진은 슬라이드 내용을 자기 폴더에 두지 않는다.

    python3 studio/paths.py            # 문서 폴더 · 제작 기준 폴더 · 사용자 설정 위치를 보여 준다

제작 기준 폴더(새로 만들 때 기본 위치)
    1. 환경변수 NEXA_SLIDE_PROJECTS
    2. 사용자 설정 settings.json 의 "projectsRoot"(시작 페이지에서 바꿀 수 있다)
    3. 운영체제의 기본 문서 폴더 아래 NexaSlide/
       Windows  알려진 폴더 Documents(OneDrive 로 옮긴 경우 그 위치) · macOS ~/Documents · Linux XDG DOCUMENTS
    제작마다 그 아래에 폴더를 하나씩 만든다. 사용자가 폴더·저장소를 지정하면 그 아래에 만든다.

사용자 설정(엔진 밖) - 최근 작업 목록·등록한 샘플 사이트·허브 포트·기준 폴더·이 PC 의 엔진 위치(engine)
    Windows %APPDATA%/nexa-slide · macOS ~/Library/Application Support/nexa-slide · Linux $XDG_CONFIG_HOME/nexa-slide
    (환경변수 NEXA_SLIDE_USER_DIR 로 바꿀 수 있다)
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
HUB_PORT = 5599
RECENT_KEEP = 30


def documents_dir() -> Path:
    """운영체제의 기본 문서 폴더."""
    if os.name == "nt":
        try:  # 문서 폴더를 OneDrive·다른 드라이브로 옮긴 경우까지 - SHGetKnownFolderPath(FOLDERID_Documents)
            import ctypes
            from ctypes import wintypes

            class GUID(ctypes.Structure):
                _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD), ("Data3", wintypes.WORD),
                            ("Data4", ctypes.c_ubyte * 8)]

            fid = GUID(0xFDD39AD0, 0x238F, 0x46AF, (ctypes.c_ubyte * 8)(0xAD, 0xB4, 0x6C, 0x85, 0x48, 0x03, 0x69, 0xC7))
            buf = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(fid), 0, None, ctypes.byref(buf)) == 0:
                p = buf.value
                ctypes.windll.ole32.CoTaskMemFree(buf)
                if p:
                    return Path(p)
        except Exception:  # noqa: BLE001
            pass
        return Path.home() / "Documents"
    if sys.platform == "darwin":
        return Path.home() / "Documents"
    try:  # Linux - XDG 사용자 폴더(한국어 환경이면 ~/문서 일 수 있다)
        r = subprocess.run(["xdg-user-dir", "DOCUMENTS"], capture_output=True, text=True, timeout=3)
        p = Path(r.stdout.strip())
        if r.returncode == 0 and p.is_absolute() and p != Path.home():
            return p
    except (OSError, subprocess.SubprocessError):
        pass
    p = Path.home() / "Documents"
    return p if p.is_dir() else Path.home()


def user_dir() -> Path:
    """사용자 설정 폴더(엔진·작업 공간 밖)."""
    env = os.environ.get("NEXA_SLIDE_USER_DIR")
    if env:
        return Path(env).expanduser().resolve()
    if os.name == "nt":
        return Path(os.environ.get("APPDATA") or Path.home() / "AppData/Roaming") / "nexa-slide"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/nexa-slide"
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "nexa-slide"


SETTINGS = user_dir() / "settings.json"


def load_settings() -> dict:
    try:
        s = json.loads(SETTINGS.read_text(encoding="utf-8"))
        return s if isinstance(s, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(s: dict):
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="settings.", suffix=".tmp", dir=str(SETTINGS.parent))
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        json.dump(s, f, ensure_ascii=False, indent=1)
    os.replace(tmp, SETTINGS)


def remember_engine():
    """이 PC 의 엔진 위치를 사용자 설정 "engine" 에 기록한다(바뀌었을 때만) - 작업 공간 실행기(nexa.py)가 PC 마다 엔진을 찾는 기준."""
    s = load_settings()
    if s.get("engine") != ENGINE.as_posix():
        s["engine"] = ENGINE.as_posix()
        save_settings(s)


LOCAL_CONFIG = "nexa-slide.local.json"  # PC 별 설정 - 공유 nexa-slide.json 위에 덮어쓴다(git 제외)
ROOT_MARKER = ".nexa-slide.json"  # 저장소 루트 표식 {"workspace": "<작업 공간 폴더>"} - 커밋한다


def repo_workspace(root):
    """저장소 루트 → 그 저장소의 작업 공간 폴더(없으면 None).
    루트 표식 .nexa-slide.json 의 "workspace"(slides · ppt · 그 밖의 이름)를 먼저, 없으면 slides/ - 실제로 nexa-slide.json 이 있을 때만."""
    root = Path(root)
    try:
        name = json.loads((root / ROOT_MARKER).read_text(encoding="utf-8")).get("workspace")
    except (OSError, ValueError, AttributeError):
        name = None
    for n in ([str(name)] if name else []) + ["slides"]:
        d = root / n
        if (d / "nexa-slide.json").is_file():
            return d
    return None


def write_root_marker(root, ws) -> bool:
    """루트 표식을 쓴다 - 없거나, 있어도 가리키는 작업 공간이 없을 때만(다른 작업 공간을 가리키고 있으면 그대로). 썼으면 True."""
    root, ws = Path(root), Path(ws)
    f = root / ROOT_MARKER
    try:
        cur = json.loads(f.read_text(encoding="utf-8")).get("workspace")
    except (OSError, ValueError, AttributeError):
        cur = None
    if cur and (root / str(cur) / "nexa-slide.json").is_file():
        return False
    name = os.path.relpath(ws, root).replace("\\", "/")
    f.write_text(json.dumps({"workspace": name, "about": "nexa-slide 저장소 표식 — 슬라이드 작업 공간 폴더(SLIDES.md 참고)"},
                            ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return True


def merge_config(base: dict, over: dict) -> dict:
    """over 를 base 위에 덮어쓴다 - 둘 다 dict 인 값은 안쪽까지(예: brand 의 한 항목만)."""
    out = dict(base)
    for k, v in over.items():
        out[k] = merge_config(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def load_ws_config(ws, local=True) -> dict:
    """작업 공간 설정 = nexa-slide.json(+ local 이면 nexa-slide.local.json 을 덮어씀). 없거나 깨졌으면 빈 dict."""
    def read(p):
        try:
            d = json.loads(Path(p).read_text(encoding="utf-8"))
            return d if isinstance(d, dict) else {}
        except (OSError, ValueError):
            return {}
    cfg = read(Path(ws) / "nexa-slide.json")
    return merge_config(cfg, read(Path(ws) / LOCAL_CONFIG)) if local else cfg


def default_projects_root() -> Path:
    return documents_dir() / "NexaSlide"


def projects_root() -> Path:
    env = os.environ.get("NEXA_SLIDE_PROJECTS")
    if env:
        return Path(env).expanduser().resolve()
    p = load_settings().get("projectsRoot")
    return Path(p).expanduser() if p else default_projects_root()


def hub_port() -> int:
    return int(load_settings().get("hubPort", HUB_PORT))


def inside_engine(p) -> bool:
    """엔진 폴더(또는 그 아래)인지 - 엔진 안에는 작업 공간을 만들거나 열지 않는다."""
    p = Path(p).resolve()
    return p == ENGINE or ENGINE in p.parents


def remember(path, title=""):
    """최근 작업 맨 앞에 올린다."""
    s = load_settings()
    path = str(Path(path).resolve())
    import datetime as dt
    rec = [r for r in s.get("recent", []) if r.get("path") != path]
    rec.insert(0, {"path": path, "title": title, "opened": dt.datetime.now().isoformat(timespec="seconds")})
    s["recent"] = rec[:RECENT_KEEP]
    save_settings(s)


def forget(path):
    s = load_settings()
    path = str(Path(path).resolve())
    s["recent"] = [r for r in s.get("recent", []) if r.get("path") != path]
    save_settings(s)


def main():
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    print(f"문서 폴더       {documents_dir()}")
    print(f"제작 기준 폴더  {projects_root()}" + ("" if projects_root() == default_projects_root() else f"  (기본 {default_projects_root()})"))
    print(f"사용자 설정     {SETTINGS}")
    print(f"허브 포트       {hub_port()}")
    print(f"엔진            {ENGINE}")


if __name__ == "__main__":
    main()
