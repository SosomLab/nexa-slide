# -*- coding: utf-8 -*-
"""보기 전용 공유 링크(허브) - 로그인 없이 토큰 URL 하나로 덱 한 개를 보기만 한다. server.py 가 쓴다(엔진 요청 #2, docs/auth.md).

    python3 studio/share.py list                # 링크 목록(상태·만든 사람·만료)
    python3 studio/share.py revoke <id>         # 회수(터미널에서 - 관리자 몫)

파일(사용자 설정 폴더) hub/share.json
  {"links": {<id>: {tokenHash, ws, wsId, deck, by, created, expires, pw: {hash, salt} | null, revoked: null | {by, t}, views, lastView}}}
  토큰 원문은 만들 때 한 번만 응답에 넣고 파일에는 sha256 만(세션과 같은 방식). 비밀번호는 auth.py 의 scrypt. 시각은 epoch 초.
  쓰기는 filelock.FileLock(hub/.studio/share.lock)으로 직렬화한다(허브 한 프로세스지만 CLI 와 겹칠 수 있다).
사용자 설정(settings.json): shareMaxDays(90) · shareCreate("any" | "admin")
"""
import datetime as dt
import hashlib
import hmac
import json
import re
import secrets
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import auth  # noqa: E402
from filelock import FileLock  # noqa: E402
from paths import user_dir  # noqa: E402

SHARE = user_dir() / "hub" / "share.json"
LOCK = user_dir() / "hub" / ".studio" / "share.lock"
DEFAULT_DAYS = 7
COOKIE = "nexa_share"
TOKEN_RX = r"[A-Za-z0-9_-]{32,64}"  # token_urlsafe(32) = 43자


def max_days() -> int:
    try:
        return max(1, int(float(auth.setting("shareMaxDays", 90))))
    except (TypeError, ValueError):
        return 90


def can_create(role) -> bool:
    """shareCreate: any(기본 - 로그인 사용자 누구나) | admin."""
    return str(auth.setting("shareCreate", "any")).lower() != "admin" or role == "admin"


def load() -> dict:
    try:
        d = json.loads(SHARE.read_text(encoding="utf-8"))
        links = d.get("links") if isinstance(d, dict) else None
        return links if isinstance(links, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(links: dict):
    auth._atomic_write(SHARE, {"links": links})


def _tok_hash(tok: str) -> str:
    return hashlib.sha256(tok.encode("utf-8")).hexdigest()


def status(rec: dict, now=None) -> str:
    """ok | revoked | expired."""
    now = time.time() if now is None else now
    if rec.get("revoked"):
        return "revoked"
    if float(rec.get("expires") or 0) <= now:
        return "expired"
    return "ok"


def create(ws, ws_id, deck, by, days=None, password=None):
    """새 링크 → (id, 토큰 원문, 기록). days 는 1~shareMaxDays(없으면 7). 비밀번호는 비우면 없음(있으면 4자 이상)."""
    try:
        days = float(DEFAULT_DAYS if days in (None, "") else days)
    except (TypeError, ValueError):
        raise ValueError("만료 일수는 숫자로")
    if not 0 < days <= max_days():
        raise ValueError(f"만료는 1~{max_days()}일(전역 설정 shareMaxDays)")
    pw = None
    if password:
        if not isinstance(password, str) or len(password) < 4 or len(password) > 200:
            raise ValueError("비밀번호는 4자 이상")
        h, s = auth.hash_password(password)
        pw = {"hash": h, "salt": s}
    tok = secrets.token_urlsafe(32)
    now = time.time()
    rec = {"tokenHash": _tok_hash(tok), "ws": str(ws), "wsId": ws_id, "deck": deck, "by": by, "created": now,
           "expires": now + days * 86400, "pw": pw, "revoked": None, "views": 0, "lastView": None}
    with FileLock(LOCK):
        links = load()
        lid = secrets.token_hex(4)
        while lid in links:
            lid = secrets.token_hex(4)
        links[lid] = rec
        _save(links)
    return lid, tok, rec


_MASK_RX = None


def mask_path(text: str) -> str:
    """로그에 쓰기 전에 `/s/<토큰>` 의 토큰 원문을 `-` 로 가린다 - 서버 로그(log_message)·접근 로그의 이른 거부(Host·hub-key 위조)처럼
    share_route 가 경로를 /s/<id> 로 바꾸기 전에 기록되는 줄용(0.22.25 #6). 링크 id(짧은 숫자)는 토큰 길이가 아니라 그대로다."""
    global _MASK_RX
    if _MASK_RX is None:
        _MASK_RX = re.compile(r"(/s/)" + TOKEN_RX + r"(?=[/?\s\"']|$)")
    return _MASK_RX.sub(r"\1-", text) if text and "/s/" in text else text


def lookup(tok):
    """토큰 원문 → (id, 기록) 또는 None. 상태(만료·회수)는 보지 않는다 - 호출한 쪽이 status() 로 가른다."""
    if not tok:
        return None
    h = _tok_hash(tok)
    for lid, rec in load().items():
        if hmac.compare_digest(str(rec.get("tokenHash", "")), h):
            return lid, rec
    return None


def get(lid):
    return load().get(str(lid or ""))


def revoke(lid, by):
    with FileLock(LOCK):
        links = load()
        rec = links.get(lid)
        if not rec:
            raise ValueError("없는 링크")
        if not rec.get("revoked"):
            rec["revoked"] = {"by": by, "t": time.time()}
            _save(links)
    return rec


def note_view(lid):
    with FileLock(LOCK):
        links = load()
        rec = links.get(lid)
        if rec:
            rec["views"] = int(rec.get("views") or 0) + 1
            rec["lastView"] = time.time()
            _save(links)


def check_password(pw, rec) -> bool:
    return bool(rec.get("pw")) and auth.check_password(pw or "", rec["pw"])


def _iso(t):
    return dt.datetime.fromtimestamp(float(t)).astimezone().isoformat(timespec="seconds") if t else None


def public(lid, rec, now=None) -> dict:
    """화면용 - 토큰 해시·비밀번호 해시는 빼고, 상태·시각(ISO)을 더한다."""
    return {"id": lid, "wsId": rec.get("wsId"), "ws": rec.get("ws"), "deck": rec.get("deck"), "by": rec.get("by"),
            "created": _iso(rec.get("created")), "expires": _iso(rec.get("expires")), "hasPassword": bool(rec.get("pw")),
            "revoked": bool(rec.get("revoked")), "revokedBy": (rec.get("revoked") or {}).get("by"),
            "views": int(rec.get("views") or 0), "lastView": _iso(rec.get("lastView")), "status": status(rec, now)}


def list_links(user=None, role=None, ws_id=None, deck=None):
    """목록 - 관리자는 전부, 그 밖은 자기가 만든 것만. ws_id·deck 으로 좁힐 수 있다. 최근 것부터."""
    now = time.time()
    out = []
    for lid, rec in load().items():
        if role != "admin" and rec.get("by") != user:
            continue
        if ws_id and rec.get("wsId") != ws_id:
            continue
        if deck and rec.get("deck") != deck:
            continue
        out.append(public(lid, rec, now))
    out.sort(key=lambda x: x["created"] or "", reverse=True)
    return out


# ---------- 비밀번호 쿠키(무상태 - 허브 공유 비밀로 서명, 재시작해도 유효) ----------
def _sign(lid, exp, rec) -> str:
    msg = f"{lid}.{exp}.{(rec.get('pw') or {}).get('hash', '')}"
    return hmac.new(auth.hub_key().encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()[:40]


def cookie_value(lid, rec) -> tuple:
    """(쿠키 값, Max-Age) - 링크 만료와 세션 7일 중 짧은 쪽."""
    exp = int(min(float(rec.get("expires") or 0), time.time() + auth.session_ttl()))
    return f"{lid}.{exp}.{_sign(lid, exp, rec)}", max(1, exp - int(time.time()))


def cookie_ok(value, lid, rec) -> bool:
    try:
        cid, exp, sig = str(value or "").split(".")
        exp = int(exp)
    except ValueError:
        return False
    return cid == lid and exp > time.time() and hmac.compare_digest(sig, _sign(lid, exp, rec))


# ---------- 명령줄 ----------
def main(argv):
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    if not argv or argv[0] not in ("list", "revoke"):
        sys.exit(__doc__)
    if argv[0] == "list":
        rows = list_links(role="admin")
        if not rows:
            print(f"공유 링크 없음 ({SHARE})")
        for r in rows:
            print(f"{r['id']}  {r['status']:7s} {r['deck']:12s} {r['wsId'] or '':30s} {r['by'] or '':12s} 만료 {r['expires']}  조회 {r['views']}{'  🔒' if r['hasPassword'] else ''}")
        return
    if len(argv) < 2:
        sys.exit("링크 id 를 준다")
    try:
        revoke(argv[1], "cli")
    except ValueError as e:
        sys.exit(str(e))
    print(f"{argv[1]} 회수")


if __name__ == "__main__":
    main(sys.argv[1:])
