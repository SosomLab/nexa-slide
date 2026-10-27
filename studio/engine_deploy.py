# -*- coding: utf-8 -*-
"""엔진 배포 - 관리자가 허브 카드의 [배포]를 누르면 engine-dev(완료된 엔진 요청)를 main 에 병합·시험·재시작·push 하고 [적용됨]까지 한 번에 한다.
docs/dev/engine-deploy-design.md. 세션은 여전히 병합·push·재시작을 못 한다 - 이 절차는 로그인한 관리자의 HTTP 요청으로만 시작된다.

    python3 studio/engine_deploy.py plan                    # 들어갈 커밋·요청·막는 이유(JSON)
    python3 studio/engine_deploy.py status                  # 마지막 배포 기록(JSON)
    python3 studio/engine_deploy.py run --by <관리자>        # 배포(허브가 떼어 낸 프로세스로 부른다 - 허브 재시작에도 끊기지 않게)
        [--no-tests] [--no-restart] [--no-push]             # 시험용·비상용

순서(run): 확인(운영 트리가 main·origin 새 커밋 ff) → 시험용 worktree 에서 --no-ff 병합 → 시험(run_all; 실패한 묶음은 병합 전 main 에서 다시 돌려
원래 있던 실패면 통과) → 처리 중 턴 기다림 → 운영 트리 main 을 병합 커밋으로 ff → 허브 재시작·생존 확인(실패하면 main 을 되돌리고 다시 재시작)
→ 떠 있던 작업 공간 서버 재시작 → push → done 요청을 applied(병합 커밋) → engine-dev 를 main 으로 ff.
push 를 맨 뒤에 두는 것은 재시작이 실패했을 때 원격에 올라간 것을 되돌리지 않아도 되게 하려는 것이다.
"""
import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

STUDIO = Path(__file__).resolve().parent
sys.path.insert(0, str(STUDIO))
import engine_requests  # noqa: E402
from paths import ENGINE, hub_port, load_settings, load_ws_config  # noqa: E402

BRANCH = "engine-dev"
WORKTREE = ENGINE / ".claude" / "worktrees" / BRANCH
STATE_FILE = engine_requests.ENGINE_DIR / "deploy.json"  # 마지막 배포 {state, by, started, finished, steps: [{t, step, ok, msg}], merge, prev, ids, log}
LOG_DIR = engine_requests.ENGINE_DIR / "deploy-logs"
RENDER_FILES = ("studio/render.js", "studio/common.py", "studio/export_pptx.py")
DRAIN_WAIT = 600  # 처리 중인 턴이 끝나길 기다리는 최대 초
SESSION_OFF_WAIT = 20  # 턴 대기 뒤 허브가 웹 엔진 세션을 끄길 기다리는 최대 초(stopped 하트비트)
TEST_TIMES = engine_requests.ENGINE_DIR / "test-times.json"  # 묶음별 지난 시험 시간 {이름: 초} - 화면의 예상 시간
BASELINE = engine_requests.ENGINE_DIR / "test-baseline.json"  # 커밋별 실패 묶음 {sha: {fail: […], t}} - 병합 전 main 을 다시 돌리지 않게
BASELINE_DAYS = 3  # 이보다 오래된 기록은 쓰지 않는다(그사이 환경이 바뀌었을 수 있다)
DOCS_ONLY = re.compile(r"^(docs/|.*\.md$)")  # 이것만 바뀌면 시험을 건너뛴다
GIT_ENV = {"GIT_TERMINAL_PROMPT": "0", "GIT_SSH_COMMAND": os.environ.get("GIT_SSH_COMMAND") or "ssh -o BatchMode=yes"}  # 묻는 창이 뜨지 않게 - 답할 사람이 없다


def _now():
    return dt.datetime.now().isoformat(timespec="seconds")


def git(*args, cwd=None, timeout=120):
    r = subprocess.run(["git", *args], cwd=str(cwd or ENGINE), capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=timeout, env={**os.environ, **GIT_ENV})
    return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()


def _out(*args, cwd=None):
    code, out = git(*args, cwd=cwd)
    return out if code == 0 else ""


def version():
    """CHANGELOG 맨 위 판 번호(## 0.22.29 - …)."""
    try:
        m = re.search(r"^## (\d+\.\d+\.\d+)", (ENGINE / "CHANGELOG.md").read_text(encoding="utf-8"), re.M)
        return m.group(1) if m else ""
    except OSError:
        return ""


# ---------- 상태 기록 ----------
def _read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _write_json(path, d):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def baseline(sha):
    """그 커밋에서 실패했던 묶음(지난 배포 시험 기록) - 없거나 오래됐으면 None."""
    b = _read_json(BASELINE, {}).get(sha)
    if not b or (dt.datetime.now() - dt.datetime.fromisoformat(b["t"])).days >= BASELINE_DAYS:
        return None
    return b["fail"]


def save_baseline(sha, fail):
    d = _read_json(BASELINE, {})
    d[sha] = {"fail": sorted(fail), "t": _now()}
    _write_json(BASELINE, dict(sorted(d.items(), key=lambda kv: kv[1]["t"])[-20:]))


def estimate(files=()):
    """예상 시간(초) - 지난 시험 시간 합 + 재시작·push 여유. 시험 기록이 없으면 None."""
    if files and all(DOCS_ONLY.match(f) for f in files):
        return 30
    t = _read_json(TEST_TIMES, {})
    return round(sum(t.values())) + 30 if t else None
def status():
    try:
        d = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"state": "none"}
    if d.get("state") == "running" and d.get("pid") and not engine_requests.pid_alive(d["pid"]):  # 배포 프로세스가 죽었다(PC 꺼짐 등) - 화면이 영영 '진행 중'이 되지 않게
        d["state"] = "failed"
        d.setdefault("steps", []).append({"t": _now(), "step": "abort", "ok": False, "msg": "배포 프로세스가 중간에 끝났다 - 운영 트리 상태를 확인하라"})
    return d


def _save(d):
    engine_requests.ENGINE_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="deploy.", suffix=".tmp", dir=str(engine_requests.ENGINE_DIR))
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, STATE_FILE)


# ---------- 계획(화면 확인용) ----------
def plan(fetch=True):
    """배포에 들어갈 것과 막는 이유. {ok, main, branch, commits:[{hash, subject}], files:[…], render, requests:[{id,title,commit}], originAhead, localAhead, blockers:[…]}"""
    blockers = []
    if fetch:
        code, out = git("fetch", "origin", "--quiet", timeout=60)
        if code:
            blockers.append(f"git fetch 실패: {out[-200:]}")
    cur = _out("rev-parse", "--abbrev-ref", "HEAD")
    if cur != "main":
        blockers.append(f"운영 트리({ENGINE})가 main 이 아니라 {cur or '?'} 에 있다")
    if not (WORKTREE / ".git").exists() and not _out("rev-parse", "--verify", "--quiet", BRANCH):
        blockers.append(f"{BRANCH} 브랜치가 없다")
    commits = [dict(zip(("hash", "subject"), l.split(" ", 1))) for l in _out("log", "--format=%h %s", f"main..{BRANCH}").splitlines() if l]
    files = [l for l in _out("diff", "--name-only", f"main...{BRANCH}").splitlines() if l]
    origin_ahead = len(_out("rev-list", "main..origin/main").splitlines())
    local_ahead = len(_out("rev-list", "origin/main..main").splitlines())
    if origin_ahead and local_ahead:
        blockers.append(f"main 과 origin/main 이 갈라졌다(원격 +{origin_ahead} · 로컬 +{local_ahead}) - 터미널에서 먼저 맞춘다")
    dirty = [l for l in _out("diff", "--name-only", "HEAD").splitlines() if l]  # 커밋하지 않은 변경(스테이징 포함)
    clash = sorted(set(dirty) & set(files))
    if clash:
        blockers.append("운영 트리에 커밋하지 않은 변경이 병합할 파일과 겹친다: " + ", ".join(clash[:5]))
    wt_dirty = _out("status", "--porcelain", "--untracked-files=no", cwd=WORKTREE) if (WORKTREE / ".git").exists() else ""
    if wt_dirty:
        blockers.append(f"{BRANCH} worktree 에 커밋하지 않은 변경이 있다 - 세션이 처리 중이거나 커밋을 빠뜨렸다")
    if not commits:
        blockers.append(f"{BRANCH} 에 main 보다 앞선 커밋이 없다")
    reqs = [{"id": x["id"], "title": x.get("title", ""), "commit": x.get("commit", "")} for x in engine_requests.load() if x.get("status") == "done"]
    st = status()
    if st.get("state") == "running":
        blockers.append("다른 배포가 진행 중이다")
    return {"ok": not blockers, "main": _out("rev-parse", "--short", "main"), "branch": BRANCH, "commits": commits, "files": files,
            "render": any(f in RENDER_FILES for f in files), "requests": reqs, "originAhead": origin_ahead, "localAhead": local_ahead,
            "blockers": blockers, "version": version(), "last": st, "estimate": estimate(files)}


# ---------- 시작(허브가 부른다) ----------
def start(by, extra=()):
    """배포 프로세스를 떼어 내 띄운다 - 허브를 재시작해도 끊기지 않게(service.py 의 서버 띄우기와 같은 방식)."""
    p = plan()
    if not p["ok"]:
        raise ValueError(" · ".join(p["blockers"]))
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log = LOG_DIR / f"{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
    _save({"state": "running", "by": by, "started": _now(), "steps": [], "ids": [r["id"] for r in p["requests"]], "log": str(log), "pid": None, "estimate": p["estimate"]})
    kw = {}
    if os.name == "nt":
        kw["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    else:
        kw["start_new_session"] = True
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
    env.pop("NEXA_SLIDE_WORKSPACE", None)
    f = open(log, "a", encoding="utf-8")
    proc = subprocess.Popen([sys.executable, str(STUDIO / "engine_deploy.py"), "run", "--by", by, *extra], cwd=str(engine_requests.ENGINE_DIR),
                            env=env, stdout=f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, **kw)
    d = status()
    d["pid"] = proc.pid
    _save(d)
    return d


# ---------- 실행 ----------
class Run:
    def __init__(self, by, tests=True, restart=True, push=True):
        self.by, self.tests, self.restart, self.push = by, tests, restart, push
        d = status() if STATE_FILE.exists() else {}
        if d.get("state") != "running" or d.get("pid") not in (None, os.getpid()):  # 허브를 거치지 않고 터미널에서 바로 부른 경우
            d = {"state": "running", "by": by, "started": _now(), "steps": [], "ids": []}
        d["pid"] = os.getpid()
        self.d = d
        self.tmp = []  # 지울 시험용 worktree
        _save(d)

    def step(self, name, ok=True, msg=""):
        print(f"[{_now()}] {'OK  ' if ok else 'FAIL'} {name} {msg}", flush=True)
        self.d["steps"].append({"t": _now(), "step": name, "ok": ok, "msg": str(msg)[:600]})
        self.d.pop("cur", None)
        _save(self.d)

    def doing(self, what):
        """지금 하는 단계(오래 걸리는 시험·대기 등) - 화면이 '배포 중' 만 보이지 않게 deploy.json 에 남긴다."""
        print(f"[{_now()}] ..   {what}", flush=True)
        self.d["cur"] = {"t": _now(), "step": what}
        _save(self.d)

    def finish(self, state, msg=""):
        self.d.pop("cur", None)
        self.d.update(state=state, finished=_now(), message=msg)
        _save(self.d)
        for w in self.tmp:
            git("worktree", "remove", "--force", str(w))
        print(f"[{_now()}] == {state} {msg}", flush=True)
        return 0 if state == "ok" else 1

    def fail(self, name, msg):
        self.step(name, False, msg)
        return self.finish("failed", f"{name}: {msg}")

    def _worktree(self, name, ref):
        w = ENGINE / ".claude" / "worktrees" / name
        if w.exists():
            git("worktree", "remove", "--force", str(w))
            shutil.rmtree(w, ignore_errors=True)
        code, out = git("worktree", "add", "--detach", str(w), ref)
        if code:
            raise RuntimeError(out[-300:])
        self.tmp.append(w)
        return w

    def _run_tests(self, root, names=(), label="병합본"):
        """run_all → 실패한 묶음 이름. 시험은 격리 포트(5799 등)를 써서 운영 허브와 겹치지 않는다.
        출력을 줄 단위로 따라가며 묶음이 끝날 때마다 deploy.json 의 tests[label] 에 남긴다 - 화면이 묶음별 진행(✓/✕·초)을 보인다."""
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
        env.pop("NEXA_SLIDE_WORKSPACE", None)
        cmd = [sys.executable, str(root / "studio" / "tests" / "run_all.py"), *(["--exact", *names] if names else [])]
        p = subprocess.Popen(cmd, cwd=str(root), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        T = self.d.setdefault("tests", {})[label] = {"total": 0, "names": [], "done": []}
        times = _read_json(TEST_TIMES, {})
        t_end = time.time() + 1800
        for line in p.stdout:
            print(line, end="", flush=True)
            if line.startswith("== 대기 · "):  # 다른 시험 실행(엔진 세션 등)이 끝나길 기다림(tests/testlock.py) - 기다린 시간은 시험 제한에 넣지 않는다
                self.doing(f"시험({label}) " + line[5:].strip())
                t_end = time.time() + 1800
            elif m := re.match(r"^== 묶음 (\d+)개: (.*)", line):
                T["total"], T["names"] = int(m.group(1)), m.group(2).split()
                _save(self.d)
            elif (m := re.match(r"^== (\S+) · ", line)) and m.group(1) in T["names"]:
                self.doing(f"시험({label}) {len(T['done']) + 1}/{T['total']} · {m.group(1)}")
            elif m := re.match(r"^-- (통과|실패) (\S+) (\d+)s", line):
                T["done"].append({"name": m.group(2), "ok": m.group(1) == "통과", "sec": int(m.group(3))})
                times[m.group(2)] = int(m.group(3))
                _save(self.d)
            if time.time() > t_end:
                p.kill()
                break
        p.wait()
        _write_json(TEST_TIMES, times)
        bad = [x["name"] for x in T["done"] if not x["ok"]]
        if p.returncode and not bad:
            bad = ["run_all"]
        return bad

    def run(self):
        p = plan()
        if not p["ok"] and not (p["blockers"] == ["다른 배포가 진행 중이다"]):  # 진행 중인 배포 = 이 프로세스
            return self.fail("확인", " · ".join(b for b in p["blockers"] if b != "다른 배포가 진행 중이다"))
        ids = [r["id"] for r in p["requests"]]
        self.d["ids"] = ids
        self.step("확인", True, f"커밋 {len(p['commits'])}개 · 요청 {', '.join('#' + str(i) for i in ids) or '없음'}")
        if p["originAhead"]:  # 다른 곳에서 올린 main 을 먼저 받는다
            code, out = git("merge", "--ff-only", "origin/main")
            if code:
                return self.fail("origin/main 받기", out[-300:])
            self.step("origin/main 받기", True, f"+{p['originAhead']}")
        prev = _out("rev-parse", "main")
        self.d["prev"] = prev
        # 1) 시험용 worktree 에서 병합 - 운영 트리는 모두 통과한 뒤에만 움직인다(정적 파일이 바로 나가므로)
        titles = " · ".join(r["title"] for r in p["requests"])[:120] or f"{len(p['commits'])}개 커밋"
        tag = "·".join("#" + str(i) for i in ids)
        msg = f"merge: {BRANCH} → main - {titles}" + (f" (engine-request {tag})" if tag else "") + f"\n\nDeployed-by: {self.by}"
        try:
            w = self._worktree("deploy-merge", prev)
        except RuntimeError as e:
            return self.fail("병합", f"시험용 worktree 를 만들지 못했다: {e}")
        code, out = git("merge", "--no-ff", BRANCH, "-m", msg, cwd=w)
        if code:
            git("merge", "--abort", cwd=w)
            return self.fail("병합", "충돌 - 터미널에서 풀어야 한다: " + out[-300:])
        merge = _out("rev-parse", "HEAD", cwd=w)
        self.d["merge"] = merge
        self.step("병합", True, merge[:7])
        # 2) 시험 - 병합본에서 실패한 묶음만 병합 전(main)에서 다시 돌려 새로 생긴 실패만 막는다
        if self.tests and all(DOCS_ONLY.match(f) for f in p["files"]):
            self.step("시험", True, "건너뜀 - 문서만 바뀌었다")
        elif self.tests:
            self.doing("시험 - 병합본 전체")
            bad = self._run_tests(w)
            if "run_all" not in bad:
                save_baseline(merge, bad)  # 배포가 끝나면 main = 이 커밋 - 다음 배포는 비교 시험을 다시 돌리지 않는다
            if bad:
                self.step("시험(병합본)", True, f"실패 {len(bad)}개 - 병합 전 main 과 비교: " + ", ".join(bad))
                known = baseline(prev)
                if "run_all" in bad:
                    before = set()
                elif known is not None:
                    before = set(known)
                    self.step("비교 기준", True, f"병합 전 main {prev[:7]} 의 지난 시험 기록을 쓴다(다시 돌리지 않음) - 실패 {len(known)}개")
                else:
                    try:
                        base = self._worktree("deploy-base", prev)
                    except RuntimeError as e:
                        return self.fail("시험", f"비교용 worktree 를 만들지 못했다: {e}")
                    self.doing(f"시험 - 실패 {len(bad)}개 묶음을 병합 전 main 에서 다시 돌려 비교")
                    before = set(self._run_tests(base, bad, label="병합 전"))
                    save_baseline(prev, before)  # 그 묶음들만 돌린 기록 - 다음에 다른 묶음이 실패하면 새 실패로 본다(막는 쪽으로 안전)
                    self.step("비교 시험(병합 전)", True, f"병합 전에도 실패: {', '.join(sorted(before)) or '없음'}")
                new = [b for b in bad if b not in before]
                if new and "run_all" not in new:  # 새 실패는 병합본에서 한 번 더 - 다시 통과하면 한때의 흔들림(시간·환경)이지 변경 탓이 아니다
                    self.doing(f"시험 - 새 실패 {len(new)}개 묶음을 병합본에서 다시 돌려 확인")
                    still = set(self._run_tests(w, new, label="재시도"))
                    flaky = [b for b in new if b not in still]
                    if flaky:
                        self.d.setdefault("tests", {}).setdefault("병합본", {})["flaky"] = flaky  # 화면은 '다시 돌려 통과'(노랑)로
                        bad = [b for b in bad if b not in flaky]
                        save_baseline(merge, bad)  # 기준에는 다시 돌려도 실패한 것만
                    self.step("재시도(병합본)", True, f"다시 돌려 통과: {', '.join(flaky) or '없음'} · 여전히 실패: {', '.join(sorted(still)) or '없음'}")
                    new = [b for b in new if b in still]
                self.d.setdefault("tests", {}).setdefault("병합본", {})["known"] = sorted(set(bad) & before)  # 화면은 이것을 '기존 실패'(노랑)로 - 빨간 ✕ 는 새 실패만
                _save(self.d)
                if new:
                    return self.fail("시험", "새로 생긴 실패: " + ", ".join(new))
                self.step("시험 판정", True, "새 실패 없음 (원래 있던 실패: " + (", ".join(bad) or "없음") + ")")
            else:
                self.step("시험", True, "전부 통과")
            if p["render"]:
                self.doing("렌더 동일성(check_parity)")
                r = subprocess.run([sys.executable, str(w / "studio" / "check_parity.py"), "-W", "example"], cwd=str(w), capture_output=True,
                                   text=True, encoding="utf-8", errors="replace", timeout=600)
                if r.returncode:
                    return self.fail("렌더 동일성", ((r.stdout or "") + (r.stderr or ""))[-400:])
                self.step("렌더 동일성", True, "check_parity -W example")
        else:
            self.step("시험", True, "건너뜀(--no-tests)")
        # 3) 처리 중인 턴이 끝나길 기다린다 - 재시작하면 턴이 끊긴다
        if self.restart:
            self.doing("처리 중인 턴이 끝나길 기다림")
            busy = self._busy()
            t0 = time.time()
            while busy and time.time() - t0 < DRAIN_WAIT:
                time.sleep(5)
                busy = self._busy()
            if busy:
                return self.fail("턴 마무리 대기", "처리 중인 턴이 끝나지 않았다: " + ", ".join(busy))
            self.step("턴 마무리 대기", True)
            # 허브가 이 단계를 보고 웹 엔진 세션을 끈다(server._deploy_stop_engine) - 끝날 때까지 잠깐 기다린 뒤 재시작(수동 세션은 그대로)
            t0 = time.time()
            while time.time() - t0 < SESSION_OFF_WAIT and (hb := engine_requests.session_state()).get("connected") and hb.get("kind") != "manual":
                time.sleep(1)
        running = self._running_ws() if self.restart else []
        # 4) 운영 트리 main 을 병합 커밋으로(fast-forward) - 커밋하지 않은 다른 변경은 그대로 둔다
        code, out = git("merge", "--ff-only", merge)
        if code:
            return self.fail("main 반영", out[-300:])
        self.step("main 반영", True, f"{prev[:7]} → {merge[:7]}")
        # 5) 재시작 - 허브가 살아나지 않으면 main 을 되돌리고 다시 띄운다
        if self.restart:
            self.doing("허브 재시작")
            ok, out = self._restart_hub()
            if not ok:
                git("reset", "--keep", prev)
                ok2, out2 = self._restart_hub()
                self.step("허브 재시작", False, out[-300:])
                return self.finish("rolledback", f"허브가 새 판으로 뜨지 않아 main 을 {prev[:7]} 로 되돌렸다" + ("" if ok2 else " - 되돌린 판도 뜨지 않는다, 터미널에서 확인하라: " + out2[-200:]))
            self.step("허브 재시작", True, out[-200:])
            for ws in running:
                code, out = self._service(["restart"], ws)
                self.step(f"작업 공간 재시작 {ws.name}", code == 0, out[-200:])
        # 6) push - 실패해도 운영은 새 판이다(로컬 main 이 앞선 채 남는다)
        warn = ""
        if self.push:
            self.doing("push")
            code, out = git("push", "origin", "main", timeout=180)
            self.step("push", code == 0, out[-300:])
            if code:
                warn = "push 실패 - 운영은 새 판, 원격에는 아직 없다(터미널에서 git push origin main)"
        # 7) 요청 적용됨 · engine-dev 를 main 으로
        ver = version()
        for i in ids:
            try:
                engine_requests.update(i, status="applied", by=self.by, appliedCommit=merge[:7], engineVersion=ver)
            except ValueError as e:  # 그사이 다른 사람이 상태를 바꿨다
                self.step(f"#{i} 적용됨", False, str(e))
        if ids:
            self.step("적용됨 표시", True, ", ".join("#" + str(i) for i in ids))
        if (WORKTREE / ".git").exists():
            code, out = git("merge", "--ff-only", "main", cwd=WORKTREE)
            self.step(f"{BRANCH} 맞춤", code == 0, out[-200:])
        return self.finish("ok" if not warn else "warn", warn or f"main {merge[:7]} · {ver}")

    # ---------- 재시작 도우미 ----------
    def _service(self, args, ws=None):
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        env.pop("NEXA_SLIDE_WORKSPACE", None)
        if ws:
            env["NEXA_SLIDE_WORKSPACE"] = str(ws)
        r = subprocess.run([sys.executable, str(STUDIO / "service.py"), *args], cwd=str(ws or engine_requests.ENGINE_DIR), env=env,
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()

    def _restart_hub(self):
        code, out = self._service(["restart"])
        if code:
            return False, out
        port = hub_port()
        for _ in range(40):  # 생존 확인 - 로그인 없이 답하는 /api/auth/state
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/auth/state", timeout=3) as r:
                    if json.loads(r.read().decode("utf-8")).get("ok"):
                        return True, out
            except Exception:  # noqa: BLE001 - 아직 뜨는 중
                pass
            time.sleep(0.5)
        return False, out + " · /api/auth/state 응답 없음"

    def _workspaces(self):
        for r in load_settings().get("recent", []):
            ws = Path(r.get("path", ""))
            if (ws / "nexa-slide.json").is_file():
                yield ws

    def _running_ws(self):
        import hub
        return [ws for ws in self._workspaces() if hub.server_state(ws)["running"]]

    def _busy(self):
        """처리 중인 턴 - 엔진 세션·작업 공간 웹 세션의 하트비트 state=running."""
        import hub
        out = []
        hb = engine_requests.session_state()
        if hb.get("connected") and hb.get("state") == "running":
            out.append("엔진 세션")
        for ws in self._workspaces():
            try:
                s = hub.session_summary(ws, load_ws_config(ws))
            except Exception:  # noqa: BLE001 - 깨진 설정
                continue
            if s.get("connected") and s.get("state") == "running":
                out.append(ws.name)
        return out


def main():
    ap = argparse.ArgumentParser(description="엔진 배포(engine-dev → main → 재시작 → push → 적용됨)")
    ap.add_argument("cmd", choices=("plan", "status", "run"))
    ap.add_argument("--by", default=os.environ.get("USERNAME") or os.environ.get("USER") or "cli")
    ap.add_argument("--no-tests", action="store_true")
    ap.add_argument("--no-restart", action="store_true")
    ap.add_argument("--no-push", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if a.cmd == "plan":
        print(json.dumps(plan(), ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "status":
        print(json.dumps(status(), ensure_ascii=False, indent=1))
        return 0
    return Run(a.by, tests=not a.no_tests, restart=not a.no_restart, push=not a.no_push).run()


if __name__ == "__main__":
    sys.exit(main())
