# -*- coding: utf-8 -*-
"""웹 AI 세션 관리자 - 서버 프로세스 안에서 돈다(docs/dev/web-session-design.md 2·3·9절). 프로필 둘:
  WorkspaceProfile  작업 공간 서버 안 - 편집기 요청(requests.json)을 묶어 claude 를 턴마다 실행(server.py /api/wsession)
  EngineProfile     허브 안 - 엔진 요청 큐(engine_requests)를 하나씩 꺼내 엔진 worktree 에서 실행(server.py /api/engine/session, docs/dev/engine-request-design.md 6절)

상태  off → ready(대기: 하트비트·요청 판정) → running(턴 실행 중) → ready | error(마지막 턴 실패 - 다음 묶음에 재시도) → off([중지]·유휴 초과·서버 종료)
턴    묶음 하나 = 어댑터 한 번 실행(cwd = 프로필의 폴더, 프롬프트는 stdin). 첫 턴의 세션 id 로 다음 턴을 이어 간다. 턴 시간 한도를 넘으면 프로세스 트리 종료 → error.
하트비트  프로필의 session.json 에 kind·agent·model·user 를 더해 쓴다 → 편집기 칩·status.py·허브가 본다.
동시 수   사용자 설정 폴더 hub/.studio/wsessions/<키>.json 에 살아 있는 세션을 등록 - PC 단위 sessionMax(엔진 세션도 센다).
로그      <state>/sessions/<시작 시각>/turn-N.jsonl(어댑터 출력 원문) · session.log. 토큰·키는 환경 변수로만.
"""
import collections
import datetime as dt
import json
import os
import signal
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

STUDIO = Path(__file__).resolve().parent
sys.path.insert(0, str(STUDIO))
from common import HUB, STATE, WORKSPACE, read_config  # noqa: E402
from paths import ENGINE, user_dir  # noqa: E402
import agents  # noqa: E402
import requests_core as rc  # noqa: E402

REGISTRY = user_dir() / "hub" / ".studio" / "wsessions"
INTERVAL = 1.0


def _now():
    return dt.datetime.now().isoformat(timespec="seconds")


def live_sessions():
    """PC 전체에서 살아 있는 웹 세션 [{key, kind, ws, user, agent, model, started}] - 등록 파일의 하트비트가 신선한 것만(죽은 등록은 지운다)."""
    out = []
    if not REGISTRY.is_dir():
        return out
    for f in REGISTRY.glob("*.json"):
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
            st = rc.heartbeat_status(r["heartbeat"])
            fresh = st["connected"] and st.get("kind") in ("web", "engine")
        except (OSError, ValueError, KeyError):
            fresh = False
        if fresh:
            out.append(r)
        else:
            f.unlink(missing_ok=True)
    return out


# ---------- 프로필 ----------
class WorkspaceProfile:
    """작업 공간 서버 - 편집기 요청 묶음(requests_core.RequestTracker, watch_requests 와 같은 규칙)."""
    kind = "web"

    def __init__(self):
        if HUB:
            raise RuntimeError("작업 공간 프로필은 작업 공간 서버에서만")
        self.cwd = WORKSPACE
        self.state_dir = STATE
        self.heartbeat_path = rc.SESSION
        self.registry_key = None  # hub.ws_id 로 늦게 정한다
        self.name = WORKSPACE.name
        self.prompt_file = STUDIO / "agents" / "turn_prompt.md"

    def key(self):
        if not self.registry_key:
            from hub import ws_id
            self.registry_key = ws_id(WORKSPACE)
        return self.registry_key

    def config(self):
        return read_config()

    def check_start(self):
        st = rc.session_status()
        if st.get("connected") and st.get("kind") != "web" and rc.pid_alive(st.get("pid")):  # 끝난 감시의 "끝남" 표시가 파일 경합으로 안 써졌을 수 있다 → pid 로 확인
            raise ValueError(f"수동 감시({st.get('label') or '?'}, pid {st.get('pid')})가 이 작업 공간을 맡고 있다 - 그 세션의 감시를 끝낸 뒤 시작한다")

    def source(self):
        return rc.RequestTracker(quiet=8.0)

    def ids(self, batch):
        return [r["id"] for r in batch]

    WEB_NOTE = ("\n웹 검색 허용 세션(관리자가 켬) - WebSearch·WebFetch 를 쓸 수 있다. 웹에서 얻은 내용은 **출처 URL** 을 적고(슬라이드 각주 또는 reply), "
                "수집 자료를 별도 문서로 보관하라는 요청이면 작업 공간 **루트**의 `research/<주제>.md` 에 정리한다(`content/` 안이 아님 - 거기는 덱 원본 폴더. Write 범위). "
                "검색어·요청 URL 에 덱 내용·사내 이름·개인 정보를 넣지 않는다.\n")

    def git_note(self, sess):
        """git·push·저장소 루트 허용 세션에만 덧붙이는 규칙."""
        g = set(sess.grants)
        if not g & {"git", "push", "root"}:
            return ""
        out = ["\n이 세션에 관리자가 연 권한:"]
        if "root" in g and sess.repo_root:
            out.append(f"- **저장소 루트 접근**: `{Path(sess.repo_root).as_posix()}` 아래 파일을 Read/Edit/Write 할 수 있다(작업일지 등 작업 공간 밖 문서). `.git/` 안은 직접 고치지 않는다. 그 밖의 폴더는 여전히 막혀 있다.")
        if g & {"git", "push"}:
            out.append("- **git 기록**: `git status`·`diff`·`log`·`add`·`commit`·`switch`/`checkout <브랜치>`·`merge`·`branch`·`stash`·`tag` 를 cwd 에서 그대로 실행한다(`git -C` 로 다른 경로 지정 금지 - 거절된다). "
                       "커밋 메시지는 저장소 규칙(저장소 루트의 `CLAUDE.md`·`AGENTS.md`, 없으면 `git log` 의 기존 형식)을 따르고, 끝에 빈 줄 뒤 `Requested-by: " + (sess.started_by or "local") + "` 트레일러를 붙인다. "
                       "요청이 브랜치→병합을 말하면 그대로, 아니면 지금 브랜치에 커밋한다. 이력 재작성(rebase·reset --hard·강제 push)·원격/설정 변경은 하지 않는다.")
        if "push" in g:
            out.append("- **push**: `git push`·`pull`·`fetch` 가능. push 전에 `git status` 와 `git log origin/<브랜치>..` 로 올라갈 커밋을 확인하고, 자격 증명 오류·거절이 나면 다시 시도하지 말고 출력 그대로 `reply` 에 적는다(대화형 로그인은 뜨지 않게 막혀 있다).")
        elif "git" in g:
            out.append("- push 는 허용되지 않았다 - 요청이 push 를 말하면 커밋까지 하고 `reply` 에 \"push 는 이 세션에 허용되지 않아 하지 않았습니다\" 라고 적는다.")
        return "\n".join(out) + "\n"

    def prompt(self, batch, reason, sess, ag):
        tpl = self.prompt_file.read_text(encoding="utf-8")
        return (tpl.replace("{guide}", ag.guide_file).replace("{reason}", str(reason)).replace("{web}", (self.WEB_NOTE if sess.allow_web else "") + self.git_note(sess))
                .replace("{shell}", ag.shell_note).replace("{batch}", json.dumps([rc.brief(r) for r in batch], ensure_ascii=False, indent=1)))

    def repo_root(self):
        """작업 공간을 품은 git 저장소 루트 - 작업 공간 자신이 루트이거나 저장소가 아니면 None. 엔진 폴더면 거절."""
        r = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=str(WORKSPACE), capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0 or not r.stdout.strip():
            return None
        root = Path(r.stdout.strip()).resolve()
        from hub import inside_engine
        if inside_engine(root):
            raise ValueError("저장소 루트가 엔진 폴더다 - 저장소 루트 접근을 열 수 없다")
        return None if root == WORKSPACE.resolve() else root

    def is_repo(self):
        r = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=str(WORKSPACE), capture_output=True, text=True)
        return r.returncode == 0 and r.stdout.strip() == "true"

    def settings_json(self, allow_web=False, grants=(), repo_root=None):
        """웹 세션 권한 JSON - 템플릿(workspace+web)에 이 작업 공간 실행기의 절대 경로 변형을 더한다.
        안내 파일(CLAUDE.md)이 `python3 <절대 경로>/nexa.py …` 로 적힌 작업 공간(허브가 만든 것)에서도 그 명령이 허용되게 - 다른 폴더의 nexa.py 는 여전히 거절.
        allow_web 면 WebFetch·WebSearch 가 열린다(agents.web_settings). grants(git·push·root)는 agents.git_grants."""
        s = agents.web_settings(allow_web)
        agents.git_grants(s["permissions"], set(grants), repo_root)
        allow = list(s["permissions"].get("allow", []))
        launcher = (WORKSPACE / "nexa.py")
        for py in ("python3", "python"):
            for f in sorted({launcher.as_posix(), str(launcher)}):
                for rule in (f"Bash({py} {f} *)", f'Bash({py} "{f}" *)'):
                    if rule not in allow:
                        allow.append(rule)
        s["permissions"]["allow"] = allow
        return s

    def env(self, sess):
        # git 이 대화형으로 묻지 않게(자격 증명 창·편집기) - 답할 사람이 없으니 바로 실패하게 한다
        return {"NEXA_SLIDE_WORKSPACE": str(WORKSPACE), "NEXA_SLIDE_SESSION": f"web:{sess.agent}", "NEXA_SLIDE_USER": sess.started_by or "local",
                "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never", "GIT_MERGE_AUTOEDIT": "no", "GIT_EDITOR": "true",
                **({"NEXA_SLIDE_REPO_ROOT": str(sess.repo_root)} if sess.repo_root else {})}  # 저장소 루트 접근 세션 - 작업 공간 밖을 읽는 명령(import_pptx)의 허용 범위

    def extra_info(self):
        st = rc.session_status()
        manual = None
        if st.get("connected") and st.get("kind") != "web":
            manual = {"label": st.get("label"), "pid": st.get("pid"), "mode": st.get("mode"), "last_seen": st.get("last_seen")}
        return {"open": st.get("open", 0), "working": st.get("working", 0), "manual": manual}

    def reconcile(self, batch, result, rc_code, emit):
        """침묵 실패 막기 - 턴이 끝났는데 묶음의 요청이 아직 working 이거나 open 에 빈 reply 면 서버가 reply 에 사유를 적고 open 으로 되돌린다."""
        ids = {r["id"] for r in batch}
        note = ((result or {}).get("text") or "").strip().splitlines()
        note = (note[0] if note else (f"턴이 비정상 종료(코드 {rc_code})" if rc_code else "세션이 답 없이 끝남"))[:200]
        unhandled = []
        for deck in {r["deck"] for r in batch}:
            p = rc.DECKS / f"{deck}.requests.json"
            try:
                rs = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            changed = False
            for q in rs:
                if q.get("id") in ids and (q.get("status") == "working" or (q.get("status") == "open" and not (q.get("reply") or "").strip())):
                    q["status"], q["reply"] = "open", f"세션이 처리하지 못했습니다: {note}"
                    unhandled.append(q["id"])
                    changed = True
            if changed:
                rc.write_json(p, rs)
        if unhandled:
            emit("warn", message=f"처리되지 않은 요청 {len(unhandled)}건 - reply 에 사유를 적고 open 으로 두었다", ids=unhandled)
        asked = [q["id"] for q in rc.all_requests() if q.get("id") in ids and q.get("status") == "done" and QUESTION_RX.search(str(q.get("reply") or ""))]
        if asked:  # 규약 위반(질문하면서 done) - 상태는 바꾸지 않고 알리기만 한다
            emit("warn", message=f"질문으로 끝나는 reply 인데 done 인 요청 {len(asked)}건 - 사용자는 [후속 요청]으로 답할 수 있다", ids=asked)
        return unhandled


QUESTION_RX = re.compile(r"(\?|？|알려\s*주세요|알려\s*주십시오|골라\s*주세요|할까요|드릴까요|원하시는)\s*[.!)\]]*\s*$")


class EngineQueueSource:
    """엔진 요청 큐 - 한 번에 하나. working 이 남아 있으면(이전 턴이 끝내지 못함) 그것부터."""

    def __init__(self):
        import engine_requests
        self.q = engine_requests

    @staticmethod
    def returned_by_session(x):
        """세션이 스스로 open 으로 되돌린 항목(질문·커밋 불가 등 - 마지막 이력이 engine-session 의 open)인가 - 사람이 답하거나 다시 열기 전에는 다시 보내지 않는다.
        (0.22.27: 이것을 가리지 않아 같은 요청을 턴마다 다시 받는 무한 반복이 있었다 - 토큰 소모)"""
        return x.get("status") == "open" and bool(x.get("awaiting"))  # engine_requests.update 가 세션의 open 되돌림에 켜고, 세션 밖의 어떤 갱신이든 끈다

    def poll(self):
        x = self.q.next_open()
        if x and x["status"] == "open" and self.returned_by_session(x):
            items = sorted((i for i in self.q.load() if i.get("status") == "open" and not self.returned_by_session(i)), key=lambda i: (-int(i.get("priority") or 0), i["id"]))
            x = items[0] if items else None
        if not x:
            return None, None
        if x["status"] == "open":
            x = self.q.update(x["id"], status="working", by="engine-session")
        return [x], "queue"


class EngineProfile:
    """허브 - 엔진 요청 큐를 엔진 worktree(<엔진>/.claude/worktrees/engine-dev, 브랜치 engine-dev)에서 처리한다. 운영 트리(main)는 건드리지 않는다."""
    kind = "engine"
    BRANCH = "engine-dev"

    def __init__(self):
        self.engine = ENGINE
        self.cwd = ENGINE / ".claude" / "worktrees" / "engine-dev"
        self.state_dir = user_dir() / "hub" / "engine" / ".studio"
        self.heartbeat_path = self.state_dir / "session.json"
        self.name = "engine"
        self.prompt_file = STUDIO / "agents" / "engine_turn_prompt.md"

    def key(self):
        return "engine"

    def config(self):
        return {}

    def _git(self, *args, cwd=None, timeout=60):
        return subprocess.run(["git", *args], cwd=str(cwd or self.engine), capture_output=True, timeout=timeout, text=True, encoding="utf-8", errors="replace")

    def ensure_worktree(self):
        """엔진 worktree 가 없으면 main 에서 engine-dev 브랜치로 만든다(있으면 그대로 - 지난 요청의 커밋이 쌓인다). 큐 CLI 실행 파일(.nexa/)도 둔다."""
        if not (self.cwd / ".git").exists():
            self.cwd.parent.mkdir(parents=True, exist_ok=True)
            r = self._git("rev-parse", "--verify", "--quiet", self.BRANCH)
            args = ["worktree", "add", str(self.cwd)] + ([self.BRANCH] if r.returncode == 0 else ["-b", self.BRANCH, "main"])
            r = self._git(*args)
            if r.returncode != 0:
                raise ValueError(f"엔진 worktree 를 만들지 못했다: {(r.stderr or r.stdout).strip()[-300:]}")
        # --restricted 세션은 Bash 명령에 cwd 밖 경로가 있으면 거부한다 → 허브 엔진의 큐 CLI 를 worktree 안의 얇은 실행 파일로 부른다(git 제외)
        shim = self.cwd / ".nexa"
        shim.mkdir(exist_ok=True)
        (shim / ".gitignore").write_text("*\n", encoding="utf-8", newline="\n")
        target = (STUDIO / "engine_request.py").as_posix()
        (shim / "outbox").mkdir(exist_ok=True)
        (shim / "engine_request.py").write_text(
            "# -*- coding: utf-8 -*-\n# 허브 엔진의 큐 CLI 를 이 worktree 안에서 부르기 위한 실행 파일(세션 시작 때 wsession 이 만든다, git 제외).\n"
            "# status 는 큐 파일(작업 공간 밖)을 직접 쓰지 않고 .nexa/outbox/ 에 적어 둔다 - 허브가 턴 끝에 반영한다(Codex 샌드박스에서 큐 파일 쓰기가 멈추던 결함, 0.22.28).\n"
            "import json, os, sys, time, runpy\n"
            "HERE = os.path.dirname(os.path.abspath(__file__))\n"
            "if len(sys.argv) > 1 and sys.argv[1] == 'status':\n"
            "    import argparse\n"
            "    ap = argparse.ArgumentParser(prog='engine_request.py status')\n"
            "    ap.add_argument('cmd'); ap.add_argument('id', type=int); ap.add_argument('status')\n"
            "    for k in ('--reply', '--reply-file', '--commit', '--applied-commit', '--branch', '--test', '--by'):\n"
            "        ap.add_argument(k)\n"
            "    a = ap.parse_args()\n"
            "    reply = open(a.reply_file, encoding='utf-8').read() if a.reply_file and a.reply_file != '-' else (sys.stdin.read() if a.reply_file == '-' else a.reply)\n"
            "    rec = {'id': a.id, 'status': a.status, 'reply': reply, 'commit': a.commit or a.applied_commit, 'branch': a.branch, 'test': a.test, 'by': a.by or 'engine-session', 't': time.time()}\n"
            "    p = os.path.join(HERE, 'outbox', '%d-%d.json' % (a.id, int(time.time() * 1000)))\n"
            "    with open(p, 'w', encoding='utf-8') as f:\n"
            "        json.dump(rec, f, ensure_ascii=False)\n"
            "    print('#%d → %s (허브가 턴 끝에 반영한다)' % (a.id, a.status))\n"
            "    sys.exit(0)\n"
            f"sys.argv[0] = {target!r}\nrunpy.run_path({target!r}, run_name='__main__')\n", encoding="utf-8", newline="\n")

    def git_info(self):
        exists = (self.cwd / ".git").exists()
        head = self._git("rev-parse", "--short", "HEAD", cwd=self.cwd if exists else self.engine)
        main = self._git("rev-parse", "--short", "main")
        ahead = self._git("rev-list", "--count", f"main..{self.BRANCH}") if exists else None
        return {"engine": str(self.engine), "worktree": str(self.cwd), "worktreeExists": exists, "branch": self.BRANCH,
                "head": head.stdout.strip(), "main": main.stdout.strip(), "ahead": int(ahead.stdout.strip() or 0) if ahead and ahead.returncode == 0 else 0}

    def check_start(self):
        st = rc.heartbeat_status(self.heartbeat_path)
        if st.get("connected") and st.get("kind") != "engine" and rc.pid_alive(st.get("pid")):
            raise ValueError(f"수동 엔진 개발 세션({st.get('label') or '?'}, pid {st.get('pid')})이 맡고 있다")
        self.ensure_worktree()
        import engine_requests
        engine_requests.reclaim_stale(by="hub")  # 이전 세션이 끊긴 채 남긴 working → open (새 세션이 이어서 받는다)

    def source(self):
        return EngineQueueSource()

    def ids(self, batch):
        return [x["id"] for x in batch]

    def req_cli(self):
        """큐 CLI - worktree 안의 실행 파일(.nexa/engine_request.py → 허브 엔진의 studio/engine_request.py). cwd 밖 경로는 --restricted 가 거부하고,
        worktree 브랜치(옛 main)에는 그 파일이 없을 수 있어서."""
        return ".nexa/engine_request.py"

    def _copy_attachments(self, x):
        """허브 화면에서 올린 첨부(사용자 설정 폴더 hub/engine/attach/<id>/)를 worktree 의 .nexa/attach/<id>/ 로 복사하고 그 상대 경로를 돌려준다 - --restricted 세션은 cwd 밖을 읽지 못한다."""
        import engine_requests
        out = []
        for a in engine_requests.attach_files(x["id"]):
            dst = self.cwd / ".nexa" / "attach" / str(x["id"]) / a["name"]
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(a["path"], dst)
                out.append(dst.relative_to(self.cwd).as_posix())
            except OSError:
                pass
        return out

    def prompt(self, batch, reason, sess, ag):
        x = batch[0]
        tpl = self.prompt_file.read_text(encoding="utf-8")
        show = {k: x.get(k) for k in ("id", "title", "body", "from", "evidence", "priority", "created", "history")}
        att = self._copy_attachments(x)
        if att:  # 큐의 evidence 는 사용자 설정 폴더 기준 경로 - 세션에는 cwd 안 사본 경로로 보여 준다
            show["evidence"] = [e for e in (show.get("evidence") or []) if not str(e).startswith("attach/")] + att
            show["attachments"] = att
        return (tpl.replace("{id}", str(x["id"])).replace("{branch}", self.BRANCH).replace("{req_cli}", self.req_cli()).replace("{shell}", ag.shell_note)
                .replace("{commit}", ag.engine_commit_note).replace("{request}", json.dumps(show, ensure_ascii=False, indent=1)))

    def settings_json(self, allow_web=False, grants=(), repo_root=None):  # 엔진 세션은 웹·grants 를 열지 않는다(무시 - 엔진 권한 묶음이 따로 있다)
        tpl = json.loads((STUDIO / "agents" / "permissions.json").read_text(encoding="utf-8"))
        eng, web = tpl["engine"]["permissions"], tpl["web"]["permissions"]
        perms = {"allow": list(eng.get("allow", [])), "deny": list(eng.get("deny", [])) + [x for x in web.get("deny", []) if x not in eng.get("deny", [])]}
        for k, v in web.items():
            if k not in ("allow", "deny"):
                perms[k] = v
        return {"permissions": perms}

    def env(self, sess):
        return {"NEXA_SLIDE_SESSION": f"engine:{sess.agent}", "NEXA_SLIDE_USER": sess.started_by or "local"}

    def extra_info(self):
        import engine_requests
        return {"queue": engine_requests.counts(), "git": self.git_info()}

    def commit_for(self, x, emit):
        """세션이 커밋하지 못한 worktree 변경을 허브가 대신 커밋한다(Codex 샌드박스는 .git 쓰기 불가 - 0.22.27). 바뀐 것이 없으면 None, 커밋했으면 짧은 해시."""
        st = self._git("status", "--porcelain", cwd=self.cwd)
        if st.returncode != 0 or not st.stdout.strip():
            return None
        self._git("add", "-A", cwd=self.cwd)
        title = " ".join(str(x.get("title") or "").split())[:70] or "엔진 요청"
        msg = f"{title} (engine-request #{x['id']})\n\n엔진 세션이 worktree 에서 고친 내용 - 허브가 대신 커밋(세션 샌드박스는 .git 쓰기 불가)\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
        r = self._git("-c", "user.name=nexa-slide hub", "-c", "user.email=hub@nexa-slide.local", "commit", "-q", "-m", msg, cwd=self.cwd)
        if r.returncode != 0:
            emit("warn", message=f"허브 대신 커밋 실패: {(r.stderr or r.stdout).strip()[-200:]}", ids=[x["id"]])
            return None
        h = self._git("rev-parse", "--short", "HEAD", cwd=self.cwd).stdout.strip()
        emit("text", text=f"허브가 worktree 변경을 대신 커밋했다: {h} (engine-request #{x['id']})")
        return h or None

    def apply_outbox(self, emit):
        """세션이 .nexa/outbox/ 에 남긴 status 갱신을 시각 순으로 큐에 반영한다(샌드박스 안에서 큐 파일을 쓰지 않게). 전이가 안 되는 것은 warn 으로 남기고 지운다."""
        import engine_requests
        box = self.cwd / ".nexa" / "outbox"
        if not box.is_dir():
            return 0
        n = 0
        for p in sorted(box.glob("*.json")):
            try:
                rec = json.loads(p.read_text(encoding="utf-8"))
                applied = rec["status"] == "applied"
                engine_requests.update(int(rec["id"]), status=rec["status"], by=rec.get("by") or "engine-session", reply=rec.get("reply"),
                                       commit=None if applied else rec.get("commit"), appliedCommit=rec.get("commit") if applied else None,
                                       branch=rec.get("branch"), test=rec.get("test"))
                n += 1
            except (OSError, ValueError, KeyError, TypeError) as e:
                emit("warn", message=f"세션의 상태 갱신을 반영하지 못함({p.name}): {e}")
            try:
                p.unlink()
            except OSError:
                pass
        return n

    def reconcile(self, batch, result, rc_code, emit):
        import engine_requests
        self.apply_outbox(emit)
        x = engine_requests.get(batch[0]["id"])
        if x and x["status"] == "done" and (not x.get("commit") or str(x.get("commit")).lower() == "auto"):  # 세션이 커밋을 못 했거나 허브에 맡김(--commit auto)
            h = self.commit_for(x, emit)
            if h:
                engine_requests.update(x["id"], by="hub", commit=h, branch=self.BRANCH)
            elif str(x.get("commit") or "").lower() == "auto":
                engine_requests.update(x["id"], by="hub", commit=None)
        if x and x["status"] == "working":
            note = ((result or {}).get("text") or "").strip().splitlines()
            note = (note[0] if note else f"턴이 끝났지만 요청을 마무리하지 못함(코드 {rc_code})")[:300]
            engine_requests.update(x["id"], status="open", by="engine-session", reply=(x.get("reply") or "") + f"\n[세션이 끝내지 못함] {note}")
            emit("warn", message=f"엔진 요청 #{x['id']} 를 끝내지 못해 open 으로 되돌렸다", ids=[x["id"]])
            return [x["id"]]
        return []


# ---------- 세션 ----------
class WebSession:
    def __init__(self, profile=None):
        self.p = profile or WorkspaceProfile()
        self.lock = threading.RLock()
        self.state = "off"
        self.agent = self.model = self.model_actual = self.session_id = None
        self.started_by = self.started_at = None
        self.turns = 0
        self.last_error = None
        self.last_activity = 0.0
        self.pending_model = None
        self.allow_web = False  # 이 세션에 웹 검색(WebSearch·WebFetch) 허용 - 전역 sessionAllowWeb 이 켜진 상태에서 관리자가 시작 때 고른다
        self.grants, self.repo_root = [], None  # git·push·root - 같은 틀(전역 + 세션 단위). repo_root = 저장소 루트 접근 때 --add-dir 할 폴더
        self.limits, self.flags = {}, {}
        self.events = collections.deque(maxlen=1000)
        self.seq = 0
        self._thread = None
        self._stop = threading.Event()
        self._proc = None
        self._source = None
        self._hb = None
        self._log_dir = None
        self._turn_log = None
        self._settings_path = None
        self.sess_file = self.p.state_dir / "wsession.json"  # 마지막 세션 정보(서버 재시작 뒤에도 "마지막" 표시용)
        self.log_root = self.p.state_dir / "sessions"
        self.last = self._read_json(self.sess_file)

    # ---------- 정보 ----------
    @staticmethod
    def _read_json(p):
        try:
            d = json.loads(Path(p).read_text(encoding="utf-8"))
            return d if isinstance(d, dict) else {}
        except (OSError, ValueError):
            return {}

    def info(self):
        with self.lock:
            d = {"kind": self.p.kind, "state": self.state, "agent": self.agent, "model": self.model, "modelActual": self.model_actual, "pendingModel": self.pending_model,
                 "sessionId": self.session_id, "cwd": str(self.p.cwd), "startedBy": self.started_by, "startedAt": self.started_at, "turns": self.turns,
                 "lastError": self.last_error, "lastActivity": dt.datetime.fromtimestamp(self.last_activity).isoformat(timespec="seconds") if self.last_activity else None,
                 "allowWeb": self.allow_web, "grants": self.grants, "repoRoot": str(self.repo_root) if self.repo_root else None, "limits": self.limits, "seq": self.seq, "logDir": str(self._log_dir) if self._log_dir else None}
            try:
                d.update(self.p.extra_info())
            except Exception as e:  # noqa: BLE001
                d["extraError"] = str(e)
            if self.state == "off":
                d["last"] = self.last or None
            return d

    def _save(self, **extra):
        self.last = {"agent": self.agent, "model": self.model, "modelActual": self.model_actual, "sessionId": self.session_id, "startedBy": self.started_by,
                     "startedAt": self.started_at, "allowWeb": self.allow_web, "grants": self.grants, "turns": self.turns, "lastError": self.last_error, "logDir": str(self._log_dir) if self._log_dir else None, **extra}
        rc.write_json(self.sess_file, self.last)

    def emit(self, kind, **kw):
        with self.lock:
            self.seq += 1
            ev = {"seq": self.seq, "t": _now(), "type": kind, **kw}
            self.events.append(ev)
        try:
            if self._log_dir:
                with open(self._log_dir / "session.log", "a", encoding="utf-8", newline="\n") as f:
                    f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        except OSError:
            pass
        return ev

    def events_since(self, since):
        with self.lock:
            return [e for e in self.events if e["seq"] > since]

    # ---------- 시작 · 중지 · 모델 ----------
    def start(self, agent=None, model=None, user=None, allow_web=False, grants=None):
        with self.lock:
            if self.state != "off":
                raise ValueError(f"이미 세션이 있다({self.state}) - 먼저 중지한다")
            self.p.check_start()
            eff = agents.effective(self.p.config())
            agent = (agent or eff["agent"]).lower()
            model = str(model or eff["model"]).strip()
            if agent not in agents.AGENTS:
                raise ValueError(f"모르는 에이전트: {agent}")
            allow_web = bool(allow_web) and self.p.kind != "engine"
            if allow_web and not eff.get("allowWeb"):
                raise ValueError("웹 검색은 관리자가 전역 설정(AI 세션 전역 기본 → 웹 검색 허용)을 켜야 고를 수 있다")
            if allow_web and agent != "claude":
                raise ValueError(f"{agent} 는 웹 검색 도구를 지원하지 않는다(미확인) - claude 로 시작한다")
            grants = [g for g in ("git", "push", "root") if g in (grants or [])] if self.p.kind != "engine" else []
            if "push" in grants and "git" not in grants:
                grants.insert(0, "git")  # push 는 git 기록을 전제로 한다
            for g in grants:
                if not eff.get("grants", {}).get(g):
                    raise ValueError({"git": "git 기록", "push": "push", "root": "저장소 루트 접근"}[g] + " 은 관리자가 전역 설정(AI 세션 전역 기본)을 켜야 고를 수 있다(작업 공간 설정에서 꺼져 있을 수도 있다)")
            if grants and agent != "claude":
                raise ValueError(f"{agent} 는 git·저장소 루트 권한을 지원하지 않는다(미확인) - claude 로 시작한다")
            if grants and not self.p.is_repo():
                raise ValueError("이 작업 공간은 git 저장소 안이 아니다 - git·저장소 루트 권한을 열 수 없다")
            repo_root = self.p.repo_root() if "root" in grants else None
            if not model:
                raise ValueError("모델을 준다")
            others = [s for s in live_sessions() if s.get("key") != self.p.key()]
            smax = eff["limits"].get("sessionMax")
            smax = 3 if smax is None else int(smax)  # 0 도 뜻이 있다(웹 세션 금지)
            if len(others) >= smax:
                raise ValueError(f"이 PC 의 동시 세션 한도({smax})에 닿았다 - 다른 세션을 먼저 중지한다: " + ", ".join(Path(s.get('ws') or s.get('key') or '?').name for s in others))
            ag = agents.get(agent)
            p = ag.probe()
            if not p["installed"]:
                raise ValueError(p["hint"] or f"{ag.label} 가 설치되어 있지 않다")
            if not p["loggedIn"]:
                raise ValueError(p["hint"] or f"{ag.label} 에 로그인되어 있지 않다")
            self.agent, self.model, self.flags, self.limits, self.allow_web = agent, model, p.get("flags") or {}, eff["limits"], allow_web
            self.grants, self.repo_root = grants, repo_root
            self.model_actual = self.session_id = self.last_error = self.pending_model = None
            # claude 세션 ID 를 미리 정한다 - 첫 턴은 --session-id 로 만들고 이후 --resume. 화면이 턴 0 부터 식별자를 보이고 `claude --resume <ID>` 로 확인한다
            self._sid_made = False
            if agent == "claude" and (p.get("flags") or {}).get("--session-id", True):
                self.session_id = str(uuid.uuid4())
            self.started_by, self.started_at, self.turns = user or "local", _now(), 0
            self.last_activity = time.time()
            self._log_dir = self.log_root / self.started_at.replace(":", "").replace("-", "")
            self._log_dir.mkdir(parents=True, exist_ok=True)
            self._settings_path = self.log_root / "claude-settings.json"
            self._settings_path.write_text(json.dumps(self.p.settings_json(allow_web, grants, repo_root), ensure_ascii=False, indent=1), encoding="utf-8")
            self._hb = {"pid": os.getpid(), "label": f"{self.p.kind}:{agent}", "mode": "web", "interval": INTERVAL, "started": self.started_at,
                        "kind": self.p.kind, "agent": agent, "model": model, "user": self.started_by, "allowWeb": allow_web, "grants": grants,
                        "sessionId": self.session_id, "cwd": str(self.p.cwd)}
            REGISTRY.mkdir(parents=True, exist_ok=True)
            rc.write_json(REGISTRY / f"{self.p.key()}.json", {"key": self.p.key(), "kind": self.p.kind, "ws": str(self.p.cwd), "heartbeat": str(self.p.heartbeat_path),
                                                                "user": self.started_by, "agent": agent, "model": model, "started": self.started_at, "pid": os.getpid(), "allowWeb": allow_web})
            self.state = "ready"
            self._stop.clear()
            self._source = self.p.source()
            self._beat()
            self._save()
            self.emit("state", state="ready", agent=agent, model=model, user=self.started_by, allowWeb=allow_web, grants=grants, repoRoot=str(repo_root) if repo_root else None)
            self._thread = threading.Thread(target=self._loop, name=f"wsession-{self.p.kind}", daemon=True)
            self._thread.start()
            # 하트비트는 별도 스레드 - 턴이 도는 동안 _loop 가 막혀도 매초 쓴다(안 그러면 편집기 칩이 "연결 없음"으로 바뀐다)
            threading.Thread(target=self._beat_loop, name=f"wsession-beat-{self.p.kind}", daemon=True).start()
            return self.info()

    def _beat(self, stopped=False):
        if self._hb:
            rc.heartbeat({**self._hb, "state": self.state, "turn": self.turns, "model": self.model}, stopped=stopped, path=self.p.heartbeat_path)

    def _beat_loop(self):
        while not self._stop.wait(INTERVAL):
            try:
                self._beat()
            except OSError:
                pass

    def stop(self, reason="user"):
        with self.lock:
            if self.state == "off":
                return self.info()
            self._stop.set()
            self._kill()
            th = self._thread
        if th and th is not threading.current_thread():
            th.join(timeout=8)
        with self.lock:
            self.state = "off"
            self._beat(stopped=True)
            (REGISTRY / f"{self.p.key()}.json").unlink(missing_ok=True)
            self._save(stoppedAt=_now(), reason=reason)
            self.emit("state", state="off", reason=reason)
            self._thread = self._source = self._hb = None
            return self.info()

    def set_model(self, model):
        model = str(model or "").strip()
        if not model:
            raise ValueError("모델을 준다")
        with self.lock:
            if self.state == "off":
                raise ValueError("세션이 없다")
            if self.state == "running":
                self.pending_model = model  # 턴이 끝난 뒤 적용(사용자 결정)
                self.emit("model", model=model, pending=True)
            else:
                self.model, self.pending_model = model, None
                if self._hb:
                    self._hb["model"] = model
                self.emit("model", model=model, pending=False)
            self._save()
            return self.info()

    # ---------- 루프 ----------
    def _loop(self):
        try:
            while not self._stop.is_set():
                try:
                    idle = float(self.limits.get("sessionIdleMinutes") or 60) * 60
                    if self.state in ("ready", "error") and time.time() - self.last_activity > idle:
                        self.emit("idle", minutes=idle / 60)
                        threading.Thread(target=self.stop, args=("idle",), daemon=True).start()
                        return
                    batch, reason = self._source.poll()
                    if batch and not self._stop.is_set():
                        self._turn(batch, reason)
                except Exception as e:  # noqa: BLE001 - 한 주기의 오류로 루프를 멈추지 않는다
                    with self.lock:
                        self.last_error = f"{type(e).__name__}: {e}"
                        self.state = "error"
                    self.emit("error", message=self.last_error)
                self._stop.wait(INTERVAL)
        finally:
            if self._stop.is_set():
                self._beat(stopped=True)

    def _turn(self, batch, reason):
        ag = agents.get(self.agent)
        with self.lock:
            if self.pending_model:
                self.model, self.pending_model = self.pending_model, None
                self._hb["model"] = self.model
                self.emit("model", model=self.model, pending=False)
            self.state = "running"
            self.turns += 1
            n = self.turns
            made = getattr(self, "_sid_made", True)
            cmd = ag.turn_cmd(self.model, self.session_id if made else None, self._settings_path if self.agent == "claude" else None,
                              max_turns=self.limits.get("sessionMaxTurns"), budget_usd=self.limits.get("sessionBudgetUsd"), flags=self.flags, allow_web=self.allow_web,
                              add_dirs=[self.repo_root] if self.repo_root and self.agent == "claude" else None,
                              new_session_id=None if made else self.session_id, name=f"nexa-slide {self.p.kind}: {self.p.cwd.name} #{(self.session_id or '')[:8]}")  # /resume 목록에서 ID 앞 8자리로 찾을 수 있게
            self._turn_log = self._log_dir / f"turn-{n}.jsonl"
        self.emit("turn.start", turn=n, count=len(batch), reason=reason, ids=self.p.ids(batch), model=self.model)
        env = {**os.environ, **ag.env(), **self.p.env(self)}
        kw = {}
        if os.name == "nt":
            kw["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        else:
            kw["start_new_session"] = True
        result, stderr_tail, rc_code = None, [], None
        try:
            proc = subprocess.Popen([str(c) for c in cmd], cwd=str(self.p.cwd), env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, **kw)
            with self.lock:
                self._proc = proc
            try:
                proc.stdin.write(self.p.prompt(batch, reason, self, ag).encode("utf-8"))
                proc.stdin.close()
            except OSError:
                pass

            def read_err():
                for line in iter(proc.stderr.readline, b""):
                    stderr_tail.append(line.decode("utf-8", "replace").rstrip())
                    if len(stderr_tail) > 50:
                        del stderr_tail[0]

            def read_out():
                nonlocal result
                with open(self._turn_log, "a", encoding="utf-8", newline="\n") as log:
                    for raw in iter(proc.stdout.readline, b""):
                        line = raw.decode("utf-8", "replace").rstrip("\r\n")
                        log.write(line + "\n")
                        ev = ag.parse(line)
                        for e in (ev if isinstance(ev, list) else [ev] if ev else []):
                            kind = e.pop("type")
                            if kind == "init":
                                with self.lock:
                                    self.session_id = e.get("sessionId") or self.session_id
                                    self._sid_made = True  # 대화가 만들어졌다 - 다음 턴부터 --resume
                                    if self._hb:
                                        self._hb["sessionId"] = self.session_id
                                    self.model_actual = e.get("model") or self.model_actual
                            elif kind == "result":
                                result = e
                                with self.lock:
                                    self.session_id = e.get("sessionId") or self.session_id
                                    self.model_actual = self.model_actual or e.get("model")  # init 의 모델이 우선(result 의 사용량 표에는 보조 모델도 섞인다)
                            if kind == "text":
                                e["text"] = e["text"][:400]
                            self.emit(kind, turn=n, **e)
            t_err = threading.Thread(target=read_err, daemon=True)
            t_out = threading.Thread(target=read_out, daemon=True)
            t_err.start()
            t_out.start()
            limit = float(self.limits.get("sessionTurnMinutes") or 20) * 60
            try:
                rc_code = proc.wait(timeout=limit)
            except subprocess.TimeoutExpired:
                self.emit("error", turn=n, message=f"턴이 {limit / 60:.0f}분 안에 끝나지 않아 끝냈다")
                self._kill()
                rc_code = -1
            t_out.join(timeout=5)
            t_err.join(timeout=2)
        except OSError as e:
            rc_code = -2
            stderr_tail.append(str(e))
        finally:
            with self.lock:
                self._proc = None
        unhandled = self.p.reconcile(batch, result, rc_code, self.emit)
        with self.lock:
            ok = rc_code == 0 and (result is None or result.get("ok", True))
            if ok:
                self.state, self.last_error = "ready", None
            else:
                self.state = "error" if not self._stop.is_set() else self.state
                self.last_error = ((result or {}).get("text") or "\n".join(stderr_tail[-5:]) or f"종료 코드 {rc_code}")[:500]
            self.last_activity = time.time()
            self._save()
        self.emit("turn.end", turn=n, ok=ok, code=rc_code, sessionId=self.session_id, model=self.model_actual,
                  costUsd=(result or {}).get("costUsd"), usage=(result or {}).get("usage"), error=None if ok else self.last_error,
                  unhandled=unhandled)

    def _kill(self):
        proc = self._proc
        if not proc or proc.poll() is not None:
            return
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True, timeout=15)
            else:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:  # noqa: BLE001 - 이미 끝났으면 그만
            pass

    def turn_log(self, n):
        p = (self._log_dir or Path(self.last.get("logDir") or "")) / f"turn-{int(n)}.jsonl"
        try:
            return p.read_text(encoding="utf-8")
        except OSError:
            return ""
