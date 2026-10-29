// 화면 병합(nexa-merge.js)이 서버 병합(deckmerge.py)과 같은 결과인지 - tests/deckmerge_cases.json 골든 사례. 실패하면 종료 코드 1.
//   node studio/tests/nexa_merge_check.js
// 객체 키 순서는 비교하지 않는다(JSON 값 같음). 충돌 수도 같아야 한다.
const fs = require("fs"), path = require("path");
require(path.join(__dirname, "..", "nexa-merge.js"));
const M = globalThis.NexaMerge;
const cases = JSON.parse(fs.readFileSync(path.join(__dirname, "deckmerge_cases.json"), "utf8"));
let bad = 0;
for (const c of cases) {
  const ins = JSON.stringify([c.base, c.ours, c.theirs]);
  const { merged, conflicts } = M.merge3(c.base, c.ours, c.theirs, c.prefer || "ours");
  const ok = M.eq(merged, c.expect) && conflicts.length === c.conflicts && JSON.stringify([c.base, c.ours, c.theirs]) === ins
    && (!c.conflictList || M.eq(JSON.parse(JSON.stringify(conflicts)), c.conflictList));
  console.log(ok ? "OK  " : "FAIL", c.name, ok ? "" : `\n  충돌 ${conflicts.length}(기대 ${c.conflicts})\n  결과 ${JSON.stringify(merged)}\n  기대 ${JSON.stringify(c.expect)}`);
  if (!ok) bad++;
  // 장·요소·탭 순서는 키 순서와 달리 뜻이 있다 - 목록 id 순서까지 같은지
  const ids = (d) => JSON.stringify([(d.slides || []).map((s) => [s.id, (s.elements || []).map((e) => e.id)]), (d.sheets || []).map((t) => t.id)]);
  if (ok && ids(merged) !== ids(c.expect)) { console.log("FAIL", c.name, "- 순서가 다름", ids(merged), ids(c.expect)); bad++; }
}
console.log(bad ? `\n실패 ${bad}` : `\n전부 통과 (${cases.length}사례 - deckmerge.py 와 같음)`);
process.exit(bad ? 1 : 0);
