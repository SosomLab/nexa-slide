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
// 저장 방식 고르기(planSave)·보내기(saveOps) - 화면 저장이 부른다(3-4 다)
const check = (name, ok, info) => { if (!ok) { bad++; console.log("FAIL", name, info === undefined ? "" : JSON.stringify(info).slice(0, 400)); } };
{
  const big = { title: "t", slides: [{ id: "s1", elements: [{ id: "e1", text: "a", x: 1 }, { id: "e2", text: "x".repeat(300000) }] }] };
  const S = JSON.stringify(big), n1 = JSON.parse(S); n1.slides[0].elements[0].text = "b"; n1.slides[0].elements[0].x = 7;
  const p = M.planSave(S, JSON.stringify(n1));
  check("planSave - 큰 문서·작업 2개 → ops", p.mode === "ops" && p.ops.length === 2 && p.ops[0].key === "geom", p);
  check("planSave - 같으면 none", M.planSave(S, S).mode === "none");
  check("planSave - 저장본 없음 → put", M.planSave(null, S).mode === "put");
  check("planSave - 작은 문서 → put", M.planSave(JSON.stringify({ slides: [] }), JSON.stringify({ slides: [{ id: "a", elements: [] }] })).mode === "put");
  check("planSave - 구조 작업 → put", M.planSave(S, JSON.stringify(n1), { struct: [{ op: "insertRows" }] }).mode === "put");
  const many = JSON.parse(S); for (let k = 0; k < 250; k++) many.slides.push({ id: "n" + k, elements: [] });
  check("planSave - 작업 200개 넘음 → put", M.planSave(S, JSON.stringify(many)).mode === "put");
  const dup = JSON.parse(S); dup.slides[0].elements.push({ id: "e1", text: "같은 id" });
  check("planSave - 작업으로 같아지지 않음(같은 id 둘) → put", M.planSave(S, JSON.stringify(dup)).mode === "put", M.planSave(S, JSON.stringify(dup)).why);
}
(async () => {
  const fake = (status, data) => async (method, url, body) => { fake.last = { method, url, body }; return { ok: status < 300, status, data }; };
  let api = fake(200, { ok: true, version: "v2", applied: 1, dropped: [] });
  const r1 = await M.saveOps(api, "덱 1", "v1", [{ op: "deck-set", key: "a", value: 1 }]);
  check("saveOps - POST /api/ops/<덱> {base, ops} → 응답", r1 && r1.version === "v2" && fake.last.method === "POST" && fake.last.url === "/api/ops/%EB%8D%B1%201" && fake.last.body.base === "v1", fake.last);
  check("saveOps - 서버가 모름(404) → null(PUT 으로)", (await M.saveOps(fake(404, null), "d", "v", [])) === null);
  check("saveOps - 거절(400) → null", (await M.saveOps(fake(400, { ok: false }), "d", "v", [])) === null);
  const r5 = await M.saveOps(fake(500, { error: "x" }), "d", "v", []);
  check("saveOps - 서버 오류(500) → {ok:false}", r5 && r5.ok === false && r5.status === 500, r5);
  console.log(bad ? `\n실패 ${bad}` : `전부 통과 (${cases.length}사례 - deckops.py 와 같음 · 저장 방식 11)`);
  process.exit(bad ? 1 : 0);
})();
