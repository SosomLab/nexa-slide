// 화면 작업(nexa-merge.js ops·applyOps)이 서버 deckops.py 와 같은지 - tests/deckops_cases.json 골든(동시 편집 3-4). 실패하면 종료 코드 1.
//   node studio/tests/nexa_ops_check.js
const fs = require("fs"), path = require("path");
require(path.join(__dirname, "..", "nexa-merge.js"));
const M = globalThis.NexaMerge;
const cases = JSON.parse(fs.readFileSync(path.join(__dirname, "deckops_cases.json"), "utf8"));
const ids = (d) => JSON.stringify([(d.slides || []).map((s) => [s.id, (s.elements || []).map((e) => e.id)]), (d.sheets || []).map((t) => t.id)]);
let bad = 0;
for (const c of cases) {
  const ins = JSON.stringify(c);
  const ops = M.ops(c.old, c.new), r = M.applyOps(c.doc, c.ops, c.base);
  const ok = JSON.stringify(ops) === JSON.stringify(c.ops) && M.eq(r.doc, c.expect) && ids(r.doc) === ids(c.expect) && r.applied === c.applied && r.dropped.length === c.dropped && JSON.stringify(c) === ins;
  if (!ok) { bad++; console.log("FAIL", c.name, `\n  작업 ${JSON.stringify(ops).slice(0, 600)}\n  기대 ${JSON.stringify(c.ops).slice(0, 600)}\n  결과 ${ids(r.doc)} / ${ids(c.expect)} 같음=${M.eq(r.doc, c.expect)}`); }
}
console.log(bad ? `\n실패 ${bad}` : `전부 통과 (${cases.length}사례 - deckops.py 와 같음)`);
process.exit(bad ? 1 : 0);
