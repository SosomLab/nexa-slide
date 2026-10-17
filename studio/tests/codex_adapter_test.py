# -*- coding: utf-8 -*-
"""Codex 어댑터(studio/agents/codex.py) - 0.22.22.
wsession 이 넘기는 키워드 인자를 모두 받는가(allow_web 등 - 첫 턴 TypeError 회귀), Windows 에서 code-mode host 가 있는 실행 파일을 고르는가,
windows.sandbox 값을 사용자 config.toml 에서 옮겨 적는가, 턴 프롬프트의 {shell} 자리에 어댑터별 안내가 들어가는가. Codex 설치·로그인 없이 돈다."""
import os
import sys
import tempfile
from pathlib import Path

STUDIO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDIO))
import agents  # noqa: E402
from agents import codex as cx  # noqa: E402

FAIL = 0


def check(name, ok, detail=""):
    global FAIL
    print(("OK   " if ok else "FAIL ") + name + (f"  - {detail}" if detail and not ok else ""))
    if not ok:
        FAIL += 1


ag = agents.get("codex")
claude = agents.get("claude")

# 1. wsession 과 같은 호출 - 모든 인자를 키워드로
cmd = ag.turn_cmd("m1", None, None, max_turns=40, budget_usd=None, flags={}, allow_web=False, add_dirs=None, new_session_id=None, name="x")
check("turn_cmd 가 wsession 의 키워드 인자를 모두 받는다", cmd[1] == "exec" and cmd[-1] == "-" and "-m" in cmd and cmd[cmd.index("-m") + 1] == "m1")
cmd2 = ag.turn_cmd("m1", "thread-1", None, flags={}, allow_web=False, add_dirs=None, new_session_id=None, name="x")
check("resume 는 exec [옵션] resume <thread_id> - (옵션이 resume 앞 - 뒤에 두면 종료 2)",
      cmd2[1] == "exec" and cmd2[-3:] == ["resume", "thread-1", "-"] and "--sandbox" in cmd2[:cmd2.index("resume")] and "--json" in cmd2[:cmd2.index("resume")])
check("--sandbox workspace-write · approval never · network_access 고정",
      "workspace-write" in cmd and 'approval_policy="never"' in cmd and "sandbox_workspace_write.network_access=true" in cmd)
check("금지 옵션이 없다", not any("danger" in c or "bypass" in c or "approve-for-me" in c for c in cmd))
if os.name == "nt":
    check("Windows 는 windows.sandbox 를 준다", any(c.startswith('windows.sandbox="') for c in cmd))

# 2. 실행 파일 고르기 - host 가 없는 PATH 판보다 host 가 있는 앱 동봉 판을 우선(Windows 흉내: 임시 폴더로 LOCALAPPDATA·PATH 바꿈)
with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    bare = td / "choco"; bare.mkdir(); (bare / "codex.exe").write_bytes(b"")
    app = td / "local" / "OpenAI" / "Codex" / "bin" / "abc"; app.mkdir(parents=True)
    (app / "codex.exe").write_bytes(b""); (app / cx.HOST_EXE).write_bytes(b"")
    old_name, old_env = os.name, dict(os.environ)
    try:
        os.name = "nt"
        os.environ["LOCALAPPDATA"] = str(td / "local")
        check("_has_host: host 없는 폴더는 거짓", cx._has_host(str(bare / "codex.exe")) is False)
        check("_has_host: host 있는 폴더는 참", cx._has_host(str(app / "codex.exe")) is True)
        check("_app_bundled 가 앱 동봉 codex.exe 를 찾는다", (cx._app_bundled() or "").lower() == str(app / "codex.exe").lower())
        os.environ["LOCALAPPDATA"] = str(td / "none")
        check("앱 폴더가 없으면 None", cx._app_bundled() is None)
        # config.toml 의 [windows] sandbox 를 옮겨 적는다
        home = td / "codexhome"; home.mkdir()
        os.environ["CODEX_HOME"] = str(home)
        check("config 없으면 elevated", cx._windows_sandbox() == "elevated")
        (home / "config.toml").write_text('[tui]\nx = 1\n\n[windows]\nsandbox = "unelevated"\n\n[desktop]\ny = 2\n', encoding="utf-8")
        check("config 의 [windows] sandbox 를 읽는다", cx._windows_sandbox() == "unelevated")
    finally:
        os.name = old_name
        os.environ.clear(); os.environ.update(old_env)

# 3. 턴 프롬프트의 {shell} - 어댑터별 안내
for f in ("turn_prompt.md", "engine_turn_prompt.md"):
    tpl = (STUDIO / "agents" / f).read_text(encoding="utf-8")
    check(f"{f} 에 {{shell}} 자리가 있다", "{shell}" in tpl)
check("codex shell_note 가 apply_patch·셸 읽기를 말한다", "apply_patch" in ag.shell_note and "Read" in ag.shell_note)
check("claude shell_note 는 Bash 거절 안내", "Bash" in claude.shell_note and "python3 nexa.py" in claude.shell_note)
src = (STUDIO / "wsession.py").read_text(encoding="utf-8")  # import 하면 작업 공간을 요구하므로 원문으로 본다
check("wsession 두 프로필(작업 공간·엔진)이 {shell} 을 바꿔 넣는다", src.count('replace("{shell}", ag.shell_note)') == 2)

print("\n" + ("실패 %d" % FAIL if FAIL else "모두 통과"))
sys.exit(1 if FAIL else 0)
