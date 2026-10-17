# -*- coding: utf-8 -*-
"""엔진 요청 검증 ④ - 등록된 모든 작업 공간의 덱을 사본에서 변경 전(기준 커밋) 엔진과 지금 트리 엔진으로 각각 PPTX 로 내보내 XML 이 같은지 본다.

    python3 studio/engine_regress.py [--base main] [--ws <작업 공간>…] [--no-example] [--allow <덱>[:<장>]…]
                                     [--max-seconds 600] [--deck-seconds 120] [--json] [--keep] [--scratch <폴더>]

- 작업 공간 목록: --ws 가 없으면 사용자 설정 settings.json 의 recent 중 nexa-slide.json 이 있는 곳 + 엔진 example(--no-example 로 뺀다).
- 기준(before): --base 의 git 리비전(기본 main = 운영에 적용된 엔진). `git archive <base> studio` 를 사용자 설정 폴더 hub/engine/scratch/engine-<해시>/ 에 풀어 쓴다(같은 해시면 재사용).
  after = 이 스크립트가 있는 트리의 studio/.
- 사본: hub/engine/scratch/regress-<시각>/<n>-<이름>/ 에 작업 공간을 복사한다(out·.history·.studio·fonts·.git 제외). 원본에는 아무것도 쓰지 않는다.
  assetRoot·content·decks 가 작업 공간 밖을 가리키면 사본의 nexa-slide.local.json 에 원래 절대 경로를 적어 그대로 읽게 한다(읽기만 한다).
- 비교: PPTX zip 의 모든 항목. docProps/core.xml(시각)은 제외, XML·rels 는 정규화(canonicalize) 뒤 비교, ppt/presentation.xml 의 구역 id({UUID})는 순번으로 치환, 그 밖(미디어 등)은 바이트.
  차이는 슬라이드별로(slideN.xml·그 rels·notesSlideN.xml → 장 N), 나머지 부품은 "other" 로 묶는다.
- 판정: --allow <덱> 또는 <덱>:<장> 으로 표시한 차이는 expected(기능 추가로 의도한 변경), 아니면 unexpected.
  종료 코드 0 = 모두 동일(또는 전부 expected) · 1 = unexpected 차이 · 2 = 오류·시간 초과(판정 불가 - 조용히 통과하지 않는다).
- 시간: 덱 하나의 내보내기마다 --deck-seconds, 전체 --max-seconds. 넘으면 남은 덱은 skipped 로 보고하고 종료 코드 2.
"""
import argparse
import datetime as dt
import difflib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

STUDIO = Path(__file__).resolve().parent
ENGINE = STUDIO.parent
sys.path.insert(0, str(STUDIO))
from paths import load_settings, load_ws_config, user_dir  # noqa: E402

CONFIG_NAME = "nexa-slide.json"
LOCAL_NAME = "nexa-slide.local.json"
SKIP_COPY = {"out", ".history", ".studio", "fonts", ".git", "node_modules", "__pycache__", ".claude", ".codex"}
SKIP_PARTS = {"docProps/core.xml"}  # 만든/고친 시각 - 같은 엔진으로 두 번 내보내도 다르다
RX_SLIDE = re.compile(r"^ppt/slides/(?:_rels/)?slide(\d+)\.xml(?:\.rels)?$")
RX_NOTES = re.compile(r"^ppt/notesSlides/(?:_rels/)?notesSlide(\d+)\.xml(?:\.rels)?$")
RX_UUID = re.compile(r"\{[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\}")


def log(msg):
    print(msg, flush=True)


def rmtree(path):
    """사본 삭제 - Windows 는 방금 끝난 하위 프로세스의 cwd 였던 폴더가 잠깐 잠겨 있을 수 있어 몇 번 다시 시도하고, 읽기 전용은 풀고 지운다."""
    def onerr(fn, p, exc):
        try:
            os.chmod(p, 0o700)
            fn(p)
        except OSError:
            pass
    for i in range(4):
        shutil.rmtree(path, onerror=onerr)
        if not Path(path).exists():
            return True
        time.sleep(0.3 * (i + 1))
    return not Path(path).exists()


# ---------- 기준 엔진 ----------
def base_engine(rev, scratch_root):
    """<base> 리비전의 studio/ 를 scratch_root/engine-<해시>/ 에 풀고 그 엔진 루트를 돌려준다(이미 있으면 재사용)."""
    r = subprocess.run(["git", "rev-parse", "--short", rev], cwd=str(ENGINE), capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0 or not r.stdout.strip():
        raise RuntimeError(f"기준 리비전을 찾지 못했다: {rev} - {r.stderr.strip()[:200]}")
    short = r.stdout.strip()
    root = scratch_root / f"engine-{short}"
    if (root / "studio" / "export_pptx.py").is_file():
        return root, short
    tmp = scratch_root / f"engine-{short}.zip"
    scratch_root.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["git", "archive", "--format=zip", "-o", str(tmp), rev, "studio"], cwd=str(ENGINE), capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"git archive 실패: {r.stderr.strip()[:200]}")
    if root.exists():
        rmtree(root)
    with zipfile.ZipFile(tmp) as z:
        z.extractall(root)
    tmp.unlink(missing_ok=True)
    return root, short


# ---------- 작업 공간 목록·사본 ----------
def registered_workspaces(include_example=True):
    out, seen = [], set()
    for row in load_settings().get("recent", []) or []:
        p = row.get("path") if isinstance(row, dict) else None
        if not p:
            continue
        try:
            key = str(Path(p).resolve()).lower()
        except OSError:
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(Path(p))
    if include_example:
        out.append(ENGINE / "example")
    return out


def _outside(ws, target):
    try:
        return not Path(target).resolve().is_relative_to(ws.resolve())
    except (OSError, ValueError):
        return True


def copy_workspace(ws, dst):
    """작업 공간 사본. 밖을 가리키는 assetRoot·content·decks 는 사본 local 설정에 절대 경로로 적는다. 사본의 덱 폴더와 덱 id 목록을 돌려준다."""
    shutil.copytree(ws, dst, ignore=lambda d, names: [n for n in names if n in SKIP_COPY], symlinks=False)
    cfg = load_ws_config(ws)
    over = {}
    for key, default in (("assetRoot", "."), ("content", "content"), ("decks", "decks")):
        target = ws / cfg.get(key, default)
        if _outside(ws, target):
            over[key] = str(target.resolve())
    if over:
        loc = dst / LOCAL_NAME
        try:
            cur = json.loads(loc.read_text(encoding="utf-8")) if loc.is_file() else {}
            cur = cur if isinstance(cur, dict) else {}
        except ValueError:
            cur = {}
        cur.update(over)
        loc.write_text(json.dumps(cur, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    decks_dir = Path(over.get("decks") or dst / cfg.get("decks", "decks"))
    ids = sorted(f.stem for f in decks_dir.glob("*.json") if not f.name.endswith(".requests.json")) if decks_dir.is_dir() else []
    return ids


# ---------- 내보내기·비교 ----------
def export(engine_root, ws_copy, deck, out, seconds):
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    env.pop("NEXA_SLIDE_WORKSPACE", None)
    cmd = [sys.executable, str(engine_root / "studio" / "export_pptx.py"), deck, "--workspace", str(ws_copy), "--out", str(out)]
    try:
        r = subprocess.run(cmd, cwd=str(ws_copy), env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=seconds)
    except subprocess.TimeoutExpired:
        return False, f"시간 초과({seconds}s)"
    if r.returncode != 0 or not out.is_file():
        tail = (r.stderr.strip() or r.stdout.strip()).splitlines()[-3:]
        return False, f"종료 {r.returncode}: " + " / ".join(tail)[:400]
    return True, ""


def normalize(name, data):
    """비교용 문자열 - XML·rels 는 정규화, presentation.xml 의 구역 id 는 순번으로. 그 밖은 bytes 그대로."""
    if not (name.endswith(".xml") or name.endswith(".rels")):
        return data
    try:
        txt = ET.canonicalize(xml_data=data.decode("utf-8"), strip_text=False)
    except (ET.ParseError, UnicodeDecodeError):
        txt = data.decode("utf-8", "replace")
    if name == "ppt/presentation.xml":
        seen = {}
        txt = RX_UUID.sub(lambda m: seen.setdefault(m.group(0), "{UUID-%d}" % (len(seen) + 1)), txt)
    return txt


def compare(a_path, b_path):
    """두 PPTX 의 차이 → {slide(int|'other'|'parts'): [{"part", "lines"}]}."""
    out = {}
    with zipfile.ZipFile(a_path) as za, zipfile.ZipFile(b_path) as zb:
        na, nb = set(za.namelist()), set(zb.namelist())
        for name in sorted(na | nb):
            if name in SKIP_PARTS:
                continue
            if name not in na or name not in nb:
                out.setdefault(_slot(name), []).append({"part": name, "lines": ["항목이 한쪽에만 있다: " + ("after" if name in nb else "before")]})
                continue
            da, db = za.read(name), zb.read(name)
            if da == db:
                continue
            ta, tb = normalize(name, da), normalize(name, db)
            if ta == tb:
                continue
            if isinstance(ta, str):
                diff = [ln.rstrip() for ln in difflib.unified_diff(ta.split("><"), tb.split("><"), "before", "after", n=0, lineterm="")]
                lines = [ln[:160] for ln in diff[2:8]]
            else:
                lines = [f"bytes {len(ta)} → {len(tb)}"]
            out.setdefault(_slot(name), []).append({"part": name, "lines": lines})
    return out


def _slot(name):
    m = RX_SLIDE.match(name) or RX_NOTES.match(name)
    return int(m.group(1)) if m else "other"


def parse_allow(items):
    """--allow 덱 / 덱:장 → {덱: None(전체) | {장…}}"""
    allow = {}
    for it in items or []:
        deck, _, slide = str(it).partition(":")
        if not slide:
            allow[deck] = None
        elif allow.get(deck, set()) is not None:
            allow.setdefault(deck, set()).add(int(slide))
    return allow


def allowed(allow, deck, slot):
    a = allow.get(deck, "none")
    if a == "none":
        return False
    if a is None:
        return True
    return isinstance(slot, int) and slot in a


# ---------- 실행 ----------
def run(a):
    t0 = time.time()
    scratch_root = Path(a.scratch) if a.scratch else user_dir() / "hub" / "engine" / "scratch"
    result = {"base": a.base, "baseCommit": None, "started": dt.datetime.now().isoformat(timespec="seconds"), "workspaces": [], "errors": [],
              "counts": {"workspaces": 0, "decks": 0, "slides": 0, "same": 0, "expected": 0, "unexpected": 0, "failed": 0, "skipped": 0}}
    try:
        base_root, short = base_engine(a.base, scratch_root)
    except RuntimeError as e:
        result["errors"].append(str(e))
        return result, 2
    result["baseCommit"] = short
    allow = parse_allow(a.allow)
    run_dir = scratch_root / ("regress-" + dt.datetime.now().strftime("%Y%m%d-%H%M%S"))
    run_dir.mkdir(parents=True, exist_ok=True)
    result["scratch"] = str(run_dir)
    wss = [Path(w) for w in a.ws] if a.ws else registered_workspaces(not a.no_example)
    code = 0
    try:
        for i, ws in enumerate(wss, 1):
            row = {"path": str(ws), "title": ws.name, "decks": [], "status": "ok"}
            result["workspaces"].append(row)
            if not (ws / CONFIG_NAME).is_file():
                row["status"] = "skipped"; row["reason"] = "작업 공간이 아니거나 없다(nexa-slide.json 없음)"
                continue
            row["title"] = load_ws_config(ws).get("title", ws.name)
            dst = run_dir / f"{i}-{re.sub(r'[^A-Za-z0-9_.-]+', '_', ws.name)[:40]}"
            try:
                ids = copy_workspace(ws, dst)
            except OSError as e:
                row["status"] = "failed"; row["reason"] = f"복사 실패: {e}"
                result["counts"]["failed"] += 1
                code = 2
                continue
            result["counts"]["workspaces"] += 1
            for deck in ids:
                d = {"deck": deck, "status": "same", "slides": {}, "other": []}
                row["decks"].append(d)
                result["counts"]["decks"] += 1
                if time.time() - t0 > a.max_seconds:
                    d["status"] = "skipped"; d["reason"] = f"전체 시간 한도({a.max_seconds}s)"
                    result["counts"]["skipped"] += 1
                    code = 2
                    continue
                pa, pb = dst / f"_regress-{deck}-before.pptx", dst / f"_regress-{deck}-after.pptx"
                ok1, why1 = export(base_root, dst, deck, pa, a.deck_seconds)
                ok2, why2 = export(ENGINE, dst, deck, pb, a.deck_seconds)
                if not (ok1 and ok2):
                    d["status"] = "failed"; d["reason"] = ("before: " + why1 if not ok1 else "") + ((" · " if not ok1 and not ok2 else "") + ("after: " + why2 if not ok2 else ""))
                    result["counts"]["failed"] += 1
                    code = 2
                    continue
                with zipfile.ZipFile(pb) as z:
                    nslides = sum(1 for n in z.namelist() if RX_SLIDE.match(n) and n.endswith(".xml"))
                result["counts"]["slides"] += nslides
                diffs = compare(pa, pb)
                if not diffs:
                    result["counts"]["same"] += 1
                    continue
                unexpected = False
                for slot, parts in sorted(diffs.items(), key=lambda kv: (isinstance(kv[0], str), kv[0])):
                    exp = allowed(allow, deck, slot)
                    entry = {"expected": exp, "parts": parts}
                    if isinstance(slot, int):
                        d["slides"][str(slot)] = entry
                    else:
                        d["other"].append(entry)
                    unexpected = unexpected or not exp
                d["status"] = "unexpected" if unexpected else "expected"
                result["counts"]["unexpected" if unexpected else "expected"] += 1
                if unexpected and code == 0:
                    code = 1
    finally:
        if a.keep:
            result["kept"] = True
        elif not rmtree(run_dir):
            result["errors"].append(f"사본을 다 지우지 못했다(손으로 지운다): {run_dir}")
    result["seconds"] = round(time.time() - t0, 1)
    return result, code


def summary(result, code):
    c = result["counts"]
    lines = [f"엔진 회귀(검증 ④) - 기준 {result['base']}({result.get('baseCommit') or '?'}) ↔ 지금 트리 · {result.get('seconds', 0)}초",
             f"작업 공간 {c['workspaces']} · 덱 {c['decks']} · 장 {c['slides']} → 동일 {c['same']} · 의도한 변경 {c['expected']} · 예상 밖 {c['unexpected']} · 실패 {c['failed']} · 건너뜀 {c['skipped']}"]
    for e in result["errors"]:
        lines.append(f"오류: {e}")
    for ws in result["workspaces"]:
        if ws["status"] != "ok":
            lines.append(f"- {ws['title']} ({ws['path']}): {ws['status']} - {ws.get('reason', '')}")
            continue
        for d in ws["decks"]:
            if d["status"] == "same":
                continue
            head = f"- {ws['title']} / {d['deck']}: {d['status']}" + (f" - {d.get('reason')}" if d.get("reason") else "")
            lines.append(head)
            for n, entry in sorted(d["slides"].items(), key=lambda kv: int(kv[0])):
                tag = "의도" if entry["expected"] else "예상 밖"
                lines.append(f"    장 {n} [{tag}] " + " · ".join(p["part"].rsplit("/", 1)[-1] for p in entry["parts"]))
                for p in entry["parts"][:1]:
                    for ln in p["lines"][:3]:
                        lines.append("      " + ln)
            for entry in d["other"]:
                tag = "의도" if entry["expected"] else "예상 밖"
                lines.append(f"    기타 부품 [{tag}] " + " · ".join(p["part"] for p in entry["parts"]))
    verdict = {0: "통과", 1: "예상 밖 차이 - 의도한 변경이면 --allow <덱>[:<장>] 으로 표시하고 reply 에 이유를 적는다", 2: "판정 불가(오류·시간 초과)"}[code]
    lines.append(f"결과: {verdict} (종료 코드 {code})")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="엔진 요청 검증 ④ - 등록된 작업 공간 덱의 PPTX XML 전후 비교")
    ap.add_argument("--base", default="main", help="기준 엔진의 git 리비전(기본 main)")
    ap.add_argument("--ws", action="append", help="작업 공간 폴더(여러 번) - 없으면 settings.json recent + example")
    ap.add_argument("--no-example", action="store_true", help="엔진 example 작업 공간을 빼다")
    ap.add_argument("--allow", action="append", help="의도한 변경: <덱> 또는 <덱>:<장>(여러 번)")
    ap.add_argument("--max-seconds", type=float, default=600)
    ap.add_argument("--deck-seconds", type=float, default=120)
    ap.add_argument("--json", action="store_true", help="결과를 JSON 으로")
    ap.add_argument("--keep", action="store_true", help="사본·내보낸 PPTX 를 지우지 않는다")
    ap.add_argument("--scratch", help="사본 자리(기본 사용자 설정 폴더 hub/engine/scratch)")
    a = ap.parse_args()
    result, code = run(a)
    if a.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
    else:
        print(summary(result, code))
    sys.exit(code)


if __name__ == "__main__":
    main()
