// nexa-doc.js 의 밖의 변경 따라가기(follower · stillChanged) 계산 시험(DOM 없음) - node studio/tests/nexa_follow_check.js
const path = require("path");
const D = require(path.join(__dirname, "..", "nexa-doc.js"));
let fail = 0, n = 0;
const J = JSON.stringify;
const eq = (name, got, want) => { n++; const ok = J(got) === J(want); if (!ok) fail++; console.log(`${ok ? "PASS" : "FAIL"} ${name}${ok ? "" : " :: " + J(got) + " ≠ " + J(want)}`); };
const tick = (ms) => new Promise((r) => setTimeout(r, ms || 0));

/** 시험용 편집기 - 부른 일을 log 에 적는다 */
function make(over = {}) {
  const S = { id: "d1", deck: {}, version: "10", saving: false, dirty: false, conflict: false, savedAt: 0, ...(over.S || {}) };
  const log = [], ver = { deck: "10", deckIds: ["d1"], ...(over.ver || {}) };
  const live = over.live || null;
  const F = D.follower({
    state: S, id: () => S.id, ready: () => !!S.deck, live: () => live,
    api: async (m, u) => { log.push("GET " + u); if (over.apiFail) throw new Error("끊김"); return { ok: true, data: { ...ver } }; },
    before: async (v) => { log.push("before"); if (over.beforeWait) await tick(over.beforeWait); if (over.duringBefore) over.duringBefore(S); },
    gone: over.gone, onGone: () => log.push("gone"), editing: () => !!over.editing,
    save: async () => { log.push("save"); }, reload: async () => { log.push("reload"); S.version = ver.deck; },
    after: async (v, gone) => { log.push("after:" + gone); }, onError: () => log.push("error"),
  });
  return { S, F, log, ver };
}

(async () => {
  { const t = make(); await t.F.poll(); eq("판이 같다 - 아무것도 하지 않는다", t.log, ["GET /api/version/d1", "before", "after:false"]); }
  { const t = make({ ver: { deck: "11" } }); await t.F.poll(); eq("판이 다르고 고치는 중이 아니다 - 다시 읽는다", [t.log.includes("reload"), t.log.includes("save"), t.S.version], [true, false, "11"]); }
  { const t = make({ ver: { deck: "11" }, S: { dirty: true } }); await t.F.poll(); eq("고친 것이 있다 - 저장해서 합친다(다시 읽지 않는다)", [t.log.includes("save"), t.log.includes("reload")], [true, false]); }
  { const t = make({ ver: { deck: "11" }, S: { dirty: true }, editing: true }); await t.F.poll(); eq("치는 중 - 저장도 다시 읽기도 미룬다", [t.log.includes("save"), t.log.includes("reload")], [false, false]); }
  { const t = make({ ver: { deck: "11" }, editing: true }); await t.F.poll(); eq("치는 중(아직 바뀐 것 없음) - 다시 읽지 않는다", t.log.includes("reload"), false); }
  { const t = make({ ver: { deck: "11" }, S: { dirty: true, conflict: true } }); await t.F.poll(); eq("충돌 배너가 떠 있다 - 저장하지 않는다", [t.log.includes("save"), t.log.includes("reload")], [false, false]); }
  { const t = make({ ver: { deck: "11" }, S: { saving: true } }); await t.F.poll(); eq("저장 중 - 손대지 않는다", [t.log.includes("save"), t.log.includes("reload")], [false, false]); }
  { const t = make({ ver: { deck: "0" } }); await t.F.poll(); eq("판 \"0\" = 지워진 문서 - 다시 읽지 않고 알린다", [t.log.includes("reload"), t.log.includes("gone"), t.log.includes("after:true")], [false, true, true]); }
  { const t = make({ ver: { deck: "11", deckIds: ["x"] } }); await t.F.poll(); eq("목록에 없다 = 지워진 문서", [t.log.includes("reload"), t.log.includes("gone")], [false, true]); }
  { const t = make({ ver: { deck: "11" }, gone: () => true }); await t.F.poll(); eq("화면이 지우는 중이라고 한다 - 다시 읽지 않는다", [t.log.includes("reload"), t.log.includes("gone")], [false, true]); }
  { const t = make({ ver: { deck: "11" }, S: { savedAt: Date.now() } }); await t.F.poll(); const first = t.log.includes("reload"); await tick(1700);
    eq("방금 내 저장이 끝났다 - 바로 다시 읽지 않고 잠시 뒤 다시 확인해 읽는다", [first, t.log.filter((x) => x.startsWith("GET")).length, t.log.includes("reload")], [false, 2, true]); }
  { const t = make({ ver: { deck: "11" }, beforeWait: 30, duringBefore: (S) => { S.saving = true; } }); await t.F.poll(); eq("기다리는 사이 저장이 시작됐다 - 다시 읽지 않는다(낡은 판)", t.log.includes("reload"), false); }
  { const t = make({ ver: { deck: "11" }, beforeWait: 40 }); const a = t.F.apply({ deck: "11", deckIds: ["d1"] }); t.F.apply({ deck: "12", deckIds: ["d1"] }); t.F.apply({ deck: "13", deckIds: ["d1"] }); await a;
    eq("처리 중에 온 판 - 마지막 하나만 이어서 한다", t.log.filter((x) => x === "before").length, 2); }
  { const live = { healthy: () => true }; const t = make({ live }); await t.F.poll(); await t.F.poll(); await t.F.poll(true);
    eq("실시간 연결이 건강하다 - 폴링은 15초 안전망만(강제는 바로)", t.log.filter((x) => x.startsWith("GET")).length, 2); }
  { const t = make({ apiFail: true }); await t.F.poll(); eq("서버 끊김 - onError", t.log.includes("error"), true); }
  { const t = make({ S: { deck: null } }); await t.F.poll(); await t.F.apply({ deck: "11" }); eq("문서를 열기 전 - 아무것도 하지 않는다", t.log, []); }
  { const S = { saving: false, dirty: false, savedAt: 0 }; let later = 0;
    eq("stillChanged - 기본 true · 저장 중/고친 것/skip 이면 false", [D.stillChanged(S), D.stillChanged({ ...S, saving: true }), D.stillChanged({ ...S, dirty: true }), D.stillChanged(S, null, () => true)], [true, false, false, false]);
    const r = D.stillChanged({ ...S, savedAt: Date.now() - 1400 }, () => { later++; }); await tick(300); eq("stillChanged - 저장 뒤 1.5초 안이면 false 이고 남은 시간 뒤 later", [r, later], [false, 1]); }
  console.log(`RESULT ${fail ? "FAIL" : "PASS"} ${n - fail}/${n}`);
  process.exit(fail ? 1 : 0);
})();
