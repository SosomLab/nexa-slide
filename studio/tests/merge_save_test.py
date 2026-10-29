# -*- coding: utf-8 -*-
"""병합 저장(동시 편집 1단계, docs/collab.md) 시험 - 작업 공간 서버의 PUT ?merge=1 과 save_deck 의 병합.
    python3 studio/tests/merge_save_test.py
- 편집기 둘이 같은 판에서 다른 요소를 고치면 둘 다 남는다(409 아님) · 같은 속성이면 나중 저장 + 충돌 · 원장 evidence.merge
- AI(save_deck): 사본을 만든 뒤 사람이 저장해도 병합되고, 같은 곳은 사람이 이긴다 · 사본이 병합 결과로 바뀐다
- 잃어버린 갱신 재현: --no-merge 면 예전처럼 409(종료 코드 2) · merge 없는 PUT 도 409 · 기준본이 없으면 409 reason=no-base
- 시트: 다른 셀·같은 셀의 값과 서식이 둘 다 남는다"""
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
WS = PROJ / "merge시험" / "slides"
ENV = {**os.environ, "NEXA_SLIDE_USER_DIR": str(USER), "NEXA_SLIDE_PROJECTS": str(PROJ), "PYTHONIOENCODING": "utf-8", "NEXA_SLIDE_WORKSPACE": str(WS)}
B = f"http://127.0.0.1:{PORT}"
FAILS = []


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else extra)
    if not cond:
        FAILS.append(name)


def get(i):
    with urllib.request.urlopen(f"{B}/api/deck/{i}", timeout=10) as r:
        return json.loads(r.read()), r.headers.get("X-Deck-Version")


def put(i, deck, **q):
    url = f"{B}/api/deck/{i}?" + "&".join(f"{k}={v}" for k, v in q.items())
    req = urllib.request.Request(url, data=json.dumps(deck, ensure_ascii=False).encode(), method="PUT", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def el(d, sid, eid):
    return next(e for s in d["slides"] if s["id"] == sid for e in s["elements"] if e["id"] == eid)


def nexa(*args):
    r = subprocess.run([sys.executable, str(STUDIO / args[0]), *args[1:]], env=ENV, cwd=str(WS), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout + r.stderr)


def main():
    if not (WS / "nexa-slide.json").is_file():
        subprocess.run([sys.executable, str(STUDIO / "init_workspace.py"), str(WS.parent), "--title", "merge시험", "--port", str(PORT)], env=ENV, capture_output=True, text=True, encoding="utf-8")
    decks = WS / "decks"; decks.mkdir(parents=True, exist_ok=True)
    e = lambda i, t: {"id": i, "type": "text", "x": 40, "y": 40, "w": 300, "h": 60, "text": t, "size": 20}  # noqa: E731
    (decks / "mg.json").write_text(json.dumps({"id": "mg", "title": "병합", "slides": [{"id": "s1", "elements": [e("e1", "하나"), e("e2", "둘")]}]}, ensure_ascii=False), encoding="utf-8")
    (decks / "ms.json").write_text(json.dumps({"id": "ms", "title": "시트", "kind": "sheet", "slides": [], "sheets": [{"id": "t01", "name": "S", "cells": {"A1": "제목", "B2": 1}}]}, ensure_ascii=False), encoding="utf-8")
    srv = subprocess.Popen([sys.executable, str(STUDIO / "server.py"), "--workspace", str(WS), "--port", str(PORT)], env=ENV, cwd=str(WS), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(f"{B}/api/decks", timeout=2).read(); break
            except Exception:  # noqa: BLE001
                time.sleep(0.5)
        # 1. 편집기 둘 - 같은 판에서 다른 요소
        d0, v0 = get("mg")
        a = json.loads(json.dumps(d0)); el(a, "s1", "e1")["text"] = "A 가 고침"
        b = json.loads(json.dumps(d0)); el(b, "s1", "e2")["fill"] = "primary"
        sa, ra = put("mg", a, base=v0)
        time.sleep(0.05)
        sb, rb = put("mg", b, base=v0, merge=1)
        d1, v1 = get("mg")
        check("편집기 둘 - 다른 요소는 둘 다 남는다(409 아님)", sa == 200 and sb == 200 and rb.get("merged") and rb.get("conflicts") == []
              and el(d1, "s1", "e1")["text"] == "A 가 고침" and el(d1, "s1", "e2").get("fill") == "primary", f"{sa} {sb} {rb}")
        check("병합 응답의 deck = 저장된 파일", rb.get("deck") and el(rb["deck"], "s1", "e1")["text"] == "A 가 고침" and rb.get("version") == v1)
        # 2. 같은 속성 - 나중 저장이 이기고 충돌로 남는다
        a = json.loads(json.dumps(d1)); el(a, "s1", "e1")["text"] = "먼저"
        b = json.loads(json.dumps(d1)); el(b, "s1", "e1")["text"] = "나중"
        put("mg", a, base=v1); time.sleep(0.05)
        sb, rb = put("mg", b, base=v1, merge=1)
        d2, v2 = get("mg")
        check("같은 속성 - 나중 저장(편집기끼리) + 충돌 1건", sb == 200 and el(d2, "s1", "e1")["text"] == "나중" and len(rb.get("conflicts") or []) == 1, str(rb.get("conflicts")))
        with urllib.request.urlopen(f"{B}/api/changes/mg?seq={rb.get('seq')}", timeout=10) as r:
            ent = json.loads(r.read()).get("entry") or {}
        check("원장에 병합 충돌(evidence.merge)", (ent.get("evidence") or {}).get("merge", {}).get("conflicts"), json.dumps(ent, ensure_ascii=False)[:300])
        # 3. merge 없으면 예전처럼 409 · 기준본 없으면 reason=no-base
        s3, r3 = put("mg", d1, base=v1)
        check("merge 없는 PUT - 예전처럼 409", s3 == 409 and r3.get("error") == "conflict")
        s4, r4 = put("mg", d2, base="12345", merge=1)
        check("기준본을 모르면 409 reason=no-base(데이터는 그대로)", s4 == 409 and r4.get("reason") == "no-base" and get("mg")[1] == v2)
        # 4. AI - 사본을 만든 뒤 사람이 저장 → save_deck 이 병합, 같은 곳은 사람이 이긴다
        code, out = nexa("draft_deck.py", "mg")
        draft = WS / "out" / ".studio" / "draft-mg.json"
        dr = json.loads(draft.read_text(encoding="utf-8"))
        el(dr, "s1", "e1")["text"] = "AI 가 고침"; el(dr, "s1", "e2")["text"] = "AI 둘"
        draft.write_text(json.dumps(dr, ensure_ascii=False, indent=1), encoding="utf-8")
        cur, v = get("mg"); el(cur, "s1", "e1")["text"] = "사람이 고침"
        put("mg", cur, base=v)
        code, out = nexa("save_deck.py", "mg", "--from", str(draft), "--note", "시험")
        d4, _ = get("mg")
        check("AI 저장 - 병합되고 같은 곳은 사람이 이긴다", code == 0 and el(d4, "s1", "e1")["text"] == "사람이 고침" and el(d4, "s1", "e2")["text"] == "AI 둘", out)
        check("AI 저장 - 출력에 병합·충돌 줄(reply 에 쓰라고)", "병합" in out and "충돌 1건" in out, out)
        dr2 = json.loads(draft.read_text(encoding="utf-8"))
        check("AI 저장 - 사본이 병합 결과로 바뀐다(이어 고쳐도 사람 변경을 되돌리지 않게)", el(dr2, "s1", "e1")["text"] == "사람이 고침")
        # 5. 잃어버린 갱신 재현 - --no-merge 면 409
        nexa("draft_deck.py", "mg")
        dr = json.loads(draft.read_text(encoding="utf-8")); el(dr, "s1", "e2")["text"] = "덮으면 안 됨"
        draft.write_text(json.dumps(dr, ensure_ascii=False, indent=1), encoding="utf-8")
        cur, v = get("mg"); el(cur, "s1", "e1")["text"] = "그 사이 사람"
        put("mg", cur, base=v)
        code, out = nexa("save_deck.py", "mg", "--from", str(draft), "--no-merge")
        check("save_deck --no-merge - 사본 뒤 사람이 저장했으면 409(종료 코드 2), 파일 그대로", code == 2 and el(get("mg")[0], "s1", "e1")["text"] == "그 사이 사람", out)
        # 6. AI 제안(--propose) - 파일은 그대로, 장마다 골라 받기(그 사이 사람 변경 유지), 나머지 버리기
        cur, v = get("mg")
        cur["slides"].append({"id": "s2", "elements": [e("f1", "둘째 장")]})
        put("mg", cur, base=v)
        code, out = nexa("draft_deck.py", "mg")
        dr = json.loads(draft.read_text(encoding="utf-8"))
        el(dr, "s1", "e2")["text"] = "AI 제안 둘"
        dr["slides"][1]["elements"][0]["text"] = "AI 제안 둘째 장"
        dr["slides"].append({"id": "s3", "elements": [e("g1", "AI 가 더한 장")]})
        draft.write_text(json.dumps(dr, ensure_ascii=False, indent=1), encoding="utf-8")
        before_v = get("mg")[1]
        code, out = nexa("save_deck.py", "mg", "--from", str(draft), "--propose", "--request", "rprop1")
        with urllib.request.urlopen(f"{B}/api/proposals/mg", timeout=10) as r:
            plist = json.loads(r.read())
        its = (plist[0]["items"] if plist else [])
        check("--propose - 파일은 그대로, 제안 3곳(s1 수정·s2 수정·s3 추가)", code == 0 and get("mg")[1] == before_v and sorted(x["id"] for x in its) == ["s:s1", "s:s2", "s:s3"] and "제안을 남겼습니다" in out, out + json.dumps(plist, ensure_ascii=False))
        cur, v = get("mg"); el(cur, "s1", "e1")["text"] = "제안 뒤 사람"
        put("mg", cur, base=v)
        req = urllib.request.Request(f"{B}/api/proposals/mg", data=json.dumps({"action": "accept", "request": "rprop1", "items": ["s:s1", "s:s3"]}).encode(), method="POST", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            ra = json.loads(r.read())
        d6 = get("mg")[0]
        check("제안 일부 받기 - s1·s3 만, 그 사이 사람 변경(e1) 유지, s2 는 그대로", ra.get("ok") and ra.get("left") == 1 and el(d6, "s1", "e2")["text"] == "AI 제안 둘"
              and el(d6, "s1", "e1")["text"] == "제안 뒤 사람" and [s["id"] for s in d6["slides"]] == ["s1", "s2", "s3"] and d6["slides"][1]["elements"][0]["text"] == "둘째 장", json.dumps(d6, ensure_ascii=False)[:400])
        with urllib.request.urlopen(f"{B}/api/changes/mg?seq={ra.get('seq')}", timeout=10) as r:
            ent = json.loads(r.read()).get("entry") or {}
        check("원장 action accept · 받은 항목", ent.get("action") == "accept" and (ent.get("evidence") or {}).get("proposal", {}).get("items") == ["s:s1", "s:s3"], json.dumps(ent, ensure_ascii=False)[:300])
        req = urllib.request.Request(f"{B}/api/proposals/mg", data=json.dumps({"action": "discard", "request": "rprop1"}).encode(), method="POST", headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10).read()
        with urllib.request.urlopen(f"{B}/api/proposals/mg", timeout=10) as r:
            check("나머지 버리기 - 제안 없음, 문서 그대로", json.loads(r.read()) == [] and get("mg")[0]["slides"][1]["elements"][0]["text"] == "둘째 장")
        # 7. 시트 - 다른 셀, 같은 셀의 값과 서식
        s0, sv = get("ms")
        a = json.loads(json.dumps(s0)); a["sheets"][0]["cells"]["B2"] = 2; a["sheets"][0]["cells"]["A1"] = "새 제목"
        b = json.loads(json.dumps(s0)); b["sheets"][0]["cells"]["C3"] = "추가"; b["sheets"][0]["cells"]["A1"] = {"v": "제목", "b": True}
        put("ms", a, base=sv); time.sleep(0.05)
        sb, rb = put("ms", b, base=sv, merge=1)
        c = get("ms")[0]["sheets"][0]["cells"]
        # 7b. 시트 AI 제안을 셀 하나씩(3-3) - 탭 안의 셀만 받고, 남은 셀은 탭째로 받기
        def prop(body):
            rq = urllib.request.Request(f"{B}/api/proposals/ms", data=json.dumps(body, ensure_ascii=False).encode(), method="POST", headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(rq, timeout=10) as r:
                return json.loads(r.read())
        p0 = get("ms")[0]
        tid = p0["sheets"][0]["id"]
        pd = json.loads(json.dumps(p0)); pd["sheets"][0]["cells"]["D4"] = "제안 D4"; pd["sheets"][0]["cells"]["E5"] = {"f": "=1+1"}
        pc = prop({"action": "create", "request": "rpropc", "deck": pd})
        subs = [x["id"] for x in (pc.get("items") or [{}])[0].get("subs") or []]
        check("시트 제안 - 탭 하나에 셀 2개(D4·E5)를 하나씩 고를 수 있게", sorted(subs) == [f"t:{tid}:D4", f"t:{tid}:E5"], json.dumps(pc, ensure_ascii=False)[:300])
        pa = prop({"action": "accept", "request": "rpropc", "items": [f"t:{tid}:D4"]})
        c7 = get("ms")[0]["sheets"][0]["cells"]
        check("셀 하나(D4)만 받기 - E5 는 아직, 남은 제안 1곳", pa.get("ok") and pa.get("left") == 1 and c7.get("D4") == "제안 D4" and "E5" not in c7, json.dumps(pa, ensure_ascii=False))
        pa = prop({"action": "accept", "request": "rpropc", "items": [f"t:{tid}"]})
        c7 = get("ms")[0]["sheets"][0]["cells"]
        with urllib.request.urlopen(f"{B}/api/proposals/ms", timeout=10) as r:
            check("남은 탭째로 받기 - E5 반영, 제안 끝", pa.get("left") == 0 and (c7.get("E5") or {}).get("f") == "=1+1" and json.loads(r.read()) == [], json.dumps(c7, ensure_ascii=False)[:300])
        # 7c. 작업(op) 저장(3-4) - 오래된 판 위의 작업을 지금 파일에 얹는다(남의 변경 유지 · 지운 요소 되살리기 · 대상 없으면 버림 · 원장 evidence.ops)
        def ops(deck, body, code=200):
            rq = urllib.request.Request(f"{B}/api/ops/{deck}", data=json.dumps(body, ensure_ascii=False).encode(), method="POST", headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(rq, timeout=10) as r:
                    return r.status, json.loads(r.read())
            except urllib.error.HTTPError as ex:
                return ex.code, json.loads(ex.read() or b"{}")
        o0, ov = get("mg")
        sid = o0["slides"][0]["id"]
        e1, e2 = [x["id"] for x in o0["slides"][0]["elements"][:2]]
        other = json.loads(json.dumps(o0)); el(other, sid, e2)["text"] = "다른 창 글"; del other["slides"][0]["elements"][0]  # 다른 창: e2 글 · e1 지움
        put("mg", other, base=ov)
        st, ra = ops("mg", {"base": ov, "ops": [{"op": "set", "slide": sid, "el": e1, "key": "text", "value": "작업 저장"},
                                                {"op": "set", "slide": sid, "el": "없는요소", "key": "text", "value": "x"}]})
        d7 = get("mg")[0]
        check("작업 저장 - 오래된 판 위의 작업: 남이 지운 e1 을 되살려 고침 · 남의 e2 글 유지 · 없는 요소 작업은 버림", st == 200 and ra.get("applied") == 1 and len(ra.get("dropped") or []) == 1 and ra.get("stale")
              and el(d7, sid, e1)["text"] == "작업 저장" and el(d7, sid, e2)["text"] == "다른 창 글" and [x["id"] for x in d7["slides"][0]["elements"][:2]] == [e1, e2], json.dumps(ra, ensure_ascii=False) + json.dumps(d7["slides"][0], ensure_ascii=False)[:300])
        with urllib.request.urlopen(f"{B}/api/changes/mg?seq={ra.get('seq')}", timeout=10) as r:
            ent = json.loads(r.read()).get("entry") or {}
        check("작업 저장 원장 - evidence.ops(작업 수·적용·버림·어디를)", ((ent.get("evidence") or {}).get("ops") or {}).get("n") == 2 and f"set {sid} {e1} text" in (ent["evidence"]["ops"].get("list") or []), json.dumps(ent, ensure_ascii=False)[:300])
        check("작업 저장 - 빈 목록 400 · 없는 덱 404", ops("mg", {"base": "", "ops": []})[0] == 400 and ops("nodeck_zz", {"base": "", "ops": [{"op": "deck-set", "key": "a", "value": 1}]})[0] == 404)
        # 8. AI 가 바꾼 셀(/api/reqdiff) - 같은 요청의 AI 저장 둘 사이에 사람이 저장한 셀은 AI 변경으로 세지 않는다
        rdiff = f"rdiff{int(time.time())}"  # 실행마다 새 요청 id(원장은 실행 사이에 남는다)
        d, v = get("ms"); d["sheets"][0]["cells"]["D1"] = "AI 하나"; put("ms", d, base=v, origin="claude", request=rdiff)
        d, v = get("ms"); d["sheets"][0]["cells"]["D2"] = "사람"; put("ms", d, base=v)
        d, v = get("ms"); d["sheets"][0]["cells"]["D3"] = "AI 둘"; put("ms", d, base=v, origin="claude", request=rdiff)
        with urllib.request.urlopen(f"{B}/api/reqdiff/ms?request={rdiff}", timeout=10) as r:
            rd = json.loads(r.read())
        check("reqdiff - AI 저장 사이 사람이 고친 셀(D2)은 빼고 D1·D3 만", sorted(x["key"] for x in rd.get("cells") or []) == ["D1", "D3"] and rd.get("saves") == 2, json.dumps(rd, ensure_ascii=False)[:300])
        # 9. 시트 행 삽입(동시 편집 3-2) - A 가 2행 위에 행을 넣는 사이 B 가 B2 를 고치면, 합친 결과에서 B 의 값은 B3 에(옮겨진 자리)
        sys.path.insert(0, str(STUDIO))
        import sheet_struct  # noqa: E402
        s0, sv = get("ms")
        s0["sheets"][0]["cells"]["E2"] = {"f": "=B2*2"}
        put("ms", s0, base=sv)
        s0, sv = get("ms")
        ops = [{"op": "insertRows", "tab": "t01", "at": 1, "n": 1}]
        a = sheet_struct.apply(s0, ops)
        b = json.loads(json.dumps(s0)); b["sheets"][0]["cells"]["B2"] = "B 가 고침"
        put("ms", b, base=sv); time.sleep(0.05)
        sa, ra = put("ms", {**a, "__struct": ops}, base=sv, merge=1)
        c9 = get("ms")[0]["sheets"][0]["cells"]
        check("시트 행 삽입 병합 - 그 사이 다른 창이 고친 B2 는 옮겨진 B3 에, 수식도 =B3*2(E3)", sa == 200 and c9.get("B3") == "B 가 고침" and "B2" not in c9
              and (c9.get("E3") or {}).get("f") == "=B3*2" and "__struct" not in json.dumps(get("ms")[0]), json.dumps(c9, ensure_ascii=False)[:400])
        check("시트 - 다른 셀 둘 다 · 같은 셀은 값(A)과 굵게(B) 둘 다", sb == 200 and c.get("B2") == 2 and c.get("C3") == "추가" and c.get("A1") == {"b": True, "v": "새 제목"}, json.dumps(c, ensure_ascii=False))
    finally:
        srv.terminate()
        try:
            srv.wait(timeout=10)
        except subprocess.TimeoutExpired:
            srv.kill()
    print(f"\n{'전부 통과' if not FAILS else '실패: ' + ', '.join(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
