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
  // 화면 저장의 작업 저장 시도(trySaveOps) - PUT 응답과 같은 꼴로 돌려주거나 null(화면이 PUT ?merge=1 로)
  {
    const big = { title: "t", slides: [{ id: "s1", elements: [{ id: "e1", text: "a" }, { id: "e2", text: "x".repeat(300000) }] }] };
    const saved = JSON.stringify(big), n = JSON.parse(saved); n.slides[0].elements[0].text = "b"; const now = JSON.stringify(n);
    const t1 = await M.trySaveOps(fake(200, { ok: true, version: "v2", applied: 1, dropped: [] }), "d", "v1", saved, now);
    check("trySaveOps - 작업 저장 성공 → {ok, status 200, viaOps, data}(merged 없음)", t1 && t1.ok && t1.status === 200 && t1.viaOps && t1.data.version === "v2" && !t1.data.merged && fake.last.url === "/api/ops/d" && fake.last.body.ops.length === 1, t1);
    const t2 = await M.trySaveOps(fake(200, { ok: true, version: "v3", applied: 1, dropped: [{ i: 0 }], stale: true, deck: big }), "d", "v1", saved, now);
    check("trySaveOps - 서버가 deck 을 주면 merged:true · conflicts [] (PUT 병합 응답과 같은 꼴)", t2 && t2.data.merged === true && Array.isArray(t2.data.conflicts) && !t2.data.conflicts.length && t2.data.deck === big, t2);
    check("droppedNotice - 버린 작업 n건 문구 · 없으면 빈 글", /반영되지 않은 변경 1건/.test(M.droppedNotice(t2.data)) && M.droppedNotice(t1.data) === "" && M.droppedNotice(null) === "");
    check("trySaveOps - 404 → null(PUT 으로)", (await M.trySaveOps(fake(404, null), "d", "v1", saved, now)) === null);
    check("trySaveOps - 500 → null(PUT 이 다시 합친다)", (await M.trySaveOps(fake(500, { error: "x" }), "d", "v1", saved, now)) === null);
    check("trySaveOps - 판 없는 응답 → null", (await M.trySaveOps(fake(200, { ok: true }), "d", "v1", saved, now)) === null);
    let called = 0; const spy = async () => { called++; return { ok: true, status: 200, data: { ok: true, version: "v9" } }; };
    const small = JSON.stringify({ slides: [{ id: "s", elements: [{ id: "e", text: "a" }] }] }), small2 = small.replace('"a"', '"b"');
    check("trySaveOps - 작은 문서 → null · 요청 없음", (await M.trySaveOps(spy, "d", "v1", small, small2)) === null && called === 0);
    globalThis.__nxOpsMin = 0;
    const t3 = await M.trySaveOps(spy, "d", "v1", small, small2);
    delete globalThis.__nxOpsMin;
    check("trySaveOps - window.__nxOpsMin = 0 이면 작은 문서도 작업 저장", t3 && t3.viaOps && called === 1, t3);
    const ko = JSON.stringify({ slides: [{ id: "s", elements: [{ id: "e", text: "a" }, { id: "k", text: "가".repeat(80000) }] }] }), ko2 = ko.replace('"a"', '"b"');  // 글자 8만(문턱 아래) · UTF-8 24만 바이트(위)
    check("planSave - 문턱은 UTF-8 바이트: 글자 수는 문턱 아래지만 바이트는 위인 한글 문서 → ops", ko.length < 200000 && M.planSave(ko, ko2).mode === "ops", M.planSave(ko, ko2).why);
    check("trySaveOps - 같은 내용 → null · 구조 작업 → null", (await M.trySaveOps(spy, "d", "v1", saved, saved)) === null && (await M.trySaveOps(spy, "d", "v1", saved, now, { struct: [{ op: "insertRows" }] })) === null && called === 1);
  }
  console.log(bad ? `\n실패 ${bad}` : `전부 통과 (${cases.length}사례 - deckops.py 와 같음 · 저장 방식 21)`);
  process.exit(bad ? 1 : 0);
})();
