# -*- coding: utf-8 -*-
"""허브 인증 · 계정 · 세션 · 접근 로그 (표준 라이브러리만). server.py 가 쓴다.

    python3 studio/auth.py list                                  # 사용자 목록
    python3 studio/auth.py reset-password <id> [<새 비밀번호>]    # 로컬에서만 - 원격에서 초기화할 길은 없다(비밀번호를 안 주면 프롬프트)
    python3 studio/auth.py add <id> [<비밀번호>] [--admin]
    python3 studio/auth.py delete <id>
    python3 studio/auth.py role <id> admin|user

원칙
- 허브(5599)는 로컬이어도 모든 요청에 로그인이 필요하다(cloudflared 같은 터널이 127.0.0.1 로 들어오므로 주소로 안팎을 가를 수 없다).
  nexa.py 로 개별로 띄운 작업 공간 서버는 인증이 없다 - 그 포트를 직접 밖에 노출하는 것은 서비스 범위가 아니다.
- 최초 설정(/setup)으로 만든 사용자가 관리자다. 역할(admin·user)은 관리자만 바꿀 수 있다.
- 계정은 엔진·작업 공간 밖, 사용자 설정 폴더에 둔다. 관리자를 잃었으면 users.json 을 지우면 최초 설정으로 돌아간다.

파일(사용자 설정 폴더 = paths.user_dir())
  users.json            {"users": {id: {hash, salt, role, created, mustChange}}}  - scrypt(n=2^14, r=8, p=1) + 16바이트 salt
  hub/sessions.json     {토큰 해시: {user, created, last, ua}}  - 쿠키에는 토큰 원문, 파일에는 sha256 만
  hub/.studio/hub-key   허브 ↔ 작업 공간 서버 공유 비밀(X-Nexa-Hub-Key) - 허브가 중계할 때 붙이고, 작업 공간 서버는 이것이 맞을 때만 X-Nexa-User 를 믿는다
  hub/logs/access-YYYY-MM-DD.log   접근 로그(JSON Lines) - 자정에 새 파일, accessLogDays(기본 30) 지난 파일은 지운다
사용자 설정(settings.json): sessionDays(7) · publicHosts([]) · accessLogDays(30) · accessLogStatic(false)
"""
import datetime as dt
import hashlib
import hmac
import json
import os
import re
import secrets
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import load_settings, user_dir  # noqa: E402

USERS = user_dir() / "users.json"
SESSIONS = user_dir() / "hub" / "sessions.json"
HUB_KEY = user_dir() / "hub" / ".studio" / "hub-key"
LOGS = user_dir() / "hub" / "logs"
COOKIE = "nexa_sid"
ID_RX = re.compile(r"^[A-Za-z0-9_.@-]{2,40}$")
MIN_PW = 8
MAX_FAIL, LOCK_SEC = 5, 15 * 60  # 로그인 실패 5회 → 15분 잠금(사용자 id 와 클라이언트 주소 각각)
_LOCK = threading.Lock()


def setting(name, default):
    v = load_settings().get(name, default)
    return default if v is None else v


def _atomic_write(p: Path, data: dict):
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=p.name + ".", suffix=".tmp", dir=str(p.parent))
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def _read(p: Path, default):
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else default
    except (OSError, ValueError):
        return default


# ---------- 비밀번호 ----------
def hash_password(pw: str, salt: bytes = None):
    salt = salt or secrets.token_bytes(16)
    h = hashlib.scrypt(pw.encode("utf-8"), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)
    return h.hex(), salt.hex()


def check_password(pw: str, rec: dict) -> bool:
    try:
        h, _ = hash_password(pw, bytes.fromhex(rec["salt"]))
        return hmac.compare_digest(h, rec["hash"])
    except (KeyError, ValueError, TypeError):
        return False


def valid_id(uid) -> bool:
    return bool(uid) and bool(ID_RX.match(str(uid)))


def valid_password(pw) -> str:
    """문제가 있으면 안내 문장, 괜찮으면 빈 문자열."""
    if not isinstance(pw, str) or len(pw) < MIN_PW:
        return f"비밀번호는 {MIN_PW}자 이상"
    if len(pw) > 200:
        return "비밀번호가 너무 길다"
    return ""


# ---------- 사용자 ----------
def load_users() -> dict:
    return _read(USERS, {}).get("users", {}) or {}


def save_users(users: dict):
    _atomic_write(USERS, {"users": users})


def has_users() -> bool:
    return bool(load_users())


def user_rec(uid):
    return load_users().get(str(uid or ""))


def public(uid, rec):
    return {"id": uid, "role": rec.get("role", "user"), "created": rec.get("created", ""), "mustChange": bool(rec.get("mustChange"))}


def add_user(uid, pw, role="user", must_change=False):
    if not valid_id(uid):
        raise ValueError("아이디는 영문·숫자·_ . @ - 로 2~40자")
    bad = valid_password(pw)
    if bad:
        raise ValueError(bad)
    if role not in ("admin", "user"):
        raise ValueError("역할은 admin 또는 user")
    with _LOCK:
        users = load_users()
        if uid in users:
            raise ValueError("이미 있는 아이디")
        h, s = hash_password(pw)
        users[uid] = {"hash": h, "salt": s, "role": role, "created": dt.datetime.now().isoformat(timespec="seconds"), "mustChange": must_change}
        save_users(users)
    return public(uid, users[uid])


def set_password(uid, pw, must_change=False):
    bad = valid_password(pw)
    if bad:
        raise ValueError(bad)
    with _LOCK:
        users = load_users()
        if uid not in users:
            raise ValueError("없는 아이디")
        h, s = hash_password(pw)
        users[uid].update({"hash": h, "salt": s, "mustChange": must_change})
        save_users(users)
    drop_user_sessions(uid)  # 다른 기기의 기존 로그인은 끊는다


def delete_user(uid):
    with _LOCK:
        users = load_users()
        if uid not in users:
            raise ValueError("없는 아이디")
        if users[uid].get("role") == "admin" and sum(1 for r in users.values() if r.get("role") == "admin") <= 1:
            raise ValueError("마지막 관리자는 지울 수 없다")
        del users[uid]
        save_users(users)
    drop_user_sessions(uid)


def set_role(uid, role):
    if role not in ("admin", "user"):
        raise ValueError("역할은 admin 또는 user")
    with _LOCK:
        users = load_users()
        if uid not in users:
            raise ValueError("없는 아이디")
        if role == "user" and users[uid].get("role") == "admin" and sum(1 for r in users.values() if r.get("role") == "admin") <= 1:
            raise ValueError("마지막 관리자의 역할은 내릴 수 없다")
        users[uid]["role"] = role
        save_users(users)


# ---------- 로그인 잠금 ----------
_FAILS = {}  # key → [횟수, 마지막 실패 시각]


def locked_for(key) -> int:
    """잠겨 있으면 남은 초, 아니면 0."""
    f = _FAILS.get(key)
    if not f or f[0] < MAX_FAIL:
        return 0
    left = int(f[1] + LOCK_SEC - time.time())
    if left <= 0:
        _FAILS.pop(key, None)
        return 0
    return left


def note_failure(*keys):
    for k in keys:
        f = _FAILS.setdefault(k, [0, 0])
        f[0] += 1
        f[1] = time.time()


def clear_failures(*keys):
    for k in keys:
        _FAILS.pop(k, None)


# ---------- 세션 ----------
_SESS = None  # 토큰 해시 → {user, created, last, ua}
_SESS_MTIME = None


def _mtime():
    try:
        return SESSIONS.stat().st_mtime_ns
    except OSError:
        return None


def _sessions():
    """파일이 밖에서 바뀌었으면(auth.py reset-password 같은 다른 프로세스가 세션을 끊음) 다시 읽는다."""
    global _SESS, _SESS_MTIME
    m = _mtime()
    if _SESS is None or m != _SESS_MTIME:
        _SESS, _SESS_MTIME = _read(SESSIONS, {}), m
    return _SESS


def _save_sessions():
    global _SESS_MTIME
    _atomic_write(SESSIONS, _sessions())
    _SESS_MTIME = _mtime()


def _tok_hash(tok: str) -> str:
    return hashlib.sha256(tok.encode("utf-8")).hexdigest()


def session_ttl() -> int:
    return int(float(setting("sessionDays", 7)) * 86400)


def new_session(uid, ua=""):
    tok = secrets.token_urlsafe(32)
    now = time.time()
    with _LOCK:
        s = _sessions()
        s[_tok_hash(tok)] = {"user": uid, "created": now, "last": now, "ua": (ua or "")[:200]}
        _prune(s)
        _save_sessions()
    return tok


def get_session(tok):
    """살아 있는 세션이면 {user, …}, 아니면 None. 마지막 사용 시각은 5분에 한 번만 파일에 적는다."""
    if not tok:
        return None
    with _LOCK:
        s = _sessions()
        rec = s.get(_tok_hash(tok))
        if not rec:
            return None
        now = time.time()
        if now - rec.get("last", 0) > session_ttl():
            s.pop(_tok_hash(tok), None)
            _save_sessions()
            return None
        if now - rec.get("last", 0) > 300:
            rec["last"] = now
            _save_sessions()
        return dict(rec)


def drop_session(tok):
    if not tok:
        return
    with _LOCK:
        if _sessions().pop(_tok_hash(tok), None) is not None:
            _save_sessions()


def drop_user_sessions(uid):
    with _LOCK:
        s = _sessions()
        gone = [k for k, v in s.items() if v.get("user") == uid]
        for k in gone:
            del s[k]
        if gone:
            _save_sessions()


def _prune(s):
    ttl = session_ttl()
    now = time.time()
    for k in [k for k, v in s.items() if now - v.get("last", 0) > ttl]:
        del s[k]


def parse_cookies(header: str) -> dict:
    out = {}
    for part in (header or "").split(";"):
        if "=" in part:
            k, v = part.strip().split("=", 1)
            out[k] = v
    return out


def cookie_header(tok, secure, max_age=None):
    """Set-Cookie 값. tok 가 None 이면 지우는 쿠키."""
    ma = 0 if tok is None else (max_age if max_age is not None else session_ttl())
    # SameSite=Lax: 메신저·메일의 링크로 /w/… 를 열어도 로그인 상태가 이어진다(Strict 면 첫 요청에 쿠키가 안 붙어 로그인 화면으로 간다).
    # 다른 사이트에서 보낸 상태 변경(POST·PUT)은 Lax 가 쿠키를 붙이지 않고, 붙여도 서버의 Origin 검사가 막는다.
    v = f"{COOKIE}={tok or ''}; Path=/; HttpOnly; SameSite=Lax; Max-Age={ma}"
    return v + ("; Secure" if secure else "")


# ---------- 허브 ↔ 작업 공간 서버 공유 비밀 ----------
_KEY = None


def hub_key() -> str:
    """없으면 만든다(허브·작업 공간 서버 어느 쪽이 먼저 떠도 같은 파일을 본다)."""
    global _KEY
    if _KEY:
        return _KEY
    try:
        k = HUB_KEY.read_text(encoding="utf-8").strip()
    except OSError:
        k = ""
    if len(k) < 32:
        k = secrets.token_hex(32)
        HUB_KEY.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(HUB_KEY), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(k)
    _KEY = k
    return k


def key_ok(v) -> bool:
    return bool(v) and hmac.compare_digest(str(v), hub_key())


# ---------- 접근 로그 ----------
_PRUNED = None


class _log_lock:
    """프로세스 사이 잠금(hub/logs/access.lock) - Windows msvcrt.locking, 그 밖 fcntl.flock. 최대 약 3초 기다리고 못 얻으면 그냥 쓴다(로그보다 서비스)."""

    def __enter__(self):
        self.fd = None
        try:
            self.fd = os.open(str(LOGS / "access.lock"), os.O_WRONLY | os.O_CREAT, 0o644)
            if os.name == "nt":
                import msvcrt
                for _ in range(30):
                    try:
                        msvcrt.locking(self.fd, msvcrt.LK_NBLCK, 1)
                        return self
                    except OSError:
                        time.sleep(0.1)
            else:
                import fcntl
                fcntl.flock(self.fd, fcntl.LOCK_EX)
        except OSError:
            pass
        return self

    def __exit__(self, *a):
        if self.fd is None:
            return
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.fd, fcntl.LOCK_UN)
        except OSError:
            pass
        os.close(self.fd)


def log_access(rec: dict):
    """한 줄 JSON 을 오늘 파일에 붙인다(열고-쓰고-닫기: 허브·작업 공간 서버 여러 프로세스가 같은 파일에 쓴다). 하루 한 번 오래된 파일을 지운다."""
    global _PRUNED
    try:
        LOGS.mkdir(parents=True, exist_ok=True)
        day = dt.date.today()
        line = (json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        with _log_lock():  # 허브·작업 공간 서버 여러 프로세스가 같은 파일에 덧붙인다 - Windows 는 O_APPEND 만으로는 줄이 유실·섞여 잠금 파일로 직렬화
            fd = os.open(str(LOGS / f"access-{day.isoformat()}.log"), os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_BINARY", 0), 0o644)
            try:
                os.write(fd, line)
            finally:
                os.close(fd)
        if _PRUNED != day:
            _PRUNED = day
            keep = int(setting("accessLogDays", 30))
            for p in LOGS.glob("access-*.log"):
                try:
                    d = dt.date.fromisoformat(p.stem[len("access-"):])
                    if (day - d).days > keep:
                        p.unlink()
                except (ValueError, OSError):
                    continue
    except OSError:
        pass  # 로그를 못 써도 서비스는 계속


# ---------- 명령줄 ----------
def _prompt_pw():
    import getpass
    a = getpass.getpass("새 비밀번호: ")
    if a != getpass.getpass("다시 입력: "):
        sys.exit("두 입력이 다르다")
    return a


def main(argv):
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    if not argv or argv[0] not in ("list", "reset-password", "add", "delete", "role"):
        sys.exit(__doc__)
    cmd, rest = argv[0], argv[1:]
    try:
        if cmd == "list":
            users = load_users()
            if not users:
                print(f"사용자 없음 - 허브에 처음 접속하면 관리자 설정 페이지가 뜬다 ({USERS})")
            for uid, r in sorted(users.items()):
                print(f"{uid:20s} {r.get('role', 'user'):6s} {r.get('created', '')}{'  (다음 로그인에 비밀번호 변경)' if r.get('mustChange') else ''}")
            return
        if cmd == "reset-password":
            uid = rest[0] if rest else sys.exit("아이디를 준다")
            if not user_rec(uid):
                sys.exit(f"없는 아이디: {uid}")
            set_password(uid, rest[1] if len(rest) > 1 else _prompt_pw(), must_change=True)
            print(f"{uid} 비밀번호를 바꿨다 - 다음 로그인에서 새 비밀번호로 바꾸게 한다. 기존 로그인은 모두 끊었다")
            return
        if cmd == "add":
            uid = rest[0] if rest else sys.exit("아이디를 준다")
            pw = next((x for x in rest[1:] if not x.startswith("--")), None) or _prompt_pw()
            r = add_user(uid, pw, "admin" if "--admin" in rest else "user")
            print(f"{uid} 추가 ({r['role']})")
            return
        if cmd == "delete":
            delete_user(rest[0] if rest else sys.exit("아이디를 준다"))
            print("지웠다")
            return
        if cmd == "role":
            if len(rest) < 2:
                sys.exit("아이디와 역할(admin|user)을 준다")
            set_role(rest[0], rest[1])
            print(f"{rest[0]} → {rest[1]}")
    except ValueError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main(sys.argv[1:])
