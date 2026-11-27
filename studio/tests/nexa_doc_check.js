// nexa-doc.js 자동 저장 상태기계 시험(DOM·서버 없음) - node studio/tests/nexa_doc_check.js
const path = require("path");
globalThis.NexaMerge = { afterSave: (body, now, merged) => ({ ...merged, _now: now !== body }) };
const D = require(path.join(__dirname, "..", "nexa-doc.js"));
let fail = 0, n = 0;
const check = (name, ok, detail) => { n++; if (!ok) fail++; console.log(`${ok ? "PASS" : "FAIL"} ${name}${ok ? "" : " :: " + JSON.stringify(detail)}`); };
const tick = (ms) => new Promise((r) => setTimeout(r, ms));

function setup(reply, opts = {}) {
  const S = { deck: { a: 1 }, version: "v1", savedJson: JSON.stringify({ a: 1 }), dirty: false, saving: false, conflict: false };
  const log = { calls: [], status: [], banner: [], toast: [], merged: 0 };
  const api = async (m, url, body) => { log.calls.push({ m, url, body }); if (opts.wait) await tick(opts.wait); return typeof reply === "function" ? reply(log.calls.length, body) : reply; };
  const sv = D.saver({ state: S, api, setStatus: (k, t) => log.status.push(k + ":" + t), banner: (on, t) => log.banner.push(on ? t : false), toast: (t) => log.toast.push(t), id: () => "d 1", json: () => JSON.stringify(S.deck),
    delay: opts.delay || 20, onlyDirty: opts.onlyDirty !== false, beforeMerged: () => "keep", onMerged: (r, b, now, keep) => { log.merged++; log.keep = keep; }, ...(opts.extra || {}) });
  return { S, log, sv };
}

(async () => {
  { const { S, log, sv } = setup({ ok: true, data: { version: "v2" } }); await sv.save();
    check("1 바뀐 것이 없으면 보내지 않는다 · 저장됨", log.calls.length === 0 && log.status.pop() === "saved:저장됨" && S.dirty === false, log); }
  { const { S, log, sv } = setup({ ok: true, data: { version: "v2", updated: "t" } }); S.deck.a = 2; S.dirty = true; await sv.save();
    const c = log.calls[0];
    check("2 병합 저장 - PUT ?base=<읽은 판>&merge=1 · 판·저장본 갱신 · dirty 풀림", c.m === "PUT" && c.url === "/api/deck/d%201?base=v1&merge=1" && c.body.a === 2 && S.version === "v2" && S.dirty === false && S.deck.updated === "t" && S.savedJson === JSON.stringify(S.deck) && log.banner[0] === false, { c, S }); }
  { const { S, log, sv } = setup({ ok: true, data: { version: "v2" } }, { wait: 30 }); S.deck.a = 2; S.dirty = true; const p = sv.save(); S.deck.a = 3; await p; await tick(120);
    check("3 저장하는 사이 더 고치면 - 저장본은 보낸 것 · dirty 남음 · 다시 예약되어 두 번째 저장", log.calls.length === 2 && log.calls[1].body.a === 3 && S.dirty === false, { n: log.calls.length, S }); }
  { const { S, log, sv } = setup({ ok: true, data: { version: "v2" } }, { wait: 40 }); S.deck.a = 2; S.dirty = true; const p = sv.save(); await sv.save(); const during = log.calls.length; await p;
    check("4 저장 중에 또 부르면 보내지 않고 다시 예약만", during === 1, during); }
  { const { S, log, sv } = setup({ ok: true, data: { version: "v3", merged: true, deck: { a: 2, b: 9 }, conflicts: [] } }); S.deck.a = 2; S.dirty = true; await sv.save();
    check("5 합쳐진 응답 - 저장본 = 서버 결과 · 화면 반영 훅(beforeMerged 의 값 전달) · 판", log.merged === 1 && log.keep === "keep" && S.version === "v3" && S.savedJson === JSON.stringify({ a: 2, b: 9 }) && S.deck.b === 9, { S, log }); }
  { const { S, log, sv } = setup({ ok: false, status: 409, data: {} }); S.deck.a = 2; S.dirty = true; await sv.save(); await sv.save();
    check("6 409 - 충돌 상태·배너 · 충돌 중에는 다시 보내지 않는다", S.conflict === true && log.calls.length === 1 && typeof log.banner[0] === "string" && log.status.pop() === "conflict:충돌" && S.saving === false, { S, log }); }
  { const { S, log, sv } = setup({ ok: true, data: { version: "v5" } }); S.deck.a = 2; S.dirty = true; S.conflict = true; await sv.save(true);
    check("7 force - 충돌 중에도 보낸다(&force=1) · 충돌 풀림", log.calls.length === 1 && /&force=1$/.test(log.calls[0].url) && S.conflict === false, { S, log }); }
  { const { S, log, sv } = setup({ ok: false, status: 500, data: { error: "boom" } }); S.deck.a = 2; S.dirty = true; await sv.save();
    check("8 그 밖의 실패 - 상태 '저장 실패' · 알림 · dirty 유지", log.status.pop() === "error:저장 실패" && /boom/.test(log.toast[0]) && S.dirty === true && S.saving === false, { S, log }); }
  { const { S, log, sv } = setup({ ok: true, data: { version: "v2" } }); sv.schedule(); await tick(60); const a = log.calls.length; S.deck.a = 2; S.dirty = true; sv.schedule(); sv.schedule(); await tick(80);
    check("9 예약 - 고친 것이 없으면 예약하지 않는다(onlyDirty) · 여러 번 예약해도 한 번 저장", a === 0 && log.calls.length === 1, { a, n: log.calls.length }); }
  { const { S, log, sv } = setup({ ok: true, data: { version: "v2" } }); S.deck.a = 2; S.dirty = true; sv.schedule(); sv.cancel(); await tick(60);
    check("10 cancel - 예약한 저장을 멈춘다", log.calls.length === 0, log.calls.length); }
  { const { S, log, sv } = setup({ ok: true, data: { version: "v2" } }); S.deck = null; await sv.save(true);
    check("11 문서를 읽기 전에는 저장하지 않는다", log.calls.length === 0, log.calls.length); }
  console.log(`RESULT ${fail ? "FAIL" : "PASS"} ${n - fail}/${n}`);
  process.exit(fail ? 1 : 0);
})();
