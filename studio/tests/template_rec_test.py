# -*- coding: utf-8 -*-
"""템플릿 추천 점수(0.25.15) - hub.template_rec · note_template.

    python3 studio/tests/template_rec_test.py

사용(최근 작업의 템플릿) 높은 배점 · 미리 보기 중간 · 그 둘과 비슷한 색 낮은 배점 · 색이 거의 같은 템플릿은 같은 중복 묶음(dup).
사용자 설정은 임시 폴더로 격리한다.
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ["NEXA_SLIDE_USER_DIR"] = tempfile.mkdtemp(prefix="nexa-tplrec-")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import hub  # noqa: E402

FAILS = []


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else extra)
    if not cond:
        FAILS.append(name)


def rec(recent):
    return {t["name"]: t["rec"] for t in hub.template_rec(hub.templates(), recent)}


r0 = rec([])
check("기록 없음 - 모든 점수 0", all(v["score"] == 0 for v in r0.values()), str(r0)[:300])
check("중복 묶음 - lecture-large 는 lecture 와 같은 묶음, 다른 템플릿은 자기 묶음", r0["lecture-large"]["dup"] == "lecture" and r0["swiss"]["dup"] == "swiss")

for _ in range(2):
    hub.note_template("keynote")
hub.note_template("../x")  # 이상한 이름은 무시
r1 = rec([{"workspace": True, "template": "swiss", "path": "x"}, {"workspace": True, "template": "swiss", "path": "y"}])
check("사용 2 → 높은 배점(×10)", r1["swiss"]["used"] == 2 and r1["swiss"]["score"] >= 20, str(r1["swiss"]))
check("미리 보기 2 → 중간 배점(×3)", r1["keynote"]["preview"] == 2 and 6 <= r1["keynote"]["score"] < 10, str(r1["keynote"]))
sim = {n: v for n, v in r1.items() if not v["used"] and not v["preview"] and v["score"] > 0}
check("비슷한 색 → 낮은 배점(2 이하, 쓰거나 본 템플릿 이름)", sim and all(v["score"] <= 2 and v["like"] in ("swiss", "keynote") for v in sim.values()), str(sim)[:300])
check("가장 닮은 것: editorial(진홍) 은 swiss(빨강) 를 닮았다", r1["editorial"]["like"] == "swiss" and r1["editorial"]["score"] > 0, str(r1["editorial"]))
check("점수 순서: 사용 > 미리 보기 > 비슷한 색", r1["swiss"]["score"] > r1["keynote"]["score"] > max(v["score"] for v in sim.values()))
check("미리 보기 기록은 사용자 설정 폴더에", hub.TPL_STATS.is_file() and str(hub.TPL_STATS).startswith(os.environ["NEXA_SLIDE_USER_DIR"]))

print("\n실패:", FAILS or "없음")
print("전부 통과" if not FAILS else "")
sys.exit(1 if FAILS else 0)
