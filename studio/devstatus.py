# -*- coding: utf-8 -*-
"""한 화면 보기 - 작업판 · 떠 있는 nexa-slide 프로세스 · 저장소(브랜치·worktree) · 시험 잠금 · 마지막 검증 요약(docs/dev/autodev.md · 전역 규칙 §4 ⑧).

    python studio/devstatus.py [--watch [초]] [--md]

- 작업판 = <공용 루트>/out/status/now.md(studio/devboard.py 가 쓴다 - 여기서는 다시 그려 보여 준다).
- 프로세스 = 명령줄에 이 저장소 경로나 nexa-slide 가 든 python·node·chrome·pwsh(PID · 이름 · 시작 · 작업 폴더 추정).
- 저장소 = worktree 마다 브랜치 · origin/main 대비 앞/뒤 · 미커밋 수.
- 시험 잠금 = studio/tests/testlock.py 의 잡은 쪽(pid · 명령 · 시작).
- 마지막 검증 = out/verify/ 의 가장 새 summary.md 표.
--watch 는 그 초(기본 10)마다 다시 그린다. --md 는 작업판(now.md)만.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

STUDIO = Path(__file__).resolve().parent
sys.path.insert(0, str(STUDIO))
import devboard  # noqa: E402

ROOT = devboard.common_root()


def sh(args, cwd=None, timeout=15):
    try:
        r = subprocess.run(args, cwd=str(cwd or ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return r.stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def procs():
    if os.name != "nt":
        out = sh(["ps", "-eo", "pid,lstart,args"])
        return [("", l.strip(), "", "") for l in out.splitlines() if "nexa" in l or str(ROOT) in l][:30]
    ps = (
        "$root = '" + str(ROOT).replace("'", "''") + "'; "
        "Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $PID -and $_.Name -match '^(python|pythonw|node|chrome|pwsh|powershell|claude)(\\.exe)?$' -and ([string]$_.CommandLine -like \"*$root*\" -or [string]$_.CommandLine -match 'nexa-slide|nexa\\.py|server\\.py|run_all|smoke\\.js') } | "
        "ForEach-Object { $c = [string]$_.CommandLine; \"{0}`t{1}`t{2}`t{3}\" -f $_.ProcessId, $_.Name, $_.CreationDate.ToString('MM-dd HH:mm:ss'), ($c.Substring(0, [Math]::Min(150, $c.Length)) -replace \"`t\", ' ') }"
    )
    out = sh(["powershell", "-NoProfile", "-Command", ps], timeout=30)
    rows = []
    for line in out.splitlines():
        c = line.split("\t")
        if len(c) == 4:
            where = next((p for p in (".claude/worktrees/", ".claude\\worktrees\\") if p in c[3]), None)
            tree = c[3].split(where, 1)[1].replace("\\", "/").split("/")[0] if where else ("main 트리" if str(ROOT).lower() in c[3].lower() else "-")
            rows.append((c[0], c[1], c[2], tree, c[3]))
    return rows


def repo():
    rows = []
    out = sh(["git", "worktree", "list", "--porcelain"])
    cur = {}
    for line in out.splitlines() + [""]:
        if not line.strip():
            if cur.get("worktree"):
                rows.append(cur)
            cur = {}
            continue
        k, _, v = line.partition(" ")
        cur[k] = v or True
    res = []
    for w in rows:
        p = Path(w["worktree"])
        br = str(w.get("branch", "")).replace("refs/heads/", "") or ("(detached)" if w.get("detached") else "?")
        ab = sh(["git", "rev-list", "--left-right", "--count", "HEAD...origin/main"], cwd=p).split()
        dirty = len([l for l in sh(["git", "status", "--short"], cwd=p).splitlines() if l.strip()])
        name = "main 트리" if p.resolve() == ROOT.resolve() else p.name
        res.append((name, br, f"+{ab[0]} / -{ab[1]}" if len(ab) == 2 else "?", dirty))
    return res


def lock():
    try:
        sys.path.insert(0, str(STUDIO / "tests"))
        import testlock_info  # noqa: F401
    except ImportError:
        pass
    import tempfile
    info = Path(tempfile.gettempdir()) / "nexa-slide-tests.lock.json"
    try:
        d = json.loads(info.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "없음"
    pid = d.get("pid")
    alive = False
    if pid:
        if os.name == "nt":
            alive = str(pid) in sh(["tasklist", "/FI", f"PID eq {pid}", "/NH"])
        else:
            try:
                os.kill(int(pid), 0); alive = True
            except OSError:
                alive = False
    if not alive:
        return "없음(마지막 기록의 프로세스는 끝남)"
    return f"잡음 - pid {pid} · {str(d.get('cmd', ''))[:100]} · {d.get('t', '')}"


def last_verify():
    root = ROOT / "out" / "verify"
    runs = sorted((p for p in root.glob("*/summary.md")), key=lambda p: p.stat().st_mtime) if root.is_dir() else []
    if not runs:
        return "(없음)"
    return runs[-1].read_text(encoding="utf-8").rstrip()


def show(md_only=False):
    p = devboard.render()
    text = [p.read_text(encoding="utf-8").rstrip()]
    if md_only:
        return "\n".join(text)
    text += ["", "## 프로세스(nexa-slide)", "", "| PID | 이름 | 시작 | 트리 | 명령 |", "|---|---|---|---|---|"]
    pr = procs()
    text += [f"| {a} | {b} | {c} | {d} | {e[:90]} |" for a, b, c, d, e in pr] or ["| (없음) | | | | |"]
    text += ["", "## 저장소", "", "| 트리 | 브랜치 | origin/main 대비 앞/뒤 | 미커밋 |", "|---|---|---|---|"]
    text += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in repo()]
    text += ["", f"## 시험 잠금: {lock()}", "", "## 마지막 검증", "", last_verify()]
    return "\n".join(text)


def main(argv):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    md = "--md" in argv
    if "--watch" in argv:
        i = argv.index("--watch")
        sec = float(argv[i + 1]) if i + 1 < len(argv) and argv[i + 1].replace(".", "").isdigit() else 10
        while True:
            os.system("cls" if os.name == "nt" else "clear")
            print(show(md), flush=True)
            time.sleep(sec)
    print(show(md))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
