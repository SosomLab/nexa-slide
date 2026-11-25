# -*- coding: utf-8 -*-
"""page_render_check.js 가 부른다 - 표준 입력의 페이지 문서를 page_doc.py 규칙으로 풀어 JSON 으로 찍는다(화면 규칙과 맞춰 보기)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import page_doc as P  # noqa: E402

d = json.loads(sys.stdin.buffer.read().decode("utf-8"))
sys.stdout.reconfigure(encoding="utf-8")
print(json.dumps({"markers": P.list_markers(d["blocks"]), "box": P.page_box(d),
                  "styles": {k: P.resolve_style(d, k) for k in ["body", "h1", "h2", "nope"]}}, ensure_ascii=False))
