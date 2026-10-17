# -*- coding: utf-8 -*-
"""OpenAI Codex CLI 어댑터 - codex exec --json. 2026-10-17 Windows(codex-cli 0.163, gpt-6-luna, ChatGPT 로그인)에서 작업 공간 웹 세션 턴을 끝까지 확인했다.

한 턴: codex exec --json --sandbox workspace-write -m <m> -c approval_policy="never" -c sandbox_workspace_write.network_access=true
              [-c windows.sandbox="<elevated|…>"] --ignore-user-config --skip-git-repo-check -        프롬프트는 stdin("-")
이어 가기: codex exec resume [같은 옵션] <thread_id> -
출력(NDJSON): thread.started(thread_id) · turn.started · item.started/completed(agent_message·command_execution·file_change·…) · turn.completed(usage) · turn.failed · error
로그인 확인: codex --version · codex login status
금지: --sandbox danger-full-access · --approve-for-me · --dangerously-bypass-approvals-and-sandbox
network_access=true 는 save_deck 이 127.0.0.1 작업 공간 서버에 저장하기 위해 필요하다.

Windows 실측(2026-10-17):
- chocolatey·npm 으로 깐 codex.exe 옆에는 `codex-code-mode-host.exe` 가 없어 모든 명령 실행이 "fail closed" 다 - 데스크톱 앱이 둔
  `%LOCALAPPDATA%/OpenAI/Codex/bin/<해시>/codex.exe`(host 동봉)를 우선 쓴다(executable()). 사용자 설정 agentPaths.codex 가 있으면 그것.
- `--ignore-user-config` 가 사용자 `~/.codex/config.toml` 의 `[windows] sandbox = "elevated"` 도 버려 기본(unelevated) 샌드박스가 되는데
  이 PC 에서는 CreateProcess 실패 → 그 값을 읽어 `-c windows.sandbox="…"` 로 다시 준다(없으면 elevated).
- 프롬프트의 Read/Edit 는 Claude 낱말이라 Codex 가 "파일 도구가 없다"며 멈췄다 → `{shell}` 자리에 shell_note(셸로 읽기·apply_patch 로 고치기)를 넣는다.
"""
import os
import re
import shutil
from pathlib import Path

from .base import Agent, run, load_settings

WANT_FLAGS = ("--json", "--sandbox", "--ignore-user-config", "--skip-git-repo-check", "-c, --config", "-m, --model")
HOST_EXE = "codex-code-mode-host.exe"  # 0.163 부터 명령 실행이 이 보조 실행 파일(같은 폴더)로 간다 - 없으면 모든 명령이 "fail closed"


def _has_host(exe):
    """Windows 에서 codex.exe 옆에 code-mode host 가 있는가(다른 OS 는 단일 실행 파일이라 늘 참)."""
    if os.name != "nt":
        return True
    try:
        return (Path(exe).resolve().parent / HOST_EXE).is_file()
    except OSError:
        return False


def _app_bundled():
    """Codex 데스크톱 앱이 둔 CLI(%LOCALAPPDATA%/OpenAI/Codex/bin/<해시>/codex.exe) - host 가 함께 있다. 가장 최근 것."""
    base = os.environ.get("LOCALAPPDATA")
    if os.name != "nt" or not base:
        return None
    cands = [p for p in Path(base).joinpath("OpenAI", "Codex", "bin").glob("*/codex.exe") if (p.parent / HOST_EXE).is_file()]
    return str(max(cands, key=lambda p: p.stat().st_mtime)) if cands else None


def _windows_sandbox():
    """사용자 `~/.codex/config.toml` 의 `[windows] sandbox` 값(--ignore-user-config 로 버려지므로 이것만 옮겨 적는다). 없으면 elevated -
    chocolatey·npm 판의 기본(unelevated)은 이 PC 에서 CreateProcess 실패, 데스크톱 앱이 준비한 elevated 샌드박스는 동작(2026-10-17 실측)."""
    try:
        txt = (Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex") / "config.toml").read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^\[windows\]\s*$(.*?)(?=^\[|\Z)", txt, re.S | re.M)
        if m:
            v = re.search(r'^\s*sandbox\s*=\s*"([^"]+)"', m.group(1), re.M)
            if v:
                return v.group(1)
    except OSError:
        pass
    return "elevated"


class CodexAgent(Agent):
    name = "codex"
    label = "Codex CLI"
    guide_file = "AGENTS.md"
    doc = "docs/openai-codex.md"
    default_models = ["gpt-6-luna"]  # 2026-10-17 ChatGPT 로그인 계정의 기본 모델(codex 가 -m 없이 고른 것). 계정마다 다르면 사용자 설정 sessionModels.codex
    verified = True  # Windows · codex-cli 0.163 에서 작업 공간 웹 세션 턴(읽기 → 요청 파일 수정 → 답) 확인
    exe_names = ("codex", "codex.exe", "codex.cmd")
    shell_note = ("**너는 Codex 다 — 이 글의 `Read` 는 셸로 파일 읽기(`Get-Content`·`cat`·`sed -n`), `Edit` 는 `apply_patch`(또는 셸로 파일 쓰기)를 뜻한다.** "
                  "샌드박스는 작업 공간(cwd) 안 쓰기만 허용하므로 그 안의 파일은 읽고 고칠 수 있고, 밖은 읽기만 한다. "
                  "`python3 nexa.py …` 외의 셸 명령도 작업 공간 안 파일을 읽고 고치는 데 쓸 수 있다(파일 삭제·외부 네트워크는 하지 않는다 — 127.0.0.1 의 편집기 서버 저장은 `save_deck` 이 한다).")

    def executable(self):
        """사용자 설정 agentPaths.codex → PATH 의 codex → (Windows) 데스크톱 앱 동봉 CLI.
        PATH 의 판(chocolatey·npm)에 code-mode host 가 없으면 명령을 하나도 못 돌리므로 host 가 있는 앱 동봉 판을 우선한다."""
        p = (load_settings().get("agentPaths") or {}).get(self.name)
        if p:
            p = Path(str(p)).expanduser()
            return str(p) if p.is_file() else None
        found = next((w for w in (shutil.which(n) for n in self.exe_names) if w), None)
        if found and _has_host(found):
            return found
        return _app_bundled() or found

    def _probe(self, exe, out):
        code, so, se = run([exe, "--version"], timeout=20)
        m = re.search(r"(\d+\.\d+\.\d+)", so + se)
        out["version"] = m.group(1) if m else (so.strip() or se.strip())[:40]
        code, so, se = run([exe, "login", "status"], timeout=20)
        out["loggedIn"] = code == 0
        code, so, se = run([exe, "exec", "--help"], timeout=20)
        out["flags"] = {f: (f in so) for f in WANT_FLAGS}
        out["codeModeHost"] = _has_host(exe)
        if os.name == "nt":
            out["windowsSandbox"] = _windows_sandbox()
        if not out["loggedIn"]:
            out["hint"] = f"로그인되어 있지 않다 - `codex login`(또는 OPENAI_API_KEY 로 `codex login --with-api-key`) ({self.doc})"
        elif not out["codeModeHost"]:
            out["hint"] = (f"{exe} 옆에 {HOST_EXE} 가 없어 명령을 실행할 수 없다(fail closed) - Codex 데스크톱 앱을 설치하거나 "
                           f"host 가 있는 codex.exe 를 사용자 설정 agentPaths.codex 로 지정한다 ({self.doc})")

    def _common(self, model, flags):
        flags = flags or {}
        cmd = ["--json", "--sandbox", "workspace-write", "-m", str(model), "-c", 'approval_policy="never"',
               "-c", "sandbox_workspace_write.network_access=true"]
        if os.name == "nt":
            cmd += ["-c", f'windows.sandbox="{_windows_sandbox()}"']
        if flags.get("--ignore-user-config", True):
            cmd += ["--ignore-user-config"]
        if flags.get("--skip-git-repo-check", True):
            cmd += ["--skip-git-repo-check"]
        return cmd

    def turn_cmd(self, model, resume_id=None, settings_path=None, max_turns=None, budget_usd=None, flags=None, allow_web=False, add_dirs=None,
                 new_session_id=None, name=None):
        """settings_path·max_turns·budget_usd·allow_web·add_dirs·new_session_id·name 은 claude 전용 - 호출 쪽(wsession)이 공통으로 넘기므로 받기만 하고 쓰지 않는다
        (웹 검색·저장소 루트 권한은 start() 가 codex 에서 거절한다. 세션 ID 는 codex 가 thread.started 로 준다)."""
        exe = self.executable() or "codex"
        if resume_id:
            return [exe, "exec", "resume", *self._common(model, flags), str(resume_id), "-"]
        return [exe, "exec", *self._common(model, flags), "-"]

    def parse(self, line):
        d = self._json(line)
        if not d:
            return None
        t = d.get("type") or ""
        if t == "thread.started":
            return {"type": "init", "sessionId": d.get("thread_id"), "model": d.get("model")}
        if t in ("item.completed", "item.started"):
            it = d.get("item") or {}
            k = it.get("type") or it.get("item_type") or ""
            if k == "agent_message" and t == "item.completed":
                return {"type": "text", "text": str(it.get("text") or it.get("content") or "")[:2000]}
            if k in ("command_execution", "file_change", "mcp_tool_call", "web_search") and t == "item.started":
                return {"type": "tool", "tool": k, "summary": str(it.get("command") or it.get("path") or it.get("changes") or "")[:200]}
            return None
        if t == "turn.completed":
            u = d.get("usage") or {}
            return {"type": "result", "sessionId": d.get("thread_id"), "model": d.get("model"), "ok": True, "turns": None,
                    "costUsd": None, "usage": u, "text": "", "subtype": "success"}
        if t == "turn.failed":
            return {"type": "result", "sessionId": d.get("thread_id"), "model": None, "ok": False, "turns": None, "costUsd": None,
                    "usage": None, "text": str((d.get("error") or {}).get("message") or d.get("error") or "")[:2000], "subtype": "failed"}
        if t == "error":
            return {"type": "error", "message": str((d.get("error") or {}).get("message") or d.get("message") or line)[:500]}
        return None
