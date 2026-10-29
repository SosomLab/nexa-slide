# -*- coding: utf-8 -*-
"""nexa-slide 로컬 서버 (표준 라이브러리만).

    python3 studio/server.py --workspace <작업 공간> [--port N | --port auto]

포트: --port > nexa-slide.json "port" > 5600. 이미 쓰는 포트면 알리고 끝낸다(--port auto 는 그 포트부터 빈 포트를 찾는다).
작업 공간마다 포트를 다르게 주면 여러 작업 공간의 서버를 함께 띄울 수 있다. 실행 중 정보는 <out>/.studio/server.json.

정적 경로
  /studio/…   엔진 폴더(편집기 index.html·render.js·studio.js). /studio/tokens.json 은 작업 공간 토큰(없으면 엔진 기본값)
  /out/…      작업 공간 산출물(PPTX·렌더 PNG). 점(.)으로 시작하는 경로는 막는다(.studio 상태·.history 백업)
  그 밖       assetRoot(덱 그림 경로 src·img 의 기준 폴더)
API
  GET  /api/decks                    덱 목록
  GET  /api/deck/<id>                덱 JSON (헤더 X-Deck-Version = 파일 mtime_ns)
  PUT  /api/deck/<id>?base=<ver>     덱 저장(원자적 쓰기, .history 백업 50개). base 가 현재와 다르면 409 (force=1 이면 무시)
                     &merge=1           base 가 다르면 409 대신 3-way 병합(deckmerge.py, docs/collab.md 1단계) → {merged, conflicts, deck}. 기준본이 없으면 409 reason=no-base
  GET  /api/version/<id>             {"deck": ver, "requests": ver}
  GET  /api/stream/<id>?tab=<탭>      실시간(동시 편집 2단계, collab.py) - SSE. event: version(= /api/version 내용, 바뀔 때만) · presence({list}) · ping(10초).
                                     파일 버전을 0.5초마다 보므로 편집기 저장·AI 의 save_deck·요청 파일 Edit 가 곧바로 간다. 끊기면 그 탭의 presence 를 지운다
  GET  /api/proposals/<id>            AI 제안 목록(동시 편집 3단계 첫 조각, proposals.py) [{request, created, items: [{id, kind, title, detail}]}]
  POST /api/proposals/<id>            {action: create, request, deck, base?, baseDoc?} - save_deck --propose 가 남긴다(파일은 그대로)
                                     {action: accept, request, items?} - 고른 단위(없으면 전부)를 기준본에 얹어 지금 파일과 병합 저장(원장 action accept)
                                     {action: discard, request, items?} - 버리기
  GET  /api/reqdiff/<id>?request=<요청> 그 요청으로 AI 가 저장한 변경 - 시트면 바뀐 셀 {cells: [{tab, name, key, before, after}], count}.
                                     원장에서 그 요청의 첫 저장 직전 백업 ↔ 마지막 저장 직후(다음 원장 줄의 직전 백업 또는 지금 파일)를 비교한다
  POST /api/presence/<id>            {tab, where, editing, user?} → 함께 보는 사람(메모리, 15초) · {leave: true} 로 뺀다. 응답 {color, list}
  GET  /api/requests/<id>            요청 메모 목록
  POST /api/requests/<id>            {"action": "add"|"update"|"delete"|"send"|"discard", ...} — add 는 status draft(초안)·region(영역)·attachments 가능
  POST /api/attach/<id>              요청 첨부 올리기 {name, type, data(base64)} → {path, name, type, size, url} — out/attach/<덱>/ (그림·PDF·글·오피스, 12MB)
  GET  /api/history/<id>             저장 전 자동 백업 목록 · ?f=<파일> 이면 그 시점 덱 JSON
  POST /api/export/<id>              PPTX 생성 → {"url": "/out/<id>.pptx"} · 시트 문서(kind sheet)는 xlsx → "/out/<id>.xlsx"
  GET  /api/render/<id>              마지막 PowerPoint 렌더 PNG 목록
  POST /api/render/<id>              PPTX 생성 + PowerPoint COM 으로 PNG 렌더
  GET  /api/layouts                  레이아웃 목록
  POST /api/newslide                 {"layout", "part"} → 자리 표시 내용으로 만든 슬라이드
  GET  /api/fonts                    글꼴 프리셋 목록·현재 값
  GET  /api/fontfile/<이름>          설치된 글꼴 파일(편집기 @font-face 용 — fonts.css)
  POST /api/fonts                    {"preset": 이름} → tokens.json 의 fonts 를 그 프리셋으로(set_fonts.py)
  GET  /api/config                   작업 공간 이름·브랜드(로고·워드마크·파비콘·로고 비율)
  GET  /api/session                  Claude 세션 연결 상태(watch_requests.py 하트비트) + 처리 중 요청 수
  POST /api/flush/<id>               "지금 보내기" — 대기 시간 없이 열린 요청을 세션에 바로 전달하라는 신호
  GET  /api/templates                템플릿 목록과 이 작업 공간이 고른 템플릿
  GET  /api/check/<id>               레이아웃 검사(check_layout.py) — 겹침·넘침·최소 글자·슬라이드 밖·고정폭 정렬
변경 원장(0.16.0 - ledger.py · deckdiff.py · docs/change-ledger.md)
  PUT  /api/deck/<id>?origin=editor|claude&action=save|restore&request=<요청 id>&note=…&label=… + 헤더 X-Nexa-Tab
                                     저장할 때마다 decks/.history/<id>/changes.jsonl 에 한 줄(출처·전후 해시·장·요소 diff). 응답에 seq
  GET  /api/version/<id>             응답에 changes(원장 파일 버전). 이 핸들러가 밖에서 바뀐 덱도 발견해 원장에 적는다(claude 추정 | external)
  GET  /api/changes/<id>             원장 조회 - ?limit=&before=<seq>&since=<seq>&origin=a,b&slide=<sid>&group=1(묶음)&recent=1(슬라이드별 최근)&seq=N(한 줄)
시작 페이지(허브) — studio/home.html · hub.py
  GET  /api/home                     기준 폴더·최근 작업·템플릿·시작용 내용·샘플·현재 작업 공간
  POST /api/project                  {"action": "create"|"plan"|"open"|"start"|"stop"|"demo"|"forget", ...} → {"url": 그 작업 공간 서버 주소}
                                     start·stop = 작업 공간 서버만 띄우기·끄기(페이지 이동 없음, 이 페이지의 서버 자신은 끄지 않음)
                                     plan = 만들 폴더·포트·init_workspace 명령(PowerShell·bash) — create 는 그 명령을 실행
  POST /api/settings                 {"projectsRoot"?, "samples"?} — 사용자 설정(엔진·작업 공간 밖)
  GET  /api/fs?path=<폴더>           폴더 고르기 — 하위 폴더 목록(git 저장소·작업 공간 표시)
  GET  /api/preview?template=&starter=  템플릿 × 시작용 내용 미리보기 — 사용자 설정 폴더의 임시 작업 공간에 빌드한 덱·토큰
  /preview/<템플릿>--<내용>/…        미리보기 덱의 그림(assetRoot)
AI 세션(B 단계 - docs/dev/web-session-design.md · studio/agents/ · wsession.py)
  GET  /api/agent[?refresh=1]        어댑터 확인 {agents: {claude, codex}: {installed, loggedIn, version, verified, hint, doc, flags, models}} +
                                     우선순위(전역 < 작업 공간)로 정한 agent·model·sources·limits·models
  GET  /api/wsession                 웹 세션 상태 {state: off|ready|running|error, agent, model, modelActual, sessionId, startedBy, startedAt, turns, lastError,
                                     open, working, manual(살아 있는 수동 감시), limits, seq, last(끊긴 마지막 세션)} - 작업 공간 서버에서만(허브 404)
  POST /api/wsession                 {"action": "start", agent?, model?, saveAs?: local|shared} · {"action": "stop"} · {"action": "model", model, saveAs?}
                                     · {"action": "defaults", sessionAgent?, sessionModel?, saveAs?} - 로그인 사용자 누구나(로컬 직접 접속은 local)
  GET  /api/wsession/events?since=N  진행 이벤트 - Accept: text/event-stream(또는 ?sse=1)이면 SSE(id=seq, event=종류, data=JSON, 25초마다 keepalive, Last-Event-ID 로 재개),
                                     아니면 폴링 JSON {state, seq, events: [{seq, t, type: state|turn.start|init|text|tool|tool_result|turn.end|warn|error|model|idle, …}]}.
                                     허브 중계는 text/event-stream 응답을 줄 단위로 바로 흘린다
  GET  /api/wsession/log?turn=N      그 턴의 어댑터 출력 원문(줄 목록)
  GET  /api/wsession/pulse           처리 중 턴의 맥박 {state, seq, turn, turnSec, outSec, tools, alive, tool?: {name, summary, sec}} - 허브 엔진 세션은 /api/engine/session/pulse
중계(허브 한 포트로 여러 작업 공간 — hub.py ws_id·proxy_target)
  /w/<id>/…                          그 작업 공간 서버(별도 프로세스·포트)로 그대로 넘기고 응답을 돌려준다(Location 은 접두를 다시 붙임).
                                     꺼져 있으면 띄운다(--port auto — 설정 포트가 쓰는 중이면 빈 포트). nexa.py 로 띄운 서버가 있으면 그 서버로.
                                     편집기(studio.js·menu.js·slide.html)는 주소의 /w/<id> 접두를 보고 /api·/out·그림 경로 앞에 붙인다.
보기 전용 공유 링크(0.22.25 - share.py · docs/auth.md) - 허브, 로그인 없이 토큰으로 덱 1개 보기만
  /s/<토큰>/…                         토큰 → 링크(만료·회수) → (비밀번호면) 쿠키 nexa_share → 허용 목록(view.html·render.js·i18n·tokens.json·fonts·
                                     그 덱의 /api/deck/<덱>(notes·hidden 장 제거)·덱이 참조하는 그림)만 그 작업 공간 서버로 중계. 그 밖·모든 쓰기 403.
  GET/POST /api/share · POST /api/share/<id>   (로그인 사용자) 목록·만들기 {action: "create", ws, deck, days?, password?} · 회수 {action: "revoke"}

작업 공간 없이 띄우면(또는 작업 공간에 덱이 없으면) / 는 시작 페이지로 간다. 덱이 있으면 편집기(Studio)로.
엔진 폴더 안의 작업 공간은 열지 않는다(허브로 뜬다) — 슬라이드 내용은 엔진 밖에 둔다.
"""
import argparse
import datetime as dt
import http.client
import io
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from http import HTTPStatus
from email.utils import formatdate
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from collections import OrderedDict
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

STUDIO = Path(__file__).resolve().parent
sys.path.insert(0, str(STUDIO))
from common import ASSET_ROOT, BRAND, CONFIG, DECKS, DEFAULT_PORT, HUB, OUT, REFUSED, SERVER_INFO, STATE, TEMPLATE, WORKSPACE, fonts_dir, list_templates, read_config, resolve_tokens, running_server, safe_id  # noqa: E402
from watch_requests import session_status  # noqa: E402
import auth  # noqa: E402
import collab  # noqa: E402
import deckdiff  # noqa: E402
import deckmerge  # noqa: E402
import proposals  # noqa: E402
import sheet_struct  # noqa: E402
import ledger  # noqa: E402
import hub  # noqa: E402
import share  # noqa: E402
sys.path.insert(0, str(STUDIO.parent / "docs" / "research" / "review"))
try:  # 템플릿 검토(검토 등록부) — 시작 페이지 메뉴 "템플릿 검토"(/review)
    import review_server as review  # noqa: E402
except ImportError:  # 문서 폴더 없이 엔진만 배포한 경우
    review = None

WS = None  # 웹 AI 세션 관리자(작업 공간 서버에서만 - main 에서 만든다)
WS_ENGINE = None  # 엔진 개발 세션 관리자(허브에서만 - wsession.EngineProfile)
HISTORY_KEEP = 50
RENDER_LOCK = threading.Lock()
WRITE_LOCK = threading.Lock()
PREVIEW_LOCK = threading.Lock()
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/vnd.openxmlformats-officedocument.presentationml.presentation", ".pptx")
mimetypes.add_type("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx")
mimetypes.add_type("application/vnd.ms-excel.sheet.macroEnabled.12", ".xlsm")


def ver(p: Path):
    try:
        return str(p.stat().st_mtime_ns)
    except FileNotFoundError:
        return "0"


def _deploy_stop_engine():
    """배포가 '턴 마무리 대기'를 지나면(= 곧 허브 재시작) 웹 엔진 세션을 끈다 - 그 전(병합·시험)에는 세션이 계속 요청을 처리한다.
    service.py 는 허브를 강제 종료해 세션의 자식 프로세스가 남으므로 허브가 먼저 정리한다. 배포가 실패로 끝나면 끄지 않는다."""
    import engine_deploy
    while True:
        time.sleep(1)
        d = engine_deploy.status()
        if d.get("state") != "running":
            return
        if any(x.get("step") == "턴 마무리 대기" for x in d.get("steps") or []):
            if WS_ENGINE is not None and WS_ENGINE.state != "off":
                WS_ENGINE.stop("deploy")
            return


def deck_path(i):
    return DECKS / f"{i}.json"


def req_path(i):
    return DECKS / f"{i}.requests.json"


atomic_write = ledger.atomic_write  # 0.16.0 - ledger.py 로 옮김(build_deck · save_deck 도 같은 것을 쓴다)


def backup(i, data=None, suffix=""):
    """덮어쓰기 직전 덱을 .history/<id>/<시각><suffix>.json 으로 - 파일(copy2) 또는 서버 메모리의 바이트(data). 만든 파일 이름을 돌려준다.
    50개(HISTORY_KEEP) 상한은 -build · -ext 도 함께 센다."""
    src = deck_path(i)
    if data is None and not src.exists():
        return None
    h = DECKS / ".history" / i
    h.mkdir(parents=True, exist_ok=True)
    name = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f") + suffix + ".json"
    if data is None:
        shutil.copy2(src, h / name)
    else:
        (h / name).write_bytes(data)
    files = sorted(h.glob("*.json"))
    for old in files[:-HISTORY_KEEP]:
        old.unlink(missing_ok=True)
    return name


# ---------- 변경 원장 - 서버가 마지막으로 알고 있는 덱 파일 상태(자기 쓰기와 밖의 쓰기를 구분하는 유일한 기억) ----------
LAST = {}      # deck → {"sig": (mtime_ns, size), "hash", "data", "obj"}
PENDING = {}   # deck → {"hash", "at"} 밖에서 바뀐 후보 - 한 폴링(GRACE)만 기다려 build·save_deck 가 자기 줄을 남길 틈을 준다
GRACE = 1.5


def _load(p: Path):
    data = p.read_bytes()
    try:
        return data, json.loads(data.decode("utf-8"))
    except ValueError:
        return data, None  # 쓰는 중(불완전) - 다음에 다시


def _remember(i, p, data, obj):
    LAST[i] = {"sig": ledger.sig(p), "hash": ledger.sha256(data), "data": data, "obj": obj}
    PENDING.pop(i, None)
    _keep_base(i, ver(p), obj)


# ---------- 병합 저장의 기준본(docs/collab.md 1단계) - 이 서버가 보여 주거나 쓴 판(버전 → 문서)을 덱마다 최근 BASE_KEEP 개 기억한다 ----------
# 편집기·AI 가 PUT ?merge=1&base=<판> 으로 보내면 그 판을 기준본으로 3-way 병합한다(deckmerge.py). 없으면(서버 재시작 등) 409 - 데이터는 잃지 않는다
BASES = {}     # deck → OrderedDict(버전 → 문서)
BASE_KEEP = 40
BASE_LOCK = threading.Lock()


def _keep_base(i, v, obj):
    if not isinstance(obj, dict) or not v or v == "0":
        return
    with BASE_LOCK:
        d = BASES.setdefault(i, OrderedDict())
        d[v] = obj
        d.move_to_end(v)
        while len(d) > BASE_KEEP:
            d.popitem(last=False)


def _base_doc(i, v):
    with BASE_LOCK:
        return (BASES.get(i) or {}).get(v)


def _meta(p, data):
    return {"ver": ver(p), "size": len(data), "hash": ledger.sha256(data)}


def _working_requests(i):
    try:
        return [r.get("id") for r in json.loads(req_path(i).read_text(encoding="utf-8")) if r.get("status") == "working"]
    except (OSError, ValueError):
        return []


def attribute(i):
    """밖에서 바뀐 덱의 출처 추정 - 결정 트리(docs/change-ledger.md). (origin, confidence, actor, evidence)"""
    st = session_status()
    working = _working_requests(i)
    act = activity()
    w = act.get("watcher") if act else None
    if st.get("connected") and working:
        return "claude", "inferred", {"label": st.get("label", ""), "request": working[0]}, \
            {"heartbeat_age_s": st.get("age"), "working": working, "watcher_state": w.get("state") if w else None}
    if st.get("connected") and w and w.get("state") == "busy":
        return "claude", "inferred", {"label": st.get("label", "")}, \
            {"heartbeat_age_s": st.get("age"), "watcher_state": "busy", "source": w.get("source"), "prompt": (w.get("prompt") or "")[:80], "watcher_id": w.get("id")}
    if act and act.get("othersBusy"):
        return "claude", "inferred", {"label": ""}, {"othersBusy": act["othersBusy"]}
    return "external", "unknown", {}, None


def track(i):
    """이 서버가 덱을 처음 볼 때 - 원장 마지막 줄의 after.hash 와 파일이 다르면 '서버가 꺼진 사이 바뀜' 한 줄(startup)을 적고 상태를 기억한다. WRITE_LOCK 안."""
    p = deck_path(i)
    if i in LAST or not p.exists():
        return
    data, obj = _load(p)
    if obj is None:
        return
    last = ledger.last_change(i)
    want = (last.get("after") or {}).get("hash") if last else None
    if want and want != ledger.sha256(data):
        before_obj, bname = None, None
        hdir = DECKS / ".history" / i
        for f in sorted(hdir.glob("*.json"), reverse=True) if hdir.exists() else []:
            if f.name == "last-build.json":
                continue
            try:
                b = f.read_bytes()
            except OSError:
                continue
            if ledger.sha256(b) == want:
                try:
                    before_obj, bname = json.loads(b), f.name
                except ValueError:
                    pass
                break
        try:
            ledger.record(i, before_obj, {**last["after"], "backup": bname}, obj, _meta(p, data), "external", "unknown", "startup",
                          {"note": "서버가 꺼진 사이에 바뀜" + ("" if bname else " - 직전 백업 없음(상세 없음)")})
        except Exception as e:  # noqa: BLE001
            sys.stderr.write(f"ledger startup {i}: {e}\n")
    _remember(i, p, data, obj)


def detect(i, immediate=False):
    """밖에서 바뀐 덱 발견(2초 폴링마다, WRITE_LOCK 안). stat 서명 → 해시 → 유예 → 원장 꼬리 대조 → 출처 추정 → -ext 백업 + detect 줄."""
    p = deck_path(i)
    if not p.exists():
        LAST.pop(i, None)
        return
    if i not in LAST:
        track(i)
        return
    last = LAST[i]
    sg = ledger.sig(p)
    if sg == last["sig"]:
        PENDING.pop(i, None)
        return
    data, obj = _load(p)
    if obj is None:
        return
    h = ledger.sha256(data)
    if h == last["hash"]:  # mtime 만 바뀜(touch·동기화) - 기록하지 않는다
        last["sig"] = sg
        PENDING.pop(i, None)
        return
    if not immediate:
        pend = PENDING.get(i)
        if not pend or pend["hash"] != h:
            PENDING[i] = {"hash": h, "at": time.time()}
            return
        if time.time() - pend["at"] < GRACE:
            return
    for e in ledger.tail(i, 5):  # build · save_deck 가 이미 자기 줄을 남겼으면 그것이 정답
        if (e.get("after") or {}).get("hash") == h:
            _remember(i, p, data, obj)
            return
    origin, conf, actor, evidence = attribute(i)
    bname = backup(i, data=last["data"], suffix="-ext")  # 덮이기 직전 상태는 서버 메모리에만 남아 있다 - 복원용으로 저장
    before = {"ver": str(last["sig"][0]), "size": last["sig"][1], "hash": last["hash"], "backup": bname}
    try:
        ledger.record(i, last["obj"], before, obj, _meta(p, data), origin, conf, "detect", actor, evidence)
    except Exception as e:  # noqa: BLE001
        sys.stderr.write(f"ledger detect {i}: {e}\n")
    _remember(i, p, data, obj)


def dumps(o):
    return json.dumps(o, ensure_ascii=False, indent=1)


def run(cmd, timeout):
    r = subprocess.run(cmd, cwd=str(WORKSPACE or STATE), capture_output=True, timeout=timeout,
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    out = (r.stdout or b"").decode("utf-8", "replace") + (r.stderr or b"").decode("utf-8", "replace")
    return r.returncode, out.strip()


def export(i):
    return run([sys.executable, str(STUDIO / "export_pptx.py"), i], 120)


def deck_kind(i):
    """문서 종류 - "sheet"(시트, docs/sheets.md) 또는 "deck"(슬라이드)."""
    try:
        return json.loads(deck_path(i).read_text(encoding="utf-8")).get("kind") or "deck"
    except (OSError, ValueError, AttributeError):
        return "deck"


CELL_RANGE = re.compile(r"^[A-Z]{1,3}[1-9][0-9]{0,6}(:[A-Z]{1,3}[1-9][0-9]{0,6})?$")  # 시트 요청 대상 범위(A1 · B2:D5)


def activity():
    """세션 활동(session_hook.py 가 쓴 out/.studio/activity.json) — 요청 감시 담당 세션의 상태와 다른 세션 작업 수.
    상태: idle(대기) · busy+chat(대화 입력 처리 중) · busy+auto(요청 등 대화 밖 작업). 15분 넘게 소식 없는 작업 중은 unknown."""
    try:
        data = json.loads((STATE / "activity.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    now = dt.datetime.now()
    out = []
    for sid, s in data.get("sessions", {}).items():
        try:
            last = dt.datetime.fromisoformat(s.get("last") or s.get("since"))
            since = dt.datetime.fromisoformat(s.get("since") or s.get("last"))
        except (TypeError, ValueError):
            continue
        st = s.get("state", "idle")
        if st == "busy" and (now - last).total_seconds() > 900:
            st = "unknown"
        out.append({"id": sid[:8], "state": st, "source": s.get("source", ""), "prompt": s.get("prompt", ""), "watcher": bool(s.get("watcher")),
                    "minutes": int((now - since).total_seconds() // 60), "last": s.get("last")})
    if not out:
        return None
    w = max((x for x in out if x["watcher"]), key=lambda x: x["last"] or "", default=None)
    return {"watcher": w, "othersBusy": sum(1 for x in out if x is not w and x["state"] == "busy"), "sessions": len(out)}


ENGINE_UI = ("index.html", "studio.js", "sheet.html", "sheet.js", "sheetnew.js", "sheetcalc.js", "sheetx.js", "wsession.js", "nexa-requests.js", "nexa-requests.css", "nexa-merge.js", "nexa-live.js", "render.js", "menu.js", "fonts.css", "i18n.js", "i18n/en.js", "i18n/en.pages.js", "i18n/en.review.js")


def hub_ui_stamp():
    """허브 화면(시작 페이지·/engine·계정·글꼴 등 studio/*.html·*.js·i18n/*.js) 판 - 바뀌면 열려 있는 허브 페이지가 [새로 고침]을 안내한다(menu.js, /api/engine/notice 에 실음)."""
    files = list(STUDIO.glob("*.html")) + list(STUDIO.glob("*.js")) + list((STUDIO / "i18n").glob("*.js"))
    return max((ver(f) for f in files), key=int, default="0")


def workspace_stamp():
    """편집기가 새로 고침·목록 갱신을 알 수 있게 하는 값(2초 폴링에 같이 보냄).
    deckIds/decksVer = 덱 목록과 그 덱들의 마지막 변경(다른 덱 추가·삭제·수정), config = nexa-slide.json(템플릿·글꼴·로고),
    engine = 편집기 코드와 템플릿 파일(엔진 업데이트) - config·engine 이 바뀌면 화면을 새로 고쳐야 반영된다."""
    files = [] if HUB or not DECKS.is_dir() else [f for f in DECKS.glob("*.json") if not f.name.endswith(".requests.json")]
    eng = [STUDIO / n for n in ENGINE_UI] + [f for f in (STUDIO / "templates").rglob("*.json")]
    if not HUB and (WORKSPACE / "templates").is_dir():  # 작업 공간 템플릿(회사 템플릿 - extends+tokenOverrides)도 바뀌면 새로 고침 안내
        eng += [f for f in (WORKSPACE / "templates").rglob("*.json")]
    return {"deckIds": sorted(f.stem for f in files), "decksVer": max((ver(f) for f in files), key=int, default="0"),
            "config": "0" if HUB else max(ver(WORKSPACE / "nexa-slide.json"), ver(WORKSPACE / "nexa-slide.local.json"), key=int), "engine": max((ver(f) for f in eng), key=int, default="0")}


def export_name(stem, ext):
    """받는 파일 이름 = 덱 제목 + 꼬리(.pptx · -fonts.pptx · .pdf). 저장은 out/<id>… 그대로(렌더·비교 도구가 id 로 찾는다) - studio.js exportName 과 같은 규칙.
    stem 이 '<id>-fonts' 면 제목 뒤에 ' - 글꼴 포함'. 덱이 없으면 stem 그대로."""
    i, tail = (stem[:-6], " - 글꼴 포함") if stem.endswith("-fonts") else (stem, "")
    try:
        title = json.loads(deck_path(i).read_text(encoding="utf-8")).get("title") or i
    except (OSError, ValueError):
        return f"{stem}{ext}"
    name = re.sub(r"[\/:*?\"<>|\x00-\x1f]+", " ", str(title))
    name = " ".join(name.split())[:120] or i
    return f"{name}{tail}{ext}"


def has_decks():
    return not HUB and DECKS.is_dir() and any(not f.name.endswith(".requests.json") for f in DECKS.glob("*.json"))


# ---------- 중계 대상 기억 - 매 요청(2초 폴링)마다 server.json·/api/config 를 묻지 않게 잠시 기억한다. 연결이 안 되면 잊고 다시 찾는다 ----------
PROXY = {}  # 중계 이름 → {"ws", "port", "at"}
PROXY_LOCK = threading.Lock()
PROXY_TTL = 60
HOP_HEADERS = {"connection", "keep-alive", "transfer-encoding", "te", "trailer", "upgrade", "proxy-connection", "host"}


def proxy_target(wid):
    with PROXY_LOCK:
        c = PROXY.get(wid)
        if c and time.time() - c["at"] < PROXY_TTL:
            return c["ws"], c["port"]
        ws, port = hub.proxy_target(wid)  # 떠 있으면 그 서버, 꺼져 있으면 띄운다(최대 10초)
        PROXY[wid] = {"ws": ws, "port": port, "at": time.time()}
        return ws, port


def forget_target(wid):
    with PROXY_LOCK:
        PROXY.pop(wid, None)


def render_list(i):
    d = OUT / i
    files = sorted(d.glob("slide-*.png")) if d.exists() else []
    return [f"/out/{i}/{f.name}?v={f.stat().st_mtime_ns}" for f in files]


MUTATING = {"POST", "PUT", "DELETE", "PATCH"}
AUTH_FREE = {"/login", "/setup", "/api/auth/state", "/api/auth/login", "/api/auth/setup", "/studio/i18n.js"}  # 허브에서 로그인 없이 닿는 전부(페이지는 CSS·JS 내장 + 표시 언어 사전)
POLL_RX = re.compile(r"(^|/w/[^/]+)/api/(version/[^/?]+|presence/[^/?]+|session|engine/notice|home/live)$")  # 주기 폴링 - /api/version/<덱> · /api/session · 알림·시작 페이지 갱신 (/api/wsession 은 아님)
SERVER_NAME = "hub" if HUB else None  # 접근 로그 server 필드 - 작업 공간은 중계 이름(ws id, 저장소형은 모두 slides/ 라 폴더 이름으로는 구분이 안 된다)


def _is_poll(path):
    return bool(POLL_RX.search((path or "").split("?")[0]))


# ---------- 보기 전용 공유 링크(허브 /s/<토큰>/…) - share.py · docs/auth.md ----------
SHARE_ASSETS = {}  # 링크 id → {"paths": 덱이 참조하는 상대 경로 집합, "at"} - 덱 JSON 을 내줄 때 계산해 그 파일들만 중계한다
SHARE_STATIC = {"/studio/render.js", "/studio/i18n.js", "/studio/tokens.json", "/studio/code_langs.json", "/studio/fonts.css", "/api/fontcss"}
SHARE_STATIC_RX = re.compile(r"^(/studio/i18n/[A-Za-z0-9_.-]+\.js|/api/fontfile/[A-Za-z0-9_.-]+|/wsfonts/[^/]+)$")
SHARE_DENIED_HTML = """<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>nexa-slide</title><style>body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;background:#1a1a1a;color:#eee;font:15px/1.6 "Malgun Gothic","Apple SD Gothic Neo",system-ui,sans-serif}
main{max-width:460px;padding:32px 28px;background:#262626;border-radius:16px}h1{font-size:19px;margin:0 0 10px}p{margin:6px 0;color:#ccc}.en{color:#999;font-size:13px}</style></head>
<body><main><h1>이 링크는 열 수 없습니다</h1><p>주소가 잘못됐거나, 기한이 지났거나, 회수된 공유 링크입니다. 링크를 보낸 사람에게 새 링크를 요청해 주세요.</p>
<p class="en">This link cannot be opened - it may be wrong, expired or revoked. Ask the sender for a new link.</p></main></body></html>"""


def _share_assets(deck: dict) -> set:
    """덱 JSON 이 참조하는 상대 경로(그림 src 등) - 공유 링크로 열 수 있는 작업 공간 파일은 이것뿐."""
    out = set()

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("src", "image", "poster") and isinstance(v, str) and v and not re.match(r"^(https?:|data:|blob:|/|#)", v):
                    out.add(unquote(v.split("?")[0].split("#")[0]).lstrip("./"))
                else:
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(deck)
    return out


def share_filter_deck(lid, data: bytes) -> bytes:
    """공유 응답용 덱 - 발표자 노트와 숨김 슬라이드를 뺀다(허브에서, 작업 공간 서버 응답을 고쳐서). 보이는 장의 원래 쪽 번호는 page 에."""
    d = json.loads(data.decode("utf-8"))
    slides = []
    for i, s in enumerate(d.get("slides") or []):
        if s.get("hidden"):
            continue
        s = {k: v for k, v in s.items() if k != "notes"}
        s["page"] = i + 1
        slides.append(s)
    d["slides"] = slides
    d.pop("notes", None)
    SHARE_ASSETS[lid] = {"paths": _share_assets(d), "at": time.time()}
    return json.dumps(d, ensure_ascii=False).encode("utf-8")


class H(BaseHTTPRequestHandler):
    server_version = "nexa-slide/0.2"
    # 요청마다 - 인증 결과·로그용
    user = role = None
    via_hub = False      # 허브 중계를 거쳐 왔다(X-Nexa-Hub-Key 확인됨) - 작업 공간 서버에서
    _status = _err = _event = None
    _share_ws = None     # 공유 링크(/s/…) 요청이면 그 작업 공간의 중계 이름(접근 로그 ws)

    def log_message(self, fmt, *args):
        if _is_poll(self.path):
            return  # 2초 폴링은 기록하지 않는다
        sys.stderr.write("%s %s\n" % (self.log_date_time_string(), share.mask_path(fmt % args)))  # 공유 토큰 원문은 서버 로그에도 남기지 않는다

    def send_response(self, code, message=None):
        self._status = code
        super().send_response(code, message)

    # ---------- 응답 도우미 ----------
    def send_json(self, obj, status=200, headers=None):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(b)

    def err(self, status, msg):
        if status >= 400:
            self._err = msg
        self.send_json({"ok": False, "error": msg}, status)

    def body_json(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b""
        return json.loads(raw.decode("utf-8") or "null")

    # ---------- 인증 · 접근 로그 (요청 하나의 바깥 틀) ----------
    def route(self, method):
        """Host 검사 → (허브) 로그인·Origin 검사 → 라우팅. 어떻게 끝나든 접근 로그 한 줄."""
        t0 = time.monotonic()
        self.user = self.role = None
        self.via_hub = False
        self._status = self._err = self._event = self._share_ws = None
        try:
            self.dispatch(method)
        except Exception as e:  # noqa: BLE001 - 라우팅 밖에서 난 예외(핸들러 안의 예외는 _route 가 500 으로 답한다)
            self._err = f"{type(e).__name__}: {e}"
            try:
                self.err(500, self._err)
            except Exception:  # noqa: BLE001 - 이미 응답을 보냈거나 연결이 끊김
                pass
        finally:
            self.access_log(method, t0)

    def dispatch(self, method):
        path = urlparse(self.path).path
        if not self.host_ok():  # DNS 리바인딩 - 루프백·publicHosts·Cloudflare 경유가 아닌 Host 는 거절
            return self.err(400, "허용되지 않은 Host")
        key = self.headers.get("X-Nexa-Hub-Key")
        if key is not None:
            if HUB or not auth.key_ok(key):  # 허브는 이 헤더를 받지 않는다(밖에서 위조한 것) · 작업 공간 서버는 비밀이 맞아야
                return self.err(403, "hub key")
            self.via_hub = True
            self.user = self.headers.get("X-Nexa-User") or None
            self.role = self.headers.get("X-Nexa-Role") or None
        if HUB:
            if path == "/s" or path.startswith("/s/"):  # 보기 전용 공유 링크 - 로그인 대신 토큰(AUTH_FREE 와 별도의 접두 분기, authenticate 전)
                return self.share_route(method, path)
            if not self.authenticate(method, path):
                return
        elif not self.via_hub and method in MUTATING and not self.origin_ok(strict=False):
            # 작업 공간 서버 로컬 직접 접속 - 로그인은 없지만 다른 사이트에서 보낸 상태 변경(CSRF)은 막는다. CLI(Origin 없음)는 그대로
            return self.err(403, "다른 출처의 요청")
        self._route(method)

    def authenticate(self, method, path):
        """허브: 로컬이어도 모든 요청에 로그인이 필요하다(터널이 127.0.0.1 로 들어와 안팎을 가를 수 없다). 예외는 AUTH_FREE 만."""
        if path in AUTH_FREE:
            if method in MUTATING and not self.origin_ok(strict=True):
                self.err(403, "다른 출처의 요청")
                return False
            return True
        sess = auth.get_session(auth.parse_cookies(self.headers.get("Cookie")).get(auth.COOKIE))
        rec = auth.user_rec(sess["user"]) if sess else None
        if not rec:  # 세션 없음·만료·사용자가 지워짐
            self.deny_login(method, path)
            return False
        if method in MUTATING and not self.origin_ok(strict=True):
            self.err(403, "다른 출처의 요청")
            return False
        self.user, self.role = sess["user"], rec.get("role", "user")
        return True

    def deny_login(self, method, path):
        """미인증 - API·중계 API·JSON 요청은 401, 페이지(GET)는 로그인으로 302. 본문에 내용은 없다."""
        self._err = "login"
        wants_json = re.match(r"^(/w/[^/]+)?/api/", path) or "application/json" in (self.headers.get("Accept") or "") or self.headers.get("X-Nexa-Tab")
        if method == "GET" and not wants_json and (path.endswith("/") or path.endswith(".html") or "." not in path.rsplit("/", 1)[-1]):
            self.send_response(302)  # 관리자가 아직 없으면 어떤 경로로 들어와도 최초 설정으로
            self.send_header("Location", "/setup" if not auth.has_users() else "/login?next=" + quote(self.path, safe=""))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_json({"ok": False, "error": "login", "login": "/login"}, 401)

    def host_ok(self):
        host = (self.headers.get("Host") or "").strip().lower()
        name = host[:host.rfind(":")] if host.count(":") == 1 or host.startswith("[") and "]:" in host else host
        if name in ("127.0.0.1", "localhost", "[::1]", "::1"):
            return True
        if self.headers.get("Cf-Ray"):  # Cloudflare 터널을 거쳐 왔다 - 브라우저(리바인딩 공격)는 이 헤더를 붙일 수 없다
            return True
        allow = {str(h).strip().lower() for h in (auth.setting("publicHosts", []) or [])}
        return host in allow or name in allow

    def origin_ok(self, strict):
        """상태 변경 요청의 출처 - Origin(없으면 Referer)의 호스트가 Host 와 같아야. strict(허브)면 둘 다 없는 요청도 거절한다."""
        src = self.headers.get("Origin") or ""
        if not src or src == "null":
            src = self.headers.get("Referer") or ""
        if not src:
            return not strict
        return urlparse(src).netloc.lower() == (self.headers.get("Host") or "").strip().lower()

    def is_secure(self):
        return (self.headers.get("X-Forwarded-Proto") or "").lower() == "https" or '"https"' in (self.headers.get("Cf-Visitor") or "")

    def client_ip(self):
        if HUB or self.via_hub:
            cf = self.headers.get("Cf-Connecting-IP")
            if cf:
                return cf
        return self.client_address[0] if self.client_address else ""

    def access_log(self, method, t0):
        u = urlparse(self.path or "")
        st = self._status or 0
        result = "deny" if st in (401, 403) or (st == 400 and self._err == "허용되지 않은 Host") else "error" if st >= 400 or not st else "allow"
        static = not re.match(r"^(/w/[^/]+)?/api/", u.path) or _is_poll(u.path)
        if result == "allow" and static and not self._event and not auth.setting("accessLogStatic", False):
            return  # 정적 파일·2초 폴링의 승인 줄은 설정으로만(부피)
        m = re.match(r"^/w/([^/]+)", u.path)
        rec = {"t": dt.datetime.now().astimezone().isoformat(timespec="milliseconds"), "result": result, "status": st, "method": method,
               "path": share.mask_path(u.path), "user": self.user,  # 이른 거부(Host·hub-key 위조)는 share_route 가 /s/<id> 로 바꾸기 전이라 여기서 가린다 "ip": self.client_ip(), "via": "cloudflare" if self.headers.get("Cf-Ray") else "hub" if self.via_hub else "local",
               "ua": (self.headers.get("User-Agent") or "")[:160], "ms": int((time.monotonic() - t0) * 1000),
               "server": SERVER_NAME or (hub.ws_id(WORKSPACE) if not HUB else "hub")}
        if m:
            rec["ws"] = unquote(m.group(1))
        elif self._share_ws:
            rec["ws"] = self._share_ws
        if self._err:
            rec["error"] = str(self._err)[:200]
        if self._event:
            rec["event"] = self._event
        auth.log_access(rec)

    # ---------- 라우팅 ----------
    def _route(self, method):
        u = urlparse(self.path)
        m = re.match(r"^/w/([^/]+)(/.*)?$", u.path)
        if m:  # 중계 - /w/<id>/… 를 그 작업 공간 서버로
            return self.proxy(method, m.group(1), (m.group(2) or "/") + (f"?{u.query}" if u.query else ""))
        parts = [unquote(p) for p in u.path.split("/") if p]
        q = parse_qs(u.query)
        if review and (parts[:1] == ["review"] or parts[:2] == ["api", "review"]):
            n = int(self.headers.get("Content-Length") or 0)
            r = review.handle_get(self.path) if method in ("GET", "HEAD") else review.handle_post(self.path, self.rfile.read(n) if n else b"")
            code, body, ctype = r or (404, json.dumps({"error": "없음"}).encode("utf-8"), "application/json; charset=utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if method != "HEAD":
                self.wfile.write(body)
            return
        if not parts or parts[0] != "api":
            if method == "GET" or method == "HEAD":
                return self.static(u.path, head=method == "HEAD")
            return self.err(405, "method")
        if method not in ("GET", "HEAD", "POST", "PUT"):
            return self.err(405, "method")
        name = parts[1] if len(parts) > 1 else ""
        arg = parts[2] if len(parts) > 2 else None
        self._rest = parts[3:]  # /api/engine/session/events 처럼 더 깊은 경로(핸들러가 본다)
        if arg is not None and not safe_id(arg):
            return self.err(400, "잘못된 id")
        try:
            fn = getattr(self, f"api_{method.lower()}_{name.replace('-', '_')}", None)  # /api/sheet-themes → api_get_sheet_themes
            if fn is None:
                return self.err(404, "없는 API")
            return fn(arg, q)
        except json.JSONDecodeError as e:
            return self.err(400, f"JSON 오류: {e}")
        except Exception as e:  # noqa: BLE001
            return self.err(500, f"{type(e).__name__}: {e}")

    # ---------- 중계(허브 한 포트로 여러 작업 공간) ----------
    def proxy(self, method, raw_id, path, prefix=None, transform=None):
        """/w/<id>/<경로> → 그 작업 공간 서버의 /<경로>. 요청 머리·본문을 그대로 넘기고 응답을 그대로 돌려준다.
        응답의 Location 이 / 로 시작하면(예: / → /studio/) 접두 /w/<id> 를 다시 붙인다. 이 서버 자신의 작업 공간이면 접두만 떼고 여기서 처리한다.
        대상이 응답하지 않으면 기억을 지우고 한 번 더 찾는다(꺼졌으면 다시 띄운다).
        raw_id 는 주소에 적힌 대로(한글은 퍼센트 부호화) - HTTP 머리(X-Forwarded-Prefix·Location)에는 이 형태를 쓰고, 작업 공간을 찾을 때만 푼다.
        prefix 를 주면(공유 링크 /s/<토큰>) 그 접두를 쓰고, transform(bytes → bytes)은 200 응답 본문을 고친다(덱에서 노트·숨김 장 제거)."""
        wid = unquote(raw_id)
        prefix = prefix or f"/w/{raw_id}"
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n) if n else b""
        try:
            ws, port = proxy_target(wid)
        except hub.HubError as e:
            return self.send_json({"ok": False, "error": str(e), **e.extra}, 404)
        if not HUB and ws == WORKSPACE:  # 자기 작업 공간 - 중계하지 않고 접두만 뗀다(인증·로그는 이미 바깥 틀에서)
            self.path, self.rfile = path, io.BytesIO(body)
            return self._route(method)
        # 밖에서 들어온 X-Nexa-* 는 버리고(위조 방지) 허브가 확인한 사용자와 공유 비밀을 붙인다 - 작업 공간 서버는 비밀이 맞을 때만 사용자를 믿는다
        hdrs = {k: v for k, v in self.headers.items() if k.lower() not in HOP_HEADERS and not k.lower().startswith("x-nexa-") or k.lower() == "x-nexa-tab"}
        hdrs["X-Forwarded-Prefix"] = prefix
        hdrs["X-Forwarded-Host"] = self.headers.get("Host", "")
        hdrs["X-Nexa-Hub-Key"] = auth.hub_key()
        if self.user:
            hdrs["X-Nexa-User"] = self.user
            hdrs["X-Nexa-Role"] = self.role or "user"
        resp = data = None
        for attempt in (1, 2):
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=600)  # PPTX 내보내기·PowerPoint 렌더는 오래 걸릴 수 있다
            try:
                conn.request(method, path, body=body or None, headers={**hdrs, "Host": f"127.0.0.1:{port}"})
                resp = conn.getresponse()
                if (resp.getheader("Content-Type") or "").startswith("text/event-stream"):  # SSE - 다 읽지 않고 줄 단위로 흘린다(keepalive 가 25초마다 온다)
                    return self._stream_through(resp, prefix, conn)
                data = resp.read()
                break
            except (OSError, http.client.HTTPException) as e:  # 연결 거부·끊김 - 서버가 꺼졌거나 포트가 바뀜
                forget_target(wid)
                if attempt == 2:
                    return self.err(502, f"작업 공간 서버(포트 {port})에 연결할 수 없다: {e}")
                try:
                    ws, port = proxy_target(wid)
                except hub.HubError as e2:
                    return self.send_json({"ok": False, "error": str(e2), **e2.extra}, 502)
            finally:
                conn.close()
        if transform and resp.status == 200 and method != "HEAD":
            data = transform(data)
        self.send_response(resp.status, resp.reason)
        for k, v in resp.getheaders():
            kl = k.lower()
            if kl in HOP_HEADERS or kl == "content-length":
                continue
            if kl == "location" and v.startswith("/"):
                v = prefix + v
            self.send_header(k, v)
        self.send_header("Content-Length", (resp.getheader("Content-Length") or "0") if method == "HEAD" else str(len(data)))
        self.end_headers()
        if method != "HEAD" and data:
            self.wfile.write(data)

    def _stream_through(self, resp, prefix, conn):
        """중계 - text/event-stream 응답을 받는 대로 브라우저에 쓴다. 어느 쪽이든 끊기면 끝(연결은 finally 에서 닫힌다)."""
        self.send_response(resp.status, resp.reason)
        for k, v in resp.getheaders():
            kl = k.lower()
            if kl in HOP_HEADERS or kl in ("content-length", "content-encoding"):
                continue
            if kl == "location" and v.startswith("/"):
                v = prefix + v
            self.send_header(k, v)
        self.end_headers()
        closed = self._watch_close(on_close=conn.close)  # 브라우저가 끊으면 작업 공간 쪽 소켓을 닫는다(FIN) → readline 이 깨고, 작업 공간 서버도 EOF 로 바로 안다
        try:
            while not closed.is_set():
                line = resp.readline()
                if not line:
                    break
                self.wfile.write(line)
                if line in (b"\n", b"\r\n"):  # 이벤트 하나가 끝날 때(빈 줄)마다 흘린다
                    self.wfile.flush()
        except (OSError, ValueError, http.client.HTTPException):
            pass

    def do_OPTIONS(self):
        self.route("OPTIONS")

    def do_DELETE(self):  # 쓰지 않는 메서드도 인증 틀·접근 로그를 거쳐 405 로(기본 501 은 로그에 남지 않는다)
        self.route("DELETE")

    def do_PATCH(self):
        self.route("PATCH")

    def do_GET(self):
        self.route("GET")

    def do_HEAD(self):
        self.route("HEAD")

    def do_PUT(self):
        self.route("PUT")

    def do_POST(self):
        self.route("POST")

    # ---------- 정적 ----------
    def static(self, path, head=False):
        if path in ("", "/", "/studio"):  # 작업할 덱이 있으면 편집기, 없으면 시작 페이지
            self.send_response(302)
            self.send_header("Location", "/studio/" if has_decks() else "/studio/home.html")
            self.end_headers()
            return
        if path == "/engine":  # 서버 작업(엔진 요청 큐) 전체 목록·검색 페이지 - 허브에서만(로그인은 authenticate 가 이미 확인)
            if not HUB:
                return self.err(404, "허브(시작 페이지)에서")
            path = "/studio/engine.html"
        if path in ("/login", "/setup", "/account"):  # 인증 페이지(CSS·JS 내장 - 다른 정적 파일 없이 뜬다). 허브에서만 뜻이 있다
            if not HUB:
                return self.err(404, "작업 공간 서버에는 로그인이 없다 - 허브(시작 페이지)에서")
            if path == "/setup" and auth.has_users():  # 관리자가 있으면 최초 설정은 다시 쓸 수 없다
                self.send_response(302)
                self.send_header("Location", "/login")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            if path != "/setup" and not auth.has_users():
                self.send_response(302)
                self.send_header("Location", "/setup")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            path = "/studio/" + ("account.html" if path == "/account" else "auth.html")
        rel = unquote(path).lstrip("/")
        parts = Path(rel).parts
        if any(p.startswith(".") for p in parts):
            return self.err(403, "숨김 경로")
        if parts and parts[0] == "studio":  # 엔진 파일
            root, rel = STUDIO, "/".join(parts[1:])
            if rel == "tokens.json":  # 템플릿 토큰 + 작업 공간이 고른 글꼴 프리셋(매번 새로 계산)
                return self.send_json(resolve_tokens(read_config()))
        elif parts and parts[0] == "out":  # 작업 공간 산출물
            root, rel = OUT, "/".join(parts[1:])
        elif parts and parts[0] == "wsfonts":  # 작업 공간 글꼴 파일(fonts/) — 글꼴은 엔진에 두지 않는다
            if not fonts_dir():
                return self.err(404, "작업 공간 없음")
            root, rel = fonts_dir(), "/".join(parts[1:])
        elif parts and parts[0] == "preview":  # 미리보기 임시 작업 공간의 그림
            root, rel = hub.PREVIEW_ROOT, "/".join(parts[1:])
        elif HUB:  # 허브: 작업 공간 파일 없음
            return self.err(404, "작업 공간 없음")
        else:  # 덱 그림 경로 기준 폴더
            root = ASSET_ROOT
        root = root.resolve()
        p = (root / rel).resolve()
        if root not in p.parents and p != root:
            return self.err(403, "허용 폴더 밖")
        if p.is_dir():
            p = p / "index.html"
        if not p.is_file():
            return self.err(404, "없음")
        ctype = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
            ctype += "; charset=utf-8"
        cacheable = not (parts and parts[0] == "studio")  # 엔진 화면 파일(HTML·JS·토큰)은 no-store, 그림·글꼴·산출물은 ETag 로 재검증(304) - 그림 많은 덱의 썸네일이 매번 다시 받지 않게
        if cacheable:
            st = p.stat()
            etag = f'"{st.st_mtime_ns:x}-{st.st_size:x}"'
            if self.headers.get("If-None-Match") == etag:
                self.send_response(304)
                self.send_header("ETag", etag)
                self.send_header("Cache-Control", "private, max-age=0, must-revalidate")
                self.end_headers()
                return
        data = p.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if cacheable:
            self.send_header("ETag", etag)
            self.send_header("Last-Modified", formatdate(st.st_mtime, usegmt=True))
            self.send_header("Cache-Control", "private, max-age=0, must-revalidate")
        else:
            self.send_header("Cache-Control", "no-store")
        if parts and parts[0] == "out" and p.parent == root and p.suffix.lower() in (".pptx", ".pdf", ".xlsx", ".xlsm"):  # 내보내기 결과는 덱 제목으로 받게
            from urllib.parse import quote as _q
            nm = export_name(p.stem, p.suffix.lower())
            self.send_header("Content-Disposition", f"attachment; filename=\"{p.name}\"; filename*=UTF-8''{_q(nm)}")
        self.end_headers()
        if not head:
            self.wfile.write(data)

    # ---------- 덱 ----------
    def api_post_decks(self, _, q):
        """덱 관리 {action: create|copy|start|rename|retitle|delete, id, …} - deck_admin 과 같은 함수(CLI `nexa.py deck …`). 허브에서는 없다.
        create 는 id 를 비우면 짧은 해시 id, copy 는 새 id 로 복제, start 는 시작 덱(id 비우면 해제)."""
        if HUB:
            return self.err(404, "작업 공간 서버에서")
        import deck_admin
        b = self.body_json() or {}
        act, i = b.get("action"), str(b.get("id") or "")
        try:
            with WRITE_LOCK:
                if act == "create":
                    out = deck_admin.create(i, b.get("title"), b.get("layout") or "cover", b.get("part") or "day1", "sheet" if b.get("kind") == "sheet" else "deck",
                                            theme=b.get("theme"), pages=b.get("pages"), vars_=b.get("vars"))
                elif act == "import":  # 엑셀 파일 → 시트 문서 {name, data(base64), title?} (sheet_import.py)
                    out = self._import_xlsx(b)
                elif act == "copy":
                    out = deck_admin.copy(i, b.get("title"))
                elif act == "start":
                    out = deck_admin.set_start(i)
                elif act == "rename":
                    if WS is not None and WS.state == "running":
                        return self.err(409, "웹 세션이 턴을 실행 중이다 - 끝난 뒤에 이름을 바꾼다")
                    out = deck_admin.rename(i, str(b.get("newId") or ""))
                    LAST.pop(i, None)
                elif act == "retitle":
                    out = deck_admin.retitle(i, b.get("title"))
                elif act == "delete":
                    if WS is not None and WS.state == "running":
                        return self.err(409, "웹 세션이 턴을 실행 중이다 - 끝난 뒤에 지운다")
                    out = deck_admin.delete(i)
                    LAST.pop(i, None)
                else:
                    return self.err(400, "action = create|import|copy|start|rename|retitle|delete")
        except ValueError as e:
            return self.err(400, str(e))
        self._event = f"deck.{act}:{i}" + (f"→{out.get('id')}" if act in ("rename", "copy") else "")
        self.send_json({"ok": True, **out, "decks": deck_admin.list_decks()})

    def _import_xlsx(self, b):
        import base64
        import deck_admin
        import sheet_import
        import zipfile
        name = str(b.get("name") or "시트.xlsx")[:120]
        if not name.lower().endswith((".xlsx", ".xlsm")):
            raise ValueError("엑셀 통합 문서(.xlsx·.xlsm)만 가져온다")
        try:
            data = base64.b64decode(str(b.get("data") or ""), validate=True)
        except (ValueError, TypeError):
            raise ValueError("data 는 base64")
        if not data or len(data) > 30 * 1024 * 1024:
            raise ValueError("내용 없음" if not data else "30MB 보다 크다")
        d = OUT / "import"
        d.mkdir(parents=True, exist_ok=True)
        src = d / f"{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}-{re.sub(r'[^0-9A-Za-z가-힣._-]+', '_', name)}"
        src.write_bytes(data)
        i = deck_admin.new_id()
        try:
            doc, warnings = sheet_import.to_doc(i, " ".join(str(b.get("title") or Path(name).stem).split())[:200] or i, src, ASSET_ROOT)
        except zipfile.BadZipFile:
            raise ValueError("엑셀 파일이 아니다(zip 형식 아님)")
        atomic_write(DECKS / f"{i}.json", dumps(doc))
        return {"id": i, "title": doc["title"], "kind": "sheet", "slides": 0, "sheets": len(doc["sheets"]), "warnings": warnings}

    def api_get_sheet_range(self, _, q):
        """시트 → 슬라이드 연결 데이터 ?deck=&tab=&range=&as=table|chart&header=1 → {rows} · {categories, series, numFmt?} (sheet_link.py)."""
        if HUB:
            return self.err(404, "작업 공간 서버에서")
        import sheet_link
        g = lambda k, d="": (q.get(k) or [d])[0]  # noqa: E731
        i = g("deck")
        if not safe_id(i) or not deck_path(i).exists():
            return self.err(404, "없는 시트 문서")
        try:
            out = sheet_link.range_data(json.loads(deck_path(i).read_text(encoding="utf-8")), g("tab"), g("range"),
                                        "chart" if g("as") == "chart" else "table", g("header", "1") != "0")
        except ValueError as e:
            return self.err(400, str(e))
        self.send_json({"ok": True, **out, "version": ver(deck_path(i))})

    def api_get_sheet_themes(self, name, q):
        """시트 테마 - 이름 없으면 목록, 있으면 theme.json(+ base 그림 주소 접두사, brandLogo). docs/sheets.md 5절."""
        if HUB:
            return self.err(404, "작업 공간 서버에서")
        import sheet_theme
        if not name:
            return self.send_json(sheet_theme.list_themes())
        t = sheet_theme.load(name)
        if not t:
            return self.err(404, "없는 테마")
        t["brandLogo"] = ("/" + BRAND["logo"]) if BRAND.get("logo") else ""
        self.send_json(t)

    def api_get_decks(self, _, q):
        out = []
        import deck_admin
        sd = deck_admin.start_deck()
        for f in sorted(DECKS.glob("*.json")):
            if f.name.endswith(".requests.json"):
                continue
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
                out.append({"id": f.stem, "title": d.get("title", f.stem), "slides": len(d.get("slides", [])),
                            "updated": d.get("updated", ""), "version": ver(f), "start": f.stem == sd, "kind": d.get("kind") or "deck",
                            **({"sheets": len(d.get("sheets") or [])} if d.get("kind") == "sheet" else {})})
            except Exception as e:  # noqa: BLE001
                out.append({"id": f.stem, "title": f"(읽기 오류: {e})", "slides": 0, "version": ver(f)})
        self.send_json(out)

    def api_get_deck(self, i, q):
        p = deck_path(i)
        if not p.exists():
            return self.err(404, "덱 없음")
        v = ver(p)
        data = p.read_bytes()
        if v == ver(p):  # 읽는 사이 바뀌지 않았으면 이 판을 기준본으로 기억(편집기가 이 판에서 고치기 시작한다)
            try:
                _keep_base(i, v, json.loads(data.decode("utf-8")))
            except ValueError:
                pass
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Deck-Version", v)
        self.end_headers()
        self.wfile.write(data)

    def api_put_deck(self, i, q):
        deck = self.body_json()
        base_doc = deck.pop("__base", None) if isinstance(deck, dict) else None  # 병합 기준본(save_deck 사본의 원본) - 서버가 그 판을 기억하지 못할 때
        struct = deck.pop("__struct", None) if isinstance(deck, dict) else None  # 시트 행·열 삽입·삭제(동시 편집 3-2) - 병합 전에 기준본·지금 파일에도 적용
        if not isinstance(deck, dict) or not isinstance(deck.get("slides"), list):
            return self.err(400, "덱 형식 아님(slides 목록 필요)")
        if deck.get("id", i) != i:
            return self.err(400, "id 불일치")
        for s in deck["slides"]:
            if not isinstance(s, dict) or not isinstance(s.get("elements", []), list):
                return self.err(400, "슬라이드 형식 아님")
        if deck.get("kind") == "sheet":  # 시트 문서(docs/sheets.md) - 탭 목록과 탭마다 cells 객체
            shs = deck.get("sheets")
            if not isinstance(shs, list) or not shs or any(not isinstance(t, dict) or not t.get("id") or not isinstance(t.get("cells", {}), dict) for t in shs):
                return self.err(400, "시트 형식 아님(sheets 목록, 탭마다 id·cells 필요)")
            if len({t["id"] for t in shs}) != len(shs):
                return self.err(400, "시트 탭 id 중복")
        base = (q.get("base") or [self.headers.get("X-Base-Version") or ""])[0]
        force = (q.get("force") or ["0"])[0] == "1"
        merge = (q.get("merge") or ["0"])[0] == "1"
        origin = (q.get("origin") or ["editor"])[0]
        action = (q.get("action") or ["save"])[0]
        if origin not in ("editor", "claude"):
            return self.err(400, "origin = editor | claude")
        if action not in ("save", "restore"):
            return self.err(400, "action = save | restore")
        actor = {"label": (q.get("label") or [""])[0][:80], "tab": (self.headers.get("X-Nexa-Tab") or None),
                 "request": (q.get("request") or [None])[0], "note": ((q.get("note") or [""])[0][:200] or None)}
        if self.user:  # 허브 로그인 사용자(중계로 들어온 저장) - 원장에 누가 저장했는지
            actor["user"] = self.user
        elif not self.via_hub and self.headers.get("X-Nexa-Session-User"):  # 웹 세션의 save_deck(로컬) - 세션을 시작한 사용자
            actor["user"] = self.headers["X-Nexa-Session-User"][:40]
        with WRITE_LOCK:
            p = deck_path(i)
            track(i)
            cur = ver(p)
            conflicts = None  # 병합했으면 충돌 목록(없으면 [])
            if p.exists() and base and base != cur and not force:
                bdoc = _base_doc(i, base) if merge else None
                if bdoc is None and merge and isinstance(base_doc, dict):
                    bdoc = base_doc
                if bdoc is None:
                    return self.send_json({"ok": False, "error": "conflict", "version": cur, **({"reason": "no-base"} if merge else {})}, 409)
                # 병합 저장 - 기준본 · 보낸 것 · 지금 파일을 요소·셀 단위로 합친다. 같은 곳 충돌은 사람끼리면 나중 저장, AI 저장이면 사람이 이긴다
                try:
                    detect(i, immediate=True)
                except Exception as e:  # noqa: BLE001
                    sys.stderr.write(f"ledger detect {i}: {e}\n")
                _, theirs = _load(p)
                if theirs is None:
                    return self.send_json({"ok": False, "error": "conflict", "version": cur}, 409)
                if isinstance(struct, list) and struct and deck.get("kind") == "sheet":
                    # 보낸 쪽이 행·열을 넣거나 지웠다 - 기준본과 지금 파일을 같은 만큼 옮긴 뒤 합쳐야 다른 쪽이 고친 셀이 제 칸에 남는다
                    bdoc, theirs = sheet_struct.apply(bdoc, struct), sheet_struct.apply(theirs, struct)
                deck, conflicts = deckmerge.merge3(bdoc, deck, theirs, prefer="theirs" if origin == "claude" else "ours")
                if conflicts:
                    actor["note"] = ((actor.get("note") or "") + f" · 병합 충돌 {len(conflicts)}건")[:200].lstrip(" ·")
            try:
                detect(i, immediate=True)  # 밖에서 바뀐 것이 있으면 먼저 그 줄을 남긴다(force 덮어쓰기에 묻히지 않게)
            except Exception as e:  # noqa: BLE001
                sys.stderr.write(f"ledger detect {i}: {e}\n")
            deck["id"] = i
            deck["updated"] = dt.datetime.now().isoformat(timespec="seconds")
            old = LAST.get(i)
            before = {"ver": cur, "size": old["sig"][1] if old else 0, "hash": old["hash"] if old else None, "backup": backup(i)}
            text = dumps(deck)
            atomic_write(p, text)
            data = text.encode("utf-8")
            seq = None
            try:
                ev = {"merge": {"base": base, "conflicts": conflicts[:50]}} if conflicts is not None else None  # 병합 저장 - 진 값을 원장에 남긴다
                seq = ledger.record(i, old["obj"] if old else None, before, deck, _meta(p, data), origin, "exact", action, actor, ev)
            except Exception as e:  # noqa: BLE001
                sys.stderr.write(f"ledger put {i}: {e}\n")
            _remember(i, p, data, deck)
            res = {"ok": True, "version": ver(p), "updated": deck["updated"], "seq": seq}
            if conflicts is not None:  # 병합했으면 결과 문서와 충돌 - 보낸 쪽(편집기·save_deck)이 이것을 새 기준으로 삼는다
                res.update({"merged": True, "conflicts": conflicts, "deck": deck})
            self.send_json(res)

    def api_get_version(self, i, q):
        with WRITE_LOCK:
            try:
                detect(i)
            except Exception as e:  # noqa: BLE001
                sys.stderr.write(f"ledger detect {i}: {e}\n")
        self.send_json({"deck": ver(deck_path(i)), "requests": ver(req_path(i)), "changes": ver(ledger.path(i)),
                        "session": session_status(), "activity": activity(), **workspace_stamp()})

    # ---------- 실시간(동시 편집 2단계, docs/collab.md) - 탭당 SSE 하나로 버전·함께 보는 사람을 밀어 준다. 폴링(/api/version)은 끊겼을 때의 안전망 ----------
    def api_get_stream(self, i, q):
        """event: version = /api/version 과 같은 내용(파일·세션·작업 공간이 바뀔 때만) · presence = 함께 보는 사람 · ping = 10초마다(살아 있음).
        파일 버전은 0.5초마다 stat 으로 보고, 덱이 바뀌었으면 /api/version 처럼 detect 로 원장에 남긴 뒤 보낸다. 끊기면 그 탭의 presence 를 지운다."""
        if not deck_path(i).exists():
            return self.err(404, "덱 없음")
        tab = ((q.get("tab") or [""])[0] or self.headers.get("X-Nexa-Tab") or "")[:40]
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        closed = self._watch_close()
        collab.PRESENCE.attach(i, tab)  # 같은 탭이 다시 붙으면(재연결) 연결이 둘인 순간이 있다 - 마지막 연결이 끊길 때만 presence 를 지운다

        def send(ev, data):
            self.wfile.write(f"event: {ev}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8"))
            self.wfile.flush()
        last_key, last_files, last_pv, n = None, None, -1, 0
        sess, act, stamp = {}, {}, {}
        try:
            self.wfile.write(b"retry: 3000\n\n")
            self.wfile.flush()
            while not closed.is_set():
                if n % 4 == 0:  # 세션·활동·작업 공간은 2초마다(파일을 더 읽는다)
                    sess, act, stamp = session_status(), activity(), workspace_stamp()
                files = (ver(deck_path(i)), ver(req_path(i)), ver(ledger.path(i)))
                if last_files is not None and files[0] != last_files[0]:  # 덱이 바뀌었다 - 밖의 쓰기면 원장에 먼저 남긴다(/api/version 과 같다)
                    with WRITE_LOCK:
                        try:
                            detect(i)
                        except Exception as e:  # noqa: BLE001
                            sys.stderr.write(f"ledger detect {i}: {e}\n")
                    files = (ver(deck_path(i)), ver(req_path(i)), ver(ledger.path(i)))
                w = (act or {}).get("watcher") or {}
                key = json.dumps([files, {k: (sess or {}).get(k) for k in ("connected", "kind", "state", "working", "open", "turn", "agent", "model", "label", "user")},
                                  w.get("state"), w.get("source"), (act or {}).get("othersBusy"), stamp], sort_keys=True, default=str)
                if key != last_key:
                    send("version", {"deck": files[0], "requests": files[1], "changes": files[2], "session": sess, "activity": act, **stamp})
                    last_key, last_files = key, files
                pv = collab.PRESENCE.version(i)
                if pv != last_pv:
                    send("presence", {"list": collab.PRESENCE.snapshot(i)})
                    last_pv = pv
                if n % 20 == 19:
                    send("ping", {})
                time.sleep(0.5)
                n += 1
        except (OSError, ValueError):  # 연결 끊김
            pass
        finally:
            collab.PRESENCE.detach(i, tab)

    # ---------- AI 제안(동시 편집 3단계 첫 조각, docs/collab.md) - 큰 변경을 파일에 바로 쓰지 않고 남겨 두고, 사람이 장·탭마다 골라 받는다 ----------
    def _save_doc(self, i, deck, origin, action, actor, evidence=None):
        """서버가 직접 만든 문서를 저장(WRITE_LOCK 안에서) - PUT 과 같은 백업·원장·기억. 원장 seq"""
        p = deck_path(i)
        track(i)
        try:
            detect(i, immediate=True)
        except Exception as e:  # noqa: BLE001
            sys.stderr.write(f"ledger detect {i}: {e}\n")
        cur = ver(p)
        deck["id"] = i
        deck["updated"] = dt.datetime.now().isoformat(timespec="seconds")
        old = LAST.get(i)
        before = {"ver": cur, "size": old["sig"][1] if old else 0, "hash": old["hash"] if old else None, "backup": backup(i)}
        text = dumps(deck)
        atomic_write(p, text)
        data = text.encode("utf-8")
        seq = None
        try:
            seq = ledger.record(i, old["obj"] if old else None, before, deck, _meta(p, data), origin, "exact", action, actor, evidence)
        except Exception as e:  # noqa: BLE001
            sys.stderr.write(f"ledger {action} {i}: {e}\n")
        _remember(i, p, data, deck)
        return seq

    def api_get_proposals(self, i, q):
        d = DECKS / ".history" / i / "proposals"
        out = []
        for f in sorted(d.glob("*.json")) if d.is_dir() else []:
            x = proposals.load(f)
            if x and x.get("items"):
                out.append({"request": x.get("request"), "created": x.get("created"), "items": x["items"]})
        self.send_json(out)

    def api_post_proposals(self, i, q):
        b = self.body_json()
        if not isinstance(b, dict):
            return self.err(400, "본문 없음")
        act, rid = b.get("action"), str(b.get("request") or "")
        if not rid or not safe_id(rid.replace(".", "_")) or not deck_path(i).exists():
            return self.err(400, "request·덱 필요")
        f = proposals.path(DECKS, i, rid)
        actor = {"label": "", "tab": self.headers.get("X-Nexa-Tab") or None, "request": rid, "note": None}
        if self.user:
            actor["user"] = self.user
        if act == "create":
            deck = b.get("deck")
            if not isinstance(deck, dict):
                return self.err(400, "deck 필요")
            base_doc = b.get("baseDoc") if isinstance(b.get("baseDoc"), dict) else _base_doc(i, str(b.get("base") or "")) or _load(deck_path(i))[1]
            its = proposals.items(base_doc, deck)
            if its:
                f.parent.mkdir(parents=True, exist_ok=True)
                atomic_write(f, json.dumps({"request": rid, "created": dt.datetime.now().isoformat(timespec="seconds"), "base": b.get("base"),
                                            "baseDoc": base_doc, "deck": deck, "items": its}, ensure_ascii=False))
            return self.send_json({"ok": True, "count": len(its), "items": its})
        x = proposals.load(f)
        if not x:
            return self.err(404, "제안 없음")
        all_ids = [it["id"] for it in x.get("items") or []]
        chosen = [k for k in (b.get("items") or all_ids) if k in all_ids]
        if act == "accept":
            if not chosen:
                return self.err(400, "받을 항목 없음")
            ours = proposals.apply(x["baseDoc"], x["deck"], chosen)
            with WRITE_LOCK:
                cur = _load(deck_path(i))[1]
                if cur is None:
                    return self.err(409, "덱을 읽는 중 - 다시 시도")
                merged, conflicts = deckmerge.merge3(x["baseDoc"], ours, cur, prefer="ours")  # 사람이 고른 것이니 고른 단위는 제안 값이 이긴다
                names = [next((it["title"] for it in x["items"] if it["id"] == k), k) for k in chosen]
                actor["note"] = f"AI 제안 받기 {len(chosen)}곳: " + ", ".join(names)[:150]
                seq = self._save_doc(i, merged, "editor", "accept", actor, {"proposal": {"request": rid, "items": chosen}, "merge": {"conflicts": conflicts[:50]}} if conflicts else {"proposal": {"request": rid, "items": chosen}})
            x["items"] = [it for it in x["items"] if it["id"] not in chosen]
        elif act == "discard":
            x["items"] = [it for it in x["items"] if it["id"] not in chosen]
            seq, conflicts = None, []
        else:
            return self.err(400, "action = create | accept | discard")
        if x["items"]:
            atomic_write(f, json.dumps(x, ensure_ascii=False))
        else:
            f.unlink(missing_ok=True)
        self.send_json({"ok": True, "seq": seq, "version": ver(deck_path(i)), "conflicts": conflicts, "left": len(x["items"])})

    def api_get_reqdiff(self, i, q):
        """요청 하나로 AI 가 바꾼 것 - 요청 카드의 "바뀐 셀 n개 · 보기 · 되돌리기". 백업이 없으면 found 는 true, cells 는 null."""
        rid = (q.get("request") or [""])[0]
        if not rid:
            return self.err(400, "request 필요")
        entries = ledger.read(i)
        idx = [k for k, e in enumerate(entries) if (e.get("actor") or {}).get("request") == rid and e.get("kind") == "change"]
        if not idx:
            return self.send_json({"ok": True, "found": False, "cells": [], "count": 0})
        hdir = DECKS / ".history" / i

        def load(name):
            try:
                return json.loads((hdir / name).read_text(encoding="utf-8")) if name and (hdir / name).is_file() else None
            except (OSError, ValueError):
                return None
        def after_of(k):  # 원장 줄 k 의 저장 직후 = 그다음 원장 줄이 쓰기 직전에 뜬 백업, 없으면 지금 파일
            for e in entries[k + 1:]:
                bk = (e.get("before") or {}).get("backup")
                if bk:
                    return load(bk)
            p = deck_path(i)
            return _load(p)[1] if p.exists() else None
        # AI 저장마다 따로 비교해 합친다 - AI 저장 사이에 사람이 저장한 셀은 AI 변경으로 세지 않는다(되돌리기가 사람의 셀을 건드리지 않게)
        found, last_after = {}, None
        for k in idx:
            bd, ad = load((entries[k].get("before") or {}).get("backup")), after_of(k)
            if bd is None or ad is None:
                return self.send_json({"ok": True, "found": True, "cells": None, "count": None, "error": "그때 백업이 없어 비교할 수 없다"})
            if ad.get("kind") != "sheet":
                return self.send_json({"ok": True, "found": True, "cells": [], "count": 0, "saves": len(idx)})
            for c in deckdiff.cell_diff(bd, ad):
                key = (c["tab"], c["key"])
                if key not in found:  # 처음 바꾼 저장의 "전" 값
                    found[key] = c
            last_after = ad
        tabs = {t.get("id"): t for t in last_after.get("sheets") or [] if isinstance(t, dict)}
        cells = []
        for (tab, key), c in found.items():  # "후" 값은 마지막 AI 저장 직후의 값
            now = ((tabs.get(tab) or {}).get("cells") or {}).get(key)
            if deckdiff._cell_norm(now) != deckdiff._cell_norm(c["before"]):  # 여러 번 고쳐 결국 처음 값으로 돌아왔으면 바뀐 셀이 아니다
                cells.append({**c, "after": now})
        self.send_json({"ok": True, "found": True, "cells": cells, "count": len(cells), "saves": len(idx), "seq": [entries[k].get("seq") for k in idx]})

    def api_post_presence(self, i, q):
        """함께 보는 사람 - {tab, where, editing, user?}. 허브 로그인 사용자면 그 이름을 쓴다(보낸 user 보다 우선). {leave: true} = 뺀다."""
        b = self.body_json()
        if not isinstance(b, dict):
            return self.err(400, "본문 없음")
        tab = str(b.get("tab") or self.headers.get("X-Nexa-Tab") or "")[:40]
        if not tab:
            return self.err(400, "tab 필요")
        if b.get("leave"):
            collab.PRESENCE.leave(i, tab)
        else:
            collab.PRESENCE.update(i, tab, {"user": self.user or b.get("user") or "", "where": b.get("where"), "editing": b.get("editing")})
        self.send_json({"ok": True, "color": collab.color_of(tab), "list": collab.PRESENCE.snapshot(i)})

    # ---------- 변경 원장 ----------
    def api_get_changes(self, i, q):
        if not deck_path(i).exists() and not ledger.path(i).exists():
            return self.err(404, "덱 없음")
        with WRITE_LOCK:
            track(i)
        entries = ledger.read(i)
        hdir = DECKS / ".history" / i

        def g1(k, d=None):
            return (q.get(k) or [d])[0]

        def bx(name):
            return bool(name) and (hdir / name).is_file()

        def mark(e):
            return {**e, "backupExists": bx((e.get("before") or {}).get("backup"))}
        out = {"ok": True, "deck": i, "latest": entries[-1]["seq"] if entries else 0, "keep": ledger.KEEP, "groupGap": ledger.GROUP_GAP,
               "ver": ver(ledger.path(i)), "tab": self.headers.get("X-Nexa-Tab") or None}
        if g1("seq"):
            e = next((x for x in entries if str(x.get("seq")) == g1("seq")), None)
            if not e:
                return self.err(404, "없는 seq")
            out["entry"] = mark(e)
            return self.send_json(out)
        sel = entries
        if g1("origin"):
            allow = set(g1("origin").split(","))
            sel = [e for e in sel if e.get("origin") in allow]
        if g1("slide"):
            sid = g1("slide")
            sel = [e for e in sel if any(it.get("sid") == sid for it in e.get("items") or [])]
        if g1("since"):
            sel = [e for e in sel if e.get("seq", 0) > int(g1("since"))]
        limit = max(1, min(500, int(g1("limit", 50))))
        if g1("recent"):
            cur = LAST[i]["obj"] if i in LAST else None
            out["recent"] = ledger.recent(sel, cur)[:limit]
        if g1("group"):
            groups = ledger.group(sel)
            if g1("before"):
                groups = [g for g in groups if g["seq"] < int(g1("before"))]
            out["more"] = len(groups) > limit
            out["groups"] = [{**g, "backupExists": bx(g.get("backup"))} for g in reversed(groups[-limit:])]
        elif not g1("recent"):
            if g1("before"):
                sel = [e for e in sel if e.get("seq", 0) < int(g1("before"))]
            out["more"] = len(sel) > limit
            out["entries"] = [mark(e) for e in reversed(sel[-limit:])]
        self.send_json(out)

    # ---------- 레이아웃 검사 ----------
    def api_get_check(self, i, q):
        if not deck_path(i).exists():
            return self.err(404, "덱 없음")
        import check_layout
        self.send_json(check_layout.check_deck(i))

    # ---------- 보기 전용 공유 링크 /s/<토큰>/… (허브, 로그인 없이) - share.py · docs/auth.md ----------
    def share_route(self, method, path):
        """토큰 → 링크(만료·회수) → (비밀번호면) 쿠키 → 허용 목록만 그 작업 공간 서버로 중계(X-Nexa-User share:<id> · Role viewer).
        잘못된 토큰·만료·회수는 같은 안내 페이지(존재 여부를 흘리지 않는다 - 상태 코드만 404/410). 로그·경로에는 토큰 대신 /s/<id>."""
        u = urlparse(self.path)
        m = re.match(rf"^/s/({share.TOKEN_RX})(/.*)?$", path)
        found = share.lookup(m.group(1)) if m else None
        if not found:
            self.path = "/s/-" + ((m.group(2) or "") if m else "")
            self._event = "share.denied:-:unknown"
            return self.share_denied(404)
        lid, rec = found
        tok, rest = m.group(1), m.group(2) or ""
        self.path = f"/s/{lid}{rest}" + (f"?{u.query}" if u.query else "")
        self.user, self.role, self._share_ws = f"share:{lid}", "viewer", rec.get("wsId")
        st = share.status(rec)
        if st != "ok":
            self._event = f"share.denied:{lid}:{st}"
            return self.share_denied(410)
        prefix = f"/s/{tok}"
        if not rest:  # /s/<토큰> → /s/<토큰>/ (페이지의 상대 경로 기준)
            self.send_response(302)
            self.send_header("Location", prefix + "/")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        authed = not rec.get("pw") or share.cookie_ok(auth.parse_cookies(self.headers.get("Cookie")).get(share.COOKIE), lid, rec)
        if rest == "/api/share/state" and method == "GET":
            return self.send_json({"ok": True, "deck": rec["deck"], "needPassword": not authed, "locked": auth.locked_for(f"share:{lid}"),
                                   "expires": share.public(lid, rec)["expires"]})
        if rest == "/api/share/auth" and method == "POST":
            if not self.origin_ok(strict=True):
                return self.err(403, "다른 출처의 요청")
            return self.share_auth(lid, rec, prefix)
        if method not in ("GET", "HEAD"):
            self._event = f"share.denied:{lid}:method"
            return self.err(403, "보기 전용 링크")
        if rest == "/":  # 보기 페이지 - 비밀번호가 있어도 페이지는 연다(입력 화면), 자료는 열지 않는다
            if authed and method == "GET":
                self._event = f"share.view:{lid}"
                share.note_view(lid)
            return self.proxy(method, rec["wsId"], "/studio/view.html", prefix=prefix)
        if not authed:
            self._err = "share.password"
            return self.send_json({"ok": False, "error": "password"}, 401)
        if rest == f"/api/deck/{rec['deck']}":
            return self.proxy(method, rec["wsId"], rest, prefix=prefix, transform=lambda data: share_filter_deck(lid, data))
        cached = SHARE_ASSETS.get(lid) or {}
        if not (rest in SHARE_STATIC or SHARE_STATIC_RX.match(rest) or unquote(rest).lstrip("/") in cached.get("paths", ())):
            self._event = f"share.denied:{lid}:path"
            return self.err(403, "이 링크로 열 수 없는 경로")
        return self.proxy(method, rec["wsId"], rest + (f"?{u.query}" if u.query else ""), prefix=prefix)

    def share_denied(self, status):
        b = SHARE_DENIED_HTML.encode("utf-8")
        self._err = "share.denied"
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def share_auth(self, lid, rec, prefix):
        """비밀번호 확인 → 쿠키 nexa_share(Path=/s/<토큰>/, 링크 만료와 세션 7일 중 짧은 쪽). 실패 잠금은 auth._FAILS(링크 id 키, 5회/15분)."""
        if not rec.get("pw"):
            return self.send_json({"ok": True})
        key = f"share:{lid}"
        left = auth.locked_for(key)
        if left:
            self._event = f"share.auth.locked:{lid}"
            return self.err(429, f"비밀번호 실패가 잦아 잠겼다 - {left // 60 + 1}분 뒤에")
        b = self.body_json() or {}
        if not share.check_password(b.get("password"), rec):
            auth.note_failure(key)
            self._event = f"share.auth.fail:{lid}"
            return self.err(401, "비밀번호가 맞지 않다")
        auth.clear_failures(key)
        self._event = f"share.auth:{lid}"
        v, ma = share.cookie_value(lid, rec)
        ck = f"{share.COOKIE}={v}; Path={prefix}/; HttpOnly; SameSite=Lax; Max-Age={ma}" + ("; Secure" if self.is_secure() else "")
        return self.send_json({"ok": True}, headers={"Set-Cookie": ck})

    # ---------- 공유 링크 관리 API(허브, 로그인 사용자) ----------
    def api_get_share(self, what, q):
        """GET /api/share?ws=<중계 이름>&deck=<덱> - 내 링크(관리자는 전부) + 한도·정책."""
        if not HUB:
            return self.err(404, "허브(시작 페이지)에서")
        if what:
            return self.err(404, "없는 API")
        ws_id, deck = (q.get("ws") or [""])[0], (q.get("deck") or [""])[0]
        return self.send_json({"ok": True, "links": share.list_links(self.user, self.role, ws_id or None, deck or None), "maxDays": share.max_days(),
                               "defaultDays": share.DEFAULT_DAYS, "canCreate": share.can_create(self.role), "admin": self.role == "admin"})

    def api_post_share(self, what, q):
        """POST /api/share {action: "create", ws, deck, days?, password?} → {link, token, url}(토큰은 이 응답에만) · POST /api/share/<id> {action: "revoke"}."""
        if not HUB:
            return self.err(404, "허브(시작 페이지)에서")
        b = self.body_json() or {}
        if what:  # 회수 - 만든 사람 또는 관리자
            rec = share.get(what)
            if not rec:
                return self.err(404, "없는 링크")
            if (b.get("action") or "revoke") != "revoke":
                return self.err(400, "action = revoke")
            if self.role != "admin" and rec.get("by") != self.user:
                self._event = f"share.denied:{what}:owner"
                return self.err(403, "만든 사람 또는 관리자만 회수할 수 있다")
            share.revoke(what, self.user)
            self._event = f"share.revoke:{what}"
            return self.send_json({"ok": True, "link": share.public(what, share.get(what))})
        if (b.get("action") or "create") != "create":
            return self.err(400, "action = create")
        if not share.can_create(self.role):
            self._event = "share.denied:-:policy"
            return self.err(403, "공유 링크 만들기는 관리자만(전역 설정 shareCreate)")
        ws_id, deck = str(b.get("ws") or ""), str(b.get("deck") or "")
        ws = hub.ws_by_id(ws_id)
        if ws is None:
            return self.err(404, "모르는 작업 공간이다 - 시작 페이지에서 연 작업 공간만")
        if not safe_id(deck):
            return self.err(400, "잘못된 덱 id")
        cfg = hub.load_ws_config(ws)
        if not (ws / str(cfg.get("decks") or "decks") / f"{deck}.json").is_file():
            return self.err(404, "덱 없음")
        try:
            lid, tok, rec = share.create(ws, ws_id, deck, self.user, b.get("days"), b.get("password") or None)
        except ValueError as e:
            return self.err(400, str(e))
        self._event = f"share.create:{lid}"
        return self.send_json({"ok": True, "link": share.public(lid, rec), "token": tok, "url": f"/s/{tok}/"})

    # ---------- 작업 공간·세션 ----------
    def me(self):
        return {"id": self.user, "role": self.role} if self.user else None

    def api_get_config(self, _, q):
        if HUB:
            return self.send_json({"mode": "hub", "workspace": "", "path": "", "port": self.server.server_port, "title": "nexa-slide",
                                   "template": None, "brand": {}, "refused": str(REFUSED) if REFUSED else None, "user": self.me()})
        from layouts import LOGO, LOGO_RATIO, WORDMARK
        self.send_json({"mode": "workspace", "workspace": WORKSPACE.name, "path": str(WORKSPACE), "port": self.server.server_port,
                        "template": {"name": TEMPLATE["name"], "label": TEMPLATE.get("label", TEMPLATE["name"])},
                        "title": CONFIG.get("title", WORKSPACE.name), "user": self.me(),
                        "brand": {**BRAND, "logo": LOGO, "wordmark": WORDMARK, "logoRatio": LOGO_RATIO}})

    # ---------- 인증(허브) - auth.py ----------
    def set_cookie(self, tok):
        return {"Set-Cookie": auth.cookie_header(tok, self.is_secure())}

    def api_get_auth(self, what, q):
        if not HUB:
            return self.err(404, "작업 공간 서버에는 로그인이 없다")
        if what == "state":  # 로그인 페이지용 - 관리자가 있는지만. mode 는 service.py·status.py 의 생존 확인용(common._serves_here)
            return self.send_json({"ok": True, "mode": "hub", "setup": not auth.has_users(), "user": self.me()})
        if what == "me":
            return self.send_json({"ok": True, "user": {**self.me(), "mustChange": bool((auth.user_rec(self.user) or {}).get("mustChange"))}})
        if what == "users":
            if self.role != "admin":
                return self.err(403, "관리자만")
            return self.send_json({"ok": True, "users": [auth.public(u, r) for u, r in sorted(auth.load_users().items())]})
        return self.err(404, "없는 API")

    def api_post_auth(self, what, q):
        if not HUB:
            return self.err(404, "작업 공간 서버에는 로그인이 없다")
        b = self.body_json() or {}
        uid, pw = str(b.get("id") or "").strip(), b.get("password") or ""
        ip = self.client_ip()
        if what == "setup":  # 최초 관리자 - 사용자가 하나도 없을 때만
            if auth.has_users():
                self._event = "setup.denied"
                return self.err(403, "이미 관리자가 있다 - 로그인으로")
            try:
                auth.add_user(uid, pw, "admin")
            except ValueError as e:
                return self.err(400, str(e))
            self.user, self.role, self._event = uid, "admin", "setup"
            return self.send_json({"ok": True, "user": self.me()}, headers=self.set_cookie(auth.new_session(uid, self.headers.get("User-Agent"))))
        if what == "login":
            # 잠금 키: 클라이언트 주소는 늘, 아이디는 밖(Cloudflare 경유)에서 온 로그인만 - 밖에서 비밀번호를 5번 틀려 관리자를 잠가 두는 일을 막고,
            # 같은 PC(로컬)에서는 아이디 잠금 없이 들어갈 수 있게 한다(ip 잠금은 그대로)
            keys = (f"u:{uid}", f"ip:{ip}") if self.headers.get("Cf-Ray") else (f"ip:{ip}",)
            left = max(auth.locked_for(k) for k in keys)
            if left:
                self._event = "login.locked"
                return self.err(429, f"로그인 실패가 잦아 잠겼다 - {left // 60 + 1}분 뒤에")
            rec = auth.user_rec(uid)
            if not rec or not auth.check_password(pw, rec):
                auth.note_failure(*keys)
                self._event = "login.fail"
                self.user = uid or None
                return self.err(401, "아이디 또는 비밀번호가 맞지 않다")
            auth.clear_failures(*keys)
            self.user, self.role, self._event = uid, rec.get("role", "user"), "login"
            return self.send_json({"ok": True, "user": self.me(), "mustChange": bool(rec.get("mustChange"))},
                                  headers=self.set_cookie(auth.new_session(uid, self.headers.get("User-Agent"))))
        if what == "logout":
            auth.drop_session(auth.parse_cookies(self.headers.get("Cookie")).get(auth.COOKIE))
            self._event = "logout"
            return self.send_json({"ok": True}, headers={"Set-Cookie": auth.cookie_header(None, self.is_secure())})
        if what == "password":  # 내 비밀번호 - 현재 비밀번호 확인
            rec = auth.user_rec(self.user)
            if not rec or not auth.check_password(b.get("current") or "", rec):
                self._event = "password.fail"
                return self.err(401, "현재 비밀번호가 맞지 않다")
            try:
                auth.set_password(self.user, b.get("new") or "")
            except ValueError as e:
                return self.err(400, str(e))
            self._event = "password.change"
            return self.send_json({"ok": True}, headers=self.set_cookie(auth.new_session(self.user, self.headers.get("User-Agent"))))  # 다른 기기는 끊고 이 기기는 다시 발급
        if what == "users":  # 관리자 - 추가·삭제·비밀번호 초기화·역할
            if self.role != "admin":
                self._event = "users.denied"
                return self.err(403, "관리자만")
            act = b.get("action")
            try:
                if act == "add":
                    auth.add_user(uid, pw, b.get("role") or "user", must_change=True)
                elif act == "delete":
                    if uid == self.user:
                        return self.err(400, "자기 계정은 지울 수 없다")
                    auth.delete_user(uid)
                elif act == "reset":
                    auth.set_password(uid, pw, must_change=True)
                elif act == "role":  # 관리자 지정·해제는 관리자만(여기) - 마지막 관리자는 내릴 수 없다(auth.set_role)
                    auth.set_role(uid, b.get("role") or "user")
                else:
                    return self.err(400, "action = add|delete|reset|role")
            except ValueError as e:
                return self.err(400, str(e))
            self._event = f"users.{act}:{uid}"
            return self.send_json({"ok": True, "users": [auth.public(u, r) for u, r in sorted(auth.load_users().items())]})
        return self.err(404, "없는 API")

    # ---------- 웹 AI 세션(B-3) - wsession.py ----------
    def api_get_wsession(self, what, q):
        if HUB or WS is None:
            return self.err(404, "허브에는 세션이 없다 - 작업 공간(중계 /w/<이름>/api/wsession)에서")
        return self._session_get(WS, what, q)

    def _session_get(self, ws, what, q):
        """세션 조회 공통 - what = None(상태) | events(SSE·폴링) | log(턴 원문). 작업 공간 세션(/api/wsession)과 엔진 세션(/api/engine/session)이 같이 쓴다."""
        if what == "events":  # SSE(Accept: text/event-stream 또는 ?sse=1) · 아니면 폴링 JSON
            since = int((q.get("since") or [self.headers.get("Last-Event-ID") or "0"])[0] or 0)
            if "text/event-stream" in (self.headers.get("Accept") or "") or (q.get("sse") or ["0"])[0] == "1":
                return self.sse_events(since, ws)
            return self.send_json({"ok": True, "state": ws.state, "seq": ws.seq, "events": ws.events_since(since)})
        if what == "log":
            return self.send_json({"ok": True, "turn": (q.get("turn") or ["1"])[0], "lines": ws.turn_log((q.get("turn") or ["1"])[0]).splitlines()})
        if what == "pulse":  # 처리 중 턴의 맥박(지금 도구·경과·마지막 출력·프로세스 생존) - 진행 창이 몇 초마다(git 을 묻지 않는 가벼운 조회)
            return self.send_json({"ok": True, **ws.pulse()})
        if what:
            return self.err(404, "없는 API")
        self.send_json({"ok": True, **ws.info()})

    def _can_allow_web(self):
        """세션에 웹 검색을 열 수 있는 사람 - 허브 관리자(중계 머리글 X-Nexa-Role). 작업 공간 서버 로컬 직접 접속은 로그인이 없으므로 그 PC 사용자 = 운영자로 본다."""
        return self.role == "admin" or (not HUB and not self.via_hub)

    def _session_post(self, ws, b, who, save_defaults=None):
        """세션 조작 공통 - {action: start|stop|model}. 작업 공간 세션은 saveAs 로 기본값도 저장한다."""
        act = b.get("action")
        if act not in ("start", "stop", "model"):
            return False  # 여기서 다루지 않는 action - 호출한 쪽이 처리
        try:
            if act == "start":
                allow_web = bool(b.get("allowWeb"))
                grants = [g for g in (b.get("grants") or []) if g in ("git", "push", "root")]
                if (allow_web or grants) and not self._can_allow_web():
                    self._event = f"{ws.p.kind}.session.denied"
                    self.err(403, "웹 검색·git·저장소 루트 권한은 관리자만 고를 수 있다")
                    return True
                info = ws.start(b.get("agent"), b.get("model"), who, allow_web=allow_web, grants=grants)
                self._event = f"{ws.p.kind}.session.start:{info['agent']}:{info['model']}" + (":web" if info.get("allowWeb") else "") + "".join(f":{g}" for g in info.get("grants") or [])
                if save_defaults and b.get("saveAs") in ("local", "shared"):
                    save_defaults(b.get("saveAs"), {"sessionAgent": info["agent"], "sessionModel": info["model"]})
                self.send_json({"ok": True, **info})
            elif act == "stop":
                was = ws.state != "off"
                info = ws.stop(str(b.get("reason") or "user")[:40])
                manual = {}
                if not was:  # 웹 세션이 없으면 터미널 세션(watch_*)의 수동 감시를 끝낸다 - 카드 [세션 중지]가 수동 세션에도 통하게
                    import procutil
                    if ws.p.kind == "engine":
                        import engine_requests
                        manual = procutil.stop_manual(engine_requests.HEARTBEAT)
                    else:
                        import requests_core
                        manual = procutil.stop_manual(requests_core.SESSION)
                self._event = f"{ws.p.kind}.session.stop" + (":manual" if manual.get("stopped") else "")
                self.send_json({"ok": True, "stopped": was or bool(manual.get("stopped")), "manual": manual, **info})
            else:
                info = ws.set_model(b.get("model"))
                self._event = f"{ws.p.kind}.session.model:{b.get('model')}"
                if save_defaults and b.get("saveAs") in ("local", "shared"):
                    save_defaults(b.get("saveAs"), {"sessionModel": str(b.get("model"))})
                self.send_json({"ok": True, **info})
        except ValueError as e:
            self._event = f"{ws.p.kind}.session.denied"
            self.err(400, str(e))
        return True  # 응답을 보냈다

    # ---------- 엔진 개발 세션 · 엔진 요청 큐(E 단계 - docs/dev/engine-request-design.md) - 허브에서만 ----------
    def api_get_engine(self, what, q):
        if not HUB:
            return self.err(404, "허브(시작 페이지)에서")
        import engine_requests
        if what == "requests":  # ?status=<상태>&q=<검색어>(제목·내용·답·요청자·커밋·#번호) - 전체 목록 페이지(/engine)와 CLI
            st = (q.get("status") or [None])[0]
            kw = ((q.get("q") or [""])[0] or "").strip().lower()
            items = [x for x in engine_requests.load() if not st or x.get("status") == st]
            if kw:
                def hit(x):
                    if kw.lstrip("#").isdigit() and str(x.get("id")) == kw.lstrip("#"):
                        return True
                    f = x.get("from") or {}
                    vals = [x.get("title"), x.get("body"), x.get("reply"), x.get("commit"), x.get("appliedCommit"), x.get("branch"), x.get("test"), f.get("user"), f.get("wsId"), f.get("ws")] + list(x.get("evidence") or [])
                    return any(v and kw in str(v).lower() for v in vals)
                items = [x for x in items if hit(x)]
            return self.send_json({"ok": True, "items": items, "counts": engine_requests.counts(), "total": len(engine_requests.load())})
        if what == "deploy":  # 배포 계획(들어갈 커밋·요청·막는 이유)과 마지막 배포 기록(관리자) - ?fetch=0 이면 git fetch 없이(진행 중 화면 갱신)
            if self.role != "admin":
                return self.err(403, "관리자만")
            import engine_deploy
            if (q.get("fetch") or ["1"])[0] == "0":
                return self.send_json({"ok": True, "last": engine_deploy.status()})
            p = engine_deploy.plan()
            return self.send_json({**p, "ok": True, "ready": p["ok"]})
        if what == "tidy":  # 엔진 개발 영역 정리 보고(관리자) - 고아 첨부·worktree 첨부 사본·회귀 사본·오래된 로그·남은 시험용 worktree(engine_tidy)
            if self.role != "admin":
                return self.err(403, "관리자만")
            import engine_tidy
            return self.send_json({"ok": True, **engine_tidy.scan()})
        if what == "session":
            if WS_ENGINE is None:
                return self.err(503, "엔진 세션 관리자가 없다")
            return self._session_get(WS_ENGINE, (self._rest or [None])[0], q)
        if what == "notice":  # 알림(메뉴 단추 배지·토스트) - 몇 초마다 부르므로 큐 파일만 읽는다
            c = engine_requests.counts()
            on = bool(WS_ENGINE and WS_ENGINE.state != "off") or engine_requests.session_state().get("kind") == "manual" and engine_requests.session_state().get("connected")
            return self.send_json({"ok": True, "admin": self.role == "admin", "triage": c.get("triage", 0), "open": c.get("open", 0), "working": c.get("working", 0),
                                   "done": c.get("done", 0), "sessionOff": not on, "startRequest": engine_requests.start_request(), "ui": hub_ui_stamp(),
                                   "titles": [f"#{x['id']} {x['title']}" for x in engine_requests.load() if x.get("status") == "triage"][:5]})
        if what == "attach":  # /api/engine/attach/<id>/<파일> - 올린 첨부 보기(로그인 사용자)
            rest = self._rest or []
            if len(rest) != 2 or not re.fullmatch(r"\d+|_new", rest[0]):
                return self.err(404, "없는 첨부")
            p = engine_requests.ATTACH_DIR / rest[0] / Path(unquote(rest[1])).name
            if not p.is_file():
                return self.err(404, "없는 첨부")
            data = p.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(str(p))[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return self.wfile.write(data)
        if what:
            return self.err(404, "없는 API")
        info = WS_ENGINE.info() if WS_ENGINE else {"state": "off"}
        if info.get("state", "off") == "off":  # 웹 엔진 세션이 없으면 수동 엔진 세션(watch_engine_requests)의 하트비트를 본다
            hb = engine_requests.session_state()
            if hb.get("connected") and hb.get("kind") == "manual":
                info = {**info, "state": "manual", "kind": "manual", "label": hb.get("label"), "pid": hb.get("pid"), "startedBy": hb.get("user"), "startedAt": hb.get("started"), "cwd": hb.get("cwd"),
                        "agent": hb.get("agent"), "model": hb.get("model"), "sessionId": hb.get("sessionId"), "entry": hb.get("entry")}  # 감시가 --agent/--model·CLAUDE_CODE_* 로 담은 것
        allq = engine_requests.load()
        recent = sorted(allq, key=lambda x: -x["id"])[:5]  # 카드는 최근 5건 - 나머지는 /engine(전체 목록·검색)
        for x in recent:  # 첨부 - 화면의 축소판·링크용(허브 /api/engine/attach/<id>/<파일> 로 본다)
            att = engine_requests.attach_files(x["id"])
            if att:
                x["attachments"] = [{"name": a["name"], "size": a["size"], "url": f"/api/engine/attach/{x['id']}/{a['name']}"} for a in att]
        return self.send_json({"ok": True, "session": info, "counts": engine_requests.counts(), "recent": recent, "total": len(allq), "git": info.get("git") or {},
                               "startRequest": engine_requests.start_request(), "sessionOff": info.get("state", "off") == "off",  # manual 도 켜진 것
                               **({"deploy": __import__("engine_deploy").status()} if self.role == "admin" else {})})  # 마지막 배포(카드 배지·진행 따라가기)

    def api_post_engine(self, what, q):
        """requests: {action: add, title, body, …}(로그인 사용자 누구나) · {action: status, id, status, reply?…}·{action: remove, id}·{action: priority, id, priority}(관리자)
        session: {action: start|stop|model}(관리자)."""
        if not HUB:
            return self.err(404, "허브(시작 페이지)에서")
        import engine_requests
        b = self.body_json() or {}
        who = self.user or "local"
        if what == "deploy":  # {action: run} - 엔진 배포(병합·시험·재시작·push·적용됨, 관리자). 떼어 낸 프로세스가 하므로 바로 돌아온다(진행은 GET ?fetch=0)
            if self.role != "admin":
                self._event = "engine.deploy.denied"
                return self.err(403, "관리자만")
            if b.get("action") != "run":
                return self.err(400, "action = run")
            if WS_ENGINE is not None and WS_ENGINE.state == "running":
                return self.err(409, "엔진 세션이 턴을 처리 중이다 - 끝난 뒤 배포한다")
            import engine_deploy
            try:
                d = engine_deploy.start(who)
            except ValueError as e:
                return self.err(409, str(e))
            if WS_ENGINE is not None:  # 세션은 병합·시험(몇 분) 동안 그대로 두고 재시작 직전에 끈다(0.22.40)
                threading.Thread(target=_deploy_stop_engine, name="deploy-stop-engine", daemon=True).start()
            self._event = "engine.deploy"
            return self.send_json({"ok": True, "last": d})
        if what == "tidy":  # {action: clean, categories: […]} - 보고된 것 중 고른 범주를 지운다(관리자, 범주가 없으면 engine_tidy.DEFAULTS)
            if self.role != "admin":
                self._event = "engine.tidy.denied"
                return self.err(403, "관리자만")
            import engine_tidy
            r = engine_tidy.clean([c for c in (b.get("categories") or []) if c in engine_tidy.CATEGORIES] or None)
            self._event = "engine.tidy"
            return self.send_json({"ok": True, **r})
        if what == "requests":
            act = b.get("action")
            try:
                if act == "add":
                    it = engine_requests.add(b.get("title"), b.get("body") or "", kind="user", user=who, ws=b.get("ws"), ws_id=b.get("wsId"),
                                             request=b.get("request"), deck=b.get("deck"), slide=b.get("slide"), evidence=b.get("evidence") or [],
                                             priority=b.get("priority") or 0)
                    att = engine_requests.claim_attachments(it["id"], b.get("attachments") or [])  # _new/ 에 올려 둔 파일을 이 요청 폴더로
                    if att:
                        it = engine_requests.update(it["id"], by=who, evidence=list(it.get("evidence") or []) + att)
                    self._event = f"engine.request.add:{it['id']}"
                    return self.send_json({"ok": True, "item": it, "counts": engine_requests.counts(), "note": engine_requests.pending_note(it["status"]),
                                           "sessionOff": not engine_requests.session_state().get("connected")})
                if act == "startRequest":  # 일반 사용자가 관리자에게 엔진 세션 시작을 요청 - 묶어서 기록, 접근 로그에 남김
                    d = engine_requests.request_start(who)
                    self._event = "engine.start_requested"
                    return self.send_json({"ok": True, "startRequest": d})
                if self.role != "admin":
                    self._event = "engine.request.denied"
                    return self.err(403, "관리자만")
                if act == "status":
                    it = engine_requests.update(b.get("id"), status=b.get("status"), by=who, reply=b.get("reply"), commit=b.get("commit"),
                                                branch=b.get("branch"), test=b.get("test"), appliedCommit=b.get("appliedCommit"), engineVersion=b.get("engineVersion"))
                    self._event = f"engine.request.{b.get('status')}:{it['id']}"
                    return self.send_json({"ok": True, "item": it, "counts": engine_requests.counts()})
                if act == "priority":
                    it = engine_requests.update(b.get("id"), by=who, priority=b.get("priority"))
                    return self.send_json({"ok": True, "item": it})
                if act == "remove":
                    engine_requests.remove(b.get("id"))
                    self._event = f"engine.request.remove:{b.get('id')}"
                    return self.send_json({"ok": True, "counts": engine_requests.counts()})
            except ValueError as e:
                return self.err(400, str(e))
            return self.err(400, "action = add|status|priority|remove")
        if what == "session":
            if self.role != "admin":  # 엔진 커밋 권한이 있는 세션 - 관리자만
                self._event = "engine.session.denied"
                return self.err(403, "엔진 개발 세션은 관리자만 시작·중지할 수 있다")
            if WS_ENGINE is None:
                return self.err(503, "엔진 세션 관리자가 없다")
            if self._session_post(WS_ENGINE, b, who):
                if b.get("action") == "start" and WS_ENGINE.state != "off":
                    engine_requests.clear_start_request()  # 시작했으니 "관리자에게 시작 요청" 은 끝
                return
            return self.err(400, "action = start|stop|model")
        if what == "attach":  # {name, type, data(base64)} → hub/engine/attach/_new/<파일> (요청 add 때 attachments 로 넘기면 그 요청 폴더로 옮긴다)
            import base64
            ctype = str(b.get("type") or "").split(";")[0].strip().lower()
            name = str(b.get("name") or "")[:120]
            ext = self.ATTACH_TYPES.get(ctype) or (Path(name).suffix.lower() if Path(name).suffix.lower() in self.ATTACH_TYPES.values() else None)
            if not ext:
                return self.err(400, f"지원하지 않는 형식: {ctype or name or '?'} (그림·PDF·글·pptx/docx/xlsx)")
            try:
                data = base64.b64decode(str(b.get("data") or ""), validate=True)
            except (ValueError, TypeError):
                return self.err(400, "data 는 base64")
            if not data or len(data) > self.ATTACH_MAX:
                return self.err(413 if data else 400, "내용 없음" if not data else f"너무 크다({len(data) // 1024 // 1024}MB > {self.ATTACH_MAX // 1024 // 1024}MB)")
            d = engine_requests.ATTACH_DIR / "_new"
            d.mkdir(parents=True, exist_ok=True)
            fid = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:22]
            p = d / f"{fid}{ext}"
            p.write_bytes(data)
            self._event = "engine.attach"
            return self.send_json({"ok": True, "name": p.name, "orig": name or p.name, "type": ctype or mimetypes.guess_type(str(p))[0], "size": len(data), "url": f"/api/engine/attach/_new/{p.name}"})
        return self.err(404, "없는 API")

    def sse_events(self, since, ws=None):
        """진행 이벤트를 SSE 로 밀어 준다 - id = seq, event = 종류, data = JSON. 25초마다 `: keepalive`(Cloudflare 무료 100초 응답 한계).
        클라이언트가 끊으면(소켓 EOF 감시) 끝난다. 중계(허브)는 text/event-stream 응답을 줄 단위로 흘린다(H.proxy)."""
        ws = ws or WS
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        last, idle = since, 0.0
        closed = self._watch_close()

        def send(text):
            self.wfile.write(text.encode("utf-8"))
            self.wfile.flush()
        try:
            send("retry: 3000\n\n")
            send(f"event: state\ndata: {json.dumps({'state': ws.state, 'seq': ws.seq, 'agent': ws.agent, 'model': ws.model}, ensure_ascii=False)}\n\n")
            while not closed.is_set():
                evs = ws.events_since(last)
                for e in evs:
                    last = e["seq"]
                    send(f"id: {e['seq']}\nevent: {e['type']}\ndata: {json.dumps(e, ensure_ascii=False)}\n\n")
                    idle = 0.0
                time.sleep(0.5)
                idle += 0.5
                if idle >= 25:
                    send(": keepalive\n\n")
                    idle = 0.0
        except (OSError, ValueError):  # 연결 끊김
            return

    def _watch_close(self, on_close=None):
        """클라이언트가 연결을 끊는 것을 바로 알아챈다(쓰기 실패에 기대면 Windows 에서는 keepalive 두 번 = 50초까지 늦다).
        스트리밍 응답은 요청 본문이 더 오지 않으므로 소켓에서 EOF 를 기다리는 스레드를 둔다. 돌려주는 Event 가 set 되면 끊긴 것."""
        closed = threading.Event()

        def watch():
            try:
                while not closed.is_set():
                    if not self.connection.recv(1):
                        break
            except OSError:  # 상대가 리셋해도 "끊김"
                pass
            closed.set()
            if on_close:
                try:
                    on_close()
                except Exception:  # noqa: BLE001
                    pass
        threading.Thread(target=watch, daemon=True).start()
        return closed

    def api_post_wsession(self, what, q):
        """{action: start, agent?, model?, saveAs?: local|shared} · {action: stop} · {action: model, model, saveAs?}. 로그인 사용자 누구나(로컬 직접 접속은 local)."""
        if HUB or WS is None:
            return self.err(404, "허브에는 세션이 없다 - 작업 공간(중계 /w/<이름>/api/wsession)에서")
        b = self.body_json() or {}
        act = b.get("action")
        who = self.user or "local"
        if self._session_post(WS, b, who, save_defaults=self._save_session_defaults):
            return  # start·stop·model 은 공통 처리에서 응답까지 끝냈다
        try:
            if act == "defaults":  # 세션 없이 작업 공간 기본(에이전트·모델)만 저장
                vals = {k: str(b[k]) for k in ("sessionAgent", "sessionModel") if b.get(k)}
                self._save_session_defaults(b.get("saveAs") or "local", vals)
                import agents
                return self.send_json({"ok": True, **agents.effective(read_config())})
        except ValueError as e:
            self._event = f"session.denied"
            return self.err(400, str(e))
        return self.err(400, "action = start|stop|model|defaults")

    def _save_session_defaults(self, where, vals):
        """작업 공간 기본 에이전트·모델 - local 은 nexa-slide.local.json(PC 별, git 제외), shared 는 nexa-slide.json(공유)."""
        from paths import LOCAL_CONFIG
        f = WORKSPACE / (LOCAL_CONFIG if where == "local" else "nexa-slide.json")
        try:
            cfg = json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {}
            cfg = cfg if isinstance(cfg, dict) else {}
        except (OSError, ValueError):
            cfg = {}
        cfg.update(vals)
        atomic_write(f, json.dumps(cfg, ensure_ascii=False, indent=2) + "\n")

    # ---------- AI 세션 어댑터(B-2) - 설치·로그인 확인과 기본값 ----------
    def api_get_agent(self, _, q):
        """{agents: {claude, codex}(probe), agent, model, sources, limits, models} - 작업 공간 서버는 그 설정까지, 허브는 전역만."""
        import agents
        refresh = (q.get("refresh") or ["0"])[0] == "1"
        eff = agents.effective(None if HUB else read_config())
        self.send_json({"ok": True, "agents": agents.probe_all(refresh=refresh), **eff, "canAllowWeb": bool(eff.get("allowWeb")) and self._can_allow_web(),
                        "canGrant": self._can_allow_web()})

    # ---------- 시작 페이지(허브) ----------
    def hub_call(self, fn, *args):
        try:
            self.send_json(fn(*args))
        except hub.HubError as e:
            self.send_json({"ok": False, "error": str(e), **e.extra}, 400)

    def api_get_home(self, what, q):
        if what == "live":  # 시작 페이지 주기 갱신 - 최근 작업의 실행·세션 상태와 서버 작업 요약만(템플릿·시작 내용 목록은 빼서 가볍게)
            d = hub.home(None if HUB else WORKSPACE, REFUSED)
            out = {"ok": True, "recent": d.get("recent", []), "current": d.get("current")}
            if HUB:
                import engine_requests
                c = engine_requests.counts()
                m = engine_requests.session_state()
                out["engineWork"] = {"pending": c.get("open", 0) + c.get("triage", 0), "triage": c.get("triage", 0), "sessionOff": not ((WS_ENGINE and WS_ENGINE.state != "off") or (m.get("connected") and m.get("kind") == "manual")),
                                     "startRequest": engine_requests.start_request()}
            return self.send_json(out)
        d = hub.home(None if HUB else WORKSPACE, REFUSED)
        d.update({"mode": "hub" if HUB else "workspace", "port": self.server.server_port, "user": self.me()})
        if HUB:  # 서버 작업 주의 표시(메뉴 배지) - 처리·승인 대기가 있는데 엔진 세션이 꺼져 있으면
            import engine_requests
            c = engine_requests.counts()
            m = engine_requests.session_state()
            d["engineWork"] = {"pending": c.get("open", 0) + c.get("triage", 0), "triage": c.get("triage", 0), "sessionOff": not ((WS_ENGINE and WS_ENGINE.state != "off") or (m.get("connected") and m.get("kind") == "manual")), "startRequest": engine_requests.start_request()}  # home.engine 은 엔진 경로(문자열)
        self.send_json(d)

    def api_post_project(self, _, q):
        b = self.body_json() or {}
        if b.get("action") == "session":  # 허브에서 작업 공간 세션 켜기·끄기·모델(꺼진 서버면 먼저 띄운다) - 로그인 사용자 누구나
            self._event = f"session.{b.get('op')}:{Path(str(b.get('path') or '')).name}" + (":web" if b.get("allowWeb") else "") + "".join(f":{g}" for g in (b.get("grants") or []) if g in ("git", "push", "root"))
            return self.hub_call(hub.session_ws, b.get("path"), b.get("op"), b.get("agent"), b.get("model"), self.user, self.role, b.get("saveAs"), bool(b.get("allowWeb")), b.get("grants"))
        if b.get("action") == "open" and not HUB and b.get("path") and Path(b["path"]).resolve() == WORKSPACE:
            hub.remember(WORKSPACE, CONFIG.get("title", WORKSPACE.name))
            return self.send_json({"ok": True, "path": str(WORKSPACE), "url": f"http://127.0.0.1:{self.server.server_port}/"})
        if b.get("action") == "template":  # 회사 템플릿 만들기(마법사) - 관리자, 또는 이 허브에서 연 작업 공간(최근 작업)에 한해 로그인 사용자. 작업 공간 서버는 자기 작업 공간만
            ws = str(b.get("ws") or b.get("path") or "")
            if HUB:
                if self.role != "admin" and hub.ws_by_id(hub.ws_id(ws or "?")) is None:
                    self._event = "template.denied"
                    return self.err(403, "회사 템플릿은 관리자 또는 이 허브에서 연 작업 공간에만 만들 수 있다")
            elif not ws or Path(ws).resolve() != WORKSPACE:
                return self.err(400, "이 서버의 작업 공간에만 만들 수 있다")
            self._event = f"template.create:{Path(ws).name}:{re.sub(r'[^A-Za-z0-9_-]', '', str(b.get('name') or ''))[:40]}"
            return self.hub_call(hub.create_template, b)
        self.hub_call(hub.project, b)

    def api_get_preview(self, _, q):
        with PREVIEW_LOCK:  # 같은 미리보기를 동시에 만들지 않게
            self.hub_call(hub.preview, (q.get("template") or [None])[0], (q.get("starter") or [None])[0], (q.get("lang") or ["ko"])[0], None if HUB else WORKSPACE)

    def api_post_settings(self, _, q):
        b = self.body_json() or {}
        if any(k in b for k in hub.SESSION_KEYS) and self.role != "admin":  # AI 세션 전역 기본은 관리자만(결정 1)
            self._event = "settings.denied"
            return self.err(403, "AI 세션 전역 설정은 관리자만 바꿀 수 있다")
        flips = [f"{k}:{'on' if b.get(k) else 'off'}" for k in ("sessionAllowWeb", "sessionAllowGit", "sessionAllowPush", "sessionRepoRoot") if k in b]
        if flips:  # 보안에 닿는 설정은 접근 로그에 남긴다
            self._event = "settings." + ",".join(flips)

        def save(body):
            hub.update_settings(body)
            return {"ok": True, **hub.home(None if HUB else WORKSPACE, REFUSED)}
        self.hub_call(save, b)

    def api_get_fs(self, _, q):
        self.hub_call(hub.list_dir, (q.get("path") or [""])[0])

    def api_get_templates(self, _, q):
        self.send_json({"current": TEMPLATE["name"], "templates": list_templates()})

    def api_get_session(self, _, q):
        self.send_json(session_status())

    def api_post_flush(self, i, q):
        """편집기 "지금 보내기" — 감시 스크립트가 다음 확인(1초 이내)에 조용한 대기 없이 바로 내보낸다."""
        STATE.mkdir(parents=True, exist_ok=True)
        atomic_write(STATE / "flush.json", dumps({"deck": i, "at": dt.datetime.now().isoformat(timespec="seconds")}))
        self.send_json({"ok": True, "session": session_status()})

    # ---------- 작업 공간 관리(정리·보관) - studio/tidy.py. 허브 관리자(중계) 또는 작업 공간 서버 로컬 직접 접속만 ----------
    def _tidy_ok(self):
        if HUB:
            self.err(404, "작업 공간 서버에서"); return False
        if not self._can_allow_web():
            self._event = "tidy.denied"; self.err(403, "관리자만"); return False
        return True

    def api_get_tidy(self, _, q):
        """정리 대상 보고 {items, summary, tidy(옮겨 둔 것), total}."""
        if not self._tidy_ok():
            return
        import tidy
        self.send_json({"ok": True, **tidy.scan()})

    def api_post_tidy(self, _, q):
        """{action: clean, categories: [...], paths: [...], includeKept} → out/.tidy/<시각>/ 로 옮김 · {action: purge} · {action: restore, stamp} · {action: archive, all, out}."""
        if not self._tidy_ok():
            return
        import tidy
        b = self.body_json() or {}
        act = b.get("action")
        try:
            if act == "clean":
                r = tidy.clean(b.get("categories") or [], b.get("paths") or [], bool(b.get("includeKept")))
            elif act == "purge":
                r = tidy.purge()
            elif act == "restore":
                r = tidy.restore(str(b.get("stamp") or ""))
            elif act == "archive":
                r = tidy.archive(bool(b.get("all")), b.get("out") or None)
            else:
                return self.err(400, "action = clean|purge|restore|archive")
        except (ValueError, OSError) as e:
            return self.err(400, str(e))
        self._event = f"tidy.{act}"
        self.send_json({"ok": True, **r, "report": tidy.scan()})

    # ---------- 요청 메모 ----------
    def _reqs(self, i):
        p = req_path(i)
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []

    def api_get_requests(self, i, q):
        self.send_json(self._reqs(i))

    def api_post_engine_request(self, _, q):
        """작업 공간 세션이 엔진 요청을 큐에 넣는 길(로컬 직접 접속만) - engine_request.py add 가 작업 공간 안에서 서버가 떠 있으면 이리로 온다.
        큐 파일은 사용자 설정 폴더(작업 공간 밖)라 Codex 샌드박스(workspace-write)에서는 직접 쓸 수 없어 명령이 멈추거나 실패했다(0.22.27) - save_deck 과 같은 방식.
        {title, body, request?, deck?, slide?, evidence?[]} → {ok, item, note}. kind 는 늘 session(triage) - 세션이 관리자 승인을 건너뛰지 못하게."""
        if HUB:
            return self.err(404, "작업 공간 서버에서")
        if self.via_hub:
            return self.err(403, "작업 공간 서버 로컬에서만(세션 CLI)")
        import engine_requests
        b = self.body_json() or {}
        title = " ".join(str(b.get("title") or "").split())
        if not title:
            return self.err(400, "제목 없음")
        try:
            wid = hub.ws_id(WORKSPACE)
        except Exception:  # noqa: BLE001
            wid = None
        user = (self.headers.get("X-Nexa-Session-User") or str(b.get("user") or "")).strip()[:40] or None
        evidence = [str(x)[:500] for x in (b.get("evidence") or []) if str(x)][:20] if isinstance(b.get("evidence"), list) else []
        it = engine_requests.add(title, str(b.get("body") or ""), kind="session", user=user, ws=str(WORKSPACE), ws_id=wid,
                                 request=(str(b["request"])[:40] if b.get("request") else None), deck=(str(b["deck"])[:80] if b.get("deck") else None),
                                 slide=(str(b["slide"])[:40] if b.get("slide") else None), evidence=evidence, priority=0)
        engine_requests.link_origin(it)  # 원 요청에 engineRequest 배지 - 자기 서버의 /api/requests 로 POST(다른 스레드) 하므로 WRITE_LOCK 밖에서
        self._event = f"engine.request:{it['id']}"
        return self.send_json({"ok": True, "item": it, "note": engine_requests.pending_note(it["status"])})

    def api_post_requests(self, i, q):
        b = self.body_json() or {}
        act = b.get("action", "add")
        with WRITE_LOCK:
            items = self._reqs(i)
            if act == "add":
                text = str(b.get("text", "")).strip()
                if not text:
                    return self.err(400, "내용 없음")
                st = b.get("status") if b.get("status") in ("draft", "open") else "open"
                par = next((r for r in items if r.get("id") == b.get("parent")), None) if b.get("parent") else None
                if b.get("parent") and not par:
                    return self.err(400, "원 요청이 없다(지워졌을 수 있다)")
                item = {"id": "r" + dt.datetime.now().strftime("%Y%m%d%H%M%S%f")[:17], "slide": b.get("slide"),
                        "element": b.get("element"), "text": text[:2000], "status": st, "reply": "",
                        "created": dt.datetime.now().isoformat(timespec="seconds")}
                if isinstance(b.get("region"), dict):  # 그리기 모드 영역 {kind: rect|pen|pin, box:[x,y,w,h], points:[[x,y]…]}
                    item["region"] = b["region"]
                rg = str(b.get("range") or "").strip().upper().replace("$", "")
                if rg and CELL_RANGE.match(rg):  # 시트 요청 - 고른 셀 범위(slide = 시트 탭 id)
                    item["range"] = rg
                els = [str(x)[:40] for x in (b.get("elements") or []) if isinstance(x, (str, int))][:50]  # 여러 요소를 고른 메모 - element 는 첫 것
                if len(els) > 1:
                    item["elements"] = els
                    item["element"] = item.get("element") or els[0]
                if par:  # 후속 요청 - 앞선 요청에 이어 묻는다. 대상(slide·element·region)은 따로 주지 않으면 물려받고, 원 요청은 그대로 둔다
                    item["parent"], item["thread"] = par["id"], par.get("thread") or par["id"]
                    for k in ("slide", "element", "region", "range"):
                        if item.get(k) is None and par.get(k) is not None:
                            item[k] = par[k]
                att = self._valid_attachments(i, b.get("attachments"))
                if att:
                    item["attachments"] = att
                items.append(item)
            elif act == "send":  # 초안(draft) → 대기(open) — "요청 N개 보내기"
                for r in items:
                    if r.get("status") == "draft" and (not b.get("slide") or r.get("slide") == b.get("slide")):
                        r["status"], r["updated"] = "open", dt.datetime.now().isoformat(timespec="seconds")
            elif act == "discard":  # 초안 지우기(현재 슬라이드 또는 전체) - 첨부도 같이
                gone = [r for r in items if r.get("status") == "draft" and (not b.get("slide") or r.get("slide") == b.get("slide"))]
                for r in gone:
                    self._drop_attachments(i, r)
                items = [r for r in items if r not in gone]
            elif act == "delete":
                for r in items:
                    if r.get("id") == b.get("id"):
                        self._drop_attachments(i, r)
                items = [r for r in items if r.get("id") != b.get("id")]
            elif act == "update":
                for r in items:
                    if r.get("id") == b.get("id"):
                        for k in ("status", "reply", "text"):
                            if k in b:
                                r[k] = b[k]
                        for k in ("engineRequest", "engineNote"):  # 엔진 요청 연결(번호)·진행 알림 - engine_requests.link_origin/resume_origin
                            if k in b:
                                if b[k] is None or b[k] == "":
                                    r.pop(k, None)
                                else:
                                    r[k] = int(b[k]) if k == "engineRequest" else str(b[k])[:500]
                        r["updated"] = dt.datetime.now().isoformat(timespec="seconds")  # 마지막 진행 시각 - 요청 탭 기본 보기(24시간)의 기준
                        if "attachments" in b:
                            new = self._valid_attachments(i, b.get("attachments"))
                            keep = {Path(str(a.get("path") or "")).name for a in new}
                            self._drop_attachments(i, {"attachments": [a for a in (r.get("attachments") or []) if Path(str(a.get("path") or "")).name not in keep]})  # 빠진 첨부 파일은 지운다
                            r["attachments"] = new
            else:
                return self.err(400, "action = add|update|delete|send|discard")
            atomic_write(req_path(i), dumps(items))
        self.send_json(items)

    # ---------- 요청 첨부(클립보드 그림·파일) - out/attach/<덱>/<id>.<확장자>, 편집기는 /out/attach/… 로 보고 세션은 작업 공간 안 경로로 Read ----------
    ATTACH_TYPES = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif", "image/webp": ".webp", "image/svg+xml": ".svg", "application/pdf": ".pdf",
                    "text/plain": ".txt", "text/markdown": ".md", "text/csv": ".csv", "application/json": ".json",
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx"}
    ATTACH_MAX = 12 * 1024 * 1024

    def _attach_dir(self, i):
        return OUT / "attach" / i

    def _valid_attachments(self, i, lst):
        """클라이언트가 보낸 첨부 목록 중 실제로 올려진 파일만(경로는 out/attach/<덱>/ 아래) - 다른 경로는 버린다."""
        out = []
        base = self._attach_dir(i).resolve()
        for a in (lst or [])[:10]:
            if not isinstance(a, dict) or not a.get("path"):
                continue
            p = (WORKSPACE / str(a["path"])).resolve()
            if base in p.parents and p.is_file():
                out.append({"path": p.relative_to(WORKSPACE.resolve()).as_posix(), "name": str(a.get("name") or p.name)[:120],
                            "type": str(a.get("type") or mimetypes.guess_type(str(p))[0] or "application/octet-stream")[:80], "size": p.stat().st_size})
        return out

    def _drop_attachments(self, i, r):
        for a in r.get("attachments") or []:
            try:
                p = (WORKSPACE / str(a.get("path") or "")).resolve()
                if self._attach_dir(i).resolve() in p.parents:
                    p.unlink(missing_ok=True)
            except OSError:
                pass

    IMAGE_TYPES = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif", "image/webp": ".webp", "image/svg+xml": ".svg"}

    def api_post_mermaid(self, _, q):
        """편집기 다이어그램(코드) - {code, name?} → mermaid-cli(npx)로 PNG 를 그려 assetRoot/assets/images/diagram-<날짜-시각>.png(+.mmd)에 두고 {src, w, h} 를 돌려준다."""
        if HUB:
            return self.err(404, "작업 공간 서버에서")
        b = self.body_json() or {}
        code = str(b.get("code") or "").strip()
        if not code:
            return self.err(400, "code 가 비었다")
        if len(code) > 20000:
            return self.err(413, "코드가 너무 길다")
        import render_mermaid
        import shutil
        import subprocess
        stem = re.sub(r"[^\w가-힣-]+", "_", str(b.get("name") or "diagram"))[:30].strip("._") or "diagram"
        d = ASSET_ROOT / "assets" / "images"
        d.mkdir(parents=True, exist_ok=True)
        png = d / f"{stem}-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}.png"
        mmd = png.with_suffix(".mmd")
        cfg = d / "_mermaid-config.json"
        cfg.write_text(json.dumps(render_mermaid.CONFIG, ensure_ascii=False, indent=1), encoding="utf-8")
        mmd.write_text(code + "\n", encoding="utf-8")
        npx = shutil.which("npx.cmd" if os.name == "nt" else "npx") or shutil.which("npx")
        if not npx:
            return self.err(400, "mermaid 렌더에 Node(npx)가 필요하다 - Node.js 를 설치한다")
        try:
            r = subprocess.run([npx, "-y", "@mermaid-js/mermaid-cli", "-i", str(mmd), "-o", str(png), "-s", "2", "-b", "white", "-c", str(cfg)],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180, cwd=str(ASSET_ROOT))
        except subprocess.TimeoutExpired:
            return self.err(504, "mermaid 렌더가 180초 안에 끝나지 않았다(처음 한 번은 mermaid-cli 내려받기)")
        if r.returncode != 0 or not png.exists():
            msg = (r.stderr or r.stdout or "").strip().splitlines()
            return self.err(400, "mermaid 렌더 실패: " + " / ".join(msg[-4:])[:600])
        head = png.read_bytes()[:24]
        w = h = None
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            w, h = int.from_bytes(head[16:20], "big") // 2, int.from_bytes(head[20:24], "big") // 2  # -s 2 로 그렸으니 CSS px 는 절반
        self._event = f"mermaid:{png.name}"
        self.send_json({"ok": True, "src": png.resolve().relative_to(ASSET_ROOT.resolve()).as_posix(), "mmd": mmd.name, "w": w, "h": h})

    def api_post_image(self, _, q):
        """편집기 그림 삽입 - {name, type, data(base64)} → 작업 공간 그림 폴더(assetRoot/assets/images/<날짜-시각>-<이름>)에 저장하고 {src} 를 돌려준다(src = assetRoot 기준, image 요소의 src)."""
        import base64
        if HUB:
            return self.err(404, "작업 공간 서버에서")
        b = self.body_json() or {}
        ctype = str(b.get("type") or "").split(";")[0].strip().lower()
        name = str(b.get("name") or "")[:120]
        ext = self.IMAGE_TYPES.get(ctype) or (Path(name).suffix.lower() if Path(name).suffix.lower() in self.IMAGE_TYPES.values() else None)
        if not ext:
            return self.err(400, f"그림 파일만(png·jpg·gif·webp·svg): {ctype or name or '?'}")
        try:
            data = base64.b64decode(str(b.get("data") or ""), validate=True)
        except (ValueError, TypeError):
            return self.err(400, "data 는 base64")
        if not data:
            return self.err(400, "내용 없음")
        if len(data) > self.ATTACH_MAX:
            return self.err(413, f"너무 크다({len(data) // 1024 // 1024}MB > {self.ATTACH_MAX // 1024 // 1024}MB)")
        stem = re.sub(r"[^\w가-힣.-]+", "_", Path(name).stem)[:40].strip("._") or "image"
        d = ASSET_ROOT / "assets" / "images"
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}-{stem}{ext}"
        n = 1
        while p.exists():
            n += 1
            p = d / f"{p.stem.rsplit('-', 1)[0] if n > 2 else p.stem}-{n}{ext}"
        p.write_bytes(data)
        self._event = f"image:{p.name}"
        self.send_json({"ok": True, "src": p.resolve().relative_to(ASSET_ROOT.resolve()).as_posix(), "name": p.name, "size": len(data)})

    def api_post_attach(self, i, q):
        """{name, type, data(base64)} → 파일로 저장하고 {path, name, type, size, url} 을 돌려준다. 요청을 add 할 때 attachments 로 넘긴다."""
        import base64
        if HUB:
            return self.err(404, "작업 공간 서버에서")
        if not deck_path(i).exists():
            return self.err(404, "덱 없음")
        b = self.body_json() or {}
        ctype = str(b.get("type") or "").split(";")[0].strip().lower()
        name = str(b.get("name") or "")[:120]
        ext = self.ATTACH_TYPES.get(ctype) or (Path(name).suffix.lower() if Path(name).suffix.lower() in self.ATTACH_TYPES.values() else None)
        if not ext:
            return self.err(400, f"지원하지 않는 형식: {ctype or name or '?'} (그림·PDF·글·pptx/docx/xlsx)")
        try:
            data = base64.b64decode(str(b.get("data") or ""), validate=True)
        except (ValueError, TypeError):
            return self.err(400, "data 는 base64")
        if not data:
            return self.err(400, "내용 없음")
        if len(data) > self.ATTACH_MAX:
            return self.err(413, f"너무 크다({len(data) // 1024 // 1024}MB > {self.ATTACH_MAX // 1024 // 1024}MB)")
        d = self._attach_dir(i)
        d.mkdir(parents=True, exist_ok=True)
        fid = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:22]
        p = d / f"{fid}{ext}"
        p.write_bytes(data)
        rel = p.resolve().relative_to(WORKSPACE.resolve()).as_posix()
        self._event = f"attach:{i}"
        self.send_json({"ok": True, "path": rel, "name": name or p.name, "type": ctype or mimetypes.guess_type(str(p))[0], "size": len(data), "url": f"/out/attach/{i}/{p.name}"})

    # ---------- 기록(자동 백업) ----------
    def api_get_history(self, i, q):
        h = DECKS / ".history" / i
        f = (q.get("f") or [""])[0]
        if f:
            p = (h / f).resolve()
            if p.parent != h.resolve() or not p.is_file() or p.suffix != ".json":
                return self.err(404, "없는 기록")
            return self.send_json(json.loads(p.read_text(encoding="utf-8")))
        out = []
        for p in sorted(h.glob("*.json"), reverse=True) if h.exists() else []:
            # last-build.json 은 백업이 아니라 마지막 빌드 결과(build_deck 의 편집 보호용) - stem "last-build" 도 "-build" 로 끝나므로 먼저 거른다
            kind = "last-build" if p.name == "last-build.json" else "build" if p.stem.endswith("-build") else "ext" if p.stem.endswith("-ext") else "save"
            if kind == "last-build":
                continue
            out.append({"file": p.name, "kind": kind, "size": p.stat().st_size,
                        "at": dt.datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds")})
        self.send_json(out)

    # ---------- 내보내기·렌더 ----------
    def api_post_export(self, i, q):
        if not deck_path(i).exists():
            return self.err(404, "덱 없음")
        if deck_kind(i) == "sheet":  # 시트 문서 → out/<id>.xlsx, 매크로(VBA)가 있으면 .xlsm (export_xlsx.py)
            code, log = run([sys.executable, str(STUDIO / "export_xlsx.py"), i], 120)
            f = OUT / f"{i}.xlsx"
            m = re.search(r"^xls[xm]: (.+)$", log, re.M)  # export_xlsx 가 실제로 쓴 파일(매크로면 .xlsm)
            if m:
                f = Path(m.group(1).strip())
            if code != 0 or not f.exists():
                return self.send_json({"ok": False, "error": "엑셀 내보내기 실패", "log": log}, 500)
            return self.send_json({"ok": True, "path": str(f), "url": f"/out/{f.name}?v={ver(f)}", "log": log, "name": export_name(i, f.suffix), "macros": f.suffix == ".xlsm"})
        if (q.get("embed") or ["0"])[0] == "1":  # 글꼴 포함 PPTX(PowerPoint) — 작업 공간 글꼴이 설치 안 됐으면 409 needInstall
            args = [sys.executable, str(STUDIO / "embed_fonts.py"), i] + (["--install"] if (q.get("install") or ["0"])[0] == "1" else [])
            code, log = run(args, 420)
            last = (log.strip().splitlines() or [""])[-1]
            try:
                res = json.loads(last)
            except ValueError:
                res = {}
            if code == 3 and res.get("needInstall"):
                return self.send_json({"ok": False, "needInstall": res["needInstall"]}, 409)
            f = OUT / f"{i}-fonts.pptx"
            if code != 0 or not f.exists():
                return self.send_json({"ok": False, "error": "글꼴 포함 저장 실패", "log": log}, 500)
            return self.send_json({"ok": True, **res, "url": f"/out/{i}-fonts.pptx?v={ver(f)}", "report": f"/out/{i}.fonts.json", "name": export_name(f"{i}-fonts", ".pptx")})
        code, log = export(i)
        f = OUT / f"{i}.pptx"
        if code != 0 or not f.exists():
            return self.send_json({"ok": False, "error": "export 실패", "log": log}, 500)
        if (q.get("pdf") or ["0"])[0] == "1":  # PDF - PowerPoint(Windows, pwsh)가 있으면 PPTX 를 PDF 로, 없으면 Chrome/Edge 헤드리스로 print.html 을 인쇄
            layout = (q.get("layout") or [""])[0]
            layout = layout if layout in ("notes", "h2", "h3", "h6") else ""  # 유인물(쪽당 2·3·6장)·노트 페이지는 Chrome 으로만(print.html?layout=)
            tag = {"notes": "-notes", "h2": "-handout2", "h3": "-handout3", "h6": "-handout6"}.get(layout, "")
            pdf = OUT / f"{i}{tag}.pdf"
            via, err = self._export_pdf(i, f, pdf, layout)
            if not pdf.exists():
                return self.send_json({"ok": False, "error": "PDF 를 만들지 못했다: " + err, "log": log}, 500)
            return self.send_json({"ok": True, "path": str(pdf), "url": f"/out/{i}{tag}.pdf?v={ver(pdf)}", "via": via, "log": log, "name": export_name(i, f"{tag}.pdf")})
        self.send_json({"ok": True, "path": str(f), "url": f"/out/{i}.pptx?v={ver(f)}", "log": log, "name": export_name(i, ".pptx")})

    def _export_pdf(self, i, pptx, pdf, layout=""):
        """(방법, 오류). PowerPoint COM(render_pptx.ps1 -Pdf) → 없으면 Chrome/Edge --print-to-pdf(print.html, 슬라이드마다 한 쪽).
        layout(notes·h2·h3·h6 = 노트 페이지·유인물)은 print.html 이 그리므로 Chrome 만 쓴다."""
        import shutil
        err = []
        pwsh = shutil.which("pwsh") or shutil.which("powershell")
        if os.name == "nt" and pwsh and not layout:
            code, log = run([pwsh, "-NoProfile", "-File", str(STUDIO / "render_pptx.ps1"), "-Pptx", str(pptx), "-OutDir", str(OUT / i), "-Pdf", str(pdf), "-NoPng"], 300)
            if code == 0 and pdf.exists():
                return "powerpoint", ""
            err.append("PowerPoint: " + (log.strip().splitlines() or ["?"])[-1][:200])
        browsers = [r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
        br = next((b for b in browsers if Path(b).exists()), None) or shutil.which("chrome") or shutil.which("google-chrome") or shutil.which("msedge") or shutil.which("chromium")
        if br:
            url = f"http://127.0.0.1:{self.server.server_port}/studio/print.html?deck={i}" + (f"&layout={layout}" if layout else "")
            prof = OUT / ".chrome-profile-pdf"
            code, log = run([br, "--headless=new", "--disable-gpu", "--no-sandbox", f"--user-data-dir={prof}", "--no-pdf-header-footer", "--virtual-time-budget=10000", f"--print-to-pdf={pdf}", url], 180)
            if pdf.exists():
                return "chrome", ""
            err.append("Chrome: " + (log.strip().splitlines() or ["?"])[-1][:200])
        else:
            err.append("PowerPoint(pwsh)도 Chrome/Edge 도 없다")
        return "", " / ".join(err)

    # ---------- 글꼴 프리셋 ----------
    def fonts_info(self):
        """글꼴 세트 목록(출처: template = 엔진 템플릿 기본 세트, workspace = 이 작업 공간이 nexa-slide.json 에 직접 정의한 세트),
        지금 쓰는 역할별 글꼴, 작업 공간 fonts/ 파일(글꼴 이름·굵기·설치 여부)."""
        cfg = read_config()
        t = resolve_tokens(cfg)
        wsp = cfg.get("fontPresets") if isinstance(cfg.get("fontPresets"), dict) else {}
        ps = []
        for k, v in t.get("fontPresets", {}).items():
            b, m = v.get("body", t["fonts"]["body"]), v.get("mono", t["fonts"]["mono"])  # 작업 공간 세트는 일부 역할만 있을 수 있다
            ps.append({"name": k, "source": "workspace" if k in wsp else "template",
                       "label": f"{b['latin']} · {m['latin']}" + (f" + {m['ea']}" if m.get("ea") not in (None, b["ea"]) else "")})
        cur = t.get("fontPreset", "")
        return {"ok": True, "current": cur, "source": "workspace" if cur in wsp else "template", "presets": ps,
                "fonts": {k: t["fonts"].get(k) for k in ("body", "heading", "mono")}, "workspacePresets": wsp,
                "fontsDir": str(fonts_dir()) if fonts_dir() else "", "files": self.font_files()}

    def font_files(self):
        d = fonts_dir()
        if not d or not d.is_dir():
            return []
        from PIL import ImageFont
        inst = [Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Windows/Fonts", Path("C:/Windows/Fonts"),
                Path.home() / "Library/Fonts", Path.home() / ".local/share/fonts"]
        out = []
        for f in sorted(d.iterdir()):
            if f.suffix.lower() not in (".ttf", ".otf", ".woff", ".woff2"):
                continue
            try:
                fam, style = ImageFont.truetype(str(f), 12).getname()
            except Exception:  # noqa: BLE001
                fam, style = f.stem, ""
            out.append({"file": f.name, "family": fam, "style": style, "installed": any((x / f.name).is_file() for x in inst)})
        return out

    FONT_FILES = {
        "Pretendard-Regular": "Pretendard-Regular.otf", "Pretendard-Medium": "Pretendard-Medium.otf",
        "Pretendard-SemiBold": "Pretendard-SemiBold.otf", "Pretendard-Bold": "Pretendard-Bold.otf",
        "Pretendard-ExtraBold": "Pretendard-ExtraBold.otf",
        "JetBrainsMono-Regular": "JetBrainsMono-Regular.ttf", "JetBrainsMono-Italic": "JetBrainsMono-Italic.ttf",
        "JetBrainsMono-Bold": "JetBrainsMono-Bold.ttf", "JetBrainsMono-BoldItalic": "JetBrainsMono-BoldItalic.ttf",
        "D2Coding": "D2Coding-Ver1.3.2-20180524.ttf", "D2Coding-Bold": "D2CodingBold-Ver1.3.2-20180524.ttf",
    }

    def api_get_fontfile(self, name, q):
        fn = self.FONT_FILES.get(name or "")
        if not fn:
            return self.err(404, "모르는 글꼴")
        for d in (Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Windows/Fonts", Path("C:/Windows/Fonts"),
                  Path.home() / "Library/Fonts", Path.home() / ".local/share/fonts"):
            p = d / fn
            if p.is_file():
                data = p.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "font/otf" if fn.endswith(".otf") else "font/ttf")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "max-age=86400")
                self.end_headers()
                self.wfile.write(data)
                return
        return self.err(404, "글꼴 파일 없음 — python3 nexa.py install_fonts 로 설치")

    WEIGHTS = (("thin", 100), ("extralight", 200), ("ultralight", 200), ("light", 300), ("medium", 500), ("semibold", 600),
               ("demibold", 600), ("extrabold", 800), ("ultrabold", 800), ("heavy", 900), ("black", 900), ("bold", 700))

    def api_get_fontcss(self, _, q):
        """작업 공간 fonts/ 의 글꼴 파일마다 @font-face — 이름·굵기는 파일에서 읽는다(편집기·미리보기가 설치 없이도 보이게)."""
        css = []
        d = fonts_dir()
        if d and d.is_dir():
            from PIL import ImageFont
            for f in sorted(d.iterdir()):
                if f.suffix.lower() not in (".ttf", ".otf", ".woff", ".woff2"):
                    continue
                try:
                    fam, style = ImageFont.truetype(str(f), 12).getname()
                except Exception:  # noqa: BLE001 — woff 등 Pillow 가 못 읽으면 파일 이름으로
                    fam, style = f.stem, f.stem
                st = (style or "").lower().replace(" ", "").replace("-", "")
                w = next((v for k, v in self.WEIGHTS if k in st), 400)
                fmt = {".otf": "opentype", ".ttf": "truetype", ".woff": "woff", ".woff2": "woff2"}[f.suffix.lower()]
                url = (self.headers.get("X-Forwarded-Prefix") or "") + "/wsfonts/" + quote(f.name)  # 허브 중계(/w/<id>)·공유 링크(/s/<토큰>)로 열렸으면 그 접두를 붙인다(허브로 새지 않게)
                css.append(f'@font-face {{ font-family: "{fam}"; font-weight: {w}; font-style: {"italic" if "italic" in st or "oblique" in st else "normal"}; '
                           f'font-display: swap; src: url("{url}") format("{fmt}"); }}')
        b = ("/* 작업 공간 글꼴(fonts/) */\n" + "\n".join(css) + "\n").encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/css; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def api_get_fontguide(self, _, q):
        """글꼴 안내 페이지(fonts.html)용 — 무료 글꼴 목록 + (작업 공간이면) 지금 세트의 역할별 글꼴·상태·설치 여부."""
        import font_report
        out = {"catalog": font_report.catalog(), "workspace": None}
        if not HUB:
            cfg = read_config()
            t = resolve_tokens(cfg)
            wsp = cfg.get("fontPresets") if isinstance(cfg.get("fontPresets"), dict) else {}
            roles, seen = [], set()
            for role in ("body", "heading", "mono"):
                f = t["fonts"].get(role) or {}
                for k in ("latin", "ea"):
                    name = f.get(k)
                    if not name or name in seen:
                        continue
                    seen.add(name)
                    st, cat = font_report.classify(name)
                    files = font_report.font_index().get(name.lower(), [])
                    roles.append({"role": role, "typeface": name, "status": st, "catalog": cat, "files": [
                        {"path": str(x), "where": "workspace" if fonts_dir() and x.parent == fonts_dir() else "system",
                         "installed": font_report.installed(x), "embed": font_report.embed_kind(font_report.fs_type(x))} for x in files[:3]]})
            out["workspace"] = {"title": CONFIG.get("title", WORKSPACE.name), "path": str(WORKSPACE), "preset": t.get("fontPreset", ""),
                                "source": "workspace" if t.get("fontPreset") in wsp else "template", "fontsDir": str(fonts_dir()), "fonts": roles}
        self.send_json(out)

    def api_get_fonts(self, _, q):
        self.send_json(self.fonts_info())

    def api_post_fonts(self, _, q):
        body = self.body_json() or {}
        if "savePreset" in body:  # 작업 공간 글꼴 세트 저장 — nexa-slide.json 의 fontPresets (엔진 템플릿은 바꾸지 않는다)
            name, pr = str(body.get("savePreset") or ""), body.get("preset")
            if HUB or not safe_id(name):
                return self.err(400, "세트 이름은 영문·숫자·-·_")
            if not isinstance(pr, dict) or not isinstance(pr.get("body"), dict) or not all(isinstance(pr["body"].get(k), str) and pr["body"].get(k) for k in ("css", "latin", "ea")):
                return self.err(400, "세트 형식: {body: {css, latin, ea, measure?}, heading?, mono?}")
            for k in pr:
                if k not in ("body", "heading", "mono") or not isinstance(pr[k], dict):
                    return self.err(400, f"모르는 역할: {k} (body·heading·mono)")
            with WRITE_LOCK:
                cfg = read_config(shared=True)  # PC 별 값(nexa-slide.local.json)을 공유 파일에 섞지 않는다
                cfg.setdefault("fontPresets", {})[name] = pr
                if body.get("select"):
                    cfg["fontPreset"] = name
                atomic_write(WORKSPACE / "nexa-slide.json", json.dumps(cfg, ensure_ascii=False, indent=2) + "\n")
            return self.send_json(self.fonts_info())
        name = str(body.get("preset", ""))
        if name not in {p["name"] for p in self.fonts_info()["presets"]}:
            return self.err(400, "없는 프리셋")
        code, log = run([sys.executable, str(STUDIO / "set_fonts.py"), name], 30)
        if code != 0:
            return self.send_json({"ok": False, "error": "프리셋 전환 실패", "log": log}, 500)
        self.send_json(self.fonts_info())

    def api_get_render(self, i, q):
        self.send_json({"ok": True, "slides": render_list(i)})

    def api_post_render(self, i, q):
        if not RENDER_LOCK.acquire(blocking=False):
            return self.err(429, "렌더 중")
        try:
            code, log = export(i)
            if code != 0:
                return self.send_json({"ok": False, "error": "export 실패", "log": log}, 500)
            ps = shutil.which("pwsh") or shutil.which("powershell")
            if not ps:
                return self.send_json({"ok": False, "error": "PowerShell 없음"}, 500)
            code, log2 = run([ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(STUDIO / "render_pptx.ps1"),
                              "-Pptx", str(OUT / f"{i}.pptx"), "-OutDir", str(OUT / i)], 300)
            if code != 0:
                return self.send_json({"ok": False, "error": "PowerPoint 렌더 실패", "log": log2}, 500)
            self.send_json({"ok": True, "slides": render_list(i), "log": log + "\n" + log2})
        finally:
            RENDER_LOCK.release()

    # ---------- 레이아웃 ----------
    def api_get_layouts(self, _, q):
        from layouts import LAYOUTS
        self.send_json([{"name": k, "label": v[0]} for k, v in LAYOUTS.items()])

    def api_get_slidetypes(self, _, q):
        """슬라이드 유형(studio/slide_types.json) — 목적별 묶음과, 유형마다 그 목적의 예시 내용으로 빌드한 슬라이드(미리보기·추가용)."""
        from content_i18n import tr
        from layouts import LAYOUTS, SAMPLES, build_slide
        cat = json.loads((STUDIO / "slide_types.json").read_text(encoding="utf-8"))
        part = (q.get("part") or ["day1"])[0]
        lang = (q.get("lang") or ["ko"])[0]  # 예시 슬라이드의 글 언어(studio/i18n/content.<lang>.json) - 유형 이름·설명은 i18n 필드로 화면이 고른다
        types = []
        for i, t in enumerate(cat["types"]):
            if t["layout"] not in LAYOUTS:
                continue
            try:
                s = tr(build_slide(t["layout"], tr({**SAMPLES.get(t["layout"], {}), **t.get("fields", {})}, lang), part, f"t{i:02d}"), lang)  # 레이아웃이 넣는 글(목차·N부·자리 글)도
            except Exception as e:  # noqa: BLE001 — 한 유형이 실패해도 목록은 보인다
                s = None
                t = {**t, "error": f"{type(e).__name__}: {e}"}
            types.append({**t, "layoutLabel": LAYOUTS[t["layout"]][0], "slide": s})
        self.send_json({"groups": cat["groups"], "types": types})

    def api_post_newslide(self, _, q):
        from layouts import SAMPLES, build_slide
        b = self.body_json() or {}
        name = b.get("layout", "bullets")
        if name not in SAMPLES:
            return self.err(400, "알 수 없는 레이아웃")
        self.send_json(build_slide(name, SAMPLES[name], b.get("part", "day1"), b.get("id", "new")))


class Server(ThreadingHTTPServer):
    """포트를 혼자 쓰는 서버. 표준 HTTPServer 는 SO_REUSEADDR 를 켜는데, Windows 에서는 이것 때문에
    두 프로세스가 같은 포트를 열 수 있다(뒤에 뜬 서버가 요청을 가로챔) → Windows 는 끄고 배타 사용을 켠다.
    macOS·Linux 는 SO_REUSEADDR 를 켜도 이미 듣고 있는 포트는 열 수 없고, 끄면 방금 끈 서버의 TIME_WAIT 연결 때문에
    restart 가 30~60초 동안 같은 포트를 열지 못한다 → 켠다."""
    allow_reuse_address = os.name != "nt"
    daemon_threads = True

    def server_bind(self):
        import socket
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def _bind(port, auto):
    """포트를 연다. 쓰는 중이면 auto 일 때 다음 포트(최대 50개)를 시도한다."""
    for p in range(port, port + (50 if auto else 1)):
        try:
            return Server(("127.0.0.1", p), H)
        except OSError:
            continue
    other = ""
    try:
        info = json.loads(SERVER_INFO.read_text(encoding="utf-8"))
        if int(info.get("port", 0)) == port:
            other = f" — 이 작업 공간의 서버가 이미 실행 중일 수 있다(pid {info.get('pid')}, {info.get('started')})"
    except (OSError, ValueError):
        pass
    sys.exit(f"포트 {port} 를 쓸 수 없다{other}. 다른 포트: --port <N>, 빈 포트 자동: --port auto, "
             f"또는 nexa-slide.json 의 \"port\" 를 바꾼다")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default=None, help="포트 번호 또는 auto (기본: nexa-slide.json port → 5600)")
    ap.add_argument("--force", action="store_true", help="이 작업 공간의 서버가 이미 떠 있어도 하나 더 띄운다")
    a = ap.parse_args()
    try:  # 이 PC 의 엔진 위치 기록 - 다른 PC 에서 만든 저장소의 실행기(nexa.py)도 이 엔진을 찾는다
        from paths import remember_engine
        remember_engine()
    except OSError:
        pass
    run = running_server()
    if run and not a.force:
        sys.exit(f"이 작업 공간의 서버가 이미 실행 중이다: {run['url']} (pid {run['pid']}, {run['started']}) — 그대로 쓰면 된다")
    auto = str(a.port).lower() == "auto"
    port = DEFAULT_PORT if a.port is None or auto else int(a.port)
    global WS, WS_ENGINE, SERVER_NAME
    import wsession
    if not HUB:
        DECKS.mkdir(parents=True, exist_ok=True)
        WS = wsession.WebSession()
        SERVER_NAME = hub.ws_id(WORKSPACE)
    else:  # 허브 - 엔진 개발 세션(엔진 요청 큐를 엔진 worktree 에서 처리, 관리자가 켠다)
        WS_ENGINE = wsession.WebSession(wsession.EngineProfile())
    srv = _bind(port, auto)
    port = srv.server_port
    if not a.force:  # 포트를 연 사이 같은 작업 공간의 다른 서버가 먼저 server.json 을 썼으면 물러난다(작업 공간당 서버 하나)
        try:
            other = json.loads(SERVER_INFO.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            other = {}
        from common import _serves_here
        if other.get("port") and int(other["port"]) != port and _serves_here(other["port"]):
            srv.server_close()
            sys.exit(f"이 작업 공간의 서버가 방금 먼저 떴다: {other.get('url')} (pid {other.get('pid')}) — 그 서버를 쓴다")
    url = f"http://127.0.0.1:{port}/"
    STATE.mkdir(parents=True, exist_ok=True)
    atomic_write(SERVER_INFO, dumps({"port": port, "url": url, "pid": os.getpid(), "workspace": "" if HUB else str(WORKSPACE),
                                     "mode": "hub" if HUB else "workspace",
                                     "title": "nexa-slide 시작 페이지" if HUB else CONFIG.get("title", WORKSPACE.name),
                                     "started": dt.datetime.now().isoformat(timespec="seconds")}))
    if HUB:
        why = f" — 엔진 폴더 안의 작업 공간은 열지 않는다: {REFUSED}" if REFUSED else ""
        print(f"nexa-slide: {url}  시작 페이지(작업 공간 없음{why})  (Ctrl+C 로 종료)", flush=True)
    else:
        print(f"nexa-slide: {url}  작업 공간 {WORKSPACE}  (Ctrl+C 로 종료)", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if WS_ENGINE is not None:
            try:
                WS_ENGINE.stop("server-stop")
            except Exception:  # noqa: BLE001
                pass
        if WS is not None:
            try:
                WS.stop("server-stop")  # 실행 중 턴의 프로세스 트리까지 끝낸다
            except Exception:  # noqa: BLE001
                pass
        srv.server_close()
        try:  # 내가 쓴 정보일 때만 지운다(같은 작업 공간에 다른 서버가 뒤에 떴을 수 있다)
            if json.loads(SERVER_INFO.read_text(encoding="utf-8")).get("pid") == os.getpid():
                SERVER_INFO.unlink()
        except (OSError, ValueError):
            pass


if __name__ == "__main__":
    main()
