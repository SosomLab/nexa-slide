# -*- coding: utf-8 -*-
"""AI 세션 어댑터의 공통 틀 - 서버의 웹 세션 관리자는 이 인터페이스만 본다(docs/dev/web-session-design.md 4절).

어댑터가 정하는 것
  executable()   실행 파일 - 사용자 설정 agentPaths.<이름> → PATH
  probe()        설치·로그인·판·지원 옵션 → {agent, installed, loggedIn, version, path, verified, hint, doc, flags}
  turn_cmd(...)  한 턴 명령줄(프롬프트는 stdin 으로 - 인자에는 옵션만). 금지 옵션은 넣지 않는다
  parse(line)    stdout 한 줄 → 공통 이벤트 {type: init|text|tool|tool_result|result|error, …} 또는 None
공통 이벤트
  init         {sessionId, model}            세션이 시작됨(이어 가기 id·실제 모델)
  text         {text}                        에이전트의 글
  tool         {tool, summary}               도구 사용(파일 이름·명령 요약만)
  tool_result  {tool, ok}
  result       {sessionId, model, ok, turns, costUsd, usage, text}   턴 끝
  error        {message}
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

STUDIO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDIO))
from paths import load_settings  # noqa: E402

PROBE_TTL = 60
_PROBES = {}  # 이름 → (시각, 결과)


def run(args, timeout=20, cwd=None, env=None, inp=None):
    """외부 명령 한 번 - (코드, stdout, stderr). 바이트로 받아 utf-8 로 푼다(Windows 코드 페이지와 무관)."""
    kw = {}
    if os.name == "nt":
        kw["creationflags"] = subprocess.CREATE_NO_WINDOW
    try:
        r = subprocess.run([str(a) for a in args], capture_output=True, timeout=timeout, cwd=cwd, env=env,
                           input=inp.encode("utf-8") if isinstance(inp, str) else inp, **kw)
        return r.returncode, r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")
    except FileNotFoundError:
        return 127, "", "실행 파일 없음"
    except subprocess.TimeoutExpired:
        return 124, "", f"{timeout}초 안에 끝나지 않음"
    except OSError as e:
        return 126, "", str(e)


class Agent:
    name = ""
    label = ""
    guide_file = "CLAUDE.md"      # 작업 공간에서 읽는 안내 파일
    doc = ""                      # 설치·로그인 안내 문서(docs/…)
    default_models = []           # 별칭 목록(사용자 설정 sessionModels.<이름> 이 우선)
    verified = False              # 이 PC 에서 명령·출력 형식을 확인했는가(아니면 화면에 "미확인")
    exe_names = ()                # PATH 에서 찾을 이름들
    # 턴 프롬프트 `{shell}` 자리 - 이 도구가 파일을 읽고 고치고 명령을 돌리는 방법(프롬프트 본문은 Claude 의 Read/Edit 낱말로 적혀 있다)
    shell_note = ""

    def executable(self):
        p = (load_settings().get("agentPaths") or {}).get(self.name)
        if p:
            p = Path(str(p)).expanduser()
            return str(p) if p.is_file() else None
        for n in self.exe_names:
            w = shutil.which(n)
            if w:
                return w
        return None

    # ---------- 확인 ----------
    def probe(self, refresh=False):
        """설치·로그인·판·지원 옵션. 60초 기억(refresh 로 다시)."""
        c = _PROBES.get(self.name)
        if c and not refresh and time.time() - c[0] < PROBE_TTL:
            return c[1]
        exe = self.executable()
        out = {"agent": self.name, "label": self.label, "installed": bool(exe), "loggedIn": False, "version": "", "path": exe or "",
               "verified": self.verified, "hint": "", "doc": self.doc, "flags": {}, "models": self.models()}
        if not exe:
            out["hint"] = f"{self.label} 가 설치되어 있지 않다(PATH 에 없음) - {self.doc} 참고. 설치 위치가 다르면 사용자 설정 agentPaths.{self.name}"
        else:
            try:
                self._probe(exe, out)
            except Exception as e:  # noqa: BLE001 - 확인 실패도 결과로
                out["hint"] = f"확인 중 오류: {type(e).__name__}: {e}"
        if not self.verified and out["installed"]:
            out["hint"] = (out["hint"] + " · " if out["hint"] else "") + "이 어댑터는 이 PC 에서 확인되지 않았다(공식 문서 기준)"
        _PROBES[self.name] = (time.time(), out)
        return out

    def _probe(self, exe, out):
        raise NotImplementedError

    def models(self):
        lst = (load_settings().get("sessionModels") or {}).get(self.name)
        return list(lst) if isinstance(lst, list) and lst else list(self.default_models)

    # ---------- 실행 ----------
    def turn_cmd(self, model, resume_id=None, settings_path=None, max_turns=None, budget_usd=None, flags=None, allow_web=False, add_dirs=None,
                 new_session_id=None, name=None):
        """한 턴의 명령줄. wsession 이 모든 인자를 키워드로 넘기므로 어댑터는 쓰지 않는 것도 받아야 한다(codex 는 allow_web·add_dirs·new_session_id·name 을 무시)."""
        raise NotImplementedError

    def env(self):
        """자식에 더할 환경 변수(토큰 등은 운영자가 환경에 두고, 여기서는 출력 형식만 고정)."""
        return {"PYTHONIOENCODING": "utf-8", "NO_COLOR": "1"}

    def parse(self, line):
        raise NotImplementedError

    @staticmethod
    def _json(line):
        try:
            d = json.loads(line)
            return d if isinstance(d, dict) else None
        except ValueError:
            return None
