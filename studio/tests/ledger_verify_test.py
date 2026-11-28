# -*- coding: utf-8 -*-
"""원장 재생(동시 편집 3-5, docs/collab.md) 시험 - ledger.py verify <덱>.
    python3 studio/tests/ledger_verify_test.py
- 통째 PUT·작업 저장(오래된 판 위·지운 요소 되살리기 포함)·병합 PUT 을 섞은 원장이 사슬·백업·재생·끝 모두 통과(rc 0)
- 변조 감지: 백업 글자 · 서버 밖에서 고친 덱 파일(끝) · 원장의 replay.ops 값 → rc 1
- 백업 이름 중복: 원장 두 줄이 같은 백업 이름을 쓰면 backup.dup · rc 1(뒤 저장이 앞 백업을 덮은 흔적 - PG-118)
- 백업 일부 삭제는 없음·건너뜀으로 세고 rc 0 · 8KB 넘는 작업 저장은 replay 를 남기지 않음 · 시트 행 삽입 PUT 은 replay.struct
- nexa.py ledger verify(작업 공간 실행기) · /api/changes 에 replay 가 새지 않음"""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import testlock  # noqa: F401 - 이 PC 에서 시험은 한 번에 하나(고정 포트·임시 폴더를 같이 쓴다, testlock.py)
for _s in (sys.stdout, sys.stderr): _s.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
STUDIO = HERE.parent
WORK = Path(os.environ.get("NEXA_TEST_DIR") or Path(tempfile.gettempdir()) / "nexa-slide-tests")
USER, PROJ, PORT = WORK / "user", WORK / "projects", 5667
WS = PROJ / "ledger시험" / "slides"
ENV = {**os.environ, "NEXA_SLIDE_USER_DIR": str(USER), "NEXA_SLIDE_PROJECTS": str(PROJ), "PYTHONIOENCODING": "utf-8", "NEXA_SLIDE_WORKSPACE": str(WS)}
B = f"http://127.0.0.1:{PORT}"
FAILS = []
NOTES = []


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else extra)
    if not cond:
        FAILS.append(name)


def call(method, url, body=None):
    rq = urllib.request.Request(B + url, data=None if body is None else json.dumps(body, ensure_ascii=False).encode(), method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(rq, timeout=15) as r:
            return r.status, json.loads(r.read() or b"{}"), r.headers.get("X-Deck-Version")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}"), None


def get(i):
    st, d, v = call("GET", f"/api/deck/{i}")
    return d, v


def put(i, d, base, merge=False):
    return call("PUT", f"/api/deck/{i}?base={base}" + ("&merge=1" if merge else ""), d)


def ops(i, base, lst):
    return call("POST", f"/api/ops/{i}", {"base": base, "ops": lst})


def el(d, eid):
    return next((e for s in d["slides"] for e in s["elements"] if e["id"] == eid), None)


def verify(deck, via_nexa=False):
    cmd = ([sys.executable, str(WS / "nexa.py"), "ledger", "verify", deck, "--json"] if via_nexa
           else [sys.executable, str(STUDIO / "ledger.py"), "verify", deck, "--json"])
    r = subprocess.run(cmd, env={**ENV, "NEXA_SLIDE_HOME": str(STUDIO.parent)}, cwd=str(WS), capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        return r.returncode, json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return r.returncode, {"raw": (r.stdout + r.stderr)[-600:]}


def hist(deck):
    return WS / "decks" / ".history" / deck


def entries(deck):
    return [json.loads(l) for l in (hist(deck) / "changes.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]


def summary(r):
    return {k: r.get(k) for k in ("entries", "chain", "backup", "replay", "end")}


def txt(i, t, y):
    return {"id": i, "type": "text", "x": 60, "y": y, "w": 400, "h": 50, "text": t, "size": 20}


def seed(deck, doc):
    (WS / "decks" / f"{deck}.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")


def history_mix(deck):
    """통째 PUT 3 → 작업 저장 3(보통 · 오래된 판 위 · 지운 요소 되살리기) → 병합 PUT 1"""
    for n in range(3):
        d, v = get(deck)
        el(d, "e1")["text"] = f"통째 {n}"
        st, r, _ = put(deck, d, v)
        assert st == 200, (st, r)
    d, v = get(deck)
    st, r, _ = ops(deck, v, [{"op": "set", "slide": "s1", "el": "e2", "key": "text", "value": "작업 1"}])
    assert st == 200 and not r.get("stale"), r
    d, v_old = get(deck)  # 오래된 판 - 다른 창이 저장한 뒤 이 판 위에 작업
    d2 = json.loads(json.dumps(d)); el(d2, "e3")["text"] = "다른 창"
    assert put(deck, d2, v_old)[0] == 200
    st, r, _ = ops(deck, v_old, [{"op": "set", "slide": "s1", "el": "e1", "key": "text", "value": "작업 2(오래된 판)"}])
    assert st == 200 and r.get("stale"), r
    d, v_old = get(deck)  # 지운 요소 되살리기 - 다른 창이 e4 를 지운 뒤 옛 판 위에서 e4 를 고침
    d2 = json.loads(json.dumps(d)); d2["slides"][0]["elements"] = [e for e in d2["slides"][0]["elements"] if e["id"] != "e4"]
    assert put(deck, d2, v_old)[0] == 200
    st, r, _ = ops(deck, v_old, [{"op": "set", "slide": "s1", "el": "e4", "key": "text", "value": "되살림"}])
    assert st == 200 and r.get("stale") and r.get("applied") == 1, r
    d, v_old = get(deck)  # 병합 PUT
    d2 = json.loads(json.dumps(d)); el(d2, "e2")["fill"] = "primary"
    assert put(deck, d2, v_old)[0] == 200
    d3 = json.loads(json.dumps(d)); el(d3, "e3")["text"] = "병합"
    st, r, _ = put(deck, d3, v_old, merge=True)
    assert st == 200 and r.get("merged"), r


def main():
    if not (WS / "nexa-slide.json").is_file():
        subprocess.run([sys.executable, str(STUDIO / "init_workspace.py"), str(WS.parent), "--title", "ledger시험", "--port", str(PORT)], env=ENV, capture_output=True, text=True, encoding="utf-8")
    (WS / "decks").mkdir(parents=True, exist_ok=True)
    base_doc = lambda i: {"id": i, "title": "원장", "slides": [{"id": "s1", "elements": [txt("e1", "하나", 40), txt("e2", "둘", 120), txt("e3", "셋", 200), txt("e4", "넷", 280)]}]}  # noqa: E731
    for i in ("lv", "lvb", "lvc", "lvd", "lve", "lvq"):
        import shutil
        shutil.rmtree(hist(i), ignore_errors=True)
        seed(i, base_doc(i))
    shutil.rmtree(hist("lvs"), ignore_errors=True)
    seed("lvs", {"id": "lvs", "title": "원장 시트", "kind": "sheet", "slides": [], "sheets": [{"id": "t01", "name": "S", "cells": {"A1": 1, "A2": 2, "B2": {"f": "=A2*2"}}}]})
    srv = subprocess.Popen([sys.executable, str(STUDIO / "server.py"), "--workspace", str(WS), "--port", str(PORT)], env=ENV, cwd=str(WS), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(f"{B}/api/decks", timeout=2).read(); break
            except Exception:  # noqa: BLE001
                time.sleep(0.5)
        # a. 섞인 원장 - 통과
        history_mix("lv")
        rc, r = verify("lv")
        rp = r.get("replay") or {}
        check("a. 통째 PUT 3·작업 저장 3(오래된 판·되살리기)·병합 PUT - verify rc 0 · 사슬 끊김 0 · 백업 다름 0 · 재생 다름 0 · 끝 같음",
              rc == 0 and r.get("chain", {}).get("broken") == 0 and r.get("backup", {}).get("bad") == 0 and rp.get("bad") == 0 and r.get("end") is True, json.dumps(summary(r), ensure_ascii=False))
        check("a. 재생 같음 2 이상(작업 저장 3건 중)", rp.get("ok", 0) >= 2 and rp.get("ok", 0) + rp.get("skipped", 0) == 3, json.dumps(rp))
        es = entries("lv")
        ops_lines = [e for e in es if (e.get("replay") or {}).get("ops")]
        NOTES.append(f"a. lv 원장 {len(es)}줄 · replay.ops 줄 {len(ops_lines)} · verify {json.dumps(summary(r), ensure_ascii=False)}")
        check("a. 원장 - 작업 저장 3줄에만 replay.ops · 통째·병합 PUT 줄에는 replay 없음", len(ops_lines) == 3 and all(not e.get("replay") for e in es if not (e.get("evidence") or {}).get("ops")), json.dumps([bool(e.get("replay")) for e in es]))
        # b. 변조 감지
        history_mix("lvb")
        bk = sorted(p for p in hist("lvb").iterdir() if p.suffix == ".json")
        raw = bk[len(bk) // 2].read_text(encoding="utf-8")
        bk[len(bk) // 2].write_text(raw.replace("하나", "하냐", 1) if "하나" in raw else raw.replace("둘", "뚤", 1), encoding="utf-8")
        rc, r = verify("lvb")
        check("b. 백업 파일 글자를 바꾸면 backup bad · rc 1", rc == 1 and r.get("backup", {}).get("bad", 0) >= 1, json.dumps(summary(r), ensure_ascii=False))
        history_mix("lvc")
        f = WS / "decks" / "lvc.json"
        d = json.loads(f.read_text(encoding="utf-8")); d["title"] = "밖에서 고침"; f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        rc, r = verify("lvc")  # 서버에 요청을 보내기 전(detect 전)
        check("b. 덱 파일을 서버 밖에서 고치고 detect 전에 verify → end 다름 · rc 1", rc == 1 and r.get("end") is False, json.dumps(summary(r), ensure_ascii=False))
        history_mix("lvd")
        lp = hist("lvd") / "changes.jsonl"
        lines = lp.read_text(encoding="utf-8").splitlines()
        k = next(n for n, l in enumerate(lines) if '"replay"' in l and json.loads(l).get("replay", {}).get("ops"))
        e = json.loads(lines[k]); e["replay"]["ops"][0]["value"] = "변조된 값"; lines[k] = json.dumps(e, ensure_ascii=False)
        lp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        rc, r = verify("lvd")
        check("b. 원장의 replay.ops 값을 바꾸면 replay bad · rc 1", rc == 1 and r.get("replay", {}).get("bad", 0) >= 1, json.dumps(summary(r), ensure_ascii=False))
        # b2. 백업 이름 중복 - 원장 두 줄이 같은 before.backup 이름을 쓴다(이름이 시계 값뿐이던 때 뒤 저장이 앞 백업을 덮은 흔적 - PG-118)
        history_mix("lve")
        rc, r = verify("lve")
        check("b2. 정상 원장 - 백업 이름 중복 없음(dup 0) · rc 0", rc == 0 and not r.get("backup", {}).get("dup"), json.dumps(summary(r), ensure_ascii=False))
        lp = hist("lve") / "changes.jsonl"
        lines = lp.read_text(encoding="utf-8").splitlines()
        ks = [n for n, l in enumerate(lines) if (json.loads(l).get("before") or {}).get("backup")]
        e1, e2 = json.loads(lines[ks[0]]), json.loads(lines[ks[1]])
        e2["before"]["backup"] = e1["before"]["backup"]; lines[ks[1]] = json.dumps(e2, ensure_ascii=False)
        lp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        rc, r = verify("lve")
        want = f"백업 이름 {e1['before']['backup']} 을 줄 [{e1['seq']}, {e2['seq']}] 이 같이 쓴다"
        whats = [p.get("what", "") for p in r.get("problems") or []]
        check("b2. 두 줄이 같은 백업 이름을 쓰면 ok False · rc 1 · backup.dup 1 · problems 에 '백업 이름 … 을 줄 [a, b] 이 같이 쓴다'",
              rc == 1 and r.get("ok") is False and r.get("backup", {}).get("dup") == 1 and any(w.startswith(want) for w in whats), json.dumps({"want": want, "backup": r.get("backup"), "whats": whats[:4], "raw": r.get("raw")}, ensure_ascii=False)[:700])
        # c. 백업 일부 삭제
        bk = sorted(p for p in hist("lv").iterdir() if p.suffix == ".json")
        for p in bk[1::2]:
            p.unlink()
        rc, r = verify("lv")
        NOTES.append(f"c. 백업 {len(bk)}개 중 {len(bk[1::2])}개 지운 뒤 verify {json.dumps(summary(r), ensure_ascii=False)}")
        check("c. 백업 일부를 지우면 missing·skipped 로 세고 rc 0", rc == 0 and r.get("backup", {}).get("missing", 0) == len(bk[1::2]) and r.get("replay", {}).get("bad") == 0, json.dumps(summary(r), ensure_ascii=False))
        # d. 8KB 넘는 작업 저장 · 시트 행 삽입 PUT
        d, v = get("lvb")
        st, rr, _ = ops("lvb", v, [{"op": "set", "slide": "s1", "el": "e2", "key": "text", "value": "큰 글 " + "가" * 4000}])
        last = entries("lvb")[-1]
        check("d. 8KB 넘는 작업 저장 - 저장은 되고 원장 줄에 replay 없음(evidence.ops 는 있음)", st == 200 and not last.get("replay") and (last.get("evidence") or {}).get("ops"), json.dumps({k: last.get(k) for k in ("seq", "replay")}, ensure_ascii=False)[:300])
        d, v = get("lvs")
        sys.path.insert(0, str(STUDIO))
        import sheet_struct  # noqa: E402 - 화면처럼 칸을 옮긴 문서 + 구조 작업을 보낸다
        so = [{"op": "insertRows", "tab": "t01", "at": 1, "n": 1}]
        st, rr, _ = put("lvs", {**sheet_struct.apply(d, so), "__struct": so}, v, merge=True)
        last = entries("lvs")[-1]
        check("d. 시트 행 삽입 PUT(__struct) - 원장 줄에 replay.struct", st == 200 and ((last.get("replay") or {}).get("struct") or [{}])[0].get("op") == "insertRows", json.dumps(last.get("replay"), ensure_ascii=False))
        d, v = get("lvs")
        d["sheets"][0]["cells"]["C1"] = "시트 작업"
        st, rr, _ = ops("lvs", v, [{"op": "cell", "tab": "t01", "key": "C1", "value": "시트 작업"}])
        rc, r = verify("lvs")
        check("d. 시트 원장(행 삽입 PUT·셀 작업 저장) verify rc 0 · 재생 같음 1", rc == 0 and r.get("replay", {}).get("ok") == 1, json.dumps(summary(r), ensure_ascii=False))
        # e. 작업 공간 실행기
        rc, r = verify("lv", via_nexa=True)
        check("e. nexa.py ledger verify lv --json 도 같은 결과", rc == 0 and r.get("deck") == "lv", json.dumps(r, ensure_ascii=False)[:300])
        # f. 변경 탭 응답에 replay 가 새지 않음
        st, ch, _ = call("GET", "/api/changes/lv")
        s = json.dumps(ch, ensure_ascii=False)
        NOTES.append(f"f. /api/changes/lv 응답 {len(s.encode('utf-8'))} 바이트")
        check("f. /api/changes 목록 응답에 replay(재생용 작업 목록)가 없음", st == 200 and '"replay"' not in s, s[:300])
        st, ch, _ = call("GET", f"/api/changes/lv?seq={entries('lv')[-1]['seq']}")
        check("f. /api/changes?seq= 한 줄 응답에도 replay 없음", st == 200 and '"replay"' not in json.dumps(ch, ensure_ascii=False), json.dumps(ch, ensure_ascii=False)[:300])
        # g. 원장에 안 남던 쓰기 - 요소 순서만 바꾼 저장 · 같은 내용 저장(updated 만 바뀜)
        d, v = get("lvq")
        st, r, _ = put("lvq", {**d, "slides": [{**d["slides"][0], "elements": d["slides"][0]["elements"][::-1]}]}, v)
        sq1 = r.get("seq")
        _, ch1, _ = call("GET", f"/api/changes/lvq?seq={sq1}")
        d, v = get("lvq")
        st2, r2, _ = ops("lvq", v, [{"op": "order", "slide": "s1", "ids": [e["id"] for e in d["slides"][0]["elements"]][::-1]}])
        check("g. 요소 자리 바꾸기 PUT·작업 저장 order - 둘 다 seq 가 나오고 변경 항목에 '요소 순서'",
              st == 200 and sq1 and st2 == 200 and r2.get("seq") and "요소 순서" in json.dumps(ch1, ensure_ascii=False), json.dumps({"seq": [sq1, r2.get("seq")], "ch": ch1}, ensure_ascii=False)[:400])
        time.sleep(1.1)
        n0 = len(entries("lvq"))
        d, v = get("lvq")
        st, r, _ = put("lvq", d, v)
        es = entries("lvq")
        quiet = [e for e in es[n0:] if e.get("kind") == "quiet"]
        _, chq, _ = call("GET", "/api/changes/lvq")
        listed = {e.get("seq") for e in (chq.get("entries") or [])}
        rc, rv = verify("lvq")
        NOTES.append(f"g. 같은 내용 PUT(1.1초 뒤): 응답 seq {r.get('seq')} · 새 줄 {[(e.get('seq'), e.get('kind')) for e in es[n0:]]} · verify {json.dumps(summary(rv), ensure_ascii=False)}")
        check("g. 같은 내용 PUT(1.1초 뒤) - 원장에 quiet 줄 · /api/changes 목록에는 없음 · verify 사슬 끊김 0·rc 0",
              st == 200 and len(quiet) == 1 and quiet[0].get("seq") not in listed and rc == 0 and rv.get("chain", {}).get("broken") == 0, json.dumps({"new": es[n0:], "rc": rc, "v": summary(rv)}, ensure_ascii=False)[:500])
        # g. quiet 줄 뒤 서버를 다시 띄워도 '서버 꺼진 사이' 줄이 생기지 않는다(시작 대조 = 마지막 쓰기)
        srv.terminate(); srv.wait(timeout=10)
        n0 = len(entries("lvq"))
        srv = subprocess.Popen([sys.executable, str(STUDIO / "server.py"), "--workspace", str(WS), "--port", str(PORT)], env=ENV, cwd=str(WS), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(60):
            try:
                urllib.request.urlopen(f"{B}/api/decks", timeout=2).read(); break
            except Exception:  # noqa: BLE001
                time.sleep(0.5)
        call("GET", "/api/changes/lvq")
        new = entries("lvq")[n0:]
        check("g. quiet 뒤 서버 재시작 - startup 줄이 생기지 않음", not any(e.get("action") == "startup" for e in new), json.dumps(new, ensure_ascii=False)[:300])
    finally:
        srv.terminate()
        try:
            srv.wait(timeout=10)
        except subprocess.TimeoutExpired:
            srv.kill()
    for n in NOTES:
        print("  ·", n)
    print(f"\n{'전부 통과' if not FAILS else '실패: ' + ', '.join(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
