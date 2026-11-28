// nexa-doc.js 의 실행 취소 기록(history) 계산 시험(DOM 없음) - node studio/tests/nexa_history_check.js
const path = require("path");
const D = require(path.join(__dirname, "..", "nexa-doc.js"));
const M = require(path.join(__dirname, "..", "nexa-merge.js"));
let fail = 0, n = 0;
const J = JSON.stringify;
const eq = (name, got, want) => { n++; const ok = J(got) === J(want); if (!ok) fail++; console.log(`${ok ? "PASS" : "FAIL"} ${name}${ok ? "" : " :: " + J(got) + " ≠ " + J(want)}`); };
const tick = (ms) => new Promise((r) => setTimeout(r, ms || 0));
const merge3 = M.merge3 || (globalThis.NexaMerge && globalThis.NexaMerge.merge3);

/** 시험용 문서 - 요소 둘(a · b)의 글. sel 을 주면 선택도 같이 적는 편집기(페이지) */
function make(over = {}) {
  const S = { undo: [], redo: [], deck: { slides: [{ id: "s1", elements: [{ id: "a", text: "A0" }, { id: "b", text: "B0" }] }] } };
  const log = []; let sel = "sel0";
  const H = D.history({
    state: S, json: () => J(S.deck), max: over.max, merge3,
    selection: over.sel ? () => sel : undefined, join: over.join, beforePush: (w) => log.push("warn"),
    apply: (deck, s, dir) => { S.deck = deck; log.push(dir + ":" + (s === undefined ? "-" : s)); }, onChange: () => log.push("chg"),
  });
  const set = (id, t, why) => { H.push(why); S.deck.slides[0].elements.find((e) => e.id === id).text = t; };
  const txt = () => S.deck.slides[0].elements.map((e) => e.text).join(",");
  return { S, H, log, set, txt, setSel: (v) => { sel = v; } };
}

(async () => {
  { const t = make(); t.set("a", "A1"); t.set("a", "A2"); const r1 = t.H.undo(), x1 = t.txt(), r2 = t.H.undo(), x2 = t.txt(), r3 = t.H.undo();
    eq("되돌리기 - 한 단계씩 · 기록이 없으면 false", [r1, x1, r2, x2, r3, t.S.redo.length], [true, "A1,B0", true, "A0,B0", false, 2]); }
  { const t = make(); t.set("a", "A1"); t.H.undo(); const r = t.H.redo(), x = t.txt(); t.H.undo(); t.set("b", "B1");
    eq("다시 실행 · 새로 고치면 다시 실행 기록이 비워진다", [r, x, t.S.redo.length, t.S.undo.length], [true, "A1,B0", 0, 1]); }
  { const t = make(); t.set("a", "A1"); eq("기록 항목 = 문자열(선택을 안 적는 편집기) · 기록 직전 경고 훅 · 단추 갱신", [typeof t.S.undo[0], t.log], ["string", ["warn", "chg"]]); }
  { const t = make({ sel: true }); t.set("a", "A1"); t.setSel("sel1"); t.H.undo(); const u = t.log.find((x) => x.startsWith("undo")); t.H.redo(); const r = t.log.find((x) => x.startsWith("redo"));
    eq("선택을 같이 적는다 - 되돌리면 그때의 선택 · 다시 실행하면 되돌리기 직전의 선택", [u, r, typeof t.S.undo[0]], ["undo:sel0", "redo:sel1", "object"]); }
  { const t = make({ max: 3 }); for (let i = 1; i <= 5; i++) t.set("a", "A" + i); eq("상한 - 오래된 것부터 버린다", [t.S.undo.length, JSON.parse(t.S.undo[0]).slides[0].elements[0].text], [3, "A2"]); }
  { const typing = (w) => w === "type" || w === "ime"; const t = make({ join: (w, l, dt) => typing(w) && typing(l) && dt < 80 });
    t.set("a", "A1", "type"); t.set("a", "A2", "ime"); t.set("a", "A3", "type"); const n1 = t.S.undo.length; await tick(120); t.set("a", "A4", "type"); const n2 = t.S.undo.length; t.set("a", "A5", "format"); t.set("a", "A6", "type");
    eq("이어 친 글은 한 묶음 - 시간이 지나거나 다른 일이 끼면 새 단계", [n1, n2, t.S.undo.length], [1, 2, 4]);
    t.H.undo(); t.set("a", "X", "type"); eq("되돌린 뒤 첫 타이핑은 앞 묶음에 붙지 않는다", t.S.undo.length, 4); }
  { const t = make(); t.set("a", "A1");  // 내 편집 뒤 남이 b 를 고친다
    t.H.seal(J(t.S.deck)); t.S.deck.slides[0].elements[1].text = "B남"; t.H.undo();
    eq("봉인 - 되돌려도 남의 변경은 남는다(내 편집만 거꾸로)", [t.txt(), t.S.redo.length], ["A0,B남", 1]); }
  { const t = make(); t.set("a", "A1"); t.set("b", "B1"); t.H.seal(J(t.S.deck)); t.S.deck.slides[0].elements[0].text = "A남";  // 남이 a 를 다시 고침
    t.H.undo(); const x1 = t.txt(); t.H.undo(); const x2 = t.txt();
    eq("봉인 여러 단계 - 각 단계의 '편집 뒤'는 다음 기록의 '편집 앞' · 같은 곳을 남도 고쳤으면 되돌리는 내 쪽이 이긴다", [x1, x2], ["A남,B0", "A0,B0"]); }
  { const t = make(); t.set("a", "A1"); t.H.seal(J(t.S.deck)); const a1 = t.S.undo[0].a; t.set("b", "B1"); t.H.seal(J(t.S.deck));
    eq("두 번 봉인 - 이미 봉인된 항목은 그대로 · 새 항목만 봉인", [t.S.undo[0].a === a1, typeof t.S.undo[1], t.S.undo[1].a === J(t.S.deck)], [true, "object", true]); }
  { const t = make({ sel: true }); t.set("a", "A1"); t.H.seal(J(t.S.deck)); t.S.deck.slides[0].elements[1].text = "B남"; t.H.undo();
    eq("봉인 + 선택 - 선택도 돌아온다", [t.txt(), t.log.filter((x) => x.startsWith("undo"))], ["A0,B남", ["undo:sel0"]]); }
  { const t = make(); t.set("a", "A1"); t.H.undo(); t.set("a", "A2"); t.H.undo(); t.H.seal(J(t.S.deck)); eq("봉인하면 다시 실행 기록은 비운다", t.S.redo.length, 0); }
  { const t = make(); const before = J(t.S.deck); t.S.deck.slides[0].elements[0].text = "끈뒤"; t.H.push("drag", before); const w = t.log.includes("warn"); t.H.undo();
    eq("미리 잡아 둔 직전 문서 넣기(끌기·글 편집) - 경고 훅은 부르지 않는다", [w, t.txt()], [false, "A0,B0"]); }
  { const t = make(); t.set("a", "A1"); t.S.deck.slides[0].elements[0].text = "A0"; t.H.drop(); eq("drop - 방금 넣은 기록을 없던 일로(다시 실행에 남기지 않는다)", [t.S.undo.length, t.S.redo.length], [0, 0]); }
  { const t = make(); t.set("a", "A1"); t.H.undo(); const c1 = t.H.can(); t.H.reset(); eq("can · reset", [c1, t.H.can()], [{ undo: false, redo: true }, { undo: false, redo: false }]); }
  { const t = make(); t.set("a", "A1"); t.S.undo = []; t.S.redo = []; t.set("a", "A2"); t.H.undo();
    eq("화면이 S.undo 를 새 배열로 갈아도(문서를 새로 열 때) 그 배열을 쓴다", [t.txt(), t.S.undo.length, t.S.redo.length], ["A1,B0", 0, 1]); }
  console.log(`RESULT ${fail ? "FAIL" : "PASS"} ${n - fail}/${n}`);
  process.exit(fail ? 1 : 0);
})();
