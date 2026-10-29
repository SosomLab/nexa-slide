/* nexa-slide 덱·시트 3-way 병합 - 서버 deckmerge.py 와 같은 규칙(docs/collab.md 1단계). 편집기·시트 화면이 같이 쓴다.
     NexaMerge.merge3(base, ours, theirs, prefer)  → { merged, conflicts }
   화면에서는 "남의 변경을 건드리지 않는 실행 취소"에 쓴다: 되돌릴 내 편집(편집 뒤 → 편집 앞)을 지금 문서 위에 병합한다.
   규칙·사례는 deckmerge.py 머리말과 tests/deckmerge_cases.json(tests/nexa_merge_check.js 가 같은지 확인).
     NexaMerge.ops(saved, now) · applyOps(doc, ops, base)  작업(op) 저장 - 서버 deckops.py 와 같다(tests/deckops_cases.json, nexa_ops_check.js · 동시 편집 3-4). */
(function (root) {
  "use strict";
  const MISSING = { missing: true };  // 없는 키·항목
  const GEOM = ["x", "y", "w", "h", "rot"];  // 요소의 위치·크기 - 한 묶음
  const SKIP_TOP = ["updated"];
  const clone = (x) => (x === undefined ? undefined : JSON.parse(JSON.stringify(x)));
  /** 같은 JSON 값인지 - 객체 키 순서는 상관없다(Python == 과 같게) */
  function eq(a, b) {
    if (a === MISSING || b === MISSING) return a === b;
    if (a === b) return true;
    if (typeof a !== typeof b || a === null || b === null || typeof a !== "object") return false;
    if (Array.isArray(a) !== Array.isArray(b)) return false;
    if (Array.isArray(a)) return a.length === b.length && a.every((x, i) => eq(x, b[i]));
    const ka = Object.keys(a), kb = Object.keys(b);
    return ka.length === kb.length && ka.every((k) => Object.prototype.hasOwnProperty.call(b, k) && eq(a[k], b[k]));
  }
  const isObj = (x) => x && typeof x === "object" && !Array.isArray(x) && x !== MISSING;
  const get = (d, k) => (isObj(d) && Object.prototype.hasOwnProperty.call(d, k) ? d[k] : MISSING);
  const orNull = (x) => (x === MISSING ? null : x);

  function M(prefer) {
    const conflicts = [];
    function val(path, b, o, t) {
      if (eq(o, t)) return o;
      if (eq(o, b)) return t;
      if (eq(t, b)) return o;
      conflicts.push({ path, kept: prefer, ours: orNull(o), theirs: orNull(t) });
      return prefer === "ours" ? o : t;
    }
    function keys(path, b, o, t, special, groups) {
      special = special || {}; groups = groups || [];
      [b, o, t] = [b, o, t].map((x) => (isObj(x) ? x : {}));
      const out = {}, grouped = new Set(groups.flat());
      for (const g of groups) {
        const pick = (d) => g.map((k) => get(d, k));
        const n = conflicts.length;
        const r = val(`${path}/${g.join("·")}`, pick(b), pick(o), pick(t));
        for (const c of conflicts.slice(n)) {  // 충돌 기록에는 묶음을 {키: 값}(없는 키는 뺌)으로 - deckmerge.py 와 같게
          for (const [side, d] of [["ours", o], ["theirs", t]]) c[side] = Object.fromEntries(g.filter((k) => get(d, k) !== MISSING).map((k) => [k, d[k]]));
        }
        g.forEach((k, n) => { if (r[n] !== MISSING) out[k] = r[n]; });
      }
      const order = [...Object.keys(t), ...Object.keys(o).filter((k) => !(k in t)), ...Object.keys(b).filter((k) => !(k in t) && !(k in o))];
      for (const k of order) {
        if (grouped.has(k) || k in out) continue;
        const bv = get(b, k), ov = get(o, k), tv = get(t, k);
        const r = special[k] ? special[k](`${path}/${k}`, bv, ov, tv) : val(`${path}/${k}`, bv, ov, tv);
        if (r !== MISSING) out[k] = r;
      }
      const res = {};
      for (const k of [...order, ...Object.keys(out).filter((k) => !order.includes(k))]) if (k in out) res[k] = out[k];
      return res;
    }
    function ilist(path, b, o, t, item) {
      const lists = [b, o, t].map((x) => (Array.isArray(x) ? x : []));
      if (lists.some((L) => L.some((x) => !isObj(x) || !x.id))) return val(path, b, o, t);
      const [bi, oi, ti] = lists.map((L) => new Map(L.map((x) => [x.id, x])));
      const kept = new Map();
      const all = [...ti.keys(), ...[...oi.keys()].filter((i) => !ti.has(i)), ...[...bi.keys()].filter((i) => !ti.has(i) && !oi.has(i))];
      for (const i of all) {
        const bx = bi.has(i) ? bi.get(i) : MISSING, ox = oi.has(i) ? oi.get(i) : MISSING, tx = ti.has(i) ? ti.get(i) : MISSING, p = `${path}/${i}`;
        if (bx === MISSING) kept.set(i, ox !== MISSING && tx !== MISSING ? item(p, {}, ox, tx) : (ox !== MISSING ? ox : tx));
        else if (ox === MISSING && tx === MISSING) continue;
        else if (ox === MISSING || tx === MISSING) {
          const other = ox === MISSING ? tx : ox;
          if (eq(other, bx)) continue;
          conflicts.push({ path: p, kept: ox === MISSING ? "theirs" : "ours", ours: ox === MISSING ? null : "(수정)", theirs: tx === MISSING ? null : "(수정)", rule: "삭제 대 수정 - 수정을 남김" });
          kept.set(i, other);
        } else kept.set(i, item(p, bx, ox, tx));
      }
      const [idsB, idsO, idsT] = lists.map((L) => L.map((x) => x.id));
      const common = idsB.filter((i) => oi.has(i) && ti.has(i));
      const rel = (ids) => ids.filter((i) => common.includes(i));
      const movedO = !eq(rel(idsO), common), movedT = !eq(rel(idsT), common);
      const [primary, other] = movedO && !movedT ? [idsO, idsT] : [idsT, idsO];
      const seq = primary.filter((i) => kept.has(i));
      for (const src of [other, idsB]) src.forEach((i, n) => {
        if (!kept.has(i) || seq.includes(i)) return;
        let prev = null; for (let m = n - 1; m >= 0; m--) if (seq.includes(src[m])) { prev = src[m]; break; }
        seq.splice(prev ? seq.indexOf(prev) + 1 : 0, 0, i);
      });
      return seq.map((i) => clone(kept.get(i)));
    }
    const element = (p, b, o, t) => keys(p, b, o, t, null, [GEOM]);
    const slide = (p, b, o, t) => keys(p, b, o, t, { elements: (pp, ...x) => ilist(pp, ...x.map((v) => (v === MISSING ? [] : v)), element) });
    function cellParts(raw) {
      if (raw === MISSING || raw == null) return [null, {}];
      const o = isObj(raw) ? raw : { v: raw };
      const fmt = {}; for (const [k, v] of Object.entries(o)) if (k !== "v" && k !== "f") fmt[k] = v;
      if (o.f) return [["f", o.f, o.v === undefined ? null : o.v], fmt];
      return [("v" in o) ? ["v", o.v] : null, fmt];
    }
    function cell(path, b, o, t) {
      const [[bc, bf], [oc, of], [tc, tf]] = [b, o, t].map(cellParts);
      const key = (c) => (c == null ? null : c.slice(0, 2));
      const kc = val(`${path}/내용`, key(bc), key(oc), key(tc));
      let content = kc == null ? null : [oc, tc, bc].find((c) => c != null && eq(c.slice(0, 2), kc));
      if (content && content[0] === "f" && oc && tc && eq(oc.slice(0, 2), kc) && eq(tc.slice(0, 2), kc)) {
        // 같은 수식 - 계산값(v)은 캐시라 충돌로 치지 않고, 기준에서 바뀐 쪽(새로 계산한 쪽)을 쓴다
        const bv = bc && eq(bc.slice(0, 2), kc) ? bc[2] : null;
        content = ["f", kc[1], eq(oc[2], bv) ? tc[2] : oc[2]];
      }
      const out = { ...keys(path, bf, of, tf) };
      if (content) {
        if (content[0] === "f") { out.f = content[1]; if (content[2] != null) out.v = content[2]; } else out.v = content[1];
      }
      const ks = Object.keys(out);
      if (!ks.length) return MISSING;
      return ks.length === 1 && ks[0] === "v" ? out.v : out;
    }
    function cells(path, b, o, t) {
      [b, o, t] = [b, o, t].map((x) => (isObj(x) ? x : {}));
      const out = {};
      for (const k of [...Object.keys(t), ...Object.keys(o).filter((k) => !(k in t)), ...Object.keys(b).filter((k) => !(k in t) && !(k in o))]) {
        const r = cell(`${path}/${k}`, get(b, k), get(o, k), get(t, k)); if (r !== MISSING) out[k] = r;
      }
      return out;
    }
    const one = (p, ...x) => keys(p, ...x.map((v) => (v === MISSING ? {} : v)));
    const tab = (p, b, o, t) => keys(p, b, o, t, { cells, cols: one, rows: one });
    function deck(b, o, t) {
      [b, o, t] = [b, o, t].map((x) => (isObj(x) ? x : {}));
      const strip = (d) => { const r = {}; for (const [k, v] of Object.entries(d)) if (!SKIP_TOP.includes(k)) r[k] = v; return r; };
      const lst = (item) => (p, ...x) => ilist(p, ...x.map((v) => (v === MISSING ? [] : v)), item);
      const res = keys("", strip(b), strip(o), strip(t), { slides: lst(slide), sheets: lst(tab) });
      for (const k of SKIP_TOP) if (k in o) res[k] = o[k];
      return res;
    }
    return { deck, conflicts };
  }

  function merge3(base, ours, theirs, prefer) {
    const m = M(prefer || "ours");
    const merged = m.deck(clone(base), clone(ours), clone(theirs));
    m.conflicts.forEach((c) => { c.path = c.path.replace(/^\/+/, ""); });
    return { merged, conflicts: m.conflicts };
  }
  function describe(conflicts, limit = 8) {
    const out = conflicts.slice(0, limit).map((c) => `${c.path}: ${c.rule || "양쪽이 다르게 고침"} → ${c.kept === "ours" ? "보낸 쪽" : "파일 쪽"} 값을 남김`);
    if (conflicts.length > limit) out.push(`… 외 ${conflicts.length - limit}건`);
    return out;
  }
  // ---------------------------------------------------------------- 화면 도우미 - 편집기(studio.js)와 시트(sheet.js)가 같은 방식으로 쓴다
  // 실행 취소 기록은 "편집 앞" 문서 JSON 문자열의 쌓기다. 남의 변경이 들어오면 seal() 로 각 항목에 "편집 뒤"(a)를 붙여 {b, a} 로 바꾸고,
  // 되돌릴 때 undoTarget() 이 (편집 뒤 → 편집 앞) 차이만 지금 문서 위에 병합한다 - 그래서 Ctrl+Z 가 남의 변경을 되돌리지 않는다.
  /** 남의 변경을 받기 직전 - undo 기록의 항목마다 편집 뒤 상태를 붙인다(now = 받기 직전의 내 문서 JSON). redo 는 비운다 */
  function seal(undo, redo, now) {
    for (let k = 0; k < undo.length; k++) {
      if (typeof undo[k] !== "string") continue;
      const next = undo[k + 1];
      undo[k] = { b: undo[k], a: k + 1 < undo.length ? (typeof next === "string" ? next : next.b) : now };
    }
    if (redo) redo.length = 0;
  }
  /** 되돌린 뒤 문서 - 봉인 안 된 항목이면 그 문서 그대로, 봉인된 항목이면 지금 문서 위에 내 편집만 거꾸로 */
  function undoTarget(entry, nowJson) {
    if (typeof entry === "string") return JSON.parse(entry);
    return merge3(JSON.parse(entry.a), JSON.parse(entry.b), JSON.parse(nowJson), "ours").merged;
  }
  /** 병합 저장 응답을 받아 화면에 둘 문서 - 저장하는 사이 더 고친 것(now ≠ sent)이 있으면 병합 결과 위에 그것도 얹는다 */
  function afterSave(sentJson, nowJson, merged) {
    if (nowJson === sentJson) return merged;
    return merge3(JSON.parse(sentJson), JSON.parse(nowJson), merged, "ours").merged;
  }
  /** 병합 저장 알림 문구 - 충돌이 없으면 짧게, 있으면 몇 건·어느 쪽이 남았는지 */
  function notice(conflicts) {
    const n = (conflicts || []).length;
    if (!n) return { text: "그 사이 다른 곳(다른 창·AI)에서 바뀐 내용과 합쳐 저장했습니다", detail: "" };
    const mine = conflicts.filter((c) => c.kept === "ours").length;
    return { text: `그 사이 바뀐 내용과 합쳐 저장했습니다 · 같은 곳을 함께 고친 ${n}건은 ${mine === n ? "내 값" : mine ? `내 값 ${mine}건·상대 값 ${n - mine}건` : "상대 값"}으로 정했습니다`, detail: describe(conflicts, 12).join("\n") };
  }
  // ---------------------------------------------------------------- 작업(op) - 동시 편집 3-4. 서버 deckops.py 와 같은 규칙(골든 tests/deckops_cases.json)
  //   ops(old, new)              마지막 저장본 → 지금 문서의 차이를 작업 목록으로 - applyOps(old, ops(old, new)).doc 이 new 와 같다
  //   applyOps(doc, ops, base)   작업을 차례로 → { doc, applied, dropped: [{i, op, why}] } (서버가 지금 파일에 하는 것과 같다)
  const kindOf = (d) => (isObj(d) && d.kind === "sheet" ? "sheets" : "slides");
  const items = (l) => (Array.isArray(l) ? l.filter((x) => isObj(x) && x.id !== undefined && x.id !== null) : []);
  function props(o, n, skip) {
    o = isObj(o) ? o : {}; n = isObj(n) ? n : {};
    const keys = [...new Set([...Object.keys(n), ...Object.keys(o)])].sort();
    return keys.filter((k) => !skip.includes(k) && !eq(get(o, k), get(n, k))).map((k) => [k, get(n, k)]);
  }
  function setOp(b, k, v) { const o = { ...b, key: k }; if (v === MISSING) o.del = true; else o.value = clone(v); return o; }
  function listOps(old, nw, pre, idk, addOp, delOp, orderOp, inner) {
    const ops = [], oi = new Map(items(old).map((x) => [x.id, x])), ni = new Map(items(nw).map((x) => [x.id, x]));
    const nids = items(nw).map((x) => x.id);
    for (const x of items(old)) if (!ni.has(x.id)) ops.push({ op: delOp, ...pre, [idk]: x.id });
    const co = items(old).map((x) => x.id).filter((i) => ni.has(i)), cn = nids.filter((i) => oi.has(i));
    if (!eq(co, cn)) ops.push({ op: orderOp, ...pre, ids: cn });
    nids.forEach((i, n) => {
      if (!oi.has(i)) ops.push({ op: addOp, ...pre, [idk]: i, after: n ? nids[n - 1] : null, value: clone(ni.get(i)) });
      else ops.push(...inner(oi.get(i), ni.get(i)));
    });
    return ops;
  }
  function ops(old, nw) {
    old = isObj(old) ? old : {}; nw = isObj(nw) ? nw : {};
    const out = props(old, nw, ["updated", "slides", "sheets"]).map(([k, v]) => setOp({ op: "deck-set" }, k, v));
    if (kindOf(nw) === "sheets") {
      const tab = (a, b) => {
        const t = { tab: a.id };
        const o = props(a, b, ["id", "cells", "cols", "rows"]).map(([k, v]) => setOp({ op: "tab-set", ...t }, k, v));
        for (const [part, op] of [["cells", "cell"], ["cols", "cols"], ["rows", "rows"]]) o.push(...props(a[part] || {}, b[part] || {}, []).map(([k, v]) => setOp({ op, ...t }, k, v)));
        return o;
      };
      out.push(...listOps(old.sheets, nw.sheets, {}, "tab", "tab-add", "tab-del", "tabs-order", tab));
      if (!eq(old.slides || [], nw.slides || [])) out.push(setOp({ op: "deck-set" }, "slides", get(nw, "slides")));
      return out;
    }
    const slide = (a, b) => {
      const s = { slide: a.id };
      const o = props(a, b, ["id", "elements"]).map(([k, v]) => setOp({ op: "slide-set", ...s }, k, v));
      const el = (x, y) => {
        const e = { slide: a.id, el: x.id }, r = []; let geo = false;
        for (const [k, v] of props(x, y, ["id"])) { if (GEOM.includes(k)) geo = true; else r.push(setOp({ op: "set", ...e }, k, v)); }
        if (geo) r.unshift({ op: "set", ...e, key: "geom", value: Object.fromEntries(GEOM.filter((k) => k in y).map((k) => [k, y[k]])) });
        return r;
      };
      return o.concat(listOps(a.elements, b.elements, s, "el", "add", "del", "order", el));
    };
    return out.concat(listOps(old.slides, nw.slides, {}, "slide", "slide-add", "slide-del", "slides-order", slide));
  }
  const findId = (l, i) => (Array.isArray(l) ? l.find((x) => isObj(x) && x.id === i) : undefined) || null;
  function insertAfter(l, v, after) {
    const ids = l.map((x) => (isObj(x) ? x.id : undefined)); if (ids.includes(v.id)) return;
    l.splice(ids.includes(after) ? ids.indexOf(after) + 1 : after === null || after === undefined ? 0 : l.length, 0, v);
  }
  function reorder(l, ids) {
    const rank = new Map(ids.map((i, n) => [i, n])), has = (x) => isObj(x) && rank.has(x.id);
    const known = l.filter(has).sort((a, b) => rank.get(a.id) - rank.get(b.id)); let k = 0;
    return l.map((x) => (has(x) ? known[k++] : x));
  }
  function put(o, t) { if (o.del) delete t[o.key]; else t[o.key] = clone(o.value); }
  function applyOps(doc, list, base) {
    const out = clone(isObj(doc) ? doc : {}), key = kindOf(out), dropped = []; let applied = 0;
    (list || []).forEach((o, i) => { const why = apply1(out, key, o, base); if (why) dropped.push({ i, op: o.op, why }); else applied++; });
    return { doc: out, applied, dropped };
  }
  function revive(out, key, base, sid) {
    const bl = items((base || {})[key]), b = findId(bl, sid); if (!b) return null;
    const n = bl.map((x) => x.id).indexOf(sid);
    insertAfter(out[key] = out[key] || [], clone(b), n ? bl[n - 1].id : null);
    return findId(out[key], sid);
  }
  function apply1(out, key, o, base) {
    const op = o.op;
    if (op === "deck-set") { put(o, out); return null; }
    const unit = key === "sheets" ? "tab" : "slide";
    const lst = out[key] = Array.isArray(out[key]) ? out[key] : [];
    if (op === "slide-add" || op === "tab-add") { insertAfter(lst, clone(o.value), o.after); return null; }
    if (op === "slide-del" || op === "tab-del") { out[key] = lst.filter((x) => !(isObj(x) && x.id === o[unit])); return null; }
    if (op === "slides-order" || op === "tabs-order") { out[key] = reorder(lst, o.ids || []); return null; }
    let cur = findId(lst, o[unit]);
    if (!cur) { cur = revive(out, key, base, o[unit]); if (!cur) return `${key === "sheets" ? "탭" : "장"} ${o[unit]} 없음`; }  // 수정 > 삭제
    if (op === "slide-set" || op === "tab-set") { put(o, cur); return null; }
    if (key === "sheets") {
      const part = { cell: "cells", cols: "cols", rows: "rows" }[op]; if (!part) return `모르는 작업 ${op}`;
      put(o, cur[part] = isObj(cur[part]) ? cur[part] : {}); return null;
    }
    const els = cur.elements = Array.isArray(cur.elements) ? cur.elements : [];
    if (op === "add") { insertAfter(els, clone(o.value), o.after); return null; }
    if (op === "del") { cur.elements = els.filter((x) => !(isObj(x) && x.id === o.el)); return null; }
    if (op === "order") { cur.elements = reorder(els, o.ids || []); return null; }
    if (op !== "set") return `모르는 작업 ${op}`;
    let e = findId(els, o.el);
    if (!e) {  // 그 사이 지운 요소를 고쳤다 - 기준본에서 되살린다
      const bs = findId(items((base || {}).slides), o.slide), be = bs && findId(bs.elements, o.el);
      if (!be) return `요소 ${o.el} 없음`;
      const bel = bs.elements.filter(isObj).map((x) => x.id), n = bel.indexOf(o.el);
      insertAfter(els, clone(be), n ? bel[n - 1] : null); e = findId(els, o.el);
    }
    if (o.key === "geom") { for (const k of GEOM) { if (isObj(o.value) && k in o.value) e[k] = o.value[k]; else delete e[k]; } }
    else put(o, e);
    return null;
  }

  // ---------------------------------------------------------------- 저장 방식 고르기(3-4 다) - 화면 저장(studio.js·sheet.js)이 부른다
  //   planSave(saved, now, opt)  마지막 저장본·지금 문서(JSON 문자열) → { mode: "none" | "ops" | "put", ops?, bytes, why }
  //     작업 저장은 문서가 크고(opt.minBytes, 기본 200KB) 작업이 적을 때(opt.maxOps, 기본 200)만. 시트 행·열 구조 작업(opt.struct)이 있으면 PUT(__struct).
  //     작업을 저장본에 얹은 결과가 지금 문서와 다르면(같은 id 가 둘 등) PUT - 작업으로 잃는 것이 없게.
  //   saveOps(api, deckId, base, ops)  POST /api/ops → 응답 data, 서버가 모르거나(404·405) 거절하면(400) null - 그러면 화면은 PUT ?merge=1 로
  function planSave(saved, now, opt = {}) {
    const bytes = (now || "").length;
    if (!saved) return { mode: "put", bytes, why: "저장본 없음" };
    if (saved === now) return { mode: "none", bytes, why: "같음" };
    if (opt.struct && opt.struct.length) return { mode: "put", bytes, why: "구조 작업" };
    if (bytes < (opt.minBytes ?? 200000)) return { mode: "put", bytes, why: "작은 문서" };
    let a, b;
    try { a = JSON.parse(saved); b = JSON.parse(now); } catch (e) { return { mode: "put", bytes, why: "읽기 실패" }; }
    const list = ops(a, b);
    if (!list.length) return { mode: "none", bytes, why: "같음" };
    if (list.length > (opt.maxOps ?? 200)) return { mode: "put", bytes, why: `작업 ${list.length}개` };
    if (!eq(applyOps(a, list).doc, b)) return { mode: "put", bytes, why: "작업으로 같아지지 않음" };
    return { mode: "ops", ops: list, bytes, why: `작업 ${list.length}개` };
  }
  async function saveOps(api, deckId, base, list) {
    const r = await api("POST", `/api/ops/${encodeURIComponent(deckId)}`, { base: base || "", ops: list });
    if (r.ok && r.data && r.data.ok) return r.data;
    if ([400, 404, 405].includes(r.status)) return null;
    return { ok: false, status: r.status, error: (r.data && r.data.error) || r.status };
  }

  root.NexaMerge = { merge3, describe, eq, seal, undoTarget, afterSave, notice, ops, applyOps, planSave, saveOps };
})(typeof window !== "undefined" ? window : globalThis);
