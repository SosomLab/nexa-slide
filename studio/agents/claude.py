# -*- coding: utf-8 -*-
"""Claude Code 어댑터 - claude -p(비대화형) + stream-json. 이 PC(2.1.299)에서 확인.

한 턴: claude -p --output-format stream-json --verbose --model <m> --permission-mode dontAsk --permission-prompts none
              --restricted --tools "Read,Edit,Write,Glob,Grep,Bash" --settings <권한 JSON> --strict-mcp-config --max-turns <n>
              [--max-budget-usd <x>] [--resume <session_id>]        프롬프트는 stdin
  --restricted 가 없는 구 판(2.1.248 미만): --setting-sources project,local --disallowedTools "mcp__*,PowerShell,WebFetch,WebSearch" 로 대신
로그인 확인: claude auth status (JSON, loggedIn) - 턴을 쓰지 않는다
금지: --dangerously-skip-permissions · bypassPermissions (어떤 설정으로도 넣지 않는다)
"""
import json
import re

from .base import Agent, run

TOOLS = "Read,Edit,Write,Glob,Grep,Bash"
DISALLOW_OLD = "mcp__*,PowerShell,WebFetch,WebSearch"
WANT_FLAGS = ("--restricted", "--permission-prompts", "--setting-sources", "--strict-mcp-config", "--max-budget-usd", "--tools", "--settings", "--resume", "--max-turns")


class ClaudeAgent(Agent):
    name = "claude"
    label = "Claude Code"
    guide_file = "CLAUDE.md"
    doc = "docs/claude-install.md"
    default_models = ["opus", "sonnet", "haiku"]
    verified = True
    exe_names = ("claude", "claude.exe", "claude.cmd")

    def _probe(self, exe, out):
        code, so, se = run([exe, "--version"], timeout=20)
        m = re.search(r"(\d+\.\d+\.\d+)", so + se)
        out["version"] = m.group(1) if m else (so.strip() or se.strip())[:40]
        code, so, se = run([exe, "auth", "status"], timeout=20)
        try:
            st = json.loads(so)
        except ValueError:
            st = {}
        out["loggedIn"] = bool(st.get("loggedIn")) if st else code == 0
        if st:
            out["account"] = {k: st.get(k) for k in ("authMethod", "subscriptionType", "email") if st.get(k)}
        code, so, se = run([exe, "--help"], timeout=20)
        out["flags"] = {f: (f in so) for f in WANT_FLAGS}
        if not out["loggedIn"]:
            out["hint"] = f"로그인되어 있지 않다 - 허브와 같은 사용자 계정에서 `claude` 를 한 번 실행해 로그인하거나, 다른 계정이면 CLAUDE_CODE_OAUTH_TOKEN/ANTHROPIC_API_KEY ({self.doc})"
        elif not out["flags"].get("--restricted"):
            out["hint"] = f"구 판({out['version']}) - --restricted 가 없어 --setting-sources project,local 로 대신한다. 2.1.248 이상을 권한다"

    def turn_cmd(self, model, resume_id=None, settings_path=None, max_turns=None, budget_usd=None, flags=None):
        flags = flags or {}
        cmd = [self.executable() or "claude", "-p", "--output-format", "stream-json", "--verbose", "--model", str(model),
               "--permission-mode", "dontAsk"]
        if flags.get("--permission-prompts", True):
            cmd += ["--permission-prompts", "none"]
        if flags.get("--restricted", True):
            cmd += ["--restricted", "--tools", TOOLS]
        else:
            cmd += ["--setting-sources", "project,local", "--disallowedTools", DISALLOW_OLD, "--allowedTools", TOOLS]
        if settings_path:
            cmd += ["--settings", str(settings_path)]
        if flags.get("--strict-mcp-config", True):
            cmd += ["--strict-mcp-config"]
        if max_turns:
            cmd += ["--max-turns", str(int(max_turns))]
        if budget_usd and flags.get("--max-budget-usd", True):
            cmd += ["--max-budget-usd", str(budget_usd)]
        if resume_id:
            cmd += ["--resume", str(resume_id)]
        return cmd

    def parse(self, line):
        d = self._json(line)
        if not d:
            return None
        t = d.get("type")
        if t == "system" and d.get("subtype") == "init":
            return {"type": "init", "sessionId": d.get("session_id"), "model": d.get("model")}
        if t == "assistant":
            evs = []
            for c in (d.get("message") or {}).get("content") or []:
                if c.get("type") == "text" and c.get("text"):
                    evs.append({"type": "text", "text": c["text"][:2000]})
                elif c.get("type") == "tool_use":
                    inp = c.get("input") or {}
                    summary = inp.get("file_path") or inp.get("command") or inp.get("pattern") or inp.get("path") or ""
                    evs.append({"type": "tool", "tool": c.get("name"), "summary": str(summary)[:200]})
            return evs or None
        if t == "user":  # 도구 결과
            for c in (d.get("message") or {}).get("content") or []:
                if c.get("type") == "tool_result":
                    return {"type": "tool_result", "tool": c.get("tool_use_id"), "ok": not c.get("is_error")}
            return None
        if t == "result":
            ok = not d.get("is_error") and d.get("subtype") == "success"
            return {"type": "result", "sessionId": d.get("session_id"), "model": (d.get("modelUsage") and next(iter(d["modelUsage"]), None)) or None,
                    "ok": ok, "turns": d.get("num_turns"), "costUsd": d.get("total_cost_usd"), "usage": d.get("usage"),
                    "text": (d.get("result") or "")[:2000], "subtype": d.get("subtype")}
        if t == "error":
            return {"type": "error", "message": str(d.get("error") or d.get("message") or line)[:500]}
        return None
