/* nexa-slide 덱·시트 3-way 병합 - 서버 deckmerge.py 와 같은 규칙(docs/collab.md 1단계). 편집기·시트 화면이 같이 쓴다.
     NexaMerge.merge3(base, ours, theirs, prefer)  → { merged, conflicts }
   화면에서는 "남의 변경을 건드리지 않는 실행 취소"에 쓴다: 되돌릴 내 편집(편집 뒤 → 편집 앞)을 지금 문서 위에 병합한다.
   규칙·사례는 deckmerge.py 머리말과 tests/deckmerge_cases.json(tests/nexa_merge_check.js 가 같은지 확인). */
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
        const r = val(`${path}/${g.join("·")}`, pick(b), pick(o), pick(t));
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
  root.NexaMerge = { merge3, describe, eq };
})(typeof window !== "undefined" ? window : globalThis);
