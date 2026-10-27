# -*- coding: utf-8 -*-
"""AI 세션 어댑터 묶음 - claude(확인됨) · codex(미확인). docs/dev/web-session-design.md 4·7절.

    get(name)                 어댑터 인스턴스
    probe_all(refresh)        {이름: probe 결과}
    effective(ws_cfg)         우선순위를 적용한 기본값 {agent, model, sources} - 전역(사용자 설정 sessionAgent·sessionModel) < 작업 공간 설정(같은 키)
    web_settings(allow_web)   웹 세션에 --settings 로 넘길 권한 JSON(dict) - permissions.json 의 workspace + web. allow_web 면 WebFetch·WebSearch 를 deny 에서 빼고 allow 에
"""
import json
import sys
from pathlib import Path

STUDIO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDIO))
from paths import load_settings  # noqa: E402
from .claude import ClaudeAgent  # noqa: E402
from .codex import CodexAgent  # noqa: E402

AGENTS = {"claude": ClaudeAgent, "codex": CodexAgent}
DEFAULT_AGENT, DEFAULT_MODEL = "claude", "opus"
LIMITS = {"sessionIdleMinutes": 60, "sessionTurnMinutes": 20, "sessionMax": 3, "sessionMaxTurns": 40, "sessionBudgetUsd": None,
          "engineMaxTurns": 150, "engineTurnMinutes": 60, "engineContinue": 2}  # 엔진 세션(개발 요청) - 도구 반복·턴 시간·한도에 걸렸을 때 같은 대화로 이어 하기 횟수


def get(name):
    cls = AGENTS.get(str(name or "").lower())
    if not cls:
        raise KeyError(f"모르는 에이전트: {name} (claude|codex)")
    return cls()


def probe_all(refresh=False):
    return {n: get(n).probe(refresh=refresh) for n in AGENTS}


def effective(ws_cfg=None):
    """전역 < 작업 공간 순으로 정한 에이전트·모델과 출처. (세션 시작 창의 선택은 호출 쪽이 덮어쓴다)"""
    s = load_settings()
    ws_cfg = ws_cfg or {}
    agent, a_src = DEFAULT_AGENT, "기본"
    if s.get("sessionAgent") in AGENTS:
        agent, a_src = s["sessionAgent"], "전역"
    if ws_cfg.get("sessionAgent") in AGENTS:
        agent, a_src = ws_cfg["sessionAgent"], "작업 공간"
    model, m_src = DEFAULT_MODEL, "기본"
    if s.get("sessionModel"):
        model, m_src = str(s["sessionModel"]), "전역"
    if ws_cfg.get("sessionModel"):
        model, m_src = str(ws_cfg["sessionModel"]), "작업 공간"
    limits = {k: (ws_cfg.get(k) if ws_cfg.get(k) is not None else s.get(k, v)) for k, v in LIMITS.items()}
    # 세션 단위로 고를 수 있는 권한 - 전역(관리자)이 켜야 하고, 작업 공간 설정에 false 로 두면 그 작업 공간에서는 꺼진다(켜는 것은 못 함)
    grants = {g: bool(s.get(k)) and ws_cfg.get(k) is not False for g, k in GRANT_KEYS.items()}
    return {"agent": agent, "model": model, "sources": {"agent": a_src, "model": m_src}, "limits": limits,
            "models": {n: get(n).models() for n in AGENTS}, "allowWeb": grants["web"], "grants": grants}


WEB_TOOLS = ("WebFetch", "WebSearch")  # 세션 단위 웹 검색 허용 때만 열리는 도구(curl·wget·powershell 은 여전히 막는다)
GRANT_KEYS = {"web": "sessionAllowWeb", "git": "sessionAllowGit", "push": "sessionAllowPush", "root": "sessionRepoRoot"}
# git 기록 허용 - 로컬 기록만(조회는 원래 허용). push 허용은 외부 전송이라 따로
GIT_ALLOW = ["Bash(git status*)", "Bash(git diff*)", "Bash(git log*)", "Bash(git show*)", "Bash(git rev-parse *)", "Bash(git add *)", "Bash(git commit *)",
             "Bash(git switch *)", "Bash(git checkout *)", "Bash(git merge *)", "Bash(git branch*)", "Bash(git stash*)", "Bash(git tag*)"]
PUSH_ALLOW = ["Bash(git push*)", "Bash(git pull*)", "Bash(git fetch*)"]
# git 을 열어도 막는 것 - 이력 재작성·강제 push·원격/설정 변경·다른 경로 지정·작업 내용 버리기
GIT_DENY = ["Bash(git push --force*)", "Bash(git push -f*)", "Bash(git push * --force*)", "Bash(git push * -f*)", "Bash(git push --mirror*)", "Bash(git push * --mirror*)",
            "Bash(git push --delete*)", "Bash(git push * --delete*)", "Bash(git push * :*)", "Bash(git reset --hard*)", "Bash(git clean*)", "Bash(git config*)",
            "Bash(git remote*)", "Bash(git filter-*)", "Bash(git rebase*)", "Bash(git -C *)", "Bash(git worktree*)", "Bash(git submodule*)", "Bash(git update-ref*)",
            "Bash(git reflog*)", "Bash(git gc*)", "Bash(git restore*)", "Bash(git checkout -- *)", "Bash(git checkout .*)", "Bash(git stash drop*)", "Bash(git stash clear*)",
            "Bash(git branch -D*)", "Bash(git branch * -D*)", "Bash(git tag -d*)", "Bash(git tag * -d*)"]


def claude_path(p):
    """권한 규칙의 절대 경로 표기 - `//d/Projects/x`(드라이브 문자 소문자, POSIX 구분자)."""
    s = Path(p).resolve().as_posix()
    if len(s) > 1 and s[1] == ":":
        s = "/" + s[0].lower() + s[2:]
    return "/" + s


def git_grants(perms, grants, repo_root=None):
    """git·push·저장소 루트 허용을 권한에 더한다(제자리). repo_root 는 작업 공간을 품은 저장소 루트(작업 공간 자신이면 None)."""
    if "git" in grants or "push" in grants:
        perms["allow"] += [x for x in GIT_ALLOW + (PUSH_ALLOW if "push" in grants else []) if x not in perms["allow"]]
        perms["deny"] += [x for x in GIT_DENY if x not in perms["deny"]]
    if "root" in grants and repo_root:
        r = claude_path(repo_root)
        perms["allow"] += [f"Read({r}/**)", f"Edit({r}/**)", f"Write({r}/**)"]
        perms["deny"] += [f"Edit({r}/.git/**)", f"Write({r}/.git/**)"]  # 저장소 내부 파일은 git 명령으로만
    return perms


def web_settings(allow_web=False):
    """웹 세션(claude -p --settings)에 넘길 설정 - 권한 템플릿의 workspace + web 을 합친 것(hooks 없음).
    allow_web 면 WebFetch·WebSearch 만 deny 에서 빼고 allow 에 넣는다(관리자가 전역을 켜고 세션 시작 때 고른 경우)."""
    tpl = json.loads((STUDIO / "agents" / "permissions.json").read_text(encoding="utf-8"))
    ws, web = tpl["workspace"]["permissions"], tpl["web"]["permissions"]
    perms = {"allow": list(ws.get("allow", [])), "deny": list(ws.get("deny", [])) + [x for x in web.get("deny", []) if x not in ws.get("deny", [])]}
    if allow_web:
        perms["deny"] = [x for x in perms["deny"] if x not in WEB_TOOLS]
        perms["allow"] += [x for x in WEB_TOOLS if x not in perms["allow"]]
    for k, v in web.items():
        if k not in ("allow", "deny"):
            perms[k] = v
    return {"permissions": perms}
