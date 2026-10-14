# -*- coding: utf-8 -*-
"""OpenAI Codex CLI 어댑터 - codex exec --json. **이 PC 에 설치가 없어 공식 문서 기준으로만 만들었다(미확인)** - 화면에 "미확인" 표시.

한 턴: codex exec --json --sandbox workspace-write -m <m> -c approval_policy="never" -c sandbox_workspace_write.network_access=true
              --ignore-user-config --skip-git-repo-check -                      프롬프트는 stdin("-")
이어 가기: codex exec resume [같은 옵션] <thread_id> -
출력(NDJSON): thread.started(thread_id) · turn.started · item.started/completed(agent_message·command_execution·file_change·…) · turn.completed(usage) · turn.failed · error
로그인 확인: codex --version · codex login status
금지: --sandbox danger-full-access · --approve-for-me
network_access=true 는 save_deck 이 127.0.0.1 작업 공간 서버에 저장하기 위해 필요하다.
"""
import re

from .base import Agent, run

WANT_FLAGS = ("--json", "--sandbox", "--ignore-user-config", "--skip-git-repo-check", "-c, --config", "-m, --model")


class CodexAgent(Agent):
    name = "codex"
    label = "Codex CLI"
    guide_file = "AGENTS.md"
    doc = "docs/openai-codex.md"
    default_models = []  # 계정에서 쓸 수 있는 모델 ID 를 직접 입력(사용자 설정 sessionModels.codex 로 목록을 둘 수 있다)
    verified = False
    exe_names = ("codex", "codex.exe", "codex.cmd")

    def _probe(self, exe, out):
        code, so, se = run([exe, "--version"], timeout=20)
        m = re.search(r"(\d+\.\d+\.\d+)", so + se)
        out["version"] = m.group(1) if m else (so.strip() or se.strip())[:40]
        code, so, se = run([exe, "login", "status"], timeout=20)
        out["loggedIn"] = code == 0
        code, so, se = run([exe, "exec", "--help"], timeout=20)
        out["flags"] = {f: (f in so) for f in WANT_FLAGS}
        if not out["loggedIn"]:
            out["hint"] = f"로그인되어 있지 않다 - `codex login`(또는 OPENAI_API_KEY 로 `codex login --with-api-key`) ({self.doc})"

    def _common(self, model, flags):
        flags = flags or {}
        cmd = ["--json", "--sandbox", "workspace-write", "-m", str(model), "-c", 'approval_policy="never"',
               "-c", "sandbox_workspace_write.network_access=true"]
        if flags.get("--ignore-user-config", True):
            cmd += ["--ignore-user-config"]
        if flags.get("--skip-git-repo-check", True):
            cmd += ["--skip-git-repo-check"]
        return cmd

    def turn_cmd(self, model, resume_id=None, settings_path=None, max_turns=None, budget_usd=None, flags=None):
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
