# -*- coding: utf-8 -*-
"""Genspark 조사 결과와 추천을 검토 등록부(registry.json)에 등록한다.

    python docs/research/review/import_genspark.py

범위(scope)·상태
  template(템플릿 검토 /review)
    reference-deck  참고 덱 156개 — 분석한 대상(상태 registered "등록")
    template        시각 템플릿 후보 8개(candidates.json) — 추천(상태 recommended "추천")
    template-type   템플릿 유형 15개(template_types.json) — 추천
  slide(슬라이드 유형 검토 /review/slides)
    layout          새 레이아웃 유형 28개(archetypes.json) — 분석한 대상(등록)
    slide-type      슬라이드 유형 52개(studio/slide_types.json) — 추천
이미 있는 대상은 상태·날짜·메모·이력을 그대로 두고(단, 아직 손대지 않은 추천 대상의 "등록"은 "추천"으로) 제목·근거만 새로 고친다.
"""
import datetime as dt
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parents[0] / "genspark-skills" / "data"
STUDIO = HERE.parents[2] / "studio"
REG = HERE / "registry.json"
TIER = {n: 1 for n in ["insight_panel", "worked_example", "line_chart", "quiz_check", "matrix_plot", "people_cards", "big_number_evidence", "case_story", "references", "photo_statement"]}
TIER.update({n: 2 for n in ["tree_org", "range_scale", "takeaway_card", "tier_columns", "funnel_pyramid", "ui_mock", "share_circle", "annotated_passage", "photo_plates", "qa_backup", "numbered_rows", "heatmap", "exhibit", "status_board"]})


def j(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    reg = j(REG) if REG.is_file() else {"items": []}
    have = {x["id"]: x for x in reg["items"]}
    now = dt.datetime.now().isoformat(timespec="seconds")
    arch = {a["name"]: a for a in j(DATA / "archetypes.json")["new"]}
    slides = j(DATA / "slides.json")
    new = []
    for t in j(DATA / "candidates.json")["templates"]:
        new.append({"id": f"gs-tpl-{t['name']}", "scope": "template", "kind": "template", "recommended": True,
                    "title": f"{t['label']} ({t['name']})", "tags": ["시각 템플릿", t["family"]],
                    "source": {"type": "genspark-template", "sources": t["sources"],
                               "detail": {"색": t["colors"], "글꼴": t["fonts"], "구조 부품": " · ".join(t["parts"]), "쓰는 곳": t["useFor"]}}})
    for t in j(DATA / "template_types.json")["types"]:
        new.append({"id": f"rec-ttype-{t['id']}", "scope": "template", "kind": "template-type", "recommended": True,
                    "title": f"{t['label']} ({t['id']})", "tags": ["템플릿 유형", f"{t['count']}덱·{t['slides']}장", f"평균 {t['avgScore']}점"],
                    "source": {"type": "template-type", "sources": t["best"], "members": t["members"], "flow": t["flow"],
                               "detail": {"목적·구성": t["desc"], "어울리는 시각 템플릿": ", ".join(t["visual"]),
                                          "대표 장 흐름": " → ".join(t["flow"]), "근거 덱": " ".join(t["members"]),
                                          "시각 계열": ", ".join(f"{k} {v}" for k, v in t["families"])}}})
    for c in j(DATA / "census.json"):
        new.append({"id": f"gs-deck-{c['no']}", "scope": "template", "kind": "reference-deck", "recommended": False,
                    "title": f"{c['no']} {c['name']} — {c['title']}", "tags": [c["category"], c["familyGroup"], f"{c['score']}점"],
                    "source": {"type": "genspark-skill", "ref": c["no"],
                               "detail": {"점수 이유": c.get("why") or "", "구성 흐름": c.get("flow") or "", "격자": c.get("grid") or ""}}})
    for a in arch.values():
        d = a["definitions"][0] if a["definitions"] else {}
        new.append({"id": f"gs-layout-{a['name']}", "scope": "slide", "kind": "layout", "recommended": False,
                    "title": f"{a['label']} ({a['name']})", "tags": [f"{TIER.get(a['name'], 3)}순위", f"{a['slides']}장·{a['skills']}스킬"],
                    "source": {"type": "genspark-layout", "examples": a["examples"],
                               "detail": {"구조": d.get("structure", ""), "쓰는 곳": d.get("useFor", ""), "묶은 이름": ", ".join(a["members"])}}})
    cat = j(STUDIO / "slide_types.json")
    gl = {g["id"]: g["label"] for g in cat["groups"]}
    for t in cat["types"]:
        ref = t.get("ref")
        ex = arch[ref]["examples"][:8] if ref in arch else [x["id"] for x in slides if x["kind"] == "existing" and x["archetype"] == t["layout"]][:8]
        new.append({"id": f"rec-stype-{t['id']}", "scope": "slide", "kind": "slide-type", "recommended": True,
                    "title": f"{t['label']} ({t['id']})", "tags": [gl[t["group"]], t["layout"], "새 레이아웃" if ref else "기존 레이아웃"],
                    "source": {"type": "slide-type", "ref": t["id"], "examples": ex,
                               "detail": {"목적": t["purpose"], "분류": gl[t["group"]], "레이아웃": t["layout"],
                                          "근거 유형": ref or f"기존 레이아웃 {t['layout']}", "이미지 자리": t.get("image", "")}}})
    added = moved = 0
    for it in new:
        if it["id"] in have:
            x = have[it["id"]]
            x.update({k: it[k] for k in ("title", "tags", "source", "kind", "scope", "recommended")})
            if it["recommended"] and x.get("status") == "registered" and len(x.get("history", [])) <= 1:
                x["status"] = "recommended"  # 아직 손대지 않은 추천 대상
                moved += 1
        else:
            st = "recommended" if it["recommended"] else "registered"
            reg["items"].append({**it, "note": "", "status": st, "registeredAt": now, "reviewedAt": None, "approvedAt": None,
                                 "history": [{"at": now, "action": "recommend" if it["recommended"] else "register",
                                              "note": "분석 결과 추천(2026-10-02)" if it["recommended"] else "Genspark 전수 조사(2026-10-02)에서 가져옴"}]})
            added += 1
    for x in reg["items"]:  # 직접 추가한 대상(사이트·파일 등)은 템플릿 검토 쪽
        x.setdefault("scope", "template")
        x.setdefault("recommended", False)
    REG.write_text(json.dumps(reg, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"등록부 {REG} — 새로 {added}개, 추천으로 옮김 {moved}개, 전체 {len(reg['items'])}개")


if __name__ == "__main__":
    main()
