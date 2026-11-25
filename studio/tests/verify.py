# -*- coding: utf-8 -*-
"""검증 진입점 - 무인 개발(docs/dev/autodev.md)이 읽는 것은 이 요약 하나다.

    python studio/tests/verify.py --level quick|full [--fail-fast]

- 단계는 싼 것부터, 실패해도 끝까지 간다(--fail-fast 면 첫 실패에서 멈춤).
    quick = pycompile(바뀐 .py, 경고도 실패) · nodecheck(바뀐 .js) · parity(check_parity -W example) · runall-quick(브라우저 없이 도는 빠른 묶음)
    full  = pycompile · nodecheck · parity · runall(기본 묶음 전체 - 빠른 묶음 포함) · regress(engine_regress - 등록된 작업 공간 덱의 PPTX XML 이 main 과 같은가)
- 결과 넷: PASS · FAIL · SKIP(판정 불가 - 통과가 아니다, 이유를 메모에) · TIMEOUT(상한 초과 → 그 단계의 프로세스 트리만 끈다).
  상한 = 이력 중앙값(최근 3회) × 3(최소 120초 · 최대 3600초), 이력이 없으면 단계별 기본값. testlock 을 기다린 시간('== 대기' 줄)은 상한에서 뺀다.
- 출력: <공용 루트>/out/verify/<시각>/summary.md(단계가 끝날 때마다 덧붙임 · FAIL/TIMEOUT 아래 첫 오류 5줄) · <단계>.log · out/verify/history.tsv.
  표준 출력에는 요약 표만. 종료 코드 = 실패 단계 수(FAIL + TIMEOUT). 진행은 작업판(studio/devboard.py → out/status/now.md)에.
- 시험용: 환경 변수 NEXA_VERIFY_INJECT="parity=fail,pycompile=sleep:30" - 그 단계를 일부러 실패시키거나 늦춘다(verify 자체 점검, 체크리스트 5).
  NEXA_VERIFY_LIMIT="pycompile=5" - 그 단계 상한(초)을 바꾼다.
"""
import argparse
import datetime as dt
import os
import re
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIO = HERE.parent
TREE = STUDIO.parent
sys.path.insert(0, str(STUDIO))
import devboard  # noqa: E402

# 브라우저 없이 도는 빠른 묶음(run_all.py TESTS 이름) - 지난 실행 합계 약 40초
QUICK = ["i18n", "codex", "reqcli", "tidy", "enginetidy", "deck", "merge", "mergesave", "ops", "sim", "tmpfiles", "ledger", "struct",
         "sheetcalc", "vba", "textmodel", "pagedoc", "pagerender", "pagedocx", "pagetpl", "pagemerge", "pagemergejs", "pagediff", "pageimport", "tplrec", "pptstart", "vbasafe", "pyshim", "sheetfont", "sheetrt", "runs", "effect", "tableobj", "chart", "docstruct"]
DEFAULT_LIMIT = {"pycompile": 120, "nodecheck": 120, "parity": 300, "runall-quick": 900, "runall": 2700, "regress": 900}
RC_SKIP = 99  # 단계가 "판정 불가"를 알리는 종료 코드
ERR = re.compile(r"(FAIL|Error|Traceback|실패|오류|SyntaxWarning|error)", re.I)


def sh(args, **kw):
    return subprocess.run(args, cwd=str(TREE), capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)


def commit():
    r = sh(["git", "rev-parse", "--short", "HEAD"])
    d = sh(["git", "status", "--short"])
    return (r.stdout.strip() or "?") + (" +미커밋" if d.stdout.strip() else "")


def changed(ext):
    """origin/main 과 갈라진 뒤 바뀐 파일 + 작업 트리의 미커밋 변경 - 지금 있는 것만."""
    base = sh(["git", "merge-base", "HEAD", "origin/main"]).stdout.strip()
    names = set()
    if base:
        names |= set(sh(["git", "diff", "--name-only", base, "HEAD"]).stdout.split())
    names |= set(sh(["git", "diff", "--name-only", "HEAD"]).stdout.split())
    names |= set(sh(["git", "ls-files", "--others", "--exclude-standard"]).stdout.split())
    return sorted(n for n in names if n.endswith(ext) and (TREE / n).is_file())


def inject():
    out = {}
    for part in (os.environ.get("NEXA_VERIFY_INJECT") or "").split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def limits_env():
    out = {}
    for part in (os.environ.get("NEXA_VERIFY_LIMIT") or "").split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            try:
                out[k.strip()] = float(v)
            except ValueError:
                pass
    return out


class History:
    def __init__(self, path):
        self.path = path
        self.rows = []
        if path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines()[1:]:
                c = line.split("\t")
                if len(c) >= 5:
                    self.rows.append(c)

    def median(self, level, step):
        """그 단계의 최근 3회(통과·실패만 - SKIP·TIMEOUT 은 소요가 의미 없다) 소요 중앙값. 수준이 달라도 같은 단계면 쓴다."""
        xs = [float(c[2]) for c in self.rows if c[1] == step and c[3] in ("PASS", "FAIL")][-3:]
        return statistics.median(xs) if xs else None

    def add(self, level, step, sec, result):
        new = not self.path.is_file()
        with open(self.path, "a", encoding="utf-8", newline="\n") as f:
            if new:
                f.write("level\tstep\tsec\tresult\tdate\n")
            f.write(f"{level}\t{step}\t{sec:.1f}\t{result}\t{dt.datetime.now().isoformat(timespec='seconds')}\n")


def kill_tree(pid):
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)
    else:
        import signal
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except OSError:
            pass


def run_step(name, argv, log, limit, on_beat):
    """자식을 띄워 로그에 받는다 → (rc 또는 'TIMEOUT', 소요, 기다린 초). testlock '== 대기' 줄이 마지막 줄인 동안은 상한 시간에 넣지 않는다."""
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    kw = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    t0 = time.time()
    with open(log, "w", encoding="utf-8", newline="\n") as lf:
        p = subprocess.Popen(argv, cwd=str(TREE), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, **kw)
        st = {"waiting": False, "since": 0.0, "waited": 0.0, "last": ""}

        def reader():
            for raw in iter(p.stdout.readline, b""):
                line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                lf.write(line + "\n"); lf.flush()
                now = time.time()
                w = line.lstrip().startswith("== 대기")
                if st["waiting"] and not w:
                    st["waited"] += now - st["since"]
                if w and not st["waiting"]:
                    st["since"] = now
                st["waiting"] = w
                if line.strip():
                    st["last"] = line.strip()[:160]
        th = threading.Thread(target=reader, daemon=True)
        th.start()
        beat = 0.0
        while p.poll() is None:
            time.sleep(0.5)
            now = time.time()
            waited = st["waited"] + (now - st["since"] if st["waiting"] else 0)
            if now - t0 - waited > limit:
                kill_tree(p.pid)
                p.wait(timeout=30)
                th.join(timeout=5)
                return "TIMEOUT", now - t0, waited, p.pid
            if now - beat >= 30:
                beat = now
                on_beat(p.pid, now - t0, waited, st["last"])
        th.join(timeout=10)
    waited = st["waited"] + (time.time() - st["since"] if st["waiting"] else 0)
    return p.returncode, time.time() - t0, waited, p.pid


def first_errors(log, n=5):
    try:
        lines = [l for l in log.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
    except OSError:
        return []
    quiet = re.compile(r"(실패: 없음|실패 0|ERROR 0|오류 없음|FAIL 0|fail(ed)? 0)", re.I)
    top = [l for l in lines if re.match(r"\s*(FAIL|-- 실패|Traceback|\S+Error)", l)]  # 판정 줄을 먼저
    hit = top or [l for l in lines if ERR.search(l) and not quiet.search(l) and not l.lstrip().startswith(("OK", "-- 통과", "통과"))]
    pick = hit[:n] if hit else lines[-n:]
    return ["    " + l.strip()[:200] for l in pick]


def memo_of(name, log, rc):
    try:
        text = log.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if name.startswith("runall"):
        ok = len(re.findall(r"^-- 통과 ", text, re.M))
        bad = re.findall(r"^-- 실패 (\S+)", text, re.M)
        return f"묶음 {ok}/{ok + len(bad)} 통과" + (f" · 실패 {', '.join(bad)}" if bad else "")
    if name == "regress":
        try:
            import json
            j = json.loads(text)
            ws = j.get("workspaces") or []
            decks = [d for w in ws for d in (w.get("decks") or [])]
            cnt = {}
            for d in decks:
                cnt[d.get("status")] = cnt.get(d.get("status"), 0) + 1
            head = f"작업 공간 {len(ws)} · 덱 {len(decks)} · " + " · ".join(f"{k} {v}" for k, v in sorted(cnt.items()))
            return ("SKIP 판정 불가 - " if rc == 2 else "") + head + f" (기준 {j.get('baseCommit', '?')})"
        except ValueError:
            pass
    if rc == RC_SKIP or name == "regress" and rc == 2:
        return "SKIP 판정 불가 - " + (lines[-1][:160] if lines else "이유 없음")
    return lines[-1][:160] if lines else ""


def steps_for(level):
    py = sys.executable
    s = [("pycompile", None), ("nodecheck", None), ("parity", [py, str(STUDIO / "check_parity.py"), "-W", "example"])]
    if level == "quick":
        s.append(("runall-quick", [py, str(HERE / "run_all.py"), "--exact", *QUICK]))
    else:
        s.append(("runall", [py, str(HERE / "run_all.py")]))
        s.append(("regress", [py, str(STUDIO / "engine_regress.py"), "--base", "origin/main", "--json"]))
    return s


def helper_argv(name, files):
    """pycompile·nodecheck - 바뀐 파일만. 작은 도우미 스크립트를 자식으로 돌린다(같은 상한·로그 규칙)."""
    py = sys.executable
    if name == "pycompile":
        code = ("import sys,py_compile,warnings\nwarnings.simplefilter('error')\nbad=0\nfor f in sys.argv[1:]:\n"
                "    try: py_compile.compile(f, doraise=True)\n    except Exception as e: bad+=1; print('FAIL', f, '-', str(e).strip().splitlines()[-1][:300])\n"
                "print(f'바뀐 py {len(sys.argv)-1}개 · 실패 {bad}')\nsys.exit(1 if bad else 0)\n")
        return [py, "-X", "utf8", "-c", code, *files]
    code = ("import subprocess,sys,shutil\nif not shutil.which('node'): print('node 없음'); sys.exit(99)\nbad=0\nfor f in sys.argv[1:]:\n"
            "    r=subprocess.run(['node','--check',f],capture_output=True,text=True,encoding='utf-8',errors='replace')\n"
            "    if r.returncode: bad+=1; print('FAIL', f, '-', (r.stderr.strip().splitlines() or ['?'])[0][:300])\n"
            "print(f'바뀐 js {len(sys.argv)-1}개 · 실패 {bad}')\nsys.exit(1 if bad else 0)\n")
    return [py, "-X", "utf8", "-c", code, *files]


def main():
    ap = argparse.ArgumentParser(description="nexa-slide 검증 진입점(요약만 읽는다)")
    ap.add_argument("--level", choices=("quick", "full"), default="quick")
    ap.add_argument("--fail-fast", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    root = devboard.common_root() / "out" / "verify"
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = root / stamp
    out.mkdir(parents=True, exist_ok=True)
    hist = History(root / "history.tsv")
    inj, lim_env = inject(), limits_env()
    steps = steps_for(a.level)
    summary = out / "summary.md"
    head = f"# verify {stamp} · level={a.level} · {TREE.name} · {commit()}\n\n| 단계 | 결과 | 초 | 메모 |\n|---|---|---|---|\n"
    summary.write_text(head, encoding="utf-8")
    bid = f"verify-{stamp}"
    eta = lambda k: sum((hist.median(a.level, n) or DEFAULT_LIMIT[n] / 3) for n, _ in steps[k:])  # noqa: E731
    devboard.event("start", bid, who=os.environ.get("NEXA_WHO", "검증"), title=f"verify {a.level} · {TREE.name}", est=round(eta(0) / 60, 1), where=TREE.name, pid=os.getpid())
    table, fails, first_fail = [], 0, None
    for k, (name, argv) in enumerate(steps):
        devboard.event("step", bid, prog=f"{k + 1}/{len(steps)}", note=name, eta=int(eta(k)))
        med = hist.median(a.level, name)
        limit = lim_env.get(name) or (min(3600, max(120, med * 3)) if med else DEFAULT_LIMIT[name])
        log = out / f"{name}.log"
        if name in ("pycompile", "nodecheck"):
            files = changed(".py" if name == "pycompile" else ".js")
            if not files:
                log.write_text("바뀐 파일 없음\n", encoding="utf-8")
                res, sec, memo, errs = "PASS", 0.0, f"바뀐 {'py' if name == 'pycompile' else 'js'} 없음", []
                table.append((name, res, sec, memo, errs))
                with open(summary, "a", encoding="utf-8") as f:
                    f.write(f"| {name} | {res} | {sec:.0f} | {memo} |\n")
                hist.add(a.level, name, sec, res)
                continue
            argv = helper_argv(name, files)
        how = inj.get(name, "")
        if how == "fail":
            argv = [sys.executable, "-c", "import sys; print('FAIL 일부러 넣은 실패(NEXA_VERIFY_INJECT)'); sys.exit(1)"]
        elif how.startswith("sleep"):
            argv = [sys.executable, "-c", f"import time; print('일부러 늦춤'); time.sleep({float(how.split(':', 1)[1] if ':' in how else 600)})"]

        def beat(pid, el, waited, last, _n=name, _k=k):
            devboard.event("step", bid, prog=f"{_k + 1}/{len(steps)}", note=f"{_n} {int(el)}초" + (f"(대기 {int(waited)})" if waited > 1 else "") + (f" · {last[:60]}" if last else ""),
                           eta=int(max(0, eta(_k) - el + waited)), pid=pid)
        rc, sec, waited, pid = run_step(name, argv, log, limit, beat)
        if rc == "TIMEOUT":
            res, memo = "TIMEOUT", f"상한 {limit:.0f}초 초과(대기 {waited:.0f}초 제외) · 프로세스 트리 종료 · {log}"
        elif rc == 0:
            res, memo = "PASS", memo_of(name, log, rc)
        elif rc == RC_SKIP or (name == "regress" and rc == 2):
            res, memo = "SKIP", memo_of(name, log, rc)
        else:
            res, memo = "FAIL", f"rc={rc} · " + memo_of(name, log, rc) + f" · {log}"
        errs = first_errors(log) if res in ("FAIL", "TIMEOUT") else []
        if waited > 1 and res != "TIMEOUT":
            memo += f" · 시험 잠금 대기 {waited:.0f}초"
        table.append((name, res, sec, memo, errs))
        with open(summary, "a", encoding="utf-8") as f:
            f.write(f"| {name} | {res} | {sec:.0f} | {memo} |\n" + "".join(e + "\n" for e in errs))
        hist.add(a.level, name, max(0.0, sec - waited), res)
        if res in ("FAIL", "TIMEOUT"):
            fails += 1
            if first_fail is None:
                first_fail = name
                devboard.event("alert", bid, note=f"첫 실패 = {name} · " + (errs[0].strip() if errs else res))
            if a.fail_fast:
                for n2, _ in steps[k + 1:]:
                    table.append((n2, "SKIP", 0.0, "SKIP 판정 불가 - --fail-fast 로 돌지 않음", []))
                    with open(summary, "a", encoding="utf-8") as f:
                        f.write(f"| {n2} | SKIP | 0 | SKIP 판정 불가 - --fail-fast 로 돌지 않음 |\n")
                break
    tail = f"\n실패 단계 {fails} · 로그 = {out}\n"
    with open(summary, "a", encoding="utf-8") as f:
        f.write(tail)
    devboard.event("done", bid, res="ok" if not fails else "fail", note=f"{a.level} 실패 {fails} · " + " ".join(f"{n}={r}" for n, r, *_ in table))
    print(summary.read_text(encoding="utf-8").rstrip())
    return fails


if __name__ == "__main__":
    sys.exit(main())
