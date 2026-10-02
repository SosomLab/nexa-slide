# -*- coding: utf-8 -*-
"""PPTX 에 실제로 쓴 글꼴 기록 — out/<덱>.fonts.json (export_pptx.py 가 내보낼 때마다 쓴다).

    python3 studio/font_report.py <덱> [--pptx <파일>]      # 다시 만들기(기록만)

기록: 글꼴 세트(이름·출처 template|workspace)·역할별 글꼴(body·heading·mono), PPTX 슬라이드 XML 에 실제로 들어간 글꼴 이름과
글꼴마다 원본 파일(작업 공간 fonts/ → 사용자·시스템 글꼴 폴더)·설치 여부·포함(임베드) 허용 여부(OS/2 fsType).
글꼴 포함 저장(embed_fonts.py)을 하면 "embedded" 에 PPTX 안에 들어간 글꼴 파일이 더해진다.
"""
import argparse
import datetime as dt
import json
import os
import re
import struct
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CONFIG, OUT, fonts_dir, resolve_tokens, safe_id  # noqa: E402

SYS_DIRS = [Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Windows/Fonts", Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts",
            Path.home() / "Library/Fonts", Path("/Library/Fonts"), Path.home() / ".local/share/fonts", Path("/usr/share/fonts")]
EXT = (".ttf", ".otf", ".ttc")
CATALOG = Path(__file__).resolve().parent / "font_catalog.json"
_index = None
_catalog = None


def catalog():
    """엔진 글꼴 안내 목록(무료·시스템 기본) — 파일은 없고 이름·라이선스·받는 곳만."""
    global _catalog
    if _catalog is None:
        _catalog = json.loads(CATALOG.read_text(encoding="utf-8"))["fonts"]
    return _catalog


def classify(typeface):
    """글꼴 이름 → (상태 free|system|custom, 목록 항목 또는 None). custom = 목록에 없는 글꼴(회사 서체 등 — 받는 사람이 구할 수 있는지 확인)."""
    t = (typeface or "").strip().lower()
    for c in catalog():
        if t in (f.lower() for f in c["families"]) or t == c["name"].lower():
            return c["status"], c
    return "custom", None


def fs_type(p):
    """OS/2 fsType — 0 제한 없음 · 2 제한(포함 금지) · 4 인쇄·미리보기 · 8 편집 가능 포함. ttc 는 첫 글꼴."""
    try:
        with open(p, "rb") as fh:
            tb = _tables(fh)
            if b"OS/2" in tb:
                fh.seek(tb[b"OS/2"][0] + 8)
                return struct.unpack(">H", fh.read(2))[0]
    except (OSError, struct.error):
        pass
    return None


def embed_kind(v):
    if v is None:
        return "알 수 없음"
    if v & 0x0200:
        return "비트맵만"
    if v == 0:
        return "제한 없음"
    if v & 0x0002:
        return "포함 금지"
    if v & 0x0008:
        return "편집 가능 포함"
    if v & 0x0004:
        return "인쇄·미리보기 포함"
    return f"기타({v})"


def _tables(fh):
    """sfnt 표 목록 {태그: (위치, 길이)} - 파일 머리만 읽는다(ttc 는 첫 글꼴)."""
    head = fh.read(12)
    if head[:4] == b"ttcf":
        base = struct.unpack(">I", fh.read(4))[0]
        fh.seek(base)
        head = fh.read(12)
    n = struct.unpack(">H", head[4:6])[0]
    d = fh.read(16 * n)
    return {d[16 * i:16 * i + 4]: struct.unpack(">II", d[16 * i + 8:16 * i + 16]) for i in range(n)}


def _names(p):
    """글꼴 파일 → 가족 이름들(영문·현지 이름 모두 — PPTX 의 ea 글꼴은 한글 이름일 수 있다). name 표만 읽는다."""
    out = set()
    try:
        with open(p, "rb") as fh:
            tb = _tables(fh)
            if b"name" not in tb:
                return out
            off, ln = tb[b"name"]
            fh.seek(off)
            b = fh.read(min(ln, 200000))
        cnt, so = struct.unpack(">HH", b[2:6])
        for k in range(cnt):
            pid, eid, lid, nid, l2, no = struct.unpack(">6H", b[6 + 12 * k: 18 + 12 * k])
            if nid not in (1, 4, 16):
                continue
            raw = b[so + no: so + no + l2]
            s = raw.decode("utf-16-be", "ignore") if pid in (0, 3) else raw.decode("latin-1", "ignore")
            if s.strip():
                out.add(s.strip().lower())
    except (OSError, struct.error):
        pass
    return out


def font_index():
    """가족 이름(소문자) → [파일] — 작업 공간 fonts/ 가 앞."""
    global _index
    if _index is None:
        _index = {}
        dirs = ([fonts_dir()] if fonts_dir() else []) + SYS_DIRS
        for d in dirs:
            if not d or not d.is_dir():
                continue
            for f in d.rglob("*") if d == Path("/usr/share/fonts") else d.iterdir():
                if f.suffix.lower() in EXT:
                    for n in _names(f):
                        _index.setdefault(n, []).append(f)
    return _index


def installed(p):
    """사용자·시스템 글꼴 폴더에 같은 파일 이름이 있으면 설치된 것으로 본다(PowerPoint 가 쓸 수 있음)."""
    return any((d / p.name).is_file() for d in SYS_DIRS)


def used_typefaces(pptx):
    faces = {}
    with zipfile.ZipFile(pptx) as z:
        for n in z.namelist():
            if re.match(r"ppt/slides/slide\d+\.xml$", n):
                for t in re.findall(r'<a:(latin|ea|cs) typeface="([^"]+)"', z.read(n).decode("utf-8")):
                    faces.setdefault(t[1], set()).add(t[0])
        embedded = sorted(n for n in z.namelist() if n.startswith("ppt/fonts/"))
    return faces, embedded


def report(deck, pptx=None):
    pptx = Path(pptx) if pptx else OUT / f"{deck}.pptx"
    t = resolve_tokens(CONFIG)
    wsp = CONFIG.get("fontPresets") if isinstance(CONFIG.get("fontPresets"), dict) else {}
    faces, embedded = used_typefaces(pptx)
    wd = fonts_dir()
    used = []
    for name, kinds in sorted(faces.items()):
        files = font_index().get(name.lower(), [])
        st, cat = classify(name)
        used.append({"typeface": name, "as": sorted(kinds), "status": st, "catalog": cat["name"] if cat else None,
                     "url": cat["url"] if cat else "", "license": cat["license"] if cat else "",
                     "files": [{"path": str(f), "where": "workspace" if wd and f.parent == wd else "system",
                                "installed": installed(f), "embed": embed_kind(fs_type(f))} for f in files[:4]],
                     "found": bool(files)})
    rep = {"deck": deck, "pptx": pptx.name, "at": dt.datetime.now().isoformat(timespec="seconds"),
           "preset": t.get("fontPreset", ""), "source": "workspace" if t.get("fontPreset") in wsp else "template",
           "roles": {k: {x: (t["fonts"].get(k) or {}).get(x) for x in ("latin", "ea", "css", "measure")} for k in ("body", "heading", "mono")},
           "used": used, "embedded": embedded}
    return rep


def write(deck, pptx=None, extra=None):
    rep = report(deck, pptx)
    if extra:
        rep.update(extra)
    out = OUT / f"{deck}.fonts.json"
    out.write_text(json.dumps(rep, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    return out, rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("id")
    ap.add_argument("--pptx")
    a = ap.parse_args()
    if not safe_id(a.id):
        sys.exit("잘못된 덱 id")
    out, rep = write(a.id, a.pptx)
    print(f"{out} — " + ", ".join(f"{u['typeface']}{'' if u['found'] else '(파일 못 찾음)'}" for u in rep["used"]))


if __name__ == "__main__":
    main()
