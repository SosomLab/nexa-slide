# -*- coding: utf-8 -*-
"""Genspark 조사 결과(docs/research/genspark-skills/data)를 검토 등록부(registry.json)에 등록한다.

    python docs/research/review/import_genspark.py

등록하는 것: 템플릿 후보(candidates.json) · 새 레이아웃 유형(archetypes.json) · 참고 덱 156개(census.json).
이미 있는 대상은 상태·날짜·메모·이력을 그대로 두고 제목·근거 정보만 새로 고친다(여러 번 실행해도 안전).
"""
import datetime as dt
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parents[0] / "genspark-skills" / "data"
REG = HERE / "registry.json"
TIER = {n: 1 for n in ["insight_panel", "worked_example", "line_chart", "quiz_check", "matrix_plot", "people_cards", "big_number_evidence", "case_story", "references", "photo_statement"]}
TIER.update({n: 2 for n in ["tree_org", "range_scale", "takeaway_card", "tier_columns", "funnel_pyramid", "ui_mock", "share_circle", "annotated_passage", "photo_plates", "qa_backup", "numbered_rows", "heatmap", "exhibit", "status_board"]})


def j(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def main():
    reg = json.loads(REG.read_text(encoding="utf-8")) if REG.is_file() else {"items": []}
    have = {x["id"]: x for x in reg["items"]}
    now = dt.datetime.now().isoformat(timespec="seconds")
    new = []
    for t in j("candidates.json")["templates"]:
        new.append({"id": f"gs-tpl-{t['name']}", "kind": "template", "title": f"{t['label']} (`{t['name']}`)", "tags": [t["family"], "Genspark"],
                    "source": {"type": "genspark-template", "sources": t["sources"],
                               "detail": {"색": t["colors"], "글꼴": t["fonts"], "구조 부품": " · ".join(t["parts"]), "쓰는 곳": t["useFor"]}}})
    for a in j("archetypes.json")["new"]:
        d = a["definitions"][0] if a["definitions"] else {}
        new.append({"id": f"gs-layout-{a['name']}", "kind": "layout", "title": f"{a['label']} (`{a['name']}`)",
                    "tags": [f"{TIER.get(a['name'], 3)}순위", f"{a['slides']}장·{a['skills']}스킬", "Genspark"],
                    "source": {"type": "genspark-layout", "examples": a["examples"],
                               "detail": {"구조": d.get("structure", ""), "쓰는 곳": d.get("useFor", ""), "묶은 이름": ", ".join(a["members"])}}})
    for c in j("census.json"):
        new.append({"id": f"gs-deck-{c['no']}", "kind": "reference-deck", "title": f"{c['no']} {c['name']} — {c['title']}",
                    "tags": [c["category"], c["familyGroup"], f"{c['score']}점", "Genspark"],
                    "source": {"type": "genspark-skill", "ref": c["no"],
                               "detail": {"점수 이유": c.get("why") or "", "구성 흐름": c.get("flow") or "", "격자": c.get("grid") or ""}}})
    added = 0
    for it in new:
        if it["id"] in have:
            have[it["id"]].update({k: it[k] for k in ("title", "tags", "source", "kind")})
        else:
            reg["items"].append({**it, "note": "", "status": "registered", "registeredAt": now, "reviewedAt": None, "approvedAt": None,
                                 "history": [{"at": now, "action": "register", "note": "Genspark 전수 조사(2026-10-02)에서 가져옴"}]})
            added += 1
    REG.write_text(json.dumps(reg, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"등록부 {REG} — 새로 {added}개, 전체 {len(reg['items'])}개")


if __name__ == "__main__":
    main()
