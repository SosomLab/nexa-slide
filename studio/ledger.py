# -*- coding: utf-8 -*-
"""변경 원장 - 덱 파일에 일어난 모든 쓰기를 덱당 추가 전용 JSONL 로 남긴다.

    decks/.history/<덱>/changes.jsonl     한 줄 = 한 변경(스키마 v1). 최근 keep 줄(기본 1,000, nexa-slide.json "ledger": {"keep"})
    out/.studio/ledger-<덱>.lock           교차 프로세스 잠금(서버 · build_deck.py · save_deck.py). 원장 파일 자체는 잠그지 않는다

줄 하나
    {"v": 1, "seq": 412, "ts": "2026-10-14T09:12:33.481+09:00", "deck": "ch03", "kind": "change",
     "origin": "editor|claude|build|external", "confidence": "exact|inferred|unknown",
     "action": "save|restore|build|detect|startup",
     "actor": {"label": "", "tab": null, "request": null, "note": null}, "evidence": {...} (inferred 일 때만),
     "before": {"ver", "size", "hash", "backup"}, "after": {"ver", "size", "hash"},
     "summary": {"수정": 1, "추가": 0, "삭제": 0, "이동": 0}, "fields": [덱 수준 키], "items": [deckdiff.diff_deck 결과]}

쓰기 순서는 언제나 "백업 → 덱 교체 → 원장 추가". 덱과 백업이 1차 진실이고 원장은 그 색인이라 fsync 는 하지 않는다(압축 때만).
읽기는 찢어진 마지막 줄(전원 장애 등)을 무시한다. seq 는 압축해도 다시 매기지 않는다.
"""
import datetime as dt
import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CONFIG, DECKS, STATE  # noqa: E402
import deckdiff  # noqa: E402

V = 1
ORIGINS = ("editor", "claude", "build", "external")
LEDGER_CFG = {"keep": 1000, "groupGap": 60, "recordTouch": False, **(CONFIG.get("ledger") or {})}
KEEP = max(50, int(LEDGER_CFG.get("keep", 1000)))
GROUP_GAP = min(600, max(15, int(LEDGER_CFG.get("groupGap", 60))))
COMPACT_SLACK = 100  # keep + 100 을 넘을 때만 압축(매 저장마다 다시 쓰지 않게)
LOCK_TIMEOUT = 5.0


def path(deck):
    return DECKS / ".history" / deck / "changes.jsonl"


def lock_path(deck):
    return STATE / f"ledger-{deck}.lock"


def now_ts():
    return dt.datetime.now().astimezone().isoformat(timespec="milliseconds")


def sha256(data: bytes):
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sig(p: Path):
    """파일 서명 (mtime_ns, size) - 둘 중 하나라도 바뀌면 해시를 다시 잰다."""
    try:
        st = p.stat()
        return (st.st_mtime_ns, st.st_size)
    except FileNotFoundError:
        return None


def meta(p: Path, data=None):
    """{ver, size, hash} - ver 는 server.ver() 와 같은 str(mtime_ns)."""
    try:
        st = p.stat()
    except FileNotFoundError:
        return {"ver": "0", "size": 0, "hash": None}
    if data is None:
        data = p.read_bytes()
    return {"ver": str(st.st_mtime_ns), "size": st.st_size, "hash": sha256(data)}


# ---------- 원자적 쓰기(server.py 에서 옮김 - build_deck · save_deck 도 쓴다) ----------
def atomic_write(path_: Path, text: str):
    path_.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path_.name + ".", suffix=".tmp", dir=str(path_.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        _replace(tmp, path_)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def _replace(tmp, dst, tries=5):
    """os.replace - Windows 에서 다른 프로세스(백신·인덱서·뷰어)가 잠깐 잡고 있으면 50→800ms 백오프로 다시 시도."""
    for k in range(tries):
        try:
            os.replace(tmp, dst)
            return
        except PermissionError:
            time.sleep(0.05 * (2 ** k))
    os.replace(tmp, dst)


# ---------- 교차 프로세스 잠금 ----------
class Lock:
    """별도 잠금 파일에 msvcrt.locking / fcntl.flock 비차단 시도 + 자체 타임아웃. OS 가 프로세스 종료 때 풀어 준다."""

    def __init__(self, deck, timeout=LOCK_TIMEOUT):
        self.p, self.timeout, self.fd = lock_path(deck), timeout, None

    def __enter__(self):
        self.p.parent.mkdir(parents=True, exist_ok=True)
        self.fd = os.open(str(self.p), os.O_RDWR | os.O_CREAT, 0o644)
        end = time.monotonic() + self.timeout
        while True:
            try:
                if os.name == "nt":
                    import msvcrt
                    os.lseek(self.fd, 0, 0)
                    msvcrt.locking(self.fd, msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except OSError:
                if time.monotonic() > end:
                    os.close(self.fd)
                    self.fd = None
                    raise TimeoutError(f"원장 잠금을 {self.timeout}초 안에 얻지 못했다: {self.p}")
                time.sleep(0.05)

    def __exit__(self, *a):
        if self.fd is None:
            return
        try:
            if os.name == "nt":
                import msvcrt
                os.lseek(self.fd, 0, 0)
                msvcrt.locking(self.fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.fd, fcntl.LOCK_UN)
        finally:
            os.close(self.fd)
            self.fd = None


# ---------- 읽기 ----------
def _parse(data: bytes):
    """줄마다 json. 마지막 조각이 비어 있지 않은데 파싱되지 않으면 찢어진 줄로 버린다. 중간 줄 오류는 건너뛴다."""
    out = []
    parts = data.split(b"\n")
    for k, raw in enumerate(parts):
        if not raw.strip():
            continue
        try:
            e = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            if k == len(parts) - 1:
                break  # 찢어진 마지막 줄
            continue
        if isinstance(e, dict) and "seq" in e:
            out.append(e)
    return out


_cache = {}


def read(deck):
    """원장 전체(오래된 것부터). 파일 (mtime_ns, size) 로 파싱 결과를 캐시한다(2초 폴링·recent·group 이 반복 읽기 때문)."""
    p = path(deck)
    s = sig(p)
    if s is None:
        _cache.pop(deck, None)
        return []
    c = _cache.get(deck)
    if c and c[0] == s:
        return c[1]
    entries = _parse(p.read_bytes())
    _cache[deck] = (s, entries)
    return entries


def last_write(deck):
    """파일을 쓴 마지막 줄(종류 무관 - change · quiet · touch). 지금 파일이 원장의 끝과 같은지 볼 때."""
    for e in reversed(read(deck)):
        if (e.get("after") or {}).get("hash"):
            return e
    return None


def tail(deck, n=5):
    return read(deck)[-n:]


def last_change(deck):
    for e in reversed(read(deck)):
        if e.get("kind", "change") == "change":
            return e
    return None


def _last_seq_raw(p: Path):
    """잠금 안에서 파일 꼬리(64KB)만 읽어 마지막 유효 seq 를 찾는다."""
    try:
        size = p.stat().st_size
    except FileNotFoundError:
        return 0, True
    with open(p, "rb") as f:
        f.seek(max(0, size - 65536))
        data = f.read()
    ends_nl = size == 0 or data.endswith(b"\n")
    seq = 0
    for e in _parse(data if size <= 65536 else data.split(b"\n", 1)[-1]):
        seq = max(seq, int(e.get("seq", 0)))
    if size > 65536 and seq == 0:  # 꼬리에 유효 줄이 없으면(거대 줄) 전체를 읽는다
        for e in _parse(p.read_bytes()):
            seq = max(seq, int(e.get("seq", 0)))
    return seq, ends_nl


# ---------- 쓰기 ----------
def append(deck, entry: dict):
    """한 줄 추가. seq 를 매기고 돌려준다. keep + 100 을 넘으면 최근 keep 줄만 남기고 압축한다."""
    p = path(deck)
    p.parent.mkdir(parents=True, exist_ok=True)
    with Lock(deck):
        seq, ends_nl = _last_seq_raw(p)
        rest = {k: v for k, v in entry.items() if k not in ("v", "seq", "deck", "ts")}
        entry = {"v": V, "seq": seq + 1, "ts": entry.get("ts") or now_ts(), "deck": deck, **rest}
        line = json.dumps(entry, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
        fd = os.open(str(p), os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_BINARY", 0))
        try:
            if not ends_nl:
                os.write(fd, b"\n")  # 찢어진 조각을 격리
            view = memoryview(line)
            while view:
                n = os.write(fd, view)
                view = view[n:]
        finally:
            os.close(fd)
        try:
            _compact_locked(p)
        except OSError as e:  # 압축 실패는 저장 실패로 번지지 않게 - 다음 append 에서 다시 시도
            sys.stderr.write(f"ledger: 압축 실패 {p}: {e}\n")
    _cache.pop(deck, None)
    return entry["seq"]


def _compact_locked(p: Path):
    data = p.read_bytes()
    n = data.count(b"\n")
    if n <= KEEP + COMPACT_SLACK:
        return
    entries = _parse(data)
    keep = entries[-KEEP:]
    tmp = p.with_name(p.name + ".tmp")
    with open(tmp, "wb") as f:
        for e in keep:
            e["v"] = V
            f.write(json.dumps(e, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n")
        f.flush()
        os.fsync(f.fileno())
    _replace(str(tmp), str(p))


def record(deck, old_obj, before, new_obj, after, origin, confidence, action, actor=None, evidence=None, ts=None, replay=None):
    """변경 한 건을 비교해 원장에 적는다. 내용이 같으면(해시 동일, 또는 항목·덱 수준 변경 없음) 적지 않고 None.
    replay = 원장 재생(verify)이 다시 적용할 것 - {"ops": [...]} (작업 저장, REPLAY_MAX 이하일 때만) · {"struct": [...]} (시트 행·열 작업, 기록용)."""
    assert origin in ORIGINS, origin
    if before.get("hash") and before.get("hash") == after.get("hash"):
        if not LEDGER_CFG.get("recordTouch"):
            return None
        kind, items, fields = "touch", [], []
    else:
        items = deckdiff.diff_deck(old_obj or {"slides": []}, new_obj or {"slides": []}) if old_obj is not None else None
        fields = deckdiff.deck_fields(old_obj or {}, new_obj or {}) if old_obj is not None else []
        # 항목으로 잡히는 것이 없어도(공백·키 순서·저장 시각만 다름) 파일 해시가 바뀌었으면 줄은 남긴다 - 안 그러면 원장의 사슬(앞 줄 결과 = 다음 줄 시작)이 끊긴다.
        # kind "quiet" 는 변경 탭·last_change 에 나오지 않고 원장 재생(verify)만 본다
        kind = "quiet" if items is not None and not items and not fields and before.get("hash") else "change"
    entry = {"ts": ts, "kind": kind, "origin": origin, "confidence": confidence, "action": action,
             "actor": {"label": "", "tab": None, "request": None, "note": None, **(actor or {})},
             "before": before, "after": after,
             "summary": deckdiff.summary(items or []), "fields": fields, "items": items}
    if evidence:
        entry["evidence"] = evidence
    if replay:
        entry["replay"] = replay
    return append(deck, entry)


# ---------- 원장 재생(동시 편집 3-5) - python studio/ledger.py verify <덱> (작업 공간에서는 nexa.py ledger verify <덱>) ----------
REPLAY_MAX = 8192  # 작업 저장의 작업 목록을 원장에 그대로 남기는 상한(JSON 바이트) - 넘으면 재생은 건너뛰고 사슬·백업 검사만


def replay_ops(ops):
    """작업 목록 → 원장에 남길 replay(너무 크면 None)."""
    try:
        size = len(json.dumps(ops, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    except (TypeError, ValueError):
        return None
    return {"ops": ops} if size <= REPLAY_MAX else None


def _same_doc(a, b):
    """저장 시각(updated)만 빼고 같은 문서인가 - 서버가 저장할 때마다 새로 찍는다."""
    strip = lambda d: {k: v for k, v in d.items() if k != "updated"} if isinstance(d, dict) else d  # noqa: E731
    return strip(a) == strip(b)


def verify(deck):
    """원장을 처음부터 따라가며 파일·백업과 맞는지 본다. 결과 dict - ok 가 False 면 problems 에 어긋난 곳.
      사슬   줄 k 의 before.hash == 줄 k-1 의 after.hash (사이에 원장에 없는 쓰기가 없었다)
      백업   before.backup 파일이 남아 있으면 그 해시 == before.hash (지워진 백업은 건너뜀으로 센다)
      재생   작업 저장(replay.ops)은 백업 문서에 작업을 다시 얹어 그 저장의 결과 문서(다음 줄의 백업, 마지막 줄이면 지금 파일)와 같은지
      끝     마지막 줄의 after.hash == 지금 파일의 해시
    통째·병합 저장은 보낸 문서가 원장에 없어 재생하지 못한다 - 사슬·백업으로만 확인한다."""
    import deckops
    entries = [e for e in read(deck) if (e.get("after") or {}).get("hash")]  # change · quiet · touch - 파일을 쓴 줄 전부
    hdir = path(deck).parent
    res = {"deck": deck, "entries": len(entries), "chain": {"ok": 0, "broken": 0}, "backup": {"ok": 0, "bad": 0, "missing": 0},
           "replay": {"ok": 0, "bad": 0, "skipped": 0}, "end": None, "problems": []}
    bad = lambda seq, what: res["problems"].append({"seq": seq, "what": what})  # noqa: E731

    def backup_bytes(e):
        name = (e.get("before") or {}).get("backup")
        f = hdir / name if name else None
        return f.read_bytes() if f and f.is_file() else None

    def load(data):
        try:
            return json.loads(data.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None

    p = DECKS / f"{deck}.json"
    cur = p.read_bytes() if p.is_file() else None
    by_ver = {}  # after.ver → 그 저장의 결과 문서 바이트(다음 줄의 백업 또는 지금 파일) - 오래된 판 위 작업의 기준본 찾기
    after_bytes = []
    for k, e in enumerate(entries):
        nxt = entries[k + 1] if k + 1 < len(entries) else None
        data = backup_bytes(nxt) if nxt else cur
        want = (e.get("after") or {}).get("hash")
        if data is not None and want and sha256(data) != want:
            data = None  # 그 사이 원장에 없는 쓰기가 있었다 - 사슬 검사가 따로 알린다
        after_bytes.append(data)
        if data is not None:
            by_ver[str((e.get("after") or {}).get("ver"))] = data
    for k, e in enumerate(entries):
        seq, before, after = e.get("seq"), e.get("before") or {}, e.get("after") or {}
        if k:
            prev = (entries[k - 1].get("after") or {}).get("hash")
            if before.get("hash") and prev:
                if before["hash"] == prev:
                    res["chain"]["ok"] += 1
                else:
                    res["chain"]["broken"] += 1
                    bad(seq, "사슬 끊김 - 앞 줄의 결과와 이 줄의 시작이 다르다(원장에 없는 쓰기)")
        bdata = backup_bytes(e)
        if before.get("backup"):
            if bdata is None:
                res["backup"]["missing"] += 1
            elif before.get("hash") and sha256(bdata) != before["hash"]:
                res["backup"]["bad"] += 1
                bad(seq, f"백업 {before['backup']} 의 해시가 원장과 다르다")
            else:
                res["backup"]["ok"] += 1
        ops = (e.get("replay") or {}).get("ops")
        if ops is None:
            continue
        src, dst = load(bdata) if bdata is not None else None, load(after_bytes[k]) if after_bytes[k] is not None else None
        if src is None or dst is None:
            res["replay"]["skipped"] += 1
            continue
        base = str(((e.get("evidence") or {}).get("ops") or {}).get("base") or "")
        bdoc = load(by_ver[base]) if base and base != str(before.get("ver")) and base in by_ver else None
        out, _, _ = deckops.apply(src, ops, base=bdoc)
        if _same_doc(out, dst):
            res["replay"]["ok"] += 1
        elif base and base != str(before.get("ver")) and bdoc is None:
            res["replay"]["skipped"] += 1  # 오래된 판 위의 작업인데 그 판의 문서가 남아 있지 않다(지운 것 되살리기를 재현할 수 없음)
        else:
            res["replay"]["bad"] += 1
            bad(seq, "작업 재생 결과가 저장된 문서와 다르다")
    if entries and cur is not None:
        res["end"] = sha256(cur) == (entries[-1].get("after") or {}).get("hash")
        if not res["end"]:
            bad(entries[-1].get("seq"), "지금 파일이 원장의 마지막 결과와 다르다(원장에 없는 쓰기)")
    res["ok"] = not res["problems"]
    return res


def _main(argv):
    import argparse
    ap = argparse.ArgumentParser(prog="ledger", description="변경 원장 도구")
    sp = ap.add_subparsers(dest="cmd", required=True)
    v = sp.add_parser("verify", help="원장을 처음부터 따라가며 백업·파일과 맞는지, 작업 저장을 다시 적용해 같은지 본다")
    v.add_argument("deck")
    v.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    r = verify(a.deck)
    if a.json:
        print(json.dumps(r, ensure_ascii=False))
    else:
        c, b, rp = r["chain"], r["backup"], r["replay"]
        print(f"원장 {r['deck']}: 변경 {r['entries']}줄")
        print(f"  사슬   확인 {c['ok']} · 끊김 {c['broken']}")
        print(f"  백업   확인 {b['ok']} · 다름 {b['bad']} · 없음(지워짐) {b['missing']}")
        print(f"  재생   같음 {rp['ok']} · 다름 {rp['bad']} · 건너뜀 {rp['skipped']}")
        print(f"  끝     {'지금 파일과 같음' if r['end'] else '확인할 것 없음' if r['end'] is None else '지금 파일과 다름'}")
        for pr in r["problems"][:20]:
            print(f"  FAIL seq {pr['seq']}: {pr['what']}")
        print("전부 통과" if r["ok"] else f"실패 {len(r['problems'])}")
    return 0 if r["ok"] else 1


# ---------- 표시용 가공 ----------
def _ts(e):
    try:
        return dt.datetime.fromisoformat(e["ts"]).timestamp()
    except (KeyError, ValueError, TypeError):
        return 0.0


BOUNDARY_ACTIONS = ("build", "restore", "detect", "startup")


def group(entries, gap=GROUP_GAP):
    """세션 윈도 묶음 - 같은 origin·tab 이고 간격 ≤ gap 이며 경계 사건(build·restore·detect·startup, 요청 전환)이 아니면 같은 묶음.
    묶음 items 는 줄별 items 의 id 단위 합집합(근사 - approx)."""
    groups = []
    prev = None
    for e in entries:
        a = e.get("actor") or {}
        same = (prev is not None and e.get("origin") == prev["origin"] and a.get("tab") == prev["tab"]
                and a.get("request") == prev["request"] and e.get("action") not in BOUNDARY_ACTIONS
                and prev["action"] not in BOUNDARY_ACTIONS and 0 <= _ts(e) - prev["last_ts"] <= gap)
        if not same:
            g = {"seq": e["seq"], "last": e["seq"], "ts": e.get("ts"), "ts_end": e.get("ts"), "origin": e.get("origin"),
                 "confidence": e.get("confidence"), "action": e.get("action"), "actor": a, "evidence": e.get("evidence"),
                 "count": 0, "items": [], "fields": [], "approx": False, "backup": (e.get("before") or {}).get("backup"), "_idx": {}}
            groups.append(g)
            prev = {"origin": e.get("origin"), "tab": a.get("tab"), "request": a.get("request"), "action": e.get("action"), "last_ts": _ts(e)}
        else:
            g = groups[-1]
            g["approx"] = True
            prev["last_ts"] = _ts(e)
            prev["action"] = e.get("action")
        g["count"] += 1
        g["last"] = e["seq"]
        g["ts_end"] = e.get("ts")
        if e.get("confidence") == "inferred":
            g["confidence"] = "inferred"
        for f in e.get("fields") or []:
            if f not in g["fields"]:
                g["fields"].append(f)
        mg = (e.get("evidence") or {}).get("merge") if isinstance(e.get("evidence"), dict) else None
        if mg is not None:  # 병합 저장(동시 편집 1단계) - 묶음 안 병합 저장 수와 같은 곳 충돌(진 값)을 모은다(변경 탭 표시)
            m = g.setdefault("merge", {"saves": 0, "conflicts": []})
            m["saves"] += 1
            m["conflicts"] += (mg.get("conflicts") or [])[:max(0, 50 - len(m["conflicts"]))]
        for it in e.get("items") or []:
            _merge_item(g, it)
    for g in groups:
        g.pop("_idx", None)
        for it in g["items"]:
            it.pop("_els", None)
        g["summary"] = deckdiff.summary(g["items"])
    return groups


def _merge_item(g, it):
    k = it["sid"]
    cur = g["_idx"].get(k)
    if cur is None:
        cur = {**it, "els": [], "extra": list(it.get("extra") or []), "_els": {}}
        g["_idx"][k] = cur
        g["items"].append(cur)
    else:
        if it["kind"] == "삭제":
            cur["kind"], cur["gone"] = "삭제", True
        elif cur["kind"] == "추가":
            pass  # 추가 뒤 수정은 여전히 추가
        elif it["kind"] == "수정" or cur["kind"] == "이동":
            cur["kind"] = "수정" if (it["kind"] == "수정" or cur["kind"] == "수정") else cur["kind"]
        cur["idx"], cur["title"] = it["idx"], it["title"]
        if it.get("moved"):
            cur["moved"] = [cur["moved"][0] if cur.get("moved") else it["moved"][0], it["moved"][1]]
        for x in it.get("extra") or []:
            if x not in cur["extra"]:
                cur["extra"].append(x)
    for el in it.get("els") or []:
        e = cur["_els"].get(el["id"])
        if e is None:
            e = {**el, "kinds": list(el.get("kinds") or [])}
            cur["_els"][el["id"]] = e
            cur["els"].append(e)
            continue
        for kd in el.get("kinds") or []:
            if kd not in e["kinds"]:
                e["kinds"].append(kd)
        if el.get("after") or el.get("gone"):
            e["after"] = el.get("after", "")
        # 사라짐은 마지막 상태를 따른다 - 추가 → 삭제 → 다시 추가(복제 후 지웠다 다시 복제 등)면 지금은 있는 요소다
        if el.get("gone"):
            e["gone"] = True
        else:
            e.pop("gone", None)
            if "삭제" in e["kinds"]:
                e["kinds"].remove("삭제")


def recent(entries, deck_obj=None):
    """슬라이드별 가장 최근에 그 장을 건드린 줄 하나씩 - 최근 것부터. idx 는 지금 덱 순서로 다시 센다."""
    d = deck_obj or {}
    pos = {s.get("id"): i for i, s in enumerate((d.get("sheets") if d.get("kind") == "sheet" else d.get("slides")) or []) if isinstance(s, dict)}
    seen, out = set(), []
    for e in reversed(entries):
        for it in e.get("items") or []:
            sid = it["sid"]
            if sid in seen:
                continue
            seen.add(sid)
            kinds = []
            for el in it.get("els") or []:
                for kd in el.get("kinds") or []:
                    if kd not in kinds:
                        kinds.append(kd)
            out.append({"sid": sid, "title": it.get("title"), "idx": pos.get(sid, it.get("idx")), "exists": sid in pos,
                        "kind": it["kind"], "kinds": kinds, "extra": it.get("extra") or [], "seq": e["seq"], "ts": e.get("ts"),
                        "origin": e.get("origin"), "confidence": e.get("confidence"), "actor": e.get("actor") or {}})
    return out


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
