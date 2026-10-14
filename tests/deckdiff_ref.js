// 0.15.3 편집기(studio.js 154-197 · 1016-1019 · render.js runs/plain)의 덱 비교 함수를 그대로 꺼낸 기준 구현.
// studio/deckdiff.py 로 옮길 때 동일성을 확인하는 데만 쓴다(check_changes.py --js). 편집기는 더 이상 이 코드를 쓰지 않는다.
"use strict";
const MARK = /\*\*(.+?)\*\*|==(.+?)==|\[\[([#\w-]+)\|(.+?)\]\]/g;
function runs(text) {
  const s = String(text == null ? "" : text);
  const out = []; let pos = 0, m; MARK.lastIndex = 0;
  while ((m = MARK.exec(s))) {
    if (m.index > pos) out.push([s.slice(pos, m.index), {}]);
    if (m[1] !== undefined) out.push([m[1], {}]); else if (m[2] !== undefined) out.push([m[2], {}]); else out.push([m[4], {}]);
    pos = MARK.lastIndex;
  }
  if (pos < s.length) out.push([s.slice(pos), {}]);
  return out.length ? out : [["", {}]];
}
const plain = (s) => runs(s).map((r) => r[0]).join("");
const GEO = new Set(["x", "y", "w", "h", "x1", "y1", "x2", "y2", "z", "rot"]);
const TXT = new Set(["text", "rows", "header", "items", "code", "lines", "cells", "label", "title", "sub"]);
const short = (v, n = 60) => { const t = plain(typeof v === "string" ? v : JSON.stringify(v ?? "")).replace(/\s+/g, " ").trim(); return t.length > n ? t.slice(0, n) + "…" : t; };
function slideTitle(s) {
  const t = s.elements.find((e) => e.role === "title") || s.elements.find((e) => e.type === "text" && (e.size || 20) >= 28);
  return t ? plain(String(t.text || "")).replace(/\n/g, " ") : `(${s.layout || "슬라이드"})`;
}
function diffEl(a, b) {
  const keys = new Set([...Object.keys(a), ...Object.keys(b)]), kinds = new Set();
  let before = "", after = "";
  for (const k of keys) {
    if (k === "id" || JSON.stringify(a[k]) === JSON.stringify(b[k])) continue;
    if (GEO.has(k)) kinds.add("위치·크기");
    else if (TXT.has(k)) { kinds.add("글자"); if (!before && !after) { before = short(a[k]); after = short(b[k]); } }
    else if (k === "src") kinds.add("그림");
    else kinds.add("모양");
  }
  return kinds.size ? { kinds: [...kinds], before, after } : null;
}
function diffDeck(old, nw) {
  const om = new Map(old.slides.map((s, i) => [s.id, [s, i]])), nm = new Map(nw.slides.map((s, i) => [s.id, [s, i]]));
  const oc = old.slides.filter((s) => nm.has(s.id)).map((s) => s.id), np = new Map(nw.slides.filter((s) => om.has(s.id)).map((s, i) => [s.id, i]));
  const seq = oc.map((id) => np.get(id)), tails = [], prev = new Array(seq.length);
  seq.forEach((v, i) => {
    let lo = 0, hi = tails.length; while (lo < hi) { const m = (lo + hi) >> 1; if (seq[tails[m]] < v) lo = m + 1; else hi = m; }
    prev[i] = lo ? tails[lo - 1] : -1; tails[lo] = i;
  });
  const stable = new Set(); for (let i = tails.length ? tails[tails.length - 1] : -1; i >= 0; i = prev[i]) stable.add(oc[i]);
  const items = [];
  nw.slides.forEach((s, i) => {
    if (!om.has(s.id)) { items.push({ sid: s.id, idx: i, kind: "추가", moved: null, title: slideTitle(s), els: [], extra: [] }); return; }
    const [o, oi] = om.get(s.id), els = [], extra = [];
    const oe = new Map((o.elements || []).map((e) => [e.id, e])), ne = new Map((s.elements || []).map((e) => [e.id, e]));
    for (const e of s.elements || []) {
      if (!oe.has(e.id)) els.push({ id: e.id, kinds: ["추가"], before: "", after: short(e.text || e.src || e.type) });
      else { const d = diffEl(oe.get(e.id), e); if (d) els.push({ id: e.id, ...d }); }
    }
    for (const e of o.elements || []) if (!ne.has(e.id)) els.push({ id: e.id, kinds: ["삭제"], before: short(e.text || e.src || e.type), after: "", gone: true });
    if (JSON.stringify(o.notes ?? "") !== JSON.stringify(s.notes ?? "")) extra.push("노트");
    for (const k of ["layout", "bg", "part"]) if (JSON.stringify(o[k]) !== JSON.stringify(s[k])) extra.push(k === "bg" ? "바탕" : k === "layout" ? "레이아웃" : "부");
    const moved = !stable.has(s.id);
    if (els.length || extra.length || moved)
      items.push({ sid: s.id, idx: i, kind: els.length || extra.length ? "수정" : "이동", moved: moved ? [oi + 1, i + 1] : null, title: slideTitle(s), els, extra });
  });
  old.slides.forEach((s, i) => { if (!nm.has(s.id)) items.push({ sid: s.id, idx: i, kind: "삭제", moved: null, title: slideTitle(s), els: [], extra: [], gone: true }); });
  return items;
}
module.exports = { diffDeck, diffEl, short, slideTitle, plain };
if (require.main === module) {
  const inp = JSON.parse(require("fs").readFileSync(0, "utf8"));
  process.stdout.write(JSON.stringify(inp.map(([o, n]) => diffDeck(o, n))));
}
