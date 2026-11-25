// 화면 병합(nexa-merge.js)이 페이지 문서에서 서버 병합(deckmerge.py)과 같은 결과인지 - node studio/tests/pagemerge_check.js
//   사례와 서버 결과는 tests/pagemerge_test.py --dump 가 낸다(자식 파이썬). 객체 키 순서는 보지 않고, 블록·행·칸의 id 순서는 본다.
const { spawnSync } = require("child_process");
const path = require("path");
require(path.join(__dirname, "..", "nexa-merge.js"));
const M = globalThis.NexaMerge;
const r = spawnSync(process.env.NEXA_PYTHON || "python", [path.join(__dirname, "pagemerge_test.py"), "--dump"], { encoding: "utf8", maxBuffer: 64 * 1024 * 1024, shell: process.platform === "win32" && !process.env.NEXA_PYTHON });
let cases;
try { cases = JSON.parse(r.stdout); } catch (e) { console.log("FAIL 서버 사례를 불러오지 못했다: " + String(r.stderr || r.error || r.stdout).slice(0, 300)); process.exit(1); }
const order = (d) => JSON.stringify([(d.blocks || []).map((b) => [b.id, (b.rows || []).map((row) => [row.id, (row.cells || []).map((c) => [c.id, (c.blocks || []).map((x) => x.id)])])]), ((d.page || {}).header || {}).blocks]);
let bad = 0;
for (const c of cases) {
  const ins = JSON.stringify([c.base, c.ours, c.theirs]);
  const { merged, conflicts } = M.merge3(c.base, c.ours, c.theirs, c.prefer);
  const ok = c.ok && M.eq(merged, c.merged) && conflicts.length === c.conflicts && order(merged) === order(c.merged) && JSON.stringify([c.base, c.ours, c.theirs]) === ins;
  if (!ok) { bad++; console.log(`FAIL ${c.name}\n  서버 통과 ${c.ok} · 충돌 ${conflicts.length}(서버 ${c.conflicts})\n  화면 ${order(merged)}\n  서버 ${order(c.merged)}`); }
}
console.log(bad ? `\n실패 ${bad}` : `\n전부 통과 (${cases.length}사례 - deckmerge.py 와 같음)`);
process.exit(bad ? 1 : 0);
