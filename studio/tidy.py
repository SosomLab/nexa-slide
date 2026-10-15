# -*- coding: utf-8 -*-
"""작업 공간 관리 - 정리(임시·산출물·끊어진 그림·고아 첨부·세션 로그)와 압축 보관.

    python3 nexa.py tidy                      # 정리 대상 보고(지우지 않음)
    python3 nexa.py tidy --apply [--only 산출물,그림]   # 지운다(실제로는 out/.tidy/<시각>/ 로 옮겨 두고, --purge 로 비움)
    python3 nexa.py tidy --purge              # out/.tidy/ 비우기
    python3 nexa.py archive [--all] [--out <zip>]   # 작업 공간 통째로 zip(기본: 산출물·백업·휴지통·PC 전용 설정 제외, --all 은 전부)

정리 대상(category):
    output   out/*.pptx·*.pdf·*.fonts.json, out/<덱>/*.png(렌더), out/import/, Chrome 프로필 - 다시 만들 수 있는 산출물
    backup   decks/.history/(자동 백업 - 50개 넘는 것은 서버가 이미 지움)·decks/.trash/(지운 덱) - 되돌리기용, 기본은 지우지 않음
    image    assets/images·assets/import 중 어느 덱(decks/*.json)·내용(content/*.json)도 참조하지 않는 그림(.mmd 짝 포함). 브랜드·글꼴은 제외.
             .history·.trash 가 참조하는 그림은 "보관 참조"로 따로 표시(기본은 지우지 않음)
    attach   out/attach/<덱>/ 중 그 덱의 요청(requests.json)이 참조하지 않는 파일, 없는 덱의 첨부 폴더
    log      out/.studio/sessions/(웹 세션 턴 로그)·server.log - 실행 중 상태 파일(server.json·session.json 등)은 손대지 않는다
서버 API(작업 공간 서버): GET /api/tidy → 보고, POST /api/tidy {action: clean|purge|archive, …}. 시작 페이지 카드 ⋯ 메뉴 "정리·보관…"."""
import argparse
import datetime as dt
import json
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ASSET_ROOT, CONFIG, CONTENT, DECKS, OUT, STATE, WORKSPACE  # noqa: E402

TIDY_DIR = OUT / ".tidy"  # 정리로 옮긴 파일(되돌릴 수 있게) - purge 로 비운다
IMG_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"}
CATEGORIES = ("output", "backup", "image", "attach", "log")
CAT_KO = {"output": "산출물(다시 만들 수 있음)", "backup": "백업·휴지통", "image": "참조 없는 그림", "attach": "고아 첨부", "log": "세션 로그"}
STATE_KEEP = {"server.json", "server.log", "start.lock", "session.json", "flush.json", "activity.json", "wsession.json", "hub-key"}  # 실행 중 상태 - 지우지 않는다(server.log 는 log 범주로만)


def _rel(p):
    try:
        return str(Path(p).resolve().relative_to(WORKSPACE.resolve())).replace("\\", "/")
    except ValueError:
        return str(p)


def _size(p):
    p = Path(p)
    if p.is_file():
        return p.stat().st_size
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def _mtime(p):
    try:
        return dt.datetime.fromtimestamp(Path(p).stat().st_mtime).isoformat(timespec="seconds")
    except OSError:
        return ""


def _item(p, cat, why):
    return {"path": _rel(p), "category": cat, "reason": why, "size": _size(p), "mtime": _mtime(p), "dir": Path(p).is_dir()}


def _strings(o, out):
    """JSON 안의 모든 문자열(그림 참조 후보)."""
    if isinstance(o, str):
        out.add(o)
    elif isinstance(o, dict):
        for v in o.values():
            _strings(v, out)
    elif isinstance(o, list):
        for v in o:
            _strings(v, out)


def _refs(files):
    s = set()
    for f in files:
        try:
            _strings(json.loads(Path(f).read_text(encoding="utf-8")), s)
        except (OSError, ValueError):
            continue
    return s


def _norm(ref):
    ref = str(ref).strip().replace("\\", "/")
    ref = re.sub(r"^\./", "", ref)
    ref = re.sub(r"[?#].*$", "", ref)
    return ref.lstrip("/")


def _referenced(refs, rel):
    """rel(assetRoot 기준 경로)이 참조 집합에 있나 - 전체 경로·파일 이름·끝부분 일치."""
    name = rel.rsplit("/", 1)[-1]
    for r in refs:
        n = _norm(r)
        if not n:
            continue
        if n == rel or n.endswith("/" + rel) or n == name or n.endswith("/" + name):
            return True
    return False


def scan():
    """정리 대상 보고 {items: [...], summary: {category: {count, size}}, workspace}."""
    items = []
    # 1. 산출물
    if OUT.is_dir():
        for f in sorted(OUT.iterdir()):
            if f.is_file() and f.suffix.lower() in (".pptx", ".pdf") or f.name.endswith(".fonts.json"):
                items.append(_item(f, "output", "내보내기 결과 - 다시 내보내면 생긴다"))
            elif f.is_dir() and f.name == "import":
                items.append(_item(f, "output", "가져오기 추출물(out/import) - 다시 가져오면 생긴다"))
            elif f.is_dir() and f.name.startswith(".chrome-profile"):
                items.append(_item(f, "output", "브라우저 프로필(PDF·비교용 임시)"))
            elif f.is_dir() and not f.name.startswith(".") and f.name != "attach":
                pngs = [x for x in f.glob("*.png")]
                if pngs and all(re.fullmatch(r"(slide|web)-\d+\.png", x.name) for x in pngs):
                    items.append(_item(f, "output", "PowerPoint 렌더·비교 그림 - 다시 렌더하면 생긴다"))
    # 2. 백업·휴지통
    hist = DECKS / ".history"
    if hist.is_dir():
        for d in sorted(hist.iterdir()):
            if d.is_dir():
                live = (DECKS / f"{d.name}.json").is_file()
                items.append(_item(d, "backup", f"자동 백업·변경 원장({'있는' if live else '없는'} 덱 {d.name}) - 되돌리기에 쓰인다"))
    trash = DECKS / ".trash"
    if trash.is_dir():
        for d in sorted(trash.iterdir()):
            items.append(_item(d, "backup", "지운 덱(휴지통) - 되살릴 수 있다"))
    # 3. 참조 없는 그림
    live_json = [f for f in DECKS.glob("*.json") if not f.name.endswith(".requests.json")] if DECKS.is_dir() else []
    live_json += list(CONTENT.glob("*.json")) if CONTENT.is_dir() else []
    live_json += [f for f in Path(__file__).resolve().parent.glob("templates/*/template.json")]  # 템플릿이 가리키는 그림(거의 없음)
    refs = _refs(live_json)
    brand = CONFIG.get("brand") or {}
    for v in brand.values():
        if isinstance(v, str):
            refs.add(v)
    kept = _refs([*(hist.rglob("*.json") if hist.is_dir() else []), *(trash.rglob("*.json") if trash.is_dir() else [])])
    for sub in ("assets/images", "assets/import"):
        base = ASSET_ROOT / sub
        if not base.is_dir():
            continue
        for f in sorted(base.rglob("*")):
            if not f.is_file() or f.name.startswith("_"):
                continue
            if f.suffix.lower() not in IMG_EXT and f.suffix.lower() != ".mmd":
                continue
            if f.suffix.lower() == ".mmd" and f.with_suffix(".png").is_file():
                continue  # mermaid 원본은 그림(.png)과 짝 - 그림을 옮길 때 같이 옮긴다
            rel = str(f.resolve().relative_to(ASSET_ROOT.resolve())).replace("\\", "/")
            key = rel[:-4] + ".png" if f.suffix.lower() == ".mmd" else rel
            if _referenced(refs, key):
                continue
            why = "어느 덱·내용도 쓰지 않는 그림"
            if _referenced(kept, key):
                why += " - 백업·휴지통의 덱이 참조(되살리면 필요할 수 있음)"
            items.append({**_item(f, "image", why), "kept": _referenced(kept, key)})
    # 4. 고아 첨부
    att = OUT / "attach"
    if att.is_dir():
        for d in sorted(att.iterdir()):
            if not d.is_dir():
                continue
            rq = DECKS / f"{d.name}.requests.json"
            if not (DECKS / f"{d.name}.json").is_file():
                items.append(_item(d, "attach", f"없는 덱 {d.name} 의 첨부 폴더"))
                continue
            used = set()
            try:
                for r in json.loads(rq.read_text(encoding="utf-8")) if rq.is_file() else []:
                    for a in r.get("attachments") or []:
                        used.add(Path(str(a.get("path") or "")).name)
            except (OSError, ValueError):
                pass
            for f in sorted(d.iterdir()):
                if f.is_file() and f.name not in used:
                    items.append(_item(f, "attach", "어느 요청도 참조하지 않는 첨부(지운 초안·바뀐 첨부)"))
    # 5. 세션 로그
    sess = STATE / "sessions"
    if sess.is_dir():
        for d in sorted(sess.iterdir()):
            items.append(_item(d, "log", "웹 세션 턴 로그"))
    log = STATE / "server.log"
    if log.is_file() and log.stat().st_size > 1_000_000:
        items.append(_item(log, "log", "서버 로그(1MB 초과) - 비우면 새로 쓴다"))
    summary = {c: {"count": 0, "size": 0} for c in CATEGORIES}
    for it in items:
        summary[it["category"]]["count"] += 1
        summary[it["category"]]["size"] += it["size"]
    tidy = {"count": 0, "size": 0}
    if TIDY_DIR.is_dir():
        tidy = {"count": sum(1 for _ in TIDY_DIR.iterdir()), "size": _size(TIDY_DIR)}
    return {"workspace": str(WORKSPACE), "items": items, "summary": summary, "categories": CAT_KO, "tidy": tidy, "total": sum(i["size"] for i in items)}


def _safe_target(rel):
    p = (WORKSPACE / rel).resolve()
    if WORKSPACE.resolve() not in p.parents:
        raise ValueError(f"작업 공간 밖: {rel}")
    for part in p.relative_to(WORKSPACE.resolve()).parts:
        if part in (".git", "nexa-slide.json", "nexa-slide.local.json", ".env"):
            raise ValueError(f"지울 수 없는 경로: {rel}")
    return p


def clean(categories=None, paths=None, include_kept=False):
    """정리 - 범주(categories) 또는 경로 목록(paths, scan 의 path)을 out/.tidy/<시각>/ 로 옮긴다. 돌려주는 값: {moved: n, size, dest}."""
    rep = scan()
    cats = set(categories or [])
    want = set(paths or [])
    pick = [i for i in rep["items"] if (i["path"] in want) or (i["category"] in cats and (include_kept or not i.get("kept")))]
    if not pick:
        return {"moved": 0, "size": 0, "dest": None, "items": []}
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = TIDY_DIR / stamp
    moved, size = [], 0
    for it in pick:
        src = _safe_target(it["path"])
        if not src.exists():
            continue
        if it["path"] == "out/.studio/server.log":  # 로그는 비운다(열려 있을 수 있음)
            try:
                src.write_text("", encoding="utf-8")
                moved.append(it["path"]); size += it["size"]
            except OSError:
                pass
            continue
        tgt = dest / it["path"]
        tgt.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(src), str(tgt))
        except OSError as e:
            moved.append(f"{it['path']} (실패: {e})"); continue
        moved.append(it["path"]); size += it["size"]
        if it["category"] == "image" and src.suffix.lower() == ".png":  # mermaid 짝 .mmd
            mmd = src.with_suffix(".mmd")
            if mmd.is_file():
                tg2 = dest / _rel(mmd); tg2.parent.mkdir(parents=True, exist_ok=True); shutil.move(str(mmd), str(tg2))
    return {"moved": len(moved), "size": size, "dest": _rel(dest) if moved else None, "items": moved}


def purge():
    """out/.tidy/ 비우기(되돌릴 수 없음)."""
    n = _size(TIDY_DIR) if TIDY_DIR.is_dir() else 0
    if TIDY_DIR.is_dir():
        shutil.rmtree(TIDY_DIR, ignore_errors=True)
    return {"purged": n}


def restore(stamp):
    """out/.tidy/<stamp>/ 의 파일을 원래 자리로."""
    d = TIDY_DIR / stamp
    if not d.is_dir():
        raise ValueError(f"없는 정리 기록: {stamp}")
    n = 0
    for f in sorted(d.rglob("*")):
        if f.is_file():
            rel = f.relative_to(d)
            tgt = WORKSPACE / rel
            tgt.parent.mkdir(parents=True, exist_ok=True)
            if not tgt.exists():
                shutil.move(str(f), str(tgt)); n += 1
    shutil.rmtree(d, ignore_errors=True)
    return {"restored": n}


ARCHIVE_SKIP = ("out", "decks/.history", "decks/.trash", ".env", "nexa-slide.local.json", ".git")  # 기본 제외(.gitignore 와 같은 기준 + .git)


def archive(include_all=False, out=None):
    """작업 공간을 zip 으로. 기본은 산출물·백업·휴지통·PC 전용 설정·.git 제외(요청 첨부 out/attach 는 넣는다). include_all 이면 .git 만 빼고 전부."""
    from paths import projects_root
    ws = WORKSPACE.resolve()
    root = ws.parent if (ws.parent / ".nexa-slide.json").is_file() else ws  # 저장소 루트 표식이 있으면 루트째
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M")
    name = (CONFIG.get("title") or ws.name or "workspace")
    name = re.sub(r"[^\w가-힣.-]+", "-", str(name)).strip("-") or "workspace"
    zpath = Path(out).expanduser().resolve() if out else (projects_root() / "_archive" / f"{name}-{stamp}.zip")
    zpath.parent.mkdir(parents=True, exist_ok=True)
    skip = [] if include_all else [str((ws / s).resolve()) for s in ARCHIVE_SKIP]
    skip.append(str((ws / ".git").resolve())); skip.append(str((root / ".git").resolve()))
    skip.append(str((OUT / ".tidy").resolve()))
    n = size = 0
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(root.rglob("*")):
            fp = str(f.resolve())
            if any(fp == s or fp.startswith(s + os.sep) for s in skip):
                continue
            if f.is_file():
                if include_all and f.resolve().parent == STATE.resolve() and f.name in STATE_KEEP:
                    continue  # 실행 중 상태 파일은 보관하지 않는다
                z.write(f, str(f.relative_to(root.parent)).replace("\\", "/"))
                n += 1; size += f.stat().st_size
    return {"zip": str(zpath), "files": n, "size": size, "zipSize": zpath.stat().st_size, "root": str(root), "excluded": [] if include_all else list(ARCHIVE_SKIP)}


def fmt_size(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024 or u == "GB":
            return f"{n:.0f}{u}" if u == "B" else f"{n:.1f}{u}"
        n /= 1024
    return f"{n:.1f}GB"


def main():
    ap = argparse.ArgumentParser(description="작업 공간 정리·보관")
    ap.add_argument("cmd", nargs="?", default="scan", choices=["scan", "clean", "purge", "restore", "archive"])
    ap.add_argument("--apply", action="store_true", help="scan 대신 clean(지운다)")
    ap.add_argument("--only", default="output,attach,log", help="정리 범주(쉼표) - output,backup,image,attach,log")
    ap.add_argument("--include-kept", action="store_true", help="백업·휴지통이 참조하는 그림도 지운다")
    ap.add_argument("--purge", action="store_true", help="out/.tidy/ 비우기")
    ap.add_argument("--stamp", help="restore 할 정리 기록")
    ap.add_argument("--all", action="store_true", help="archive: 산출물·백업까지 전부")
    ap.add_argument("--out", help="archive: zip 경로")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.purge:
        a.cmd = "purge"
    elif a.apply and a.cmd == "scan":
        a.cmd = "clean"
    if a.cmd == "scan":
        r = scan()
        if a.json:
            print(json.dumps(r, ensure_ascii=False, indent=1)); return
        print(f"작업 공간 {r['workspace']} - 정리 대상 {len(r['items'])}개 · {fmt_size(r['total'])}")
        for c in CATEGORIES:
            s = r["summary"][c]
            if s["count"]:
                print(f"  [{c}] {CAT_KO[c]}: {s['count']}개 · {fmt_size(s['size'])}")
        for it in r["items"]:
            print(f"    {it['category']:7s} {fmt_size(it['size']):>8s}  {it['path']}  - {it['reason']}")
        if r["tidy"]["count"]:
            print(f"  out/.tidy/ 에 옮겨 둔 정리 기록 {r['tidy']['count']}개 · {fmt_size(r['tidy']['size'])} (--purge 로 비움, restore --stamp 로 되돌림)")
        print("지우려면: nexa.py tidy --apply [--only output,attach,log,image,backup]")
    elif a.cmd == "clean":
        r = clean([c.strip() for c in a.only.split(",") if c.strip()], include_kept=a.include_kept)
        print(json.dumps(r, ensure_ascii=False, indent=1) if a.json else f"옮김 {r['moved']}개 · {fmt_size(r['size'])} → {r['dest'] or '(없음)'}")
    elif a.cmd == "purge":
        r = purge(); print(f"비움 {fmt_size(r['purged'])}")
    elif a.cmd == "restore":
        r = restore(a.stamp); print(f"되돌림 {r['restored']}개")
    elif a.cmd == "archive":
        r = archive(a.all, a.out)
        print(json.dumps(r, ensure_ascii=False, indent=1) if a.json else f"보관: {r['zip']} ({r['files']}개 · {fmt_size(r['size'])} → {fmt_size(r['zipSize'])})" + ("" if a.all else f"\n제외: {', '.join(r['excluded'])} (전부 넣으려면 --all)"))


if __name__ == "__main__":
    main()
