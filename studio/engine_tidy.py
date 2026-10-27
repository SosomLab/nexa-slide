# -*- coding: utf-8 -*-
"""엔진 개발 영역 정리 - 엔진 요청·세션·배포·회귀 확인이 남기는 임시·불필요 파일(작업 공간 정리 tidy.py 의 엔진 쪽 짝).

    python3 studio/engine_tidy.py                       # 정리 대상 보고(지우지 않음)
    python3 studio/engine_tidy.py --apply [--only attach,scratch]   # 지운다(다시 생기거나 기록뿐인 것이라 옮겨 두지 않고 바로 지운다)

정리 대상(category) - 모두 사용자 설정 폴더 hub/engine/ 와 엔진 <엔진>/.claude/worktrees/ 안:
    attach    큐에 없는 요청의 attach/<id>/, 하루 넘게 요청에 붙지 않은 attach/_new/ 파일(engine_requests.tidy_scan)
    copy      엔진 worktree 의 .nexa/attach/<id>/ 중 끝난(done·applied·rejected)·없는 요청의 사본 - 세션에 보낼 때마다 다시 복사한다
    scratch   회귀 확인 사본 scratch/regress-*(--keep·지우기 실패로 남은 것)·풀다 남은 engine-*.zip, 쓰다 남은 *.tmp - 한 시간 지난 것만
    log       엔진 세션 턴 로그 .studio/sessions/<시각>/(최근 SESSION_KEEP 개 제외)·배포 로그 deploy-logs/*.log(최근 DEPLOY_LOG_KEEP 개 제외)
    worktree  배포가 죽어 남은 시험용 worktree(.claude/worktrees/deploy-*) - 배포 중이 아닐 때만
큐(requests.json)·배포 기록(deploy.json)·시험 시간·기준 엔진 사본(scratch/engine-<해시>, engine_regress 가 3개로 줄인다)·.nexa/outbox(반영 전 status)는 손대지 않는다.
허브 API(관리자): GET /api/engine/tidy → 보고, POST /api/engine/tidy {action: clean, categories: […]}. 시작 페이지 서버 요청 카드의 🧹."""
import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_requests  # noqa: E402
from paths import ENGINE  # noqa: E402

ENGINE_DIR = engine_requests.ENGINE_DIR
WORKTREES = ENGINE / ".claude" / "worktrees"
WORKTREE = WORKTREES / "engine-dev"
SCRATCH = ENGINE_DIR / "scratch"
SESSIONS = ENGINE_DIR / ".studio" / "sessions"
DEPLOY_LOGS = ENGINE_DIR / "deploy-logs"
DEPLOY_STATE = ENGINE_DIR / "deploy.json"
CATEGORIES = ("attach", "copy", "scratch", "log", "worktree")
CAT_KO = {"attach": "고아 첨부", "copy": "worktree 첨부 사본", "scratch": "회귀 확인 사본·임시 파일", "log": "오래된 세션·배포 로그", "worktree": "남은 시험용 worktree"}
DEFAULTS = ("attach", "copy", "scratch", "worktree")  # 로그는 문제를 되짚을 때 쓰므로 기본으로 고르지 않는다
SESSION_KEEP = 10
DEPLOY_LOG_KEEP = 20
STALE_SECONDS = 3600  # 이보다 새것은 쓰는 중일 수 있어 건너뛴다


def _size(p):
    p = Path(p)
    try:
        if p.is_file():
            return p.stat().st_size
        return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
    except OSError:
        return 0


def _old(p):
    try:
        return time.time() - Path(p).stat().st_mtime > STALE_SECONDS
    except OSError:
        return False


def _item(p, cat, why):
    p = Path(p)
    return {"path": str(p), "category": cat, "reason": why, "size": _size(p), "dir": p.is_dir()}


def _deploying():
    """배포가 도는 중인가 - deploy.json 이 running 이고 그 프로세스가 살아 있으면."""
    try:
        d = json.loads(DEPLOY_STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return d.get("state") == "running" and (not d.get("pid") or engine_requests.pid_alive(d["pid"]))


def scan():
    """정리 대상 보고 {items, summary: {category: {count, size}}, categories, defaults, total, deploying}. path 는 절대 경로."""
    items = []
    # 1. 큐의 첨부
    for it in engine_requests.tidy_scan()["items"]:
        items.append(_item(ENGINE_DIR / it["path"], "attach", it["reason"]))
    # 2. worktree 의 첨부 사본 - 세션이 아직 볼 수 있는 요청(triage·open·working)의 것은 둔다
    live = {str(x.get("id")) for x in engine_requests.load() if x.get("status") in ("triage", "open", "working")}
    copies = WORKTREE / ".nexa" / "attach"
    if copies.is_dir():
        for d in sorted(copies.iterdir()):
            if d.is_dir() and d.name not in live:
                items.append(_item(d, "copy", f"끝났거나 없는 요청 #{d.name} 의 첨부 사본"))
    # 3. 회귀 확인 사본·임시 파일
    if SCRATCH.is_dir():
        for p in sorted(SCRATCH.iterdir()):
            if p.is_dir() and p.name.startswith("regress-") and _old(p):
                items.append(_item(p, "scratch", "회귀 확인 사본(--keep 또는 지우기 실패로 남음)"))
            elif p.is_file() and p.name.startswith("engine-") and p.suffix == ".zip" and _old(p):
                items.append(_item(p, "scratch", "기준 엔진을 풀다 남은 압축 파일"))
    if ENGINE_DIR.is_dir():
        for p in sorted(ENGINE_DIR.glob("*.tmp")):
            if p.is_file() and _old(p):
                items.append(_item(p, "scratch", "쓰다 남은 임시 파일(원자적 쓰기 중 끊김)"))
    deploying = _deploying()
    # 4. 로그 - 최근 것은 남긴다
    if SESSIONS.is_dir():
        dirs = sorted((p for p in SESSIONS.iterdir() if p.is_dir()), key=lambda p: p.name, reverse=True)
        for p in dirs[SESSION_KEEP:]:
            if _old(p):
                items.append(_item(p, "log", f"엔진 세션 턴 로그(최근 {SESSION_KEEP}개 밖)"))
    if DEPLOY_LOGS.is_dir() and not deploying:
        logs = sorted(DEPLOY_LOGS.glob("*.log"), key=lambda p: p.name, reverse=True)
        for p in logs[DEPLOY_LOG_KEEP:]:
            items.append(_item(p, "log", f"배포 로그(최근 {DEPLOY_LOG_KEEP}개 밖)"))
    # 5. 배포가 남긴 시험용 worktree
    if WORKTREES.is_dir() and not deploying:
        for p in sorted(WORKTREES.glob("deploy-*")):
            if p.is_dir():
                items.append(_item(p, "worktree", "배포 시험용 worktree(배포가 끊겨 남음) - 다음 배포도 다시 만든다"))
    summary = {c: {"count": 0, "size": 0} for c in CATEGORIES}
    for it in items:
        summary[it["category"]]["count"] += 1
        summary[it["category"]]["size"] += it["size"]
    return {"workspace": str(ENGINE_DIR), "items": items, "summary": summary, "categories": CAT_KO, "order": list(CATEGORIES),
            "defaults": list(DEFAULTS), "total": sum(i["size"] for i in items), "deploying": deploying}


def _remove_worktree(p):
    subprocess.run(["git", "worktree", "remove", "--force", str(p)], cwd=str(ENGINE), capture_output=True, timeout=120)
    if p.exists():
        shutil.rmtree(p, ignore_errors=True)
    subprocess.run(["git", "worktree", "prune"], cwd=str(ENGINE), capture_output=True, timeout=60)


def clean(categories=None):
    """scan 이 보고한 것 중 고른 범주를 지운다 → {moved, size, items, report}(moved 는 작업 공간 정리 화면과 같은 이름)."""
    cats = set(categories or DEFAULTS)
    roots = [ENGINE_DIR.resolve(), WORKTREES.resolve()]
    done, size = [], 0
    for it in scan()["items"]:
        if it["category"] not in cats:
            continue
        p = Path(it["path"])
        if not any(r in p.resolve().parents for r in roots):  # 보고에서 온 경로지만 한 번 더 - 엔진 영역 밖은 지우지 않는다
            continue
        try:
            if it["category"] == "worktree":
                _remove_worktree(p)
            elif p.is_dir():
                shutil.rmtree(p)
            elif p.is_file():
                p.unlink()
        except (OSError, subprocess.SubprocessError) as e:
            done.append(f"{it['path']} (실패: {e})")
            continue
        done.append(it["path"]); size += it["size"]
    return {"moved": len(done), "size": size, "dest": None, "items": done, "report": scan()}


def main():
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(description="엔진 개발 영역 정리")
    ap.add_argument("--apply", action="store_true", help="보고 대신 지운다")
    ap.add_argument("--only", default=",".join(DEFAULTS), help=f"정리 범주(쉼표) - {','.join(CATEGORIES)}")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.apply:
        r = clean([c.strip() for c in a.only.split(",") if c.strip()])
        r.pop("report", None)
        print(json.dumps(r, ensure_ascii=False, indent=1) if a.json else f"지움 {r['moved']}개 · {_fmt(r['size'])}")
        return
    r = scan()
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1)); return
    print(f"엔진 영역 {r['workspace']} - 정리 대상 {len(r['items'])}개 · {_fmt(r['total'])}" + (" (배포 중 - 로그·worktree 는 건너뜀)" if r["deploying"] else ""))
    for c in CATEGORIES:
        s = r["summary"][c]
        if s["count"]:
            print(f"  [{c}] {CAT_KO[c]}: {s['count']}개 · {_fmt(s['size'])}")
    for it in r["items"]:
        print(f"    {it['category']:8s} {_fmt(it['size']):>8s}  {it['path']}  - {it['reason']}")
    print(f"지우려면: engine_tidy.py --apply [--only {','.join(CATEGORIES)}]")


def _fmt(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024 or u == "GB":
            return f"{n:.0f}{u}" if u == "B" else f"{n:.1f}{u}"
        n /= 1024
    return f"{n:.1f}GB"


if __name__ == "__main__":
    main()
