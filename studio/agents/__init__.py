# -*- coding: utf-8 -*-
"""AI 세션 어댑터 묶음 - claude(확인됨) · codex(미확인). docs/dev/web-session-design.md 4·7절.

    get(name)                 어댑터 인스턴스
    probe_all(refresh)        {이름: probe 결과}
    effective(ws_cfg)         우선순위를 적용한 기본값 {agent, model, sources} - 전역(사용자 설정 sessionAgent·sessionModel) < 작업 공간 설정(같은 키)
    web_settings()            웹 세션에 --settings 로 넘길 권한 JSON(dict) - permissions.json 의 workspace + web
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
LIMITS = {"sessionIdleMinutes": 60, "sessionTurnMinutes": 20, "sessionMax": 3, "sessionMaxTurns": 40, "sessionBudgetUsd": None}


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
    return {"agent": agent, "model": model, "sources": {"agent": a_src, "model": m_src}, "limits": limits,
            "models": {n: get(n).models() for n in AGENTS}}


def web_settings():
    """웹 세션(claude -p --settings)에 넘길 설정 - 권한 템플릿의 workspace + web 을 합친 것(hooks 없음)."""
    tpl = json.loads((STUDIO / "agents" / "permissions.json").read_text(encoding="utf-8"))
    ws, web = tpl["workspace"]["permissions"], tpl["web"]["permissions"]
    perms = {"allow": list(ws.get("allow", [])), "deny": list(ws.get("deny", [])) + [x for x in web.get("deny", []) if x not in ws.get("deny", [])]}
    for k, v in web.items():
        if k not in ("allow", "deny"):
            perms[k] = v
    return {"permissions": perms}
