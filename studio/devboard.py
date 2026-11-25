# -*- coding: utf-8 -*-
"""작업판 - 5분 넘게 걸리는 일(시험·검증·측정·위임)이 언제 시작해 어디까지 갔고 언제쯤 끝날지를 파일 하나로 보인다(docs/dev/autodev.md · 전역 규칙 §4).

    python studio/devboard.py start <id> <작업자> "<제목>" <예상 분> [--where <트리·PC>] [--pid <PID>] [--by <적은 이>]
    python studio/devboard.py step  <id> <n>/<N> "<지금 단계>" [--eta <남은 초>] [--pid <PID>] [--seen] [--ev "<진행 증거>"]
    python studio/devboard.py ack   <id>
    python studio/devboard.py done  <id> ok|fail|skip "<한 줄 결과>"
    python studio/devboard.py alert <id> "<첫 실패 · 경고 한 줄>"
    python studio/devboard.py render

- 작업자 = 개발 | 협업 | 하위:<이름>(하위 에이전트) | 원격:<이름>(다른 PC·클라우드). --by = 작업자가 판에 직접 쓸 수 없어 맡긴 세션이 대신 적을 때 그 세션.
- 저장 = <공용 루트>/out/status/board.tsv(한 줄 = 사건, 덧붙이기만 - 여러 세션이 잠금 없이 같이 쓴다) → 읽을 때 id 마다 마지막 상태로 접는다.
  사람용 = out/status/now.md(사건마다 다시 쓴다 - 편집기에 열어 두면 저절로 갱신). 공용 루트 = git 공용 폴더의 부모(모든 worktree 가 같은 판을 본다).
- now.md 맨 위: ✗ 첫 실패(alert) · ⚠ 멈춤 의심(신호 3분 없음 또는 예상의 3배) · 대리 기록이면 ⏰ 확인할 때(마지막 확인 10분 넘음) · 응답 미확인 · 진행 없음(증거가 두 번 연속 같음).
- 다른 모듈에서: import devboard; devboard.event("step", id, prog="2/5", note="…", eta=120) - 실패해도 예외를 내지 않는다(판은 보조 기록).
"""
import os
import subprocess
import sys
import time
from pathlib import Path

FIELDS = ("t", "id", "ev", "who", "title", "est", "prog", "note", "res", "eta", "by", "seen", "evid", "where", "pid")
STALL = 180       # 신호가 이만큼(초) 없으면 멈춤 의심
CHECK = 600       # 대리 기록 - 마지막 확인 뒤 이만큼 지나면 확인할 때
KEEP_LINES = 2000  # 넘으면 하루 지난 끝난 일을 걷어 낸다


def common_root():
    """모든 worktree 가 같이 쓰는 저장소 루트(git 공용 폴더의 부모). git 이 없으면 이 파일의 저장소."""
    here = Path(__file__).resolve().parent.parent
    try:
        r = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=str(here), capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and r.stdout.strip():
            return Path(r.stdout.strip()).resolve().parent
    except (OSError, subprocess.SubprocessError):
        pass
    return here


def board_dir():
    d = Path(os.environ.get("NEXA_BOARD_DIR") or common_root() / "out" / "status")
    d.mkdir(parents=True, exist_ok=True)
    return d


def _clean(s):
    return str(s if s is not None else "").replace("\t", " ").replace("\r", " ").replace("\n", " ")


def _add(**kv):
    row = {k: "" for k in FIELDS}
    row.update({k: _clean(v) for k, v in kv.items() if k in row})
    row["t"] = str(int(time.time()))
    with open(board_dir() / "board.tsv", "a", encoding="utf-8", newline="\n") as f:
        f.write("\t".join(row[k] for k in FIELDS) + "\n")


def _read():
    p = board_dir() / "board.tsv"
    if not p.is_file():
        return []
    out = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            c = line.rstrip("\n").split("\t")
            if len(c) < 3:
                continue
            c += [""] * (len(FIELDS) - len(c))
            out.append(dict(zip(FIELDS, c)))
    return out


def _trim(rows):
    p = board_dir() / "board.tsv"
    if len(rows) <= KEEP_LINES:
        return rows
    cut = time.time() - 86400
    old = {r["id"] for r in rows if r["ev"] == "done" and int(r["t"] or 0) < cut}
    keep = [r for r in rows if r["id"] not in old]
    tmp = p.with_suffix(".tsv.tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        for r in keep:
            f.write("\t".join(r[k] for k in FIELDS) + "\n")
    os.replace(tmp, p)
    return keep


def fold(rows=None):
    """사건들 → id 마다 상태 dict(시작 순서). 같은 id 를 다시 start 하면 새 일로 본다."""
    items, order = {}, []
    for r in rows if rows is not None else _read():
        t, i, ev = int(r["t"] or 0), r["id"], r["ev"]
        if ev == "start":
            items[i] = {"id": i, "who": r["who"], "title": r["title"], "est": float(r["est"] or 0), "start": t, "state": "running", "prog": "", "note": "",
                        "eta": None, "upd": 0, "by": r["by"], "where": r["where"], "pid": r["pid"], "ack": 0, "chk": 0, "evid": "", "evt": 0, "stall": 0, "alert": "", "res": "", "end": 0}
            order = [x for x in order if x != i] + [i]
            continue
        x = items.get(i)
        if x is None:
            continue
        if ev == "ack":
            x["ack"] = t
        elif ev == "step":
            x["prog"], x["note"], x["upd"] = r["prog"] or x["prog"], r["note"], t
            x["eta"] = t + float(r["eta"]) if r["eta"] else None
            if r["pid"]:
                x["pid"] = r["pid"]
            if r["seen"] == "seen":
                x["chk"] = t
                x["ack"] = x["ack"] or t
            if r["evid"]:
                if r["evid"] == x["evid"]:
                    x["stall"] += 1
                else:
                    x["evid"], x["evt"], x["stall"] = r["evid"], t, 0
        elif ev == "done":
            x["state"], x["res"], x["end"] = r["res"] or "ok", r["note"], t
        elif ev == "alert":
            x["alert"] = r["note"]
    return [items[i] for i in order]


def _hm(t):
    return time.strftime("%H:%M", time.localtime(t)) if t else "-"


def _dur(s):
    s = max(0, int(s))
    h, m, sec = s // 3600, (s % 3600) // 60, s % 60
    return (f"{h}h" if h else "") + f"{m}m" + (f"{sec:02d}s" if s < 600 else "")


def _ago(t, now):
    return f"{_hm(t)}({int((now - t) // 60)}분 전)"


def render():
    """now.md 를 다시 쓴다 - 맨 위 경고 줄 · 진행 중 표 · 최근 끝난 일 표."""
    rows = _trim(_read())
    now = time.time()
    items = fold(rows)
    run = [x for x in reversed(items) if x["state"] == "running"]
    fin = [x for x in sorted(items, key=lambda x: x["end"], reverse=True) if x["state"] != "running"][:8]
    top = []
    for x in run:
        if x["alert"]:
            top.append(f"> ✗ **{x['title']}**: {x['alert']}")
    for x in run:
        late3 = x["est"] > 0 and now - x["start"] > x["est"] * 60 * 3
        if x["by"]:
            last = x["chk"] or x["start"]
            if x["stall"] >= 2:
                top.append(f"> ✗ {x['who']} 진행 없음({int((now - x['evt']) // 60)}분): **{x['title']}** - 증거 \"{x['evid']}\" 가 {x['stall']}번 연속 같음")
            if not x["ack"]:
                top.append(f"> ⚠ 응답 미확인: **{x['title']}** ({x['who']}) - 위임 {_ago(x['start'], now)}")
            if now - last > CHECK:
                top.append(f"> ⏰ 확인할 때: **{x['title']}** ({x['who']} · 대리 {x['by']}) - 마지막 확인 {_ago(last, now)}")
            elif late3:
                top.append(f"> ⚠ 예상의 3배: **{x['title']}** ({x['who']})")
            continue
        sig = x["upd"] or x["start"]
        if now - sig > STALL:
            top.append(f"> ⚠ 멈춤 의심: **{x['title']}** - 신호가 {int((now - sig) // 60)}분째 없음")
        elif late3:
            top.append(f"> ⚠ 멈춤 의심: **{x['title']}** - 예상의 3배를 넘김")
    out = [f"# 작업판 - 갱신 {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now))}", ""]
    if top:
        out += [*top, ""]
    out += ["## 진행 중", "", "| 무엇 | 누가 | 어디서 | 시작 | 경과 | 진행 | 지금 단계 | 예상 종료 | PID |", "|---|---|---|---|---|---|---|---|---|"]
    for x in run:
        eta = x["eta"] or (x["start"] + x["est"] * 60 if x["est"] > 0 else 0)
        who = x["who"] + ("" if not x["by"] else f" (대리:{x['by']}" + (f" · 확인 {_ago(x['chk'], now)}" if x["chk"] else " · 확인 없음") + ")")
        out.append(f"| {x['title']} | {who} | {x['where'] or '-'} | {_hm(x['start'])} | {_dur(now - x['start'])} | {x['prog'] or '-'} | {x['note'] or '-'} | "
                   f"{(_hm(eta) + (' ⚠ 늦음' if now > eta else '')) if eta else '예상 없음'} | {x['pid'] or '-'} |")
    if not run:
        out.append("| (없음) | | | | | | | | |")
    out += ["", "## 최근 끝난 일", "", "| 무엇 | 누가 | 결과 | 소요 | 끝 | 한 줄 |", "|---|---|---|---|---|---|"]
    for x in fin:
        out.append(f"| {x['title']} | {x['who']} | {x['state']} | {_dur(x['end'] - x['start'])} | {_hm(x['end'])} | {x['res'] or '-'} |")
    if not fin:
        out.append("| (없음) | | | | | |")
    p = board_dir() / "now.md"
    tmp = p.with_suffix(".md.tmp")
    tmp.write_text("\n".join(out) + "\n", encoding="utf-8")
    os.replace(tmp, p)
    return p


def event(kind, id_, **kv):
    """다른 모듈에서 부르는 길 - 판은 보조 기록이라 실패해도 예외를 내지 않는다."""
    try:
        if kind == "start":
            _add(id=id_, ev="start", who=kv.get("who", ""), title=kv.get("title", id_), est=kv.get("est", 0), by=kv.get("by", ""), where=kv.get("where", ""), pid=kv.get("pid", ""))
        elif kind == "step":
            _add(id=id_, ev="step", prog=kv.get("prog", ""), note=kv.get("note", ""), eta=kv.get("eta", ""), pid=kv.get("pid", ""),
                 seen="seen" if kv.get("seen") else "", evid=kv.get("evid", ""))
        elif kind == "ack":
            _add(id=id_, ev="ack")
        elif kind == "done":
            _add(id=id_, ev="done", res=kv.get("res", "ok"), note=kv.get("note", ""))
        elif kind == "alert":
            _add(id=id_, ev="alert", note=kv.get("note", ""))
        render()
        return True
    except Exception as e:  # noqa: BLE001
        print(f"(작업판 기록 실패: {e})", file=sys.stderr)
        return False


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(prog="devboard", description="작업판(out/status/board.tsv · now.md)")
    sp = ap.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("start"); a.add_argument("id"); a.add_argument("who"); a.add_argument("title"); a.add_argument("est", type=float, nargs="?", default=0)
    a.add_argument("--where", default=""); a.add_argument("--pid", default=""); a.add_argument("--by", default="")
    a = sp.add_parser("step"); a.add_argument("id"); a.add_argument("prog"); a.add_argument("note", nargs="?", default="")
    a.add_argument("--eta", default=""); a.add_argument("--pid", default=""); a.add_argument("--seen", action="store_true"); a.add_argument("--ev", default="")
    a = sp.add_parser("ack"); a.add_argument("id")
    a = sp.add_parser("done"); a.add_argument("id"); a.add_argument("res", choices=("ok", "fail", "skip")); a.add_argument("note", nargs="?", default="")
    a = sp.add_parser("alert"); a.add_argument("id"); a.add_argument("note")
    sp.add_parser("render")
    o = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if o.cmd == "render":
        print(render()); return 0
    kv = {k: v for k, v in vars(o).items() if k not in ("cmd", "id")}
    if o.cmd == "start":
        ok = event("start", o.id, who=o.who, title=o.title, est=o.est, where=o.where, pid=o.pid, by=o.by)
    elif o.cmd == "step":
        ok = event("step", o.id, prog=o.prog, note=o.note, eta=o.eta, pid=o.pid, seen=o.seen, evid=o.ev)
    elif o.cmd == "done":
        ok = event("done", o.id, res=o.res, note=o.note)
    elif o.cmd == "alert":
        ok = event("alert", o.id, note=o.note)
    else:
        ok = event(o.cmd, o.id, **kv)
    print(board_dir() / "now.md")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
